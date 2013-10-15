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

# Translation (@default context)
from translate import tr

# GENERIC CONFIGURATION AND OPTION HANDLING

# Generic configuration dialog handling class
class genericDialog(QDialog):
    def __init__(self, parent, buttons = ['ok','cancel'], **kwargs):
        super(genericDialog, self).__init__(parent, **kwargs)        

        self.sizer = QVBoxLayout()
        self.layout = QVBoxLayout()
        
        QButtons = {
            'ok':QDialogButtonBox.Ok,
            'cancel':QDialogButtonBox.Cancel,
        }
        Qbtn = 0
        for k in buttons:
            Qbtn = Qbtn | QButtons[k]
        
        # Setup default button configurations etc.
        self.buttonBox = QDialogButtonBox(Qbtn)
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
        
# Web views

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

class QWebPageExtend(QWebPage):
    def shouldInterruptJavascript():
        return False


class QWebViewExtend(QWebView):

    def __init__(self, parent, onNavEvent=None, **kwargs):
        super(QWebViewExtend, self).__init__(parent, **kwargs)        
        
        self.w = parent
        self.setPage( QWebPageExtend(self.w) )
        self.setHtml(BLANK_DEFAULT_HTML,QUrl("~"))
        
        self.page().setContentEditable(False)
        self.page().setLinkDelegationPolicy( QWebPage.DelegateExternalLinks )
        self.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding )
        self.loadFinished.connect(self._loadFinished)
        self._is_svg_with_js = False
        
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

    def setSVG(self, svg):
        self._is_svg_with_js = True
        super(QWebViewExtend, self).setHtml(svg, QUrl('~') )             
        #super(QWebViewExtend, self).setContent(svg, "image/svg+xml") <- this would be preferable but has encoding issues
        
    def _loadFinished(self, ok):
        sizer = self.sizeHint()   
        self.page().currentFrame().addToJavaScriptWindowObject("QtWebView", self)
        if self._is_svg_with_js:
            self.page().currentFrame().evaluateJavaScript( "QtViewportSize={'x':%s,'y':%s};" % ( sizer.width()-30, sizer.height()-80 ) ) #-magic number for scrollbars (ugh)        
            self.page().currentFrame().evaluateJavaScript( "_metapath_render_trigger();" ) #-magic number for scrollbars (ugh)        
                        
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

        

# View Dialogs

# Source data selection dialog
# Present a list of widgets (drop-downs) for each of the interfaces available on this plugin
# in each list show the data sources that can potentially file that slot. 
# Select the currently used 
class DialogDataSource(genericDialog):
    def __init__(self, parent=None, view=None, **kwargs):
        super(DialogDataSource, self).__init__(parent, **kwargs)        
        
        self.v = view
        self.m = view.m
        
        self.setWindowTitle( tr("Select Data Source(s)") )

        # Build a list of dicts containing the widget
        # with target data in there
        self.lw_consumeri = list()
        for n,cd in enumerate(self.v.data.consumer_defs):
            
            self.lw_consumeri.append( QComboBox() )
            cdw = self.lw_consumeri[n] # Shorthand
            datasets = self.v.data.can_consume_which_of(self.m.datasets, [cd])
            
            cdw.addItem('No input')
            
            for nd, dataset in enumerate(datasets):

                e = set()
                for el in dataset.entities_t:
                    e |= set(el) # Add entities to the set
                e = e - {'NoneType'} # Remove if it's in there
            
                entities = ', '.join( e )
                dimensions = 'x'.join( [str(s) for s in dataset.shape ] )

                cdw.addItem( QIcon(dataset.manager.v.plugin.workspace_icon),'%s %s %s (%s)' % (dataset.name, dataset.manager.v.name, entities, dimensions) )

                # If this is the currently used data source for this interface, set it active
                if cd.target in self.v.data.i and dataset == self.v.data.i[cd.target]:
                    cdw.setCurrentIndex(nd+1) #nd+1 because of the None we've inserted at the front

            cdw.consumer_def = cd
            cdw.datasets = [None] + datasets
            
            self.layout.addWidget( QLabel( "%s:" % cd.title  ) )
            self.layout.addWidget(cdw)
            
        self.setMinimumSize( QSize(600,100) )
        self.layout.setSizeConstraint(QLayout.SetMinimumSize)
        
        # Build dialog layout
        self.dialogFinalise()
        
        

