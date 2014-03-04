#!/usr/bin/env python
# -*- coding: utf-8 -*-



# Import Pyqt5.Qt5 classes
from . import qt5

from collections import defaultdict

import os, copy, re, json, importlib, sys, traceback

try:
    from urllib.request import urlopen
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse
    from urllib import urlopen

# Pathomx classes
from . import utils, threads

import numpy as np

from . import data, config


# Translation (@default context)
from .translate import tr


from numpy import arange, sin, pi
from .backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backend_bases import NavigationToolbar2
from matplotlib.figure import Figure
from matplotlib.colors import Colormap
import matplotlib.cm as cm

#import seaborn

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





# Handler for the views available for each app. Extended implementation of the qt5.QTabWidget
# to provide extra features, e.g. refresh handling, auto focus-un-focus, status color-hinting
class ViewManager( qt5.QTabWidget ):
    """ 
    Manager class for the tool views.
    
    Inherits from qt5.QTabWidget to focusing tabs on add and unfocus-on-refresh. The qt5.QTabWidget method
    is overridden to wrap addView. All other qt5.QTabWidget methods and attributes are available.
    """
    auto_unfocus_tabs = ['?']
    # Signals
    source_data_updated = qt5.pyqtSignal()
    updated = qt5.pyqtSignal()

    def __init__(self, parent, **kwargs):
        super(ViewManager, self).__init__()
        self.w = parent
        self.m = parent.m
        self.setSizePolicy( qt5.QSizePolicy.Expanding, qt5.QSizePolicy.Expanding )
            
        self.setDocumentMode(True)
        self.setTabsClosable(False)
        self.setTabPosition( qt5.QTabWidget.South )
        self.setMovable(True)
            
        self._unfocus_tabs_enabled = True
        
        self.data = dict() # Stores data from which figures are rendered
    
        self.source_data_updated.connect(self.onRefreshAll)
    
    # A few wrappers to 
    def addView(self, widget, name, focused=True, unfocus_on_refresh=False, **kwargs):
        '''
        Add a view to this view manager.

        Adds the specified widget to the ViewManager under a named tab.

        :param widget: The widget to add as a view.
        :type widget: object inherited from qt5.QWidget or views.BaseView
        :param name: The name of the widget, will be shown on the tab and used as a data-redirector selector.
        :type name: str
        :rtype: int tab/view index     
        '''
        widget.setSizePolicy( qt5.QSizePolicy.Expanding, qt5.QSizePolicy.Expanding )
        # Automagically unfocus the help (+any other equivalent) tabs if were' refreshing a more interesting one
        widget._unfocus_on_refresh = unfocus_on_refresh
        widget.vm = self
        widget.name = name
        t = super(ViewManager, self).addTab(widget, name, **kwargs)
        return t
    
    def onRefreshAll(self):
        for w in range(0, self.count()):
            if hasattr(self.widget(w),'autogenerate') and self.widget(w).autogenerate:
                try:
                    self.widget(w).autogenerate()
                except:
                    traceback.print_exc()
                    # Failure; disable the tab
                    self.setTabEnabled( w, False)
                else:
                    # Success; enable the tab
                    self.setTabEnabled( w, True)
        
    def addTab(self, widget, name, **kwargs):
        '''
        Overridden to redirect addTab calls to addView method. Do not use.
        '''
        self.addView(widget, name, **kwargs)
    
    def autoSelect(self):
        '''
        Autoselect one of the current views.

        Iterates through all current views and selects the first that is not flagged `_unfocus_on_refresh`. 
        This is used primarily to unfocus the help tabs following successful data calculation.
        '''    
        if self._unfocus_tabs_enabled:
            cw = self.currentWidget()
            if cw._unfocus_on_refresh:
                for w in range(0, self.count()):
                    uf = self.widget(w)._unfocus_on_refresh
                    if not uf and self.widget(w).isEnabled():
                        self.setCurrentIndex( w )
                        self._unfocus_tabs_enabled = False # Don't do this again (so user can select whatever they want)
                        break
         
