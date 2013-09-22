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

from yapsy.PluginManager import PluginManager, PluginManagerSingleton
import plugins

import os, urllib, urllib2, copy, re

# MetaPath classes
import utils

import numpy as np

import data


# GENERIC CONFIGURATION AND OPTION HANDLING

# Generic configuration dialog handling class
class genericDialog(QDialog):
    def __init__(self, parent, **kwargs):
        super(genericDialog, self).__init__(parent, **kwargs)        

        self.sizer = QVBoxLayout()
        self.layout = QVBoxLayout()
        
        # Setup default button configurations etc.
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
                
    def dialogFinalise(self):
        self.sizer.addLayout(self.layout)
        self.sizer.addWidget(self.buttonBox)
    
        # Set dialog layout
        self.setLayout(self.sizer)

    def setListControl(self, control, list, checked):
        # Automatically set List control checked based on current options list
        items = control.GetItems()
        try:
            idxs = [items.index(e) for e in list]
            for idx in idxs:
                if checked:
                    control.Select(idx)
                else:
                    control.Deselect(idx)
        except:
            pass
            


class RenderPageToFile(QWebPage):
    def __init__(self, fn, wv):
        super(RenderPageToFile, self).__init__()

        self.mainFrame().setScrollBarPolicy(Qt.Vertical, Qt.ScrollBarAlwaysOff)
        self.mainFrame().setScrollBarPolicy(Qt.Horizontal, Qt.ScrollBarAlwaysOff)

        self.settings().setAttribute( QWebSettings.JavascriptEnabled,False)

        self.finished = False
        self.size = wv.size()
        
        self.loadFinished.connect(self._loadFinished)
        self.fn = fn

        c = wv.page().mainFrame().toHtml()
        c = c.replace('<html><head></head><body>','')
        c = c.replace('</body></html>','')
        self.mainFrame().setHtml( c )
    
    def _loadFinished(self, ok):
        frame = self.mainFrame()
        self.size = frame.contentsSize()#        self.setViewportSize(self.size)
        self.setViewportSize(self.size)
        image = QImage(self.size, QImage.Format_ARGB32)
        image.setDotsPerMeterX(11811)
        image.setDotsPerMeterY(11811)
        painter = QPainter(image)
        frame.render(painter)
        painter.end()

        image.save(self.fn)
        self.finished = True

class QWebPageJSLog(QWebPage):
    """
    Makes it possible to use a Python logger to print javascript console messages
    """
    def __init__(self, parent=None, **kwargs):
        super(QWebPageJSLog, self).__init__(parent, **kwargs)

    def javaScriptConsoleMessage(self, msg, lineNumber, sourceID):
        print "JsConsole(%s:%d): %s" % (sourceID, lineNumber, msg)


class QWebViewExtend(QWebView):

    def __init__(self, parent, onNavEvent=None, **kwargs):
        super(QWebViewExtend, self).__init__(parent, **kwargs)        
        
        self.w = parent
        #self.js_page_object = QWebPageJSLog()
        #self.setPage( self.js_page_object)
        self.page().setContentEditable(False)
        self.page().setLinkDelegationPolicy( QWebPage.DelegateExternalLinks )
        self.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding )
        self.loadFinished.connect(self._loadFinished)

        # Override links for internal link cleverness
        if onNavEvent:
            self.onNavEvent = onNavEvent
            self.linkClicked.connect( self.onNavEvent )

        self.setContextMenuPolicy(Qt.CustomContextMenu) # Disable right-click
    
    def sizeHint(self):
        if self.w:
            return self.w.size()
        else:
            return super(QWebViewExtend, self).sizeHint()        
    
    def _loadFinished(self):
        frame = self.page().mainFrame()
        frame.addToJavaScriptWindowObject("QtWebView", self)
        if self.w:
            x = self.w.size().width()-30
            y = self.w.size().height()-100
            self.page().setViewportSize( QSize(x,y) ) # Hacky weirdness needed in Qt5 for rendering non-focused tabs
            frame.evaluateJavaScript( "QtViewportSize={'x':%s,'y':%s}" % (x,y) ) #-magic number for tabs (ugh)
                
    @pyqtSlot(str)
    def delegateLink(self, url):
        self.onNavEvent( QUrl(url) )
        return True

    def saveAsImage(self, fn):
        filename, _ = QFileDialog.getSaveFileName(self, 'Save current figure', '',  "Tagged Image File Format (*.tif);;\
                                                                                     Portable Network Graphics (*.png)")
        if filename:
            r = RenderPageToFile(filename, self ) 
            while r.finished != True:
                QCoreApplication.processEvents()
                

class QWebViewScrollFix(QWebViewExtend):
    
    def __init__(self, parent, onNavEvent=None, **kwargs):
        super(QWebViewScrollFix, self).__init__(parent, onNavEvent=onNavEvent, **kwargs)        

        

#We ran into the same issue. We worked around the problem by overriding QWebView::wheelEvent, and doing the following:
#When a wheelEvent comes in, we start a 25 ms single-shot timer and process the wheelEvent. For any future wheelEvent's that come in while the timer is active, we just accumulate the event->delta( )'s (and pos & globalPos values, too). When the timer finally fires, the accumulated deltas are packaged into a QWheelEvent and delivered to QWebView::wheelEvent. (One further refinement is that we only do this for wheelEvents that have NoButton and NoModifier.)


