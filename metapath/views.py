#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# Import PyQt5 classes
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWebKit import *
from PyQt5.QtNetwork import *
from PyQt5.QtWidgets import *
from PyQt5.QtWebKitWidgets import *
from PyQt5.QtPrintSupport import *

from collections import defaultdict

import os, urllib, urllib2, copy, re, json, importlib, sys

# MetaPath classes
import utils

import numpy as np

import data, config


# Translation (@default context)
from translate import tr


from numpy import arange, sin, pi
from backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

progname = os.path.basename(sys.argv[0])
progversion = "0.1"

        
# Web views default HTML
BLANK_DEFAULT_HTML = '''
<html>
<style>
    * {
        width:100%;
        height:100%;
        margin:0;
        background-color: #f5f5f5;
    }
</style>
<body>&nbsp;</body></html>
'''





# Handler for the views available for each app. Extended implementation of the QTabWidget
# to provide extra features, e.g. refresh handling, auto focus-un-focus, status color-hinting
class ViewManager( QTabWidget ):

    auto_unfocus_tabs = ['?']

    def __init__(self, parent, **kwargs):
        super(ViewManager, self).__init__(parent, **kwargs)
        self.w = parent
        self.m = parent.m
        self.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding )
            
        self.setDocumentMode(True)
        self.setTabsClosable(False)
        self.setTabPosition( QTabWidget.South )
        self.setMovable(True)
            
        self._unfocus_tabs_enabled = True
    
    def sizeHint(self):
        return self.w.size()
    
    # A few wrappers to 
    def addView(self, widget, name, source_data=None, focused=True, unfocus_on_refresh=False, **kwargs):
        widget.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding )
        # Automagically unfocus the help (+any other equivalent) tabs if were' refreshing a more interesting one
        widget._unfocus_on_refresh = unfocus_on_refresh
        t = super(ViewManager, self).addTab(widget, name, **kwargs)
        
        if source_data:
            self.source_data = source_data
            self.w.data.viewers[source_data].add( widget )

        return t
    
    def autoSelect(self):
        if self._unfocus_tabs_enabled:
            cw = self.currentWidget()
            if cw._unfocus_on_refresh:
                for w in range(0, self.count()):
                    uf = self.widget(w)._unfocus_on_refresh
                    if not uf and self.widget(w).isEnabled():
                        self.setCurrentIndex( w )
                        self._unfocus_tabs_enabled = False # Don't do this again (so user can select whatever they want)
                        break
                        

# Views for Svg/HTML based views (inc d3)
class RenderPageToFile(QWebPage): 
    def __init__(self, wv, fn, size=None, dpm=11811, resample=True): # 11811 == 300dpi
        super(RenderPageToFile, self).__init__()

        self.mainFrame().setScrollBarPolicy(Qt.Vertical, Qt.ScrollBarAlwaysOff)
        self.mainFrame().setScrollBarPolicy(Qt.Horizontal, Qt.ScrollBarAlwaysOff)

        #self.settings().setAttribute( QWebSettings.JavascriptEnabled,False)

        self.finished = False
            
        self.size = size if size != None else wv.size() 
        self.dpm = dpm
        self.resample = resample

        self.setViewportSize(self.size)
        self.loadFinished.connect(self._loadFinished)
        self.fn = fn
        
        c = wv.page().mainFrame().toHtml()
        c = c.replace('<html><head></head><body>','')
        c = c.replace('</body></html>','')
        if self.resample: # Remove drawn graph; we'll regenerate
            c = re.sub( '\<g.*\/g\>', '', c,  re.MULTILINE)
        else:
            # Keep graph but apply sizing; using svg viewport scaling
            # this is a bit hacky; rewriting the svg width/height parameters using regex
            c = re.sub( '(\<svg.*width=")([^"]*)(".*\>)', '\g<1>%d\g<3>' % self.size.width(), c)
            c = re.sub( '(\<svg.*height=")([^"]*)(".*\>)', '\g<1>%d\g<3>' % self.size.height(), c)
            
        self.mainFrame().setHtml( c )
    
    def _loadFinished(self, ok):

        frame = self.mainFrame()
        if self.resample: # If resampling we need to regenerate the graph
            frame.evaluateJavaScript( "_metapath_render_trigger();" )

        #self.size = frame.contentsSize()#        self.setViewportSize(self.size)
        image = QImage(self.size, QImage.Format_ARGB32)
        image.setDotsPerMeterX(self.dpm)
        image.setDotsPerMeterY(self.dpm)
        painter = QPainter(image)
        frame.render(painter)
        painter.end()

        image.save(self.fn)
        self.finished = True