class DialogDataOutput(genericDialog):
    def __init__(self, parent=None, view=None, **kwargs):
        super(DialogDataOutput, self).__init__(parent, buttons=['ok'], **kwargs)        
        
        self.v = view
        self.m = view.m

        self.setWindowTitle("Data Output(s)")

        self.lw_sources = QTreeWidget() # Use TreeWidget but flat; for multiple column view
        self.lw_sources.setColumnCount(5)
        self.lw_sources.setHeaderLabels(['','Source','Data','Entities', 'Size']) #,'#'])
        self.lw_sources.setUniformRowHeights(True)
        self.lw_sources.rootIsDecorated()
        self.lw_sources.hideColumn(0)                
        
        datasets = self.m.datasets # Get a list of dataset objects to test
        self.datasets = []
        
        for k,dataset in self.v.data.o.items():
            
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
            e = e - {'NoneType'} # Remove if it's in there
            
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


# Overload this to provide some better size hinting to the inside tabs
class QTabWidgetExtend( QTabWidget ):

    auto_unfocus_tabs = ['?']

    def __init__(self, parent, **kwargs):
        super(QTabWidgetExtend, self).__init__(parent, **kwargs)
        self.w = parent
        self.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding )
    
    def sizeHint(self):
        return self.w.size()
    
    # A few wrappers to 
    def addTab(self, widget, name, focused=True, try_to_keep_unfocused=False, **kwargs):
        widget.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding )
        t = super(QTabWidgetExtend, self).addTab(widget, name, **kwargs)

        # Automagically unfocus the help (+any other equivalent) tabs if were' adding a second
        # tab to the widget. Not after, as must be selected intentionally
        #if self.count() == 2 and self.tabText(0) in self.auto_unfocus_tabs: # 
        #    self.setCurrentIndex( t )
        
        return t
        