class BaseView():
    """
    Base View prototype with stubs and data-handling functions that are generically useful.
    Sub-class from this if you want to create a new type of view, e.g. supporting an alternative
    graph rendering engine. If you just want to create a new graph-type you should sub-class
    from one of the backend specific stubs, e.g. MplView or D3View.
    """
        
    _offers_rerender_on_save = False
    is_floatable_view = False
    is_mpl_toolbar_enabled = False

    @property
    def data(self):
        return self.vm.data[ self.name ] 
        
    def autogenerate(self):
        self.generate( **self.vm.data[ self.name ] )

        
    def _build_entity_cmp(self,s,e,l):
        return e == None

    def _build_label_cmp(self,s,e,l):
        return e != None or l == None or str(s) == l

    def build_markers(self, zo, i, cmp_fn):
        accumulator = []
        last_v = None
        no = 0
        for n, (s,e,l) in enumerate(zo):
            v = zo[n][i]
            if cmp_fn(s, e, l):
                last_v = None
                continue
            no += 1
            if last_v == None or v != accumulator[-1][2]:
                accumulator.append( [s,s,v] )
            else:
                accumulator[-1][1] = s
            
            last_v = v
        
        print("%s reduced to %s" % ( no, len(accumulator) )) 
        return accumulator
        
        

# Views for Svg/HTML based views (inc d3)
class RenderPageToFile(qt5.QWebPage): 
    def __init__(self, wv, fn, settings): # 11811 == 300dpi
        super(RenderPageToFile, self).__init__()

        self.mainFrame().setScrollBarPolicy(qt5.Qt.Vertical, qt5.Qt.ScrollBarAlwaysOff)
        self.mainFrame().setScrollBarPolicy(qt5.Qt.Horizontal, qt5.Qt.ScrollBarAlwaysOff)

        #self.settings().setAttribute( qt5.QWebSettings.JavascriptEnabled,False)

        self.finished = False
            
        self.size = settings.get_pixel_dimensions()
        self.dpm = settings.get_dots_per_meter()
        self.resample = settings.get_resample()

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
            frame.evaluateJavaScript( "_pathomx_render_trigger();" )

        #self.size = frame.contentsSize()#        self.setViewportSize(self.size)
        image = qt5.QImage(self.size, qt5.QImage.Format_ARGB32)
        image.setDotsPerMeterX(self.dpm)
        image.setDotsPerMeterY(self.dpm)
        painter = qt5.QPainter(image)
        frame.render(painter)
        painter.end()

        image.save(self.fn)
        self.finished = True


class WebPageJSLog(qt5.QWebPage):
    """
    Redirects Javascript errors to the console (STDOUT) for debugging.
    """

    def __init__(self, parent=None, **kwargs):
        super(WebPageJSLog, self).__init__(parent, **kwargs)

    def javaScriptConsoleMessage(self, msg, lineNumber, sourceID):
        print("JsConsole(%s:%d): %s" % (sourceID, lineNumber, msg))

class QWebPageExtend(qt5.QWebPage):
    def shouldInterruptJavascript():
        return False


        
class TableView(qt5.QTableView):
    """
    Modified qt5.QTableView with additional metadata for internal use.
    """
    is_floatable_view = False
    is_mpl_toolbar_enabled = False