# View Dialogs

class DialogDataSource(genericDialog):
    def __init__(self, parent=None, view=None, **kwargs):
        super(DialogDataSource, self).__init__(parent, **kwargs)        
        
        self.v = view
        self.m = view.m
        
        self.setWindowTitle("Select Data Source(s)")

        self.lw_sources = QTreeWidget() # Use TreeWidget but flat; for multiple column view
        self.lw_sources.setColumnCount(6)
        self.lw_sources.setHeaderLabels(['','Source','Data','Entities', 'Size']) #,'#'])
        self.lw_sources.setUniformRowHeights(True)
        self.lw_sources.rootIsDecorated()
        self.lw_sources.hideColumn(0)                
        
        datasets = self.m.datasets # Get a list of dataset objects to test
        self.datasets = []
        
        print "Datasets:", self.m.datasets
        for dataset in datasets:
            if self.v.data.can_consume(dataset):
                self.datasets.append( dataset )
                
                print "+", dataset
                #QListWidgetItem(dataset.name, self.lw_sources)
                tw = QTreeWidgetItem()

                tw.setText(0, str( len(self.datasets)-1) ) # Store index
                tw.setText(1, dataset.manager.v.name )
                if dataset.manager.v.plugin.workspace_icon:
                    tw.setIcon(1, dataset.manager.v.plugin.workspace_icon )

                tw.setText(2, dataset.name)
                e = set()
                for el in dataset.entities_t:
                    e |= set(el) # Add entities to the set
                e.remove('NoneType')
                tw.setText(3, ', '.join( e ) )

                tw.setText(4, 'x'.join( [str(s) for s in dataset.shape ] ) )
                
                self.lw_sources.addTopLevelItem(tw) 

        for c in range(5):
            self.lw_sources.resizeColumnToContents(c)
        
        self.layout.addWidget(self.lw_sources)
        self.setMinimumSize( QSize(600,100) )
        self.layout.setSizeConstraint(QLayout.SetMinimumSize)
        
        # Build dialog layout
        self.dialogFinalise()




#### View Object Prototypes (Data, Assignment, Processing, Analysis, Visualisation) e.g. used by plugins
class GenericView( QMainWindow ):
    def __init__(self, plugin, parent, **kwargs):
        super(GenericView, self).__init__(parent, **kwargs)
    
        self.plugin = plugin
        self.m = parent
        self.id = str( id( self ) )
        self.data = data.DataManager(self.m, self)
        self.name = self.m.plugin_names[ self.plugin.__class__.__module__ ] 

        #self.w = QMainWindow()
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setTabsClosable(False)
        self.tabs.setTabPosition( QTabWidget.South )
        
        self.toolbars = {}
        self.controls = defaultdict( dict ) # Store accessible controls

        self.setCentralWidget(self.tabs)
        
        self.config = QSettings()
        
        self.workspace_item = self.m.addWorkspaceItem(self, self.plugin.default_workspace_category, self.name, is_selected=True, icon=self.plugin.workspace_icon) #, icon = None)
        

    def render(self, metadata):
        return
    
    def generate(self):
        return
    
    
        printAction = QAction(QIcon.fromTheme("document-print", QIcon( os.path.join( utils.scriptdir, 'icons', 'printer.png') )), u'&Print\u2026', self)
        printAction.setShortcut('Ctrl+P')
        printAction.setStatusTip('Print current metabolic pathway')
        printAction.triggered.connect(self.onPrint)
        self.menuBar['file'].addAction(printAction)
        
    def set_name(self, name):
        self.name = name
        try:
            self.workspace_item.setText(0, name)
        except:
            pass

    def setWorkspaceStatus(self, status):
        self.m.setWorkspaceStatus( self.workspace_item, status)

    def clearWorkspaceStatus(self):
        self.m.clearWorkspaceStatus( self.workspace_item )


    def addDataToolBar(self):            
        t = self.addToolBar('Data')
        t.setIconSize( QSize(16,16) )

        select_dataAction = QAction( QIcon( os.path.join(  utils.scriptdir, 'icons', 'database-import.png' ) ), 'Select a data source\u2026', self.m)
        select_dataAction.setStatusTip('Select a compatible data source')
        select_dataAction.triggered.connect(self.onSelectDataSource)
        t.addAction(select_dataAction)

        select_dataAction = QAction( QIcon( os.path.join(  utils.scriptdir, 'icons', 'arrow-circle-double.png' ) ), 'Recalculate', self.m)
        select_dataAction.setStatusTip('Recalculate')
        select_dataAction.triggered.connect(self.onRecalculate)
        t.addAction(select_dataAction)
        
        self.toolbars['image'] = t        

        
    def onSelectDataSource(self):
        # Basic add data source dialog. Extend later for multiple data sources etc.
        """ Open the mining setup dialog to define conditions, ranges, class-comparisons, etc. """
        dialog = DialogDataSource(parent=self, view=self)
        ok = dialog.exec_()
        if ok:
            for i in dialog.lw_sources.selectedItems():
                dso = dialog.datasets[ int( i.text(0) ) ]
                self.data.consume( dso )

            self.generate()

    def addFigureToolBar(self):            
        t = self.addToolBar('Image')
        t.setIconSize( QSize(16,16) )

        export_imageAction = QAction( QIcon( os.path.join(  utils.scriptdir, 'icons', 'image-export.png' ) ), 'Export current figure as image\u2026', self.m)
        export_imageAction.setStatusTip('Export figure to image')
        export_imageAction.triggered.connect(self.onSaveImage)
        t.addAction(export_imageAction)
        
        self.toolbars['image'] = t

    def onSaveImage(self):
        # Get currently selected webview
        self.tabs.currentWidget().saveAsImage('/Users/mxf793/Desktop/test.tiff')        


    def onRecalculate(self):
        self.generate()