#### View Object Prototypes (Data, Assignment, Processing, Analysis, Visualisation) e.g. used by plugins
class GenericView( QMainWindow ):

    help_tab_html_filename = None

    def __init__(self, plugin, parent, **kwargs):
        super(GenericView, self).__init__(parent, **kwargs)
    
        self.plugin = plugin
        self.m = parent
        self.m.views.append( self )
        
        self.id = str( id( self ) )
        self.data = data.DataManager(self.m, self)
        self.name = self.m.plugin_names[ self.plugin.__class__.__module__ ] 

        self.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding )
        
        #self.w = QMainWindow()
        self.tabs = QTabWidgetExtend(self)
        self.tabs.setDocumentMode(True)
        self.tabs.setTabsClosable(False)
        self.tabs.setTabPosition( QTabWidget.South )
        self.tabs.setMovable(True)
        
        self.file_watcher = QFileSystemWatcher()            
        self.file_watcher.fileChanged.connect( self.onFileChanged )

        if self.plugin.help_tab_html_filename:
            self.help = QWebViewExtend(self, self.m.onBrowserNav) # Watch browser for external nav
            self.tabs.addTab(self.help,'?')            
            template = self.plugin.templateEngine.get_template(self.plugin.help_tab_html_filename)
            self.help.setHtml( template.render( {
                        'htmlbase': os.path.join( utils.scriptdir,'html'),
                        'pluginbase': self.plugin.path,
                        'view': self,                        
                        } ), QUrl("~") 
                        )
        
        self.toolbars = {}
        self.controls = defaultdict( dict ) # Store accessible controls
        
        self.register_url_handler( self.default_url_handler )

        self.setCentralWidget(self.tabs)
        
        self.config = QSettings()
        
        self.workspace_item = self.m.addWorkspaceItem(self, self.plugin.default_workspace_category, self.name, is_selected=True, icon=self.plugin.workspace_icon) #, icon = None)

    def register_url_handler(self, url_handler):
        self.m.register_url_handler( self.id, url_handler ) 

    def render(self, metadata):
        return
    
    def autogenerate(self, *args, **kwargs):
        if self._pause_analysis_flag:
            self.setWorkspaceStatus('paused')
            return False
            
        self.generate(*args, **kwargs)
    
    def generate(self):
        return
    
        
    def set_name(self, name):
        self.name = name
        try:
            self.workspace_item.setText(0, name)
        except:
            pass

        try: # Notify the mainview of the workspace change
            self.m.workspace_updated.emit()            
        except:
            pass

    def setWorkspaceStatus(self, status):
        self.m.setWorkspaceStatus( self.workspace_item, status)

    def clearWorkspaceStatus(self):
        self.m.clearWorkspaceStatus( self.workspace_item )


    def addDataToolBar(self, default_pause_analysis=False):            
        t = self.addToolBar('Data')
        t.setIconSize( QSize(16,16) )

        select_dataAction = QAction( QIcon( os.path.join(  utils.scriptdir, 'icons', 'data-source.png' ) ), tr('Select a data source…'), self.m)
        select_dataAction.setStatusTip('Select a compatible data source')
        select_dataAction.triggered.connect(self.onSelectDataSource)
        t.addAction(select_dataAction)

        select_dataAction = QAction( QIcon( os.path.join(  utils.scriptdir, 'icons', 'arrow-circle-double.png' ) ), tr('Recalculate'), self.m)
        select_dataAction.setStatusTip('Recalculate')
        select_dataAction.triggered.connect(self.onRecalculate)
        t.addAction(select_dataAction)
        
        pause_analysisAction = QAction( QIcon( os.path.join(  utils.scriptdir, 'icons', 'control-pause.png' ) ), tr('Pause automatic analysis'), self.m)
        pause_analysisAction.setStatusTip('Do not automatically refresh analysis when source data updates')
        pause_analysisAction.setCheckable(True)
        pause_analysisAction.setChecked(default_pause_analysis)
        pause_analysisAction.toggled.connect(self.onAutoAnalysisToggle)
        t.addAction(pause_analysisAction)        
        self._pause_analysis_flag = default_pause_analysis

        select_dataAction = QAction( QIcon( os.path.join(  utils.scriptdir, 'icons', 'data-output.png' ) ), tr('View resulting data…'), self.m)
        select_dataAction.setStatusTip('View resulting data output from this plugin')
        select_dataAction.triggered.connect(self.onViewDataOutput)
        t.addAction(select_dataAction)
        
        self.toolbars['image'] = t        

        
    def onSelectDataSource(self):
        # Basic add data source dialog. Extend later for multiple data sources etc.
        """ Open the mining setup dialog to define conditions, ranges, class-comparisons, etc. """
        dialog = DialogDataSource(parent=self, view=self)
        ok = dialog.exec_()
        if ok:
            for cb in dialog.lw_consumeri: # Get list of comboboxes
                i = cb.currentIndex() # Get selected item
                consumer_def = cb.consumer_def
                print consumer_def.target, i, len(cb.datasets)
                if i > 0: # Something in the list (-1) and not 'No data'
                    dso = cb.datasets[i]
                    self.data.consume_with(dso, consumer_def)  
                    
                else: # Stop consuming through this interface
                    self.data.stop_consuming( consumer_def.target )
             
            # Trigger notification for data source change; re-render inheritance map        
            #self.m.onDataInheritanceChanged()
            
            #self.generate() automatic
            
    def onViewDataOutput(self):
        # Basic add data source dialog. Extend later for multiple data sources etc.
        """ Open the mining setup dialog to define conditions, ranges, class-comparisons, etc. """
        dialog = DialogDataOutput(parent=self, view=self)        
        dialog.exec_()

    def getCreatedToolbar(self, name, id):
        if id not in self.toolbars:       
            self.toolbars[id] = self.addToolBar(name)
            self.toolbars[id].setIconSize( QSize(16,16) )

        return self.toolbars[id] 

    def addFigureToolBar(self):            
        t = self.getCreatedToolbar(tr('Figures'),'figure')

        export_imageAction = QAction( QIcon( os.path.join(  utils.scriptdir, 'icons', 'image-export.png' ) ), tr('Export current figure as image…'), self.m)
        export_imageAction.setStatusTip( tr('Export figure to image') )
        export_imageAction.triggered.connect(self.onSaveImage)
        t.addAction(export_imageAction)

        printAction = QAction(QIcon.fromTheme("document-print", QIcon( os.path.join( utils.scriptdir, 'icons', 'printer.png') )), tr('&Print…'), self)
        printAction.setShortcut('Ctrl+P')
        printAction.setStatusTip( tr('Print current figure') )
        #printAction.triggered.connect(self.onPrint)
        t.addAction(printAction)        
                        
        zoominAction = QAction(QIcon.fromTheme("zoom-in", QIcon( os.path.join( utils.scriptdir,'icons', 'zoom-in.png') )), tr('&Zoom in'), self)
        zoominAction.setShortcut('Ctrl++')
        zoominAction.setStatusTip( tr('Zoom in') )
        #zoominAction.triggered.connect(self.onZoomIn)
        t.addAction(zoominAction)

        zoomoutAction = QAction(QIcon.fromTheme("zoom-out", QIcon( os.path.join( utils.scriptdir,'icons', 'zoom-out.png') )), tr('&Zoom out'), self)
        zoomoutAction.setShortcut('Ctrl+-')
        zoomoutAction.setStatusTip( tr('Zoom out') )
        #zoomoutAction.triggered.connect(self.onZoomOut)
        t.addAction(zoomoutAction)


    def addExternalDataToolbar(self):     
        t = self.getCreatedToolbar( tr('External Data'),'external-data')
        
        watch_fileAction = QAction( QIcon( os.path.join(  utils.scriptdir, 'icons', 'eye--exclamation.png' ) ), tr('Watch data file(s) for changes…'), self.m)
        watch_fileAction.setStatusTip( tr('Watch external data file(s) for changes and automatically refresh') )
        watch_fileAction.triggered.connect(self.onWatchSourceDataToggle)
        watch_fileAction.setCheckable(True)
        watch_fileAction.setChecked(False)
        t.addAction(watch_fileAction)
        self._autoload_source_files_on_change = False


    
    def onWatchSourceDataToggle(self, checked):
        self._autoload_source_files_on_change = checked

    def onAutoAnalysisToggle(self, checked):
        self._pause_analysis_flag = checked
        
    def onFileChanged(self, file):
        if self._autoload_source_files_on_change:
            self.load_datafile( file )
    
    
    def onSaveImage(self):
        # Get currently selected webview
        self.tabs.currentWidget().saveAsImage('/Users/mxf793/Desktop/test.tiff')        


    def onRecalculate(self):
        self.generate()

    # Url handler for all default plugin-related actions; making these accessible to all plugins
    # from a predefined url structure: metapath://<view.id>/default_actions/data_source/add
    def default_url_handler(self, url):

        kind, id, action = url.split('/') # FIXME: Can use split here once stop using pathwaynames           
        
        # url is Qurl kind
        # Add an object to the current view
        if kind == "default_actions":
            
            if action == 'add' and id == 'data_source':
                # Add the pathway and regenerate
                self.onSelectDataSource()        

        
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