class WebView(qt5.QWebView, BaseView):
    """
    Modified qt5.QWebView with internal navigation handling, loadfinished-resize triggers
    for SVG, HTML, etc.
    """

    def __init__(self, parent, **kwargs):
        super(WebView, self).__init__(None, **kwargs)        
        
        self.w = parent
        self.m = parent.m
        self.setPage( WebPageJSLog(self.w) )
        self.setHtml(BLANK_DEFAULT_HTML,qt5.QUrl("~"))

        self.page().setContentEditable(False)
        self.page().setLinkDelegationPolicy( qt5.QWebPage.DelegateExternalLinks )
        self.setSizePolicy( qt5.QSizePolicy.Expanding, qt5.QSizePolicy.Expanding )
        self.loadFinished.connect(self._loadFinished)
        
        # Override links for internal link cleverness
        if hasattr(self.w,'onBrowserNav'):
            self.onNavEvent = self.w.onBrowserNav
            self.linkClicked.connect( self.delegateUrlWrapper )

        self.setContextMenuPolicy(qt5.Qt.CustomContextMenu) # Disable right-click

    
    def delegateUrlWrapper(self, url):
        if url.isRelative() and url.hasFragment(): # Fugly; use Jqt5.Query to scroll to anchors (qt5.Qt is broken if using setHtml)
            self.page().currentFrame().evaluateJavaScript("$('html,body').scrollTop( $(\"a[name='%s']\").offset().top );" % url.fragment()) 
        else:
            self.onNavEvent(url)
        
       
    def _loadFinished(self, ok):
        sizer = self.w.views.size()
        self.page().currentFrame().addToJavaScriptWindowObject("QtWebView", self)
        self.page().currentFrame().evaluateJavaScript( "QtViewportSize={'x':%s,'y':%s};" % ( sizer.width()-30, sizer.height()-80 ) ) #-magic number for scrollbars (ugh)        
        self.page().currentFrame().evaluateJavaScript( "_pathomx_render_trigger();" )

 
    def saveAsImage(self,settings): # Size, dots per metre (for print), resample (redraw) image
        filename, _ = qt5.QFileDialog.getSaveFileName(self, 'Save current figure', '',  "Tagged Image File Format (*.tif);;\
                                                                                     Portable Network Graphics (*.png)")
        if filename:
            r = RenderPageToFile(self, filename, settings ) 
            while r.finished != True:
                qt5.QCoreApplication.processEvents()
    
    def getSize(self):
        if self.w.size() == qt5.QSize(100,30):
            return self.w.sizeHint()
        else:
            return self.w.size()
                
    def sizeHint(self):
        return qt5.QSize(600,400)
            
    @qt5.pyqtSlot(str)
    def delegateLink(self, url):
        self.onNavEvent( qt5.QUrl(url) )
        return True
        
    def generate(self):
        pass


class D3View(WebView):

    """
    Modified qt5.QWebView (via WebView) with d3 generated SVG image saving handler.
    
    Use this as a basis for any custom d3-based rendering views.
    """

    d3_template = 'd3/figure.svg'
    _offers_rerender_on_save = True

    def setSVG(self, svg):
        super(D3View, self).setHtml(svg, qt5.QUrl('file:///') )             


    def generate_d3(self, metadata):
        metadata['htmlbase'] = os.path.join( utils.scriptdir,'html')
        template = self.m.templateEngine.get_template(self.d3_template)
        self.setSVG(template.render( metadata ))


class HTMLView(WebView):
    """
    Convenience wrapper for WebView for HTML viewing.
    """
    def __init__(self, parent, html=None, **kwargs):
        super(HTMLView, self).__init__(parent, **kwargs)        
        if html:
            self.generate(html)
    
    def generate(self, html):
        self.setHtml(html, qt5.QUrl('file:///')) 
        
class StaticHTMLView(HTMLView):
    """
    Convenience wrapper for WebView for HTML viewing of non-dynamic content.
    
    This is used for tool help files which do not need to refresh on data update.
    """
    autogenerate = False


class SVGView(D3View):
    
    def generate(self, svg):
        self.setSVG(svg)

class WheezyView(WebView):
    
    def generate(self, template, metadata={}):
        metadata['htmlbase'] = os.path.join( utils.scriptdir,'html')
        self.setHtml(template.render( metadata ),qt5.QUrl("~")) 