# Data view prototypes

class DataView(GenericView):
    def __init__(self, plugin, parent, **kwargs):
        super(DataView, self).__init__(plugin, parent, **kwargs)

        self.summary = QWebViewScrollFix(self.tabs)
        self.table = QTableView()
        self.viewer = QWebViewScrollFix(self.tabs, onNavEvent=self.m.onBrowserNav) # Optional viewer; activate only if there is scale data

        self.tabs.addTab(self.summary, 'Summary')
        self.tabs.addTab(self.table,'Table')
        self.viewer_tab_index = self.tabs.addTab(self.viewer,'View')
        self.tabs.setTabEnabled( self.viewer_tab_index, False)
    
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
        
        print "%s reduced to %s" % ( no, len(accumulator) ) 
        return accumulator
        

    def render(self, metadata):
        # If we have scale data, enable and render the Viewer tab
        #FIXME: Must be along the top axis 
        if 'output' in self.data.o:
            dso = self.data.o['output']
            self.data.o['output'].as_table.refresh()

            if float in [type(t) for t in dso.scales[1]]:
                self.tabs.setTabEnabled( self.viewer_tab_index, True)
            
                print "Scale data up top; make a spectra view"
                metadata['htmlbase'] = os.path.join( utils.scriptdir,'html')
            
                dso_z = zip( dso.scales[1], dso.entities[1], dso.labels[1] )
                
                # Copy to sort without affecting original
                scale = np.array(dso.scales[1])
                data = np.array(dso.data)
                
                # Sort along x axis
                sp = np.argsort( scale )
                scale = scale[sp]
                data = data[:,sp]
                
                metadata['figure'] = {
                    'data':zip( scale, data.T ), # (ppm, [data,data,data])
                    'compounds': self.build_markers( dso_z, 1, self._build_entity_cmp ),
                    'labels': self.build_markers( dso_z, 2, self._build_label_cmp ),
                }

                template = self.m.templateEngine.get_template('d3/spectra.svg')
                self.viewer.setHtml(template.render( metadata ),QUrl('~')) 
                
                f = open('/Users/mxf793/Desktop/test3.svg','w')
                f.write( template.render( metadata ) )
                f.close()
            
        return

# Import Data viewer

class ImportDataView( DataView ):

    import_type = 'Data'
    import_filename_filter = "All Files (*.*);;"
    import_description =  "Open experimental data from file"

    def __init__(self, plugin, parent, **kwargs):
        super(ImportDataView, self).__init__(plugin, parent, **kwargs)
    
        self.data.addo('output') # Add output slot
        self.data.o['output'].data = np.zeros((10,10))
        self.table.setModel(self.data.o['output'].as_table)
        
        t = self.addToolBar('Data Import')
        t.setIconSize( QSize(16,16) )

        import_dataAction = QAction( QIcon( os.path.join(  utils.scriptdir, 'icons', 'disk--arrow.png' ) ), 'Import from file\u2026', self.m)
        import_dataAction.setStatusTip('Import from a compatible file source')
        import_dataAction.triggered.connect(self.onImportData)
        t.addAction(import_dataAction)
        
        self.toolbars['data_import'] = t
        
        fn = self.onImportData()

    def onImportData(self):
        """ Open a data file"""
        filename, _ = QFileDialog.getOpenFileName(self.m, self.import_description, '', self.import_filename_filter)
        if filename:

            self.load_datafile( filename )

            self.file_watcher = QFileSystemWatcher()            
            self.file_watcher.fileChanged.connect( self.onFileChanged )
            self.file_watcher.addPath( filename )

            self.render({})
            
            self.workspace_item.setText(0, os.path.basename(filename))
            
        return False
        
    def onFileChanged(self, file):
        self.load_datafile( file )




# Analysis/Visualisation view prototypes