# Workspace overview (Home) class

class HomeView( GenericView ):

    def __init__(self, parent, **kwargs):
        super(GenericView, self).__init__(parent, **kwargs) # We're overriding all of the GenericView Init, so super it
    
        self.plugin = None
        self.m = parent
        
        self.id = 'home' #str( id( self ) )
        self.name = "Home"

        self.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding )
        
        #self.w = QMainWindow()
        self.tabs = QTabWidgetExtend(self)
        self.tabs.setDocumentMode(True)
        self.tabs.setTabsClosable(False)
        self.tabs.setTabPosition( QTabWidget.South )
        self.tabs.setMovable(True)
        
        # Display welcome file
        self.help = QWebViewExtend(self, self.m.onBrowserNav) # Watch browser for external nav
        self.tabs.addTab(self.help,'?')            
        template = self.m.templateEngine.get_template('welcome.html')
        self.help.setHtml( template.render( {
                    'htmlbase': os.path.join( utils.scriptdir,'html'),
                    } ), QUrl("~") 
                    )

        self.workspace = QWebViewExtend( self, onNavEvent=self.m.onBrowserNav )
        self.tabs.addTab(self.workspace,'Workspace')

        self.toolbars = {}
        self.controls = defaultdict( dict ) # Store accessible controls
        
        self.register_url_handler( self.workspace_url_handler )
        self.setCentralWidget(self.tabs)
        
        self.config = QSettings()
        
        self.addFigureToolBar()
        
        self.workspace_item = self.m.addWorkspaceItem(self, None, self.name, is_selected=True, icon=QIcon( os.path.join( utils.scriptdir,'icons','home.png' )) )#, icon = None)

    def render(self):
        objects = []
        for v in self.m.views:
            objects.append( (v.id, v) )

        inheritance = []
        for v in self.m.views:
            # v.id = origin
            for i,ws in v.data.watchers.items():
                for w in ws:
                    inheritance.append( (v.id, w.v.id) ) # watcher->view->id
        print "************ REGENERATE *************"
        template = self.m.templateEngine.get_template('d3/workspace.svg')
        self.workspace.setSVG(template.render( {'htmlbase': os.path.join( utils.scriptdir,'html'), 'objects':objects, 'inheritance':inheritance} )) 

        f = open("/Users/mxf793/Desktop/workspace.svg",'w')
        f.write( template.render( {'htmlbase': os.path.join( utils.scriptdir,'html'), 'objects':objects, 'inheritance':inheritance} ) ) 
        f.close()
        
    # Url handler for all default plugin-related actions; making these accessible to all plugins
    # from a predefined url structure: metapath://<view.id>/default_actions/data_source/add
    def workspace_url_handler(self, url):

        kind, id, action = url.split('/') # FIXME: Can use split here once stop using pathwaynames           
        print "Workspace handler: %s" % url
        # url is Qurl kind
        # Add an object to the current view
        if kind == "view":
            if action == 'view':
                for v in self.m.views:
                    if v.id == id:
                        # We've got the view object; find index in the stack
                        si = self.m.stack.indexOf(v)
                        if si:
                            self.m.stack.setCurrentIndex(si)
                        break      

            elif action == "connect":
                #"metapath://home/view/4545179728:scores,4545247392:input/connect"                          
                #id = origin:int,dest:int
                origin, dest = [o.split(':') for o in id.split(',')]
                #o/d[0] == view, [1] == interface
                # We have the view ids; so find the real things
                for v in self.m.views:
                    if v.id == origin[0]:
                        origin[0] = v
                        break

                for v in self.m.views:
                    if v.id == dest[0]:
                        dest[0] = v
                        break
                
                # Get the origin data
                source_data = origin[0].data.o[origin[1]]
                
                # We now have the two views
                for d in dest[0].data.consumer_defs:
                    if d.target == dest[1]:
                        dest[0].data.consume_with(source_data, d)
                        break
                                    