class MplNavigationHandler(NavigationToolbar2):
    def _init_toolbar(self):
        pass
        
    def draw_rubberband(self, event, x0, y0, x1, y1):
        height = self.canvas.figure.bbox.height
        y1 = height - y1
        y0 = height - y0

        w = abs(x1 - x0)
        h = abs(y1 - y0)

        rect = [int(val)for val in (min(x0, x1), min(y0, y1), w, h)]
        self.canvas.drawRectangle(rect)
        


# Matplotlib-based views handler. Extend with render call for specific views (e.g. bar, scatter, heatmap)
class MplView(FigureCanvas, BaseView):
    """
    Base class for matplotlib based views. This handles graph canvas setup, toolbar initialisation
    and figure save options. Subclass for your own graph-specific views.
    """
    is_floatable_view = True
    is_mpl_toolbar_enabled = True

    """Ultimately, this is a qt5.QWidget (as well as a FigureCanvasAgg, etc.)."""
    def __init__(self, parent, width=5, height=4, dpi=100, **kwargs):

        self.v = parent

        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.ax = self.fig.add_subplot(111)

        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        self.ax.get_xaxis().tick_bottom()
        self.ax.get_yaxis().tick_left()

        FigureCanvas.__init__(self, self.fig)

        self.setParent(parent.views)

        FigureCanvas.setSizePolicy(self,
                                   qt5.QSizePolicy.Expanding,
                                   qt5.QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)
        
        # Install navigation handler; we need to provide a qt5.Qt interface that can handle multiple 
        # plots in a window under separate tabs
        self.navigation = MplNavigationHandler( self )
        

    def generate(self):
        pass

    def saveAsImage(self, settings): # Size, dots per metre (for print), resample (redraw) image
        filename, _ = qt5.QFileDialog.getSaveFileName(self, 'Save current figure', '',  "Tagged Image File Format (*.tif);;\
                                                                                     Portable Document File (*.pdf);;\
                                                                                     Encapsulated Postscript File (*.eps);;\
                                                                                     Scalable Vector Graphics (*.svg);;\
                                                                                     Portable Network Graphics (*.png)")
                                                                                     
        if filename:
            size = settings.get_print_size('in')
            dpi = settings.get_dots_per_inch()
            prev_size = self.fig.get_size_inches()
            self.fig.set_size_inches(*size)
            
            self.fig.savefig(filename, dpi=dpi)
            self.fig.set_size_inches(*prev_size)
            self.redraw()
            
    def redraw(self):
        #FIXME: Ugly hack to refresh the canvas
        self.resize( self.size() - qt5.QSize(1,1) )
        self.resize( self.size() + qt5.QSize(1,1) )
        
    def resizeEvent(self,e):
        FigureCanvas.resizeEvent(self,e)
            
    
class D3PrerenderedView(D3View):
    
    def generate(self, metadata, template):
        self.d3_template = template
        self.generate_d3( metadata )
    

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
class D3SpectraView(D3View):

    d3_template = 'd3/spectra.svg'

    def generate(self, dso=None):
        if not float in [type(t) for t in dso.scales[1]]:   
            assert False # Can't continue
            
        # If we have scale data, enable and render the Viewer tab
        #FIXME: Must be along the top axis 
        print("Scale data up top; make a spectra view")
        metadata = {'htmlbase': os.path.join( utils.scriptdir,'html')}
    
        dso_z = list(zip( dso.scales[1], dso.entities[1], dso.labels[1] ))

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
            'data':list(zip( scale, data.T )), # (ppm, [data,data,data])
            'compounds': self.build_markers( dso_z, 1, self._build_entity_cmp ),
            'labels': self.build_markers( dso_z, 2, self._build_label_cmp ),
        }

        template = self.m.templateEngine.get_template(self.d3_template)
        self.setSVG(template.render( metadata ))
        