# Class for analysis views, using graph-based visualisations of defined datasets
# associated layout and/or analysis
class AnalysisView(GenericView):
    def __init__(self, plugin, parent, **kwargs):
        super(AnalysisView, self).__init__(plugin, parent, **kwargs)

        self.browser = QWebViewScrollFix( self, onNavEvent=parent.onBrowserNav )
        self.browser2 = QWebViewScrollFix( self, onNavEvent=parent.onBrowserNav )
        self.tabs.addTab(self.browser, 'View')
        self.tabs.addTab(self.browser2, 'View2')
    
    def render(self, metadata):
        metadata['htmlbase'] = os.path.join( utils.scriptdir,'html')

        template = self.m.templateEngine.get_template('d3/figure.svg')
        self.browser.setHtml(template.render( metadata ),QUrl('~')) 

        self.browser2.setHtml(template.render( metadata ),QUrl('~')) 
        
        f = open('/Users/mxf793/Desktop/test.svg','w')
        f.write( template.render( metadata ) )
        f.close()
        
    #self.build_log2_change_table_of_classtypes( self.phosphate, labelsX )
    def build_log2_change_table_of_classtypes(self, objs, classes):
        dso = self.data.i['input']
        
        # Reduce dimensionality; combine all class/entity objects via np.mean()
        dso = dso.as_summary()
        
        entities = []
        for o in objs:
            entities.extend( [ self.m.db.index[id] for id in o if id in self.m.db.index] )
        # Filter for the things we're displaying
        dso = dso.as_filtered( entities=entities)
        

        #data = data.as_class_grouped(classes=classes)
        print "Objs/classes:", objs, classes
        
        data = np.zeros( (len(objs), len(classes)) )

        for y,obj in enumerate(objs): #[u'PYRUVATE', u'PHOSPHO-ENOL-PYRUVATE']
            for x,o in enumerate(obj):
                try:
                    e = self.m.db.index[o] # Get entity for lookup
                    data[y,x] = dso.data[ 0, dso.entities[1].index(e) ]
                except: # Can't find it
                    pass
                
        return data
  

    def build_log2_change_control_vs_multi(self, objs, classes):
        data = np.zeros( (len(objs), len(classes)) )
        for x,xl in enumerate(classes):
            for y,yl in enumerate(objs):
                data[y,x] = self.parent.data.get_log2(yl,xl) - self.parent.data.get_log2( yl , self.parent.experiment['control'] )
    
        return data


    def build_raw_change_control_vs_multi(self, objs, classes):
        data = np.zeros( (len(objs), len(classes)) )
        for x,xl in enumerate(classes):
            for y,yl in enumerate(objs):
                data[y,x] = np.mean( self.parent.data.quantities[yl][xl] ) - np.mean( self.parent.data.quantities[ yl ][ self.parent.experiment['control'] ] )
    
        return data

    def get_fig_tempfile(self, fig):
        tf = QTemporaryFile()
        tf.open()
        fig.savefig(tf.fileName(), format='png', bbox_inches='tight')
        return tf

    def addExperimentToolBar(self):

        t = self.addToolBar('Experiment')
        t.setIconSize( QSize(16,16) )

        # DATA MENU
        define_experimentAction = QAction( QIcon( os.path.join( utils.scriptdir,'icons','layout-design.png') ), 'Define experiment\u2026', self)
        define_experimentAction.setShortcut('Ctrl+Q')
        define_experimentAction.setStatusTip('Define experiment control, test and timecourse settings')
        define_experimentAction.triggered.connect(self.onDefineExperiment)

        t.addAction(define_experimentAction)
        
        t.cb_control = QComboBox()
        t.cb_control.addItems(['Control'])
        t.cb_control.currentIndexChanged.connect(self.onModifyExperiment)

        t.cb_test = QComboBox()
        t.cb_test.addItems(['Test'])
        t.cb_test.currentIndexChanged.connect(self.onModifyExperiment)

        t.addWidget(t.cb_control)
        t.addWidget(t.cb_test)
    
        self.toolbars['experiment'] = t

    def repopulate_experiment_classes(self):
        # Empty the toolbar controls
        self.toolbars['experiment'].cb_control.clear()
        self.toolbars['experiment'].cb_test.clear()
        # Data source change; update the experimental control with the data input source
        self.toolbars['experiment'].cb_control.addItems( [i for i in self.data.i['input'].classes_l[0]] )
        self.toolbars['experiment'].cb_test.addItems( [i for i in self.data.i['input'].classes_l[0]] )

    def onDataChanged(self):
        self.repopulate_experiment_classes()
        self.generate()
        
    def onDefineExperiment(self):
        pass

    def onModifyExperiment(self):
        pass

# Class for analysis views, using graph-based visualisations of defined datasets
# associated layout and/or analysis
class AnalysisD3View(AnalysisView):
        
    def render(self, metadata, debug=False, template_name='figure'):
        metadata['htmlbase'] = os.path.join( utils.scriptdir,'html')
        
        
        template = self.m.templateEngine.get_template('d3/%s.svg' % template_name)
        self.browser.setHtml(template.render( metadata ),QUrl('~'))
        
        f = open('/Users/mxf793/Desktop/test.svg','w')
        f.write( template.render( metadata ) )
        f.close()        

                    
        