# Data view prototypes

class DataView(GenericView):
    def __init__(self, plugin, parent, **kwargs):
        super(DataView, self).__init__(plugin, parent, **kwargs)

        self.summary = QWebViewExtend(self)
        self.table = QTableView()
        self.viewer = QWebViewExtend(self, onNavEvent=self.m.onBrowserNav) # Optional viewer; activate only if there is scale data

        self.tabs.addTab(self.table, tr('Table') )
        self.viewer_tab_index = self.tabs.addTab(self.viewer, tr('View'))
        self.tabs.setTabEnabled( self.viewer_tab_index, False)
        #self.tabs.addTab(self.summary, 'Summary')

    def render(self, metadata):
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

                template = self.m.templateEngine.get_template('d3/spectra.svg')
                self.viewer.setSVG(template.render( metadata ))

        return
        

# Import Data viewer

class ImportDataView( DataView ):

    import_type = tr('Data')
    import_filename_filter = tr("All Files") + " (*.*);;"
    import_description =  tr("Open experimental data from file")
    
    def __init__(self, plugin, parent, **kwargs):
        super(ImportDataView, self).__init__(plugin, parent, **kwargs)
    
        self.data.add_interface('output') # Add output slot
        self.table.setModel(self.data.o['output'].as_table)
        
        self.addImportDataToolbar()
        
        fn = self.onImportData()

    def onImportData(self):
        """ Open a data file"""
        filename, _ = QFileDialog.getOpenFileName(self.m, self.import_description, '', self.import_filename_filter)
        if filename:
            self.load_datafile( filename )

            self.file_watcher = QFileSystemWatcher()            
            self.file_watcher.fileChanged.connect( self.onFileChanged )
            self.file_watcher.addPath( filename )
            
            self.workspace_item.setText(0, os.path.basename(filename))
            
        return False

    def onFileChanged(self, file):
        pass
        #self.load_datafile( file )

    def addImportDataToolbar(self):   
        t = self.getCreatedToolbar( tr('External Data'),'external-data')
        
        import_dataAction = QAction( QIcon( os.path.join(  utils.scriptdir, 'icons', 'disk--arrow.png' ) ), 'Import %s file…' % self.import_type, self.m)
        import_dataAction.setStatusTip(self.import_description)
        import_dataAction.triggered.connect(self.onImportData)
        t.addAction(import_dataAction)
    
        self.addExternalDataToolbar()



# Analysis/Visualisation view prototypes