class QWebPageExtend(QWebPage):
    def shouldInterruptJavascript():
        return False

class D3View(QWebView):

    d3_template = 'd3/figure.svg'
    # Signals
    source_updated = pyqtSignal()

    def __init__(self, parent, source_data = None, **kwargs):
        super(D3View, self).__init__(parent, **kwargs)        
        
        self.w = parent
        self.m = parent.m
        self.setPage( QWebPageExtend(self.w) )
        self.setHtml(BLANK_DEFAULT_HTML,QUrl("~"))
        
        self.source_data = source_data
        
        self.page().setContentEditable(False)
        self.page().setLinkDelegationPolicy( QWebPage.DelegateExternalLinks )
        self.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding )
        self.loadFinished.connect(self._loadFinished)
        
        # Override links for internal link cleverness
        if hasattr(self.w,'onBrowserNav'):
            self.onNavEvent = self.w.onBrowserNav
            self.linkClicked.connect( self.w.onBrowserNav )

        self.setContextMenuPolicy(Qt.CustomContextMenu) # Disable right-click

        # Lame        
        self.source_updated.connect( self.render )
    
    def sizeHint(self):
        if self.w:
            return self.w.size()
        else:
            return super(D3View, self).sizeHint()        

    def setSVG(self, svg):
        super(D3View, self).setHtml(svg, QUrl('file:///') )             
        
    def _loadFinished(self, ok):
        sizer = self.sizeHint()   
        self.page().currentFrame().addToJavaScriptWindowObject("QtWebView", self)
        self.page().currentFrame().evaluateJavaScript( "QtViewportSize={'x':%s,'y':%s};" % ( sizer.width()-30, sizer.height()-80 ) ) #-magic number for scrollbars (ugh)        
        self.page().currentFrame().evaluateJavaScript( "_metapath_render_trigger();" )
            
    @pyqtSlot(str)
    def delegateLink(self, url):
        self.onNavEvent( QUrl(url) )
        return True
        
    def saveAsImage(self, size=(800,600), dpm=11811, resample=True): # Size, dots per metre (for print), resample (redraw) image
        filename, _ = QFileDialog.getSaveFileName(self, 'Save current figure', '',  "Tagged Image File Format (*.tif);;\
                                                                                     Portable Network Graphics (*.png)")
        if filename:
            r = RenderPageToFile(self, filename, size, dpm, resample ) 
            while r.finished != True:
                QCoreApplication.processEvents()

    def render_to_svg(self, metadata):
        metadata['htmlbase'] = os.path.join( utils.scriptdir,'html')
        template = self.m.templateEngine.get_template(self.d3_template)
        self.setSVG(template.render( metadata ))

    def render(self):
        pass
        
    def render_updated(self):
        self.render() # Default to full re-render; override if possible



# Matplotlib-based views handler. Extend with render call for specific views (e.g. bar, scatter, heatmap)
class MplView(FigureCanvas):

    # Signals
    source_updated = pyqtSignal()

    """Ultimately, this is a QWidget (as well as a FigureCanvasAgg, etc.)."""
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        # We want the axes cleared every time plot() is called
        self.axes.hold(False)

        self.render_initial()

        FigureCanvas.__init__(self, fig)
        self.setParent(parent)

        FigureCanvas.setSizePolicy(self,
                                   QSizePolicy.Expanding,
                                   QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)
        
        # Lame        
        self.source_updated.connect( self.render )

    def render(self):
        pass

    def render_updated(self):
        self.render() # Default to full re-render; override if possible




class D3HomeView(D3View):

    d3_template = 'd3/workspace.svg'

    def render(self):
        objects = []
        for v in self.m.views:
            objects.append( (v.id, v) )

        inheritance = [] # Inter datasetmanager links; used for view hierarchy
        for v in self.m.views:
            # v.id = origin
            for i,ws in v.data.watchers.items():
                for w in ws:
                    inheritance.append( (v.id, w.v.id) ) # watcher->view->id
                    
        links = [] # Links inputs -> outputs (dso links)
        

        template = self.m.templateEngine.get_template(self.d3_template)
        self.setSVG(template.render( {'htmlbase': os.path.join( utils.scriptdir,'html'), 'objects':objects, 'inheritance':inheritance} )) 