class MplSpectraView(MplView):
    """
    A matplotlib-based spectra-like lineplot viewer, particular suited to NMR-like spectra.
    
    To be extended/replaced to support more generic uses (and general line-chart plotting).
    Plots different classes in the data as distinct lines (coloured).
    """
    def __init__(self, parent, **kwargs):
        super(MplSpectraView, self).__init__(parent, **kwargs)        
        self.ax.invert_xaxis()
        

    def generate(self, dso=None):
        if not float in [type(t) for t in dso.scales[1]]:   
            # Add fake axis scale for plotting
            dso.scales[1] = list(range( len(dso.scales[1])))
            
        #FIXME: Should probably be somewhere else. Label up the top 50    
        wmx = np.amax( np.absolute( dso.data), axis=0 )
        dso_z = list(zip( dso.scales[1], dso.entities[1], dso.labels[1] ))
        dso_z = sorted( zip( dso_z, wmx ), key=lambda x: x[1])[-20:] # Top 50
        dso_z = [x for x, wmx in dso_z ]    

        print(dso_z)
        
        # Compress data along the 0-dimensions by class (reduce the number of data series; too large)                
        dsot = dso.as_summary(dim=0, match_attribs=['classes'])

        # Copy to sort without affecting original
        scale = np.array(dso.scales[1])
        data = np.array(dsot.data)
        
        # Sort along x axis
        sp = np.argsort( scale )
        scale = scale[sp]
        data = data[:,sp]


        self.ax.cla()

        self.ax.plot(scale, data.T, linewidth=0.75)

        for c in self.build_markers( dso_z, 1, self._build_entity_cmp ):
            self.ax.axvspan( c[0], c[1], facecolor='#dddddd', edgecolor='#dddddd', linewidth=0.5)
            self.ax.text( (c[0]+c[1])/2, self.ax.get_ylim()[1], c[2], rotation='60', rotation_mode='anchor', color='#dddddd', size=6.5)

        #for c in self.build_markers( dso_z, 2, self._build_label_cmp ):
        #    self.ax.axvspan( c[0], c[1], facecolor='#eeeeee', edgecolor='#eeeeee', linewidth=0.5)
        #    self.ax.text( (c[0]+c[1])/2, self.ax.get_ylim()[1], c[2], rotation='60', rotation_mode='anchor', color='#eeeeee', size=6.5)

        self.ax.set_xlabel('ppm')
        self.ax.set_ylabel('Rel')
                
        self.draw()
                
        
        
        
class D3DifferenceView(D3View):
    """
    A matplotlib-based difference-lineplot viewer.
    
    Takes two inputs - line A and B and plots both, highlighting the regions where they differ.
    """
    
    d3_template = 'd3/difference.svg'
    
    def generate(self, dso_a, dso_b):
        metadata = {'htmlbase': os.path.join( utils.scriptdir,'html')}
        
        # Get common scales
        datai = np.mean( dso_a.data, 0) # Mean flatten
        datao = np.mean( dso_b.data, 0) # Mean flatten
        
        # Interpolate the data for shorter set
        if len(datao) < len(datai):
            datao = np.interp( dso_a.scales[1], dso_b.scales[1], datao)

        metadata['figure'] = {
            'data':list(zip( dso_a.scales[1], datai.T, datao.T )), # (ppm, [dataa,datab])
        }
        
        template = self.m.templateEngine.get_template(self.d3_template)
        self.setSVG(template.render( metadata ))
        
        
class MplDifferenceView(MplSpectraView):

    def generate(self, dso_a, dso_b):

        # Get common scales
        datai = np.mean( dso_a.data, 0) # Mean flatten
        datao = np.mean( dso_b.data, 0) # Mean flatten
        
        # Interpolate the data for shorter set
        if len(datao) < len(datai):
            datao = np.interp( dso_a.scales[1], dso_b.scales[1], datao)
        
        x  = dso_a.scales[1]
        y1 = datai.T
        y2 = datao.T

        self.ax.cla()
        self.ax.plot(x, y2, color='black', linewidth=0.25)
        self.ax.fill_between(x, y1, y2, where=y2>=y1, facecolor=utils.category10[0], interpolate=True)
        self.ax.fill_between(x, y1, y2, where=y2<=y1, facecolor=utils.category10[1], interpolate=True)
        
        self.ax.set_xlabel('ppm')
        self.ax.set_ylabel('Rel')
        
        self.draw()
        