# Class for analysis views, using graph-based visualisations of defined datasets
# associated layout and/or analysis
class AnalysisView(GenericView):
    def __init__(self, plugin, parent, **kwargs):
        super(AnalysisView, self).__init__(plugin, parent, **kwargs)

        self.browser = QWebViewExtend( self, onNavEvent=parent.onBrowserNav )
        self.tabs.addTab(self.browser, tr('View') )
    
    def render(self, metadata, template='d3/figure.svg', target=None):
        if target == None:
            target = self.browser
            
        metadata['htmlbase'] = os.path.join( utils.scriptdir,'html')

        template = self.m.templateEngine.get_template(template)
        target.setSVG(template.render( metadata ))
                
        f = open("/Users/mxf793/Desktop/test.svg","w")
        f.write(template.render( metadata ))
        f.close()                
        
        
    # Build change table 
    def build_change_table_of_classes(self, dso, objs, classes):
        
        # Reduce dimensionality; combine all class/entity objects via np.mean()
        dso = dso.as_summary()
        
        #FIXME: Need to allow entities to be passed in and use entity / labels
        #entities = []
        #for o in objs:
        #    entities.extend( [ self.m.db.index[id] for id in o if id in self.m.db.index] )
         
           
        # Filter for the things we're displaying
        dso = dso.as_filtered( labels=objs)

        #data = data.as_class_grouped(classes=classes)
        data = np.zeros( (len(objs), len(classes)) )

        for y,l in enumerate(objs): #[u'PYRUVATE', u'PHOSPHO-ENOL-PYRUVATE']
            for x,c in enumerate(classes):
                try:
                    #e = self.m.db.index[o] # Get entity for lookup
                    data[y,x] = dso.data[ dso.classes[0].index(c), dso.labels[1].index(l) ]
                except: # Can't find it
                    pass
                
        return data
  
  
    def build_change_table_of_entitytypes(self, dso, objs, entityt):
        
        # Reduce dimensionality; combine all class/entity objects via np.mean()
        dso = dso.as_summary()
        
        entities = []
        for o in objs:
            entities.extend( [ self.m.db.index[id] for id in o if id in self.m.db.index] )
        # Filter for the things we're displaying
        dso = dso.as_filtered( entities=entities)

        #data = data.as_class_grouped(classes=classes)
        data = np.zeros( (len(objs), len(entityt)) )

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

        t = self.addToolBar( tr('Experiment') )
        t.setIconSize( QSize(16,16) )

        # DATA MENU
        define_experimentAction = QAction( QIcon( os.path.join( utils.scriptdir,'icons','layout-design.png') ), tr('Define experiment…'), self)
        define_experimentAction.setShortcut('Ctrl+Q')
        define_experimentAction.setStatusTip( tr('Define experiment control, test and timecourse settings') )
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
        self.toolbars['experiment'].cb_test.addItem("*")
        self.toolbars['experiment'].cb_test.addItems( [i for i in self.data.i['input'].classes_l[0]] )

    def onDataChanged(self):
        self.repopulate_experiment_classes()
        self.generate()
        
    def onDefineExperiment(self):
        pass

    def onModifyExperiment(self):
        """ Update the experimental settings for analysis then regenerate """    
        self._experiment_control = self.toolbars['experiment'].cb_control.currentText()
        self._experiment_test = self.toolbars['experiment'].cb_test.currentText()
        self.generate()
    
# Class for analysis views, using graph-based visualisations of defined datasets
# associated layout and/or analysis
class AnalysisD3View(AnalysisView):
        
    def render(self, metadata, debug=False, template_name='figure'):
        metadata['htmlbase'] = os.path.join( utils.scriptdir,'html')
        
        
        template = self.m.templateEngine.get_template('d3/%s.svg' % template_name)
        self.browser.setSVG(template.render( metadata ))

        self.m.workspace_updated.emit()
                
        f = open("/Users/mxf793/Desktop/test.svg","w")
        f.write(template.render( metadata ))
        f.close()                
        