class D3ForceView(D3View):
 
    def generate(self):
        current_pathways = [self.parent.db.pathways[p] for p in self.parent.config.value('/Pathways/Show').split(',') if p in self.parent.db.pathways]
        # Iterate pathways and get a list of all metabolites (list, for index)
        metabolites = []
        reactions = []
        metabolite_pathway_groups = {}
        for p in current_pathways:

            for r in p.reactions:
                ms = r.mtins + r.mtouts
                for m in ms:
                    if m not in metabolites:
                        metabolites.append(m)

                for m in ms:
                    metabolite_pathway_groups[m] = current_pathways.index(p)

                for mi in r.mtins:
                    for mo in r.mtouts:
                        reactions.append( [ metabolites.index(mi), metabolites.index(mo) ] )
                
        
        # Get list of all reactions
        # In template:
        # Loop metabolites (nodes; plus their groups)
    
    
        metadata = { 'htmlbase': os.path.join( utils.scriptdir,'html'),
                     'pathways':[self.parent.db.pathways[p] for p in self.parent.config.value('/Pathways/Show').split(',')],
                     'metabolites':metabolites,
                     'metabolite_pathway_groups':metabolite_pathway_groups, 
                     'reactions':reactions,
                     }
        template = self.parent.templateEngine.get_template(self.d3_template)

        self.setSVG(template.render( metadata ))


# D3 Based bargraph view
class D3BarView(D3View):

    d3_template = 'd3/bar.svg'


    def render(self): 
        # Source data in self.source_data as a list of interfaces
        dso = self.w.data.geto(self.source_data)
        fd = np.mean( dso.data, axis=0 )

        fdm = zip( dso.labels[1], fd )
        sms = sorted(fdm,key=lambda x: abs(x[1]), reverse=True )
        metabolites = [m for m,s in sms]

        # Get mean version of dataset (or alternative; +/- error)
        # Requires compressing dataset >1 for each alternative information set

        dso_mean = dso.as_summary( fn=np.mean, dim=0, match_attribs=['classes']) # Get mean dataset/ Classes only
        dso_std = dso.as_summary( fn=np.std, dim=0, match_attribs=['classes']) # Get std_dev/ Classes only
        
        classes = dso_mean.classes[0]
        groups = metabolites[:10]

        data = []
        for g in groups:
            
            data.append(
                ( g, 
                    {c: dso_mean.data[n, dso_mean.labels[1].index(g)] for n,c in enumerate(classes)},
                    {c: dso_std.data[n, dso_std.labels[1].index(g)] for n,c in enumerate(classes)} #2sd?
                     )
            )
    
        self.render_to_svg( {
            'figure':  {
                            'type':'bar',
                            'data': data,
                        },                        
        })


# D3 Based bargraph view
class D3SpectraView(D3View):

    d3_template = 'd3/spectra.svg'

    def render(self, metadata={}):
        # If we have scale data, enable and render the Viewer tab
        #FIXME: Must be along the top axis 
        if 'output' in self.data.o:
            dso = self.data.o['output']

            if float in [type(t) for t in dso.scales[1]]:
                self.tabs.setTabEnabled( self.viewer_tab_index, True)
            
                print "Scale data up top; make a spectra view"
                metadata['htmlbase'] = os.path.join( utils.scriptdir,'html')
            
                dso_z = zip( dso.scales[1], dso.entities[1], dso.labels[1] )

                # Compress data along the 0-dimensions by class (reduce the number of data series; too large)                
                dsot = dso.as_summary(dim=0, match_attribs=['classes'])

                # Copy to sort without affecting original
                scale = np.array(dso.scales[1])
                data = np.array(dsot.data)
                
                # Sort along x axis
                sp = np.argsort( scale )
                scale = scale[sp]
                data = data[:,sp]
                
                metadata['figure'] = {
                    'data':zip( scale, data.T ), # (ppm, [data,data,data])
                    'compounds': self.build_markers( dso_z, 1, self._build_entity_cmp ),
                    'labels': self.build_markers( dso_z, 2, self._build_label_cmp ),
                }

                template = self.m.templateEngine.get_template(self.d3_template)
                self.setSVG(template.render( metadata ))

        return
        