# Class for analysis views, using graph-based visualisations of defined datasets
# associated layout and/or analysis
class D3View(AnalysisView):
    def __init__(self, plugin, parent, **kwargs):
        super(D3View, self).__init__(plugin, parent, **kwargs)        
    
        self.parent = parent
        self.browser = QWebViewScrollFix( self, onNavEvent=parent.onBrowserNav )
    
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
        template = self.parent.templateEngine.get_template('d3/force.svg')

        self.browser.setHtml(template.render( metadata ),QUrl('~')) 

        f = open('/Users/mxf793/Desktop/test.html','w')
        f.write( template.render( metadata ) )
        f.close()
      

# Class for analysis views, using graph-based visualisations of defined datasets
# associated layout and/or analysis
class AnalysisHeatmapView(AnalysisD3View):

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



class AnalysisCircosView(AnalysisD3View):
    def __init__(self, plugin, parent, **kwargs):
        super(AnalysisCircosView, self).__init__(plugin, parent, **kwargs)        
        self.parent = parent
        self.browser = QWebViewExtend( self, onNavEvent=parent.onBrowserNav )

    def build_matrix(self, targets, target_links):

        data = []
        for mx in targets:
            row = []
            for my in targets:
                n = len( list( target_links[my] & target_links[mx] ) )
                row.append( n )
    
            data.append( row )
        return data, targets







class AnalysisCircosPathwayView(AnalysisHeatmapView):
    def __init__(self, plugin, parent, **kwargs):
        super(AnalysisCircosPathwayView, self).__init__(plugin, parent, **kwargs)        

        self.parent = parent
        self.browser = QWebViewExtend( self, onNavEvent=parent.onBrowserNav )


    def build_matrix(self, targets, target_links):

        data = []
        for mx in targets:
            row = []
            for my in targets:
                n = len( list( target_links[my] & target_links[mx] ) )
                row.append( n )
    
            data.append( row )
        return data, targets


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

"""                        
                        {
                            'type':'circos',
                            'data': data_m,
                            'labels': labels_m,
                            'n':1,  
                            'legend':('Metabolic pathway interconnections','Complete set of shared metabolites for pathways in current database')
                                                      
                        },
                        {
                            'type':'circos',
                            'data': data_r,
                            'labels': labels_r,
                            'n':2,  
                            'legend':('Metabolic pathway interconnections','Complete set of shared metabolites for pathways in current database')
                                                      
                        }],
                        [


                            {
                            'type':'corrmatrix',
                            'data': [
                              {'group':"setosa","sepal length":1, "sepal width":5, "petal length":3, "petal width":2},
                              {'group':"versicolor","sepal length":2, "sepal width":5, "petal length":3, "petal width":1},
                              {'group':"virginica","sepal length":3, "sepal width":5, "petal length":3, "petal width":1},
                              {'group':"setosa","sepal length":4, "sepal width":5, "petal length":3, "petal width":0},
                              {'group':"versicolor","sepal length":5, "sepal width":5, "petal length":3, "petal width":1},
                              {'group':"virginica","sepal length":6, "sepal width":5, "petal length":3, "petal width":2},
                            ],
                            'traits': ["sepal length", "sepal width", "petal length", "petal width"],
                            'groups': ["setosa", "versicolor", "virginica"],
                            'n':5,
                            'legend':('a','b'),
"""   


class remoteQueryDialog(genericDialog):

    def parse(self, data):
        # Parse incoming data and return a dict mapping the displayed values to the internal value
        l = data.split('\n')
        return dict( zip( l, l ) )

    def do_query(self):
        f = urllib2.urlopen(self.query_target % urllib.quote( self.textbox.text() ) )
        query_result = f.read()
        f.close()
        
        self.data = self.parse( query_result ) 
        self.select.clear()
        self.select.addItems( self.data.keys() )

    def __init__(self, parent, query_target=None, **kwargs):
        super(remoteQueryDialog, self).__init__(parent, **kwargs)        

        self.textbox = QLineEdit()
        querybutton = QPushButton('↺')
        querybutton.clicked.connect( self.do_query )

        queryboxh = QHBoxLayout()
        queryboxh.addWidget( self.textbox )        
        queryboxh.addWidget( querybutton )        
        
        self.data = None # Deprecated
        
        self.select = QListWidget()
        self.query_target = query_target
        
        self.layout.addLayout( queryboxh )
        self.layout.addWidget( self.select )
        
        self.dialogFinalise()