# Class for analysis views, using graph-based visualisations of defined datasets
# associated layout and/or analysis
class D3View(AnalysisView):
    def __init__(self, plugin, parent, **kwargs):
        super(D3View, self).__init__(plugin, parent, **kwargs)        
    
        self.parent = parent
        self.browser = QWebViewExtend( self.tabs, onNavEvent=parent.onBrowserNav )
    
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

        self.browser.setSVG(template.render( metadata ))

          

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

    workspace_updated = pyqtSignal()

    def __init__(self):

        super(MainWindowUI, self).__init__()

        menubar = self.menuBar()
        self.menuBar = {
            'file': menubar.addMenu( tr('&File') ),
            'plugins': menubar.addMenu( tr('&Plugins') ),
            'database': menubar.addMenu( tr('&Database') ),
        }

        # FILE MENU 
        aboutAction = QAction(QIcon.fromTheme("help-about"), 'About', self)
        aboutAction.setStatusTip( tr('About MetaPath') )
        aboutAction.triggered.connect(self.onAbout)
        self.menuBar['file'].addAction(aboutAction)

        newAction = QAction(QIcon.fromTheme("new-workspace", QIcon( os.path.join( utils.scriptdir, 'icons', 'document-new.png') )), tr('&New Blank Workspace'), self)
        newAction.setShortcut('Ctrl+N')
        newAction.setStatusTip( tr('Create new blank workspace') )
        newAction.triggered.connect(self.onSaveAs)
        self.menuBar['file'].addAction(newAction)
        

        openAction = QAction(QIcon.fromTheme("open-workspace", QIcon( os.path.join( utils.scriptdir, 'icons', 'folder-open-document.png') )), tr('&Open…'), self)
        openAction.setShortcut('Ctrl+O')
        openAction.setStatusTip( tr('Open previous analysis workspace') )
        openAction.triggered.connect(self.onSaveAs)
        self.menuBar['file'].addAction(openAction)

        self.menuBar['file'].addSeparator()
                
        saveAction = QAction(QIcon.fromTheme("save-workspace", QIcon( os.path.join( utils.scriptdir, 'icons', 'disk.png') )), tr('&Save'), self)
        saveAction.setShortcut('Ctrl+S')
        saveAction.setStatusTip( tr('Save current workspace for future use') )
        saveAction.triggered.connect(self.onSaveAs)
        self.menuBar['file'].addAction(saveAction)

        saveAsAction = QAction(QIcon.fromTheme("save-workspace", QIcon( os.path.join( utils.scriptdir, 'icons', 'document-save-as.png') )), tr('Save &As…'), self)
        saveAsAction.setShortcut('Ctrl+A')
        saveAsAction.setStatusTip( tr('Save current workspace for future use') )
        saveAsAction.triggered.connect(self.onSaveAs)
        self.menuBar['file'].addAction(saveAsAction)

        self.menuBar['file'].addSeparator()        

        printAction = QAction(QIcon.fromTheme("document-print", QIcon( os.path.join( utils.scriptdir, 'icons', 'printer.png') )), tr('&Print…'), self)
        printAction.setShortcut('Ctrl+P')
        printAction.setStatusTip( tr('Print current figure') )
        printAction.triggered.connect(self.onPrint)
        self.menuBar['file'].addAction(printAction)

        self.menuBar['file'].addSeparator()        

        #exportImagesAction = QAction(QIcon.fromTheme("image-export", QIcon( os.path.join( utils.scriptdir, 'icons', 'image-export.png') )), tr('&Export figures…'), self)
        #exportImagesAction.setShortcut('Ctrl+E')
        #exportImagesAction.setStatusTip( tr('Save current figure') )
        #exportImagesAction.triggered.connect(self.onSaveCurrentFigure)
        #self.menuBar['file'].addAction(exportImagesAction)

        
        # DATABASE MENU
        load_identitiesAction = QAction(QIcon.fromTheme("document-import", QIcon( os.path.join( utils.scriptdir,'icons','database-import.png') )), tr('&Load database unification…'), self)
        load_identitiesAction.setStatusTip('Load additional unification mappings into database')
        load_identitiesAction.triggered.connect(self.onLoadIdentities)
        self.menuBar['database'].addAction(load_identitiesAction)
        
        self.menuBar['database'].addSeparator()
        
        reload_databaseAction = QAction(QIcon.fromTheme("system-restart-panel", QIcon( os.path.join( utils.scriptdir,'icons','exclamation-red.png') )), tr('&Reload database'), self)
        reload_databaseAction.setStatusTip('Reload pathway & metabolite database')
        reload_databaseAction.triggered.connect(self.onReloadDB)
        self.menuBar['database'].addAction(reload_databaseAction)
        
        
        # GLOBAL WEB SETTINGS
        QNetworkProxyFactory.setUseSystemConfiguration( True )

        QWebSettings.setMaximumPagesInCache( 0 )
        QWebSettings.setObjectCacheCapacities(0, 0, 0)
        QWebSettings.clearMemoryCaches()

        # Display a introductory helpfile 
        self.mainBrowser = QWebViewExtend( None, onNavEvent=self.onBrowserNav )
        
        self.pluginManager = PluginManagerSingleton.get()
        self.pluginManager.m = self
        
        self.pluginManager.setPluginPlaces([os.path.join( utils.scriptdir,'plugins')])
        categories_filter = {
               "Data" : plugins.DataPlugin,
               "Processing" : plugins.ProcessingPlugin,
               "Identification": plugins.IdentificationPlugin,
               "Analysis" : plugins.AnalysisPlugin,
               "Visualisation" : plugins.VisualisationPlugin,
#               tr("Output") : plugins.OutputPlugin,
#               tr("Misc") : plugins.MiscPlugin,
               }
        self.pluginManager.setCategoriesFilter(categories_filter)
        self.pluginManager.collectPlugins()

        plugin_categories = ["Data","Processing","Identification","Analysis","Visualisation"] #categories_filter.keys()
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

        self.dataDock = QDockWidget( tr('Database') )

        self.dbBrowser = QWebViewExtend( self.dataDock, onNavEvent=self.onBrowserNav )
        # Display a list of supporting orgs
        template = self.templateEngine.get_template('sponsors.html')
        self.dbBrowser.setHtml(template.render( {'htmlbase': os.path.join( utils.scriptdir,'html')} ),QUrl('~')) 
        
        self.dataDock.setWidget(self.dbBrowser)
        self.dataDock.setMinimumWidth(300)
        self.dataDock.setMaximumWidth(300)
        
        #self.dataDock.setFeatures(QDockWidget.NoDockWidgetFeatures)

        self.stack = QStackedWidget()
        self.views = []
        #self.stack.addWidget(self.mainBrowser)
        
        self.setCentralWidget(self.stack)

        self.stack.setCurrentIndex(0)

        self.workspace_count = 0 # Auto-increment
        self.workspace_parents = {}
        
        self.workspace = QTreeWidget()
        self.workspace.setColumnCount(4)
        #∞Σ⌘⁉★⌘↛⇲Σ▼◎♥⚑☺⬚↛⑃        
        self.workspace.setHeaderLabels(['','ID',' ◎',' ⚑']) #,'#'])
        self.workspace.setUniformRowHeights(True)
        self.workspace.hideColumn(1)
        

        self.home = HomeView(self)
        # Signals
        self.workspace_updated.connect( self.home.render )
        

        #self.addWorkspaceItem( self.home, None, 'Home', QIcon( os.path.join( utils.scriptdir,'icons','home.png' ) )   )
        
        app_category_icons = {
               "Data": QIcon.fromTheme("data", QIcon( os.path.join( utils.scriptdir,'icons','ruler.png' ) ) ),
               "Processing": QIcon.fromTheme("processing", QIcon( os.path.join( utils.scriptdir,'icons','ruler-triangle.png' ) ) ),
               "Identification": QIcon.fromTheme("identification", QIcon( os.path.join( utils.scriptdir,'icons','target.png' ) ) ),
               "Analysis": QIcon.fromTheme("analysis", QIcon( os.path.join( utils.scriptdir,'icons','calculator.png' ) ) ),
               "Visualisation": QIcon.fromTheme("visualisation", QIcon( os.path.join( utils.scriptdir,'icons','star.png' ) ) ),
               }
    
        template = self.templateEngine.get_template('apps.html')
        for category in plugin_categories:
            self.appBrowsers[ category ] = QWebViewExtend(  self.workspace, onNavEvent=self.onBrowserNav )
            self.appBrowsers[ category ].setHtml(template.render( 
                {
                'htmlbase': os.path.join( utils.scriptdir,'html'),
                'category': tr(category),
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

        self.workspaceDock = QDockWidget( tr('Workspace') )
        self.workspaceDock.setWidget(self.workspace)
        self.workspace.setHorizontalScrollBarPolicy( Qt.ScrollBarAlwaysOff )
        self.workspace.setColumnWidth(0, 298-25*2) 
        self.workspace.setColumnWidth(2, 24) 
        self.workspace.setColumnWidth(3, 24) 
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
        tw.setText(0, tr(title) )
        tw.setText(1, str( stack_index ) )
        
        if icon:
            tw.setIcon(0, icon )
        
        if section:
            self.workspace_parents[ section ].addChild(tw)
            self.workspace_updated.emit() # Notify change to workspace layout        
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
            'paused':  QIcon( os.path.join( utils.scriptdir,'icons','flag-white.png' ) ),
            'done':     QIcon( os.path.join( utils.scriptdir,'icons','flag-checker.png' ) ),
            'clear':    QIcon(None)
        }
            
        if status not in status_icons.keys():
            status = 'clear'

        workspace_item.setIcon(3, status_icons[status] )
        self.workspace.update( self.workspace.indexFromItem( workspace_item ) )
        self.app.processEvents()

    def clearWorkspaceStatus(self, workspace_item):
        self.setWorkspaceStatus(workspace_item, 'clear')        
        
    def onPathwayMiningToggle(self, checked):
        self.config.setValue( '/Data/MiningActive', checked)
        self.generateGraphView()


    def register_url_handler( self, identifier, url_handler ):
        self.url_handlers[ identifier ].append( url_handler )
        

    