# D3 legacy figure views (single js/svg; needs extracting)
class D3LegacyView(D3View):

    d3_template = 'figure.svg'

    def generate(self, metadata):

        metadata['htmlbase'] = os.path.join( utils.scriptdir,'html')

        template = self.m.templateEngine.get_template(self.d3_template)
        self.setSVG(template.render( metadata ))




class MplScatterView(MplView):
    """
    A matplotlib-based scatter plot.
    
    Plots classes on a unified X,Y scatter plot.
    """
    def __init__(self, parent, **kwargs):
        super(MplScatterView, self).__init__(parent, **kwargs)        

    def generate(self, dso=None): #figure_data
        """
        Generate an XY scatter plot from source dataset object.

        :param dso: The dataset object to plot consisting of two columns (X, Y) of data.
                    Multiple classes of data can be supplied as indicated by the axis 0 class list.
        :type dso: DataSet object
        """
        self.ax.cla()
        sp = {}
        colors = self.ax._get_lines.color_cycle

        # Scores dso is no_of_samples x no_of_series (axes) ; only plot first two
        # Group plotting by classes (if no class; will be single plot)
        
        classes = dso.classes_l[0]
        for c in classes:
            df = dso.as_filtered(dim=0,classes=[c])
            sp[c] = self.ax.scatter(df.data[:,0], df.data[:,1], c=next(colors) )

        self.ax.legend(list(sp.values()),
           list(sp.keys()),
           scatterpoints=1,
           loc='upper left', bbox_to_anchor=(1, 1))
           
        self.ax.set_xlabel(dso.labels[1][0])
        self.ax.set_ylabel(dso.labels[1][1])

        # Square the plot
        x0,x1 = self.ax.get_xlim()
        y0,y1 = self.ax.get_ylim()           
        self.ax.set_aspect((x1-x0)/(y1-y0))
        self.draw()
                



 

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







# D3 Based bargraph view
class D3CircosView(D3View):

    d3_template = 'd3/circos.svg'

    def generate(self, dso=None):
        print(dso)

        self.generate_d3( {
            'figure': {
                            'type':'circos',
                            'data': dso.data,
                            'labels': dso.labels[1],
                            'n':1,  
                            'legend':('Metabolic pathway reaction interconnections','Links between pathways indicate proportions of shared reactions between the two pathways in MetaCyc database')                             
                        },
                    })
        


class AnalysisCircosPathwayView(D3LegacyView):

    def generate(self):
        pathways = list(self.parent.db.pathways.keys())
        pathway_metabolites = dict()
        
        for k,p in list(self.parent.db.pathways.items()):
            pathway_metabolites[p.id] = set( [m for m in p.metabolites] )

        data_m, labels_m = self.build_matrix(pathways, pathway_metabolites)

        pathway_reactions = dict()
        
        for k,p in list(self.parent.db.pathways.items()):
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

    
class AppView(HTMLView):
    pass
    
    
    


# D3 Based bargraph view
class D3BarView(D3View):

    d3_template = 'd3/bar.svg'

    def generate(self, dso): 
        fd = np.mean( dso.data, axis=0 )

        fdm = list(zip( dso.labels[1], fd ))
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
    
        self.generate_d3( {
            'figure':  {
                            'type':'bar',
                            'data': data,
                        },                        
        })

    