class MainWindowUI(QMainWindow):

    def __init__(self):

        super(MainWindowUI, self).__init__()

        menubar = self.menuBar()
        self.menuBar = {
            'file': menubar.addMenu('&File'),
            'pathways': menubar.addMenu('&Pathways'),
            'data': menubar.addMenu('&Data'),
            'view': menubar.addMenu('&View'),
            'database': menubar.addMenu('&Database'),
        }

        # FILE MENU 
        aboutAction = QAction(QIcon.fromTheme("help-about"), 'About', self)
        aboutAction.setStatusTip('About MetaPath')
        aboutAction.triggered.connect(self.onAbout)
        self.menuBar['file'].addAction(aboutAction)

        newAction = QAction(QIcon.fromTheme("new-workspace", QIcon( os.path.join( utils.scriptdir, 'icons', 'document-new.png') )), u'&New Blank Workspace', self)
        newAction.setShortcut('Ctrl+O')
        newAction.setStatusTip('Create new blank workspace')
        newAction.triggered.connect(self.onSaveAs)
        self.menuBar['file'].addAction(newAction)
        

        openAction = QAction(QIcon.fromTheme("open-workspace", QIcon( os.path.join( utils.scriptdir, 'icons', 'folder-open-document.png') )), u'&Open\u2026', self)
        openAction.setShortcut('Ctrl+O')
        openAction.setStatusTip('Open previous analysis workspace')
        openAction.triggered.connect(self.onSaveAs)
        self.menuBar['file'].addAction(openAction)

        self.menuBar['file'].addSeparator()
                
        saveAction = QAction(QIcon.fromTheme("save-workspace", QIcon( os.path.join( utils.scriptdir, 'icons', 'disk.png') )), u'&Save', self)
        saveAction.setShortcut('Ctrl+S')
        saveAction.setStatusTip('Save current workspace for future use')
        saveAction.triggered.connect(self.onSaveAs)
        self.menuBar['file'].addAction(saveAction)

        saveAsAction = QAction(QIcon.fromTheme("save-workspace", QIcon( os.path.join( utils.scriptdir, 'icons', 'document-save-as.png') )), u'Save &As\u2026', self)
        saveAsAction.setShortcut('Ctrl+A')
        saveAsAction.setStatusTip('Save current workspace for future use')
        saveAsAction.triggered.connect(self.onSaveAs)
        self.menuBar['file'].addAction(saveAsAction)

        self.menuBar['file'].addSeparator()        

        printAction = QAction(QIcon.fromTheme("document-print", QIcon( os.path.join( utils.scriptdir, 'icons', 'printer.png') )), u'&Print\u2026', self)
        printAction.setShortcut('Ctrl+P')
        printAction.setStatusTip('Print current metabolic pathway')
        printAction.triggered.connect(self.onPrint)
        self.menuBar['file'].addAction(printAction)

        self.menuBar['file'].addSeparator()        

        exportImagesAction = QAction(QIcon.fromTheme("image-export", QIcon( os.path.join( utils.scriptdir, 'icons', 'image-export.png') )), u'&Export figures\u2026', self)
        exportImagesAction.setShortcut('Ctrl+E')
        exportImagesAction.setStatusTip('Save current metabolic pathway map in multiple formats')
        exportImagesAction.triggered.connect(self.onSaveAs)
        self.menuBar['file'].addAction(exportImagesAction)


        resetAction = QAction(QIcon.fromTheme("system-restart-panel", QIcon( os.path.join( utils.scriptdir,'icons','system-restart-panel.png') )), u'&Reset configuration', self)
        resetAction.setStatusTip('Reset config to systm defaults')
        resetAction.triggered.connect(self.onResetConfig)
        self.menuBar['file'].addAction(resetAction)

        #fileMenu.addAction(exitAction)

        # PATHWAY MENU
        show_pathwaysAction = QAction(QIcon.fromTheme("document-open", QIcon( os.path.join( utils.scriptdir,'icons','document-open.png') )), '&Show Selected Pathways\u2026', self)
        show_pathwaysAction.setStatusTip('Show and hide specific metabolic pathways')
        show_pathwaysAction.triggered.connect(self.onPathwaysShow)
        self.menuBar['pathways'].addAction(show_pathwaysAction)



        # VIEW MENU 
        refreshAction = QAction(QIcon.fromTheme("view-refresh", QIcon( os.path.join( utils.scriptdir,'icons', 'refresh.png') )), u'&Refresh', self)
        refreshAction.setShortcut('Ctrl+R')
        refreshAction.setStatusTip('Refresh metabolic pathway map')
        refreshAction.triggered.connect(self.onRefresh)
        self.menuBar['view'].addAction(refreshAction)
        
        zoominAction = QAction(QIcon.fromTheme("zoom-in", QIcon( os.path.join( utils.scriptdir,'icons', 'zoom-in.png') )), u'&Zoom in', self)
        zoominAction.setShortcut('Ctrl++')
        zoominAction.setStatusTip('Zoom in')
        zoominAction.triggered.connect(self.onZoomIn)
        self.menuBar['view'].addAction(zoominAction)

        zoomoutAction = QAction(QIcon.fromTheme("zoom-out", QIcon( os.path.join( utils.scriptdir,'icons', 'zoom-out.png') )), u'&Zoom out', self)
        zoomoutAction.setShortcut('Ctrl+-')
        zoomoutAction.setStatusTip('Zoom out')
        zoomoutAction.triggered.connect(self.onZoomOut)
        self.menuBar['view'].addAction(zoomoutAction)
        
        
        # DATABASE MENU
        load_identitiesAction = QAction(QIcon.fromTheme("document-import", QIcon( os.path.join( utils.scriptdir,'icons','database-import.png') )), u'&Load metabolite identities\u2026', self)
        load_identitiesAction.setStatusTip('Load additional metabolite identities/synonyms')
        load_identitiesAction.triggered.connect(self.onLoadIdentities)
        self.menuBar['database'].addAction(load_identitiesAction)
        
        self.menuBar['database'].addSeparator()
        
        reload_databaseAction = QAction(QIcon.fromTheme("system-restart-panel", QIcon( os.path.join( utils.scriptdir,'icons','exclamation-red.png') )), u'&Reload database', self)
        reload_databaseAction.setStatusTip('Reload pathway & metabolite database')
        reload_databaseAction.triggered.connect(self.onReloadDB)
        self.menuBar['database'].addAction(reload_databaseAction)
        
        
        
        # TOOLBARS
        self.setToolButtonStyle( Qt.ToolButtonFollowStyle ) #Qt.ToolButtonTextUnderIcon
        self.setIconSize( QSize(16,16) )
        #self.setUnifiedTitleAndToolBarOnMac( True )
        self.fileToolbar = self.addToolBar('File')


        self.fileToolbar.addAction(openAction)
        self.fileToolbar.addAction(saveAction)
        self.fileToolbar.addAction(exportImagesAction)
        self.fileToolbar.addAction(printAction)
        self.fileToolbar.addAction(printAction)
        
        self.viewToolbar = self.addToolBar('View')
        self.viewToolbar.addAction(zoominAction)

        self.viewToolbar.addAction(zoomoutAction)
        self.viewToolbar.addAction(refreshAction)
        


        self.addToolBarBreak()


        #self.vboxlayout.addWidget(self.mainBrowser)
        QNetworkProxyFactory.setUseSystemConfiguration( True )

        #QWebSettings.globalSettings().setAttribute( QWebSettings.PluginsEnabled, True)
        #QWebSettings.globalSettings().setAttribute( QWebSettings.LocalContentCanAccessRemoteUrls, True)
        #QWebSettings.globalSettings().setAttribute( QWebSettings.LocalContentCanAccessFileUrls, True)

        QWebSettings.setMaximumPagesInCache( 0 )
        QWebSettings.setObjectCacheCapacities(0, 0, 0)
        QWebSettings.clearMemoryCaches()
        #QWebSettings.globalSettings().setAttribute( QWebSettings.WebAttribute.DeveloperExtrasEnabled, True)
        
        self.mainBrowser = QWebViewScrollFix( None, onNavEvent=self.onBrowserNav )

        #∞Σ⌘⁉★⌘↛⇲Σ▼◎♥⚑☺⬚↛
        

        self.dbBrowser_CurrentURL = None

        # Display a introductory helpfile 
        template = self.templateEngine.get_template('welcome.html')
        self.mainBrowser.setHtml(template.render( {'htmlbase': os.path.join( utils.scriptdir,'html')} ),QUrl('~')) 
        self.mainBrowser.loadFinished.connect( self.onBrowserLoadDone )
        
        self.pluginManager = PluginManagerSingleton.get()
        self.pluginManager.m = self
        
        self.pluginManager.setPluginPlaces([os.path.join( utils.scriptdir,'plugins')])
        self.pluginManager.setCategoriesFilter({
               "Data" : plugins.DataPlugin,
               "Processing" : plugins.ProcessingPlugin,
               "Identification": plugins.IdentificationPlugin,
               "Analysis" : plugins.AnalysisPlugin,
               "Visualisation" : plugins.VisualisationPlugin,
               "Output" : plugins.OutputPlugin,
               "Misc" : plugins.MiscPlugin,
               })
        self.pluginManager.collectPlugins()

        plugin_categories = ['Data','Processing','Identification','Analysis','Visualisation']
        apps = defaultdict(list)
        self.appBrowsers = {}
        self.plugin_names = dict()
        
        # Loop round the plugins and print their names.
        for category in plugin_categories:
            for plugin in self.pluginManager.getPluginsOfCategory(category):
                self.plugin_names[ plugin.plugin_object.__module__ ] = plugin.name
                
                plugin_image = os.path.join( os.path.dirname(plugin.path), 'icon.png' )
                if not os.path.isfile( plugin_image ):
                    plugin_image = None
                
                apps[category].append({
                    'id': plugin.plugin_object.__module__, 
                    'image': plugin_image,          
                    'name': plugin.name,
                    'description': plugin.description,
                })

        self.dataDock = QDockWidget('Database')

        self.dbBrowser = QWebViewScrollFix( self.dataDock, onNavEvent=self.onBrowserNav )
        # Display a list of supporting orgs
        template = self.templateEngine.get_template('sponsors.html')
        self.dbBrowser.setHtml(template.render( {'htmlbase': os.path.join( utils.scriptdir,'html')} ),QUrl('~')) 
        
        self.dataDock.setWidget(self.dbBrowser)
        self.dataDock.setMinimumWidth(300)
        self.dataDock.setMaximumWidth(300)
        
        #self.dataDock.setFeatures(QDockWidget.NoDockWidgetFeatures)

        self.stack = QStackedWidget()
        #self.stack.addWidget(self.mainBrowser)
        
        self.setCentralWidget(self.stack)

        self.stack.setCurrentIndex(0)

        self.workspace_count = 0 # Auto-increment
        self.workspace_parents = {}
        
        self.workspace = QTreeWidget()
        self.workspace.setColumnCount(3)
        self.workspace.setHeaderLabels(['','ID','⚑']) #,'#'])
        self.workspace.setUniformRowHeights(True)
        self.workspace.hideColumn(1)
        

        self.addWorkspaceItem( self.mainBrowser, None, 'Home', QIcon( os.path.join( utils.scriptdir,'icons','home.png' ) )   )
        
        app_category_icons = {
               "Data" : QIcon.fromTheme("data", QIcon( os.path.join( utils.scriptdir,'icons','ruler.png' ) ) ),
               "Processing" : QIcon.fromTheme("processing", QIcon( os.path.join( utils.scriptdir,'icons','ruler-triangle.png' ) ) ),
               "Identification" : QIcon.fromTheme("identification", QIcon( os.path.join( utils.scriptdir,'icons','target.png' ) ) ),
               "Analysis" : QIcon.fromTheme("analysis", QIcon( os.path.join( utils.scriptdir,'icons','calculator.png' ) ) ),
               "Visualisation" : QIcon.fromTheme("visualisation", QIcon( os.path.join( utils.scriptdir,'icons','star.png' ) ) ),
               }
    
        template = self.templateEngine.get_template('apps.html')
        for category in plugin_categories:
            self.appBrowsers[ category ] = QWebViewScrollFix(  self.workspace, onNavEvent=self.onBrowserNav )
            self.appBrowsers[ category ].setHtml(template.render( 
                {
                'htmlbase': os.path.join( utils.scriptdir,'html'),
                'category':category,
                'apps':apps[ category ],
                }                
             ),QUrl('~')) 
                
            self.appBrowsers[ category ].loadFinished.connect( self.onBrowserLoadDone )
                
            self.addWorkspaceItem( self.appBrowsers[ category ], None, category, app_category_icons[category]   )


        #self.addWorkspaceItem( self.mainBrowser, 'Visualisation', "Hs_Glycolysis_and_Gluconeogenesis_WP534_51732",QIcon.fromTheme("save-workspace", QIcon( os.path.join( utils.scriptdir, 'icons', 'disk.png') ))  )
        #self.addWorkspaceItem( self.mainBrowser, 'Visualisation', "Hs_Glycolysis_and_Gluconeogenesis_WP534_51732",QIcon.fromTheme("save-workspace", QIcon( os.path.join( utils.scriptdir, 'icons', 'disk.png') ))  )

        self.workspace.setSelectionMode( QAbstractItemView.SingleSelection )

        self.workspace.currentItemChanged.connect( self.onWorkspaceStackChange)
        
        #QObject.connect(self.workspace, SIGNAL("itemActivated()"),
        #self.stack, SLOT("setCurrentIndex(int)"))

        self.workspaceDock = QDockWidget('Workspace')
        self.workspaceDock.setWidget(self.workspace)
        self.workspace.setHorizontalScrollBarPolicy( Qt.ScrollBarAlwaysOff )
        self.workspace.setColumnWidth(0, 298-25) 
        self.workspace.setColumnWidth(2, 24) 
        self.workspaceDock.setMinimumWidth(300)
        self.workspaceDock.setMaximumWidth(300)
        #self.workspaceDock.setFeatures(QDockWidget.NoDockWidgetFeatures)

        self.addDockWidget(Qt.LeftDockWidgetArea, self.dataDock)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.workspaceDock)

        #self.workspace.resizeColumnToContents(0)
        self.tabifyDockWidget( self.workspaceDock, self.dataDock ) 
        self.workspaceDock.raise_()

    def onWorkspaceStackChange(self, item, previous):
        self.stack.setCurrentIndex( int( item.text(1) ) )

    def addWorkspaceItem(self, widget, section, title, icon = None, is_selected=None):
        
        stack_index = self.stack.addWidget( widget )
        
        tw = QTreeWidgetItem()
        tw.setText(0, title)
        tw.setText(1, str( stack_index ) )
        
        if icon:
            tw.setIcon(0, icon )
        
        if section:
            self.workspace_parents[ section ].addChild(tw)
        else:
            self.workspace.addTopLevelItem(tw) 
            self.workspace_parents[ title ] = tw

        if is_selected:
            if section:
                self.workspace_parents[ section ].setExpanded(True)
            self.workspace.setCurrentItem(tw)

        return tw

    
    def setWorkspaceStatus(self, workspace_item, status):
        status_icons = {
            'active':   QIcon( os.path.join( utils.scriptdir,'icons','flag-green.png' ) ),
            'waiting':  QIcon( os.path.join( utils.scriptdir,'icons','flag-yellow.png' ) ),
            'error':    QIcon( os.path.join( utils.scriptdir,'icons','flag-red.png' ) ),
            'done':     QIcon( os.path.join( utils.scriptdir,'icons','flag-checker.png' ) ),
            'clear':    QIcon(None)
        }

        if status not in status_icons.keys():
            status = 'clear'
            
        workspace_item.setIcon(2, status_icons[status] )
        self.workspace.update( self.workspace.indexFromItem( workspace_item ) )
        self.app.processEvents()

    def clearWorkspaceStatus(self, workspace_item):
        self.setWorkspaceStatus(workspace_item, 'clear')        
        
    def onPathwayMiningToggle(self, checked):
        self.config.setValue( '/Data/MiningActive', checked)
        self.generateGraphView()