# D3 legacy figure views (single js/svg; needs extracting)
class D3LegacyView(D3View):

    d3_template = 'figure.svg'

    def render(self, metadata):
        if target == None:
            target = self.browser
            
        metadata['htmlbase'] = os.path.join( utils.scriptdir,'html')

        template = self.m.templateEngine.get_template(self.d3_template)
        self.setSVG(template.render( metadata ))


 

# Class for analysis views, using graph-based visualisations of defined datasets
# associated layout and/or analysis
class AnalysisHeatmapView(D3LegacyView):

    #self.build_heatmap_buckets( labelsX, labelsY, self.build_log2_change_table_of_classtypes( self.phosphate, labelsX ), remove_empty_rows=True, sort_data=True  )
    def build_heatmap_buckets(self, labelsX, labelsY, data, remove_empty_rows=False, remove_incomplete_rows=False, sort_data=False):
        buckets = []

        if remove_empty_rows:
            mask = ~np.isnan(data).all(axis=1)
            data = data[mask]
            labelsY = [l for l,m in zip(labelsY,mask) if m]

        elif remove_incomplete_rows:
            mask = ~np.isnan(data).any(axis=1)
            data = data[mask]
            labelsY = [l for l,m in zip(labelsY,mask) if m]


        # Broken, fix if needed
        #if remove_empty_cols:
        #    mask = ~np.isnan(data).all(axis=0)
        #    data = data.T[mask.T]
        #    labelsX = [l for l,m in zip(labelsX,mask) if m]

        if sort_data:
            # Preferable would be to sort by the total for each row
            # can then use that to sort the labels list also
            totals = np.ma.masked_invalid(data).sum(1).data # Get sum for rows, ignoring NaNs
            si = totals.argsort()[::-1]
            data = data[si] # Sort
            labelsY = list( np.array( labelsY )[si] ) # Sort Ylabels via numpy array.
        
        for x, xL in enumerate(labelsX):
            for y, yL in enumerate(labelsY):  

                if data[y][x] != np.nan:
                    buckets.append([ xL, yL, data[y][x] ] )

        return buckets    






class AnalysisCircosPathwayView(D3LegacyView):

    def generate(self):
        pathways = self.parent.db.pathways.keys()
        pathway_metabolites = dict()
        
        for k,p in self.parent.db.pathways.items():
            pathway_metabolites[p.id] = set( [m for m in p.metabolites] )

        data_m, labels_m = self.build_matrix(pathways, pathway_metabolites)

        pathway_reactions = dict()
        
        for k,p in self.parent.db.pathways.items():
            pathway_reactions[p.id] = set( [m for m in p.reactions] )

        data_r, labels_r = self.build_matrix(pathways, pathway_reactions)


        pathway_active_reactions = dict()
        pathway_active_metabolites = dict()
        active_pathways = [self.parent.db.pathways[p] for p in self.parent.config.value('/Pathways/Show').split(',')]
        active_pathways_id = []
        
        for p in active_pathways:
            pathway_active_reactions[p.id] = set( [r for r in p.reactions] )
            pathway_active_metabolites[p.id] = set( [r for r in p.metabolites] )
            active_pathways_id.append(p.id)
    

        data_ar, labels_ar = self.build_matrix(active_pathways_id, pathway_active_reactions)
        data_am, labels_am = self.build_matrix(active_pathways_id, pathway_active_metabolites)


        self.render( {
            'htmlbase': os.path.join( utils.scriptdir,'html'),
            'figures': [[
                        {
                            'type':'circos',
                            'data': data_ar,
                            'labels': labels_ar,
                            'n':1,  
                            'legend':('Metabolic pathway reaction interconnections','Links between pathways indicate proportions of shared reactions between the two pathways in MetaCyc database')                             
                        },
                        {
                            'type':'circos',
                            'data': data_am,
                            'labels': labels_am,
                            'n':2,  
                            'legend':('Metabolic pathway metabolite interconnections','Links between pathways indicate proportions of shared metabolites between the two pathways in MetaCyc database')
                        },                                             
                    ]],
                    }, debug=True)

    

    