class MplCategoryBarView(MplView):

    def generate(self,dso):
        # Build x positions; we're grouping by X (entity) then plotting the classes
        self.ax.cla()
        
        limit_to = 10
        colors = self.ax._get_lines.color_cycle

        # FIXME: Remove this once UI allows selection of data to plot
        fd = np.mean( dso.data, axis=0 )
        fdm = list(zip( dso.labels[1], fd ))
        sms = sorted(fdm,key=lambda x: abs(x[1]), reverse=True )
        labels = [m for m,s in sms]
        
        sp = {}
        classes = dso.classes[0]
        #labels = [e if e != None else dso.labels[1][n] for n,e in enumerate(dso.entities[1][0:limit_to]) ]
        #data = dso.data[:,0:limit_to]
        data = np.array( [ dso.data[ :, dso.labels[1].index( l ) ] for l in labels ] ).T[:,:limit_to]

        #0,1,-,4,5,-,6,7
        
        # 2 classes
        # 3 data points
        
        # 3*2 = 6;  3*(2+1) = 9
        
        # Build spaced sets (around middle value)
        # 0 -0.5->+0.5, 

        xa = []        
        for n,ag in enumerate( data.T ): # Axis groups (can reverse with classes; later)
            xa.append( np.arange(0, len(classes) ) + n*(len(classes)+1) ) # Build table
            
        x = np.array(xa).reshape( len(data.T), len(classes) )
                
        self.ax.set_xlim( np.min(x)-1, np.max(x)+1 )
                  
        for n,c in enumerate(classes):
            cdata = data[n]
            if 'error' in dso.statistics:
                err = dso.statistics['error']['stddev'][:,:limit_to][n]
                yperr = [(0,1)[e>0] for e in cdata ]
                ynerr = [(0,1)[e<0] for e in cdata ]
                
                yperr = np.array(yperr) * err
                ynerr = np.array(ynerr) * err
                yerr = (ynerr, yperr)
            else:
                yerr = None
                
            print(yerr)

            color = next(colors)
            sp[c] = self.ax.bar(x[:,n], cdata, align='center', color=color, yerr=yerr, ecolor=color )

        xticks = np.mean(x,axis=1)
        self.ax.set_xticks( xticks )
        self.ax.set_xticklabels(labels, rotation=45, ha='right', rotation_mode='anchor' )

        self.ax.legend(list(sp.values()),
           list(sp.keys()),
           scatterpoints=1,
           loc='upper left', bbox_to_anchor=(1, 1))
           
        #if options.title:
        #    self.ax.title(options.title)
        #else:
        #    self.ax..title(metabolite)
    
        #plt.gca().xaxis.set_label_text(options.xlabel)
        #plt.gca().yaxis.set_label_text(options.ylabel)
    
        # Add some padding either side of graphs
        #plt.xlim( ind[0]-1, ind[-1]+1)
    
        
        self.draw()
        
class MplHeatmapView(MplView):
    """
    A matplotlib-based heatmap plotter.
    
    Plots heatmap data of measurements against class groupings.
    """

    def __init__(self, parent, **kwargs):
        super(MplHeatmapView, self).__init__(parent, **kwargs)        
        self.ax.spines['top'].set_visible(True)
        self.ax.spines['bottom'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        self.ax.get_xaxis().tick_top()

    def generate(self, dso=None):
        # Note that DSO is output as provided (axis 0 vertical, axis 1 along top)
        # Build x positions; we're grouping by X (entity) then plotting the classes
        self.ax.cla()
        
        limit_to = 10
        ylim = np.max( np.abs( dso.data) )
        # Check if we have zero-range data, and adjust the limit to paint white instead of blue
        if ylim == 0:
            ylim = 1
            
        self.ax.imshow( dso.data, interpolation='none', aspect='auto', vmin=-ylim, vmax=+ylim, cmap=cm.bwr)

        self.ax.set_xticks( list(range( dso.shape[1])) )
        self.ax.set_yticks( list(range( dso.shape[0])) )
        self.ax.set_yticklabels( dso.labels[0], size=7 )
        self.ax.set_xticklabels( dso.labels[1], rotation=60, rotation_mode='anchor', ha="left", size=7 )
    
        
        self.draw()
        
