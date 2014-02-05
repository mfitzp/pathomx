#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os, sys, re, math, codecs, locale, json, importlib, functools

UTF8Writer = codecs.getwriter('utf8')
sys.stdout = UTF8Writer(sys.stdout)
reload(sys).setdefaultencoding('utf8')

# Import PyQt5 classes
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWebKit import *
from PyQt5.QtNetwork import *
from PyQt5.QtWidgets import *
from PyQt5.QtWebKitWidgets import *
from PyQt5.QtPrintSupport import *

import urllib2, textwrap

from optparse import Values
from collections import defaultdict

import numpy as np

from yapsy.PluginManager import PluginManager, PluginManagerSingleton

# wheezy templating engine
from wheezy.template.engine import Engine
from wheezy.template.ext.core import CoreExtension
from wheezy.template.ext.code import CodeExtension
from wheezy.template.loader import FileLoader

try:
    import xml.etree.cElementTree as et
except ImportError:
    import xml.etree.ElementTree as et
    
import matplotlib as mpl

# Pathomx classes
import db, data, utils, ui, threads, custom_exceptions # core, layout - removed to plugin MetaViz, figure -deprecated in favour of d3
import plugins # plugin helper/manager
from editor.editor import WorkspaceEditor

# Translation (@default context)
from translate import tr

import logging
logging.basicConfig(level=logging.DEBUG)


class DialogAbout(QDialog):
    def __init__(self, parent, **kwargs):
        super(DialogAbout, self).__init__(parent, **kwargs)        


        self.help = ui.QWebViewExtend(self, parent.onBrowserNav)
        template = parent.templateEngine.get_template('about.html')
        self.help.setHtml( template.render( {
                    'htmlbase': os.path.join( utils.scriptdir,'html'),
                    } ), QUrl("~")
                    )
                    
        self.layout = QVBoxLayout()
        self.layout.addWidget( self.help )

        # Setup default button configurations etc.
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Close)
        self.buttonBox.rejected.connect(self.close)
        self.layout.addWidget( self.buttonBox )
        self.setLayout(self.layout)                

    def sizeHint(self):
        return QSize(600,400)


class dialogDefineExperiment(ui.genericDialog):
    
    def filter_classes_by_timecourse_regexp(self, text):
        try:
            rx = re.compile('(?P<timecourse>%s)' % text)                
        except:
            return
        
        filtered_classes = list( set(  [rx.sub('',c) for c in self.classes] ) )
        self.cb_control.clear()
        self.cb_control.addItems( filtered_classes )
        self.cb_test.clear()
        self.cb_test.addItems( filtered_classes )
        # Ensure something remains selected
        self.cb_control.setCurrentIndex(0)
        self.cb_test.setCurrentIndex(0)
        

    def __init__(self, parent=None, **kwargs):
        super(dialogDefineExperiment, self).__init__(parent, **kwargs)        
        
        self.classes = sorted( parent.data.classes )
        self.setWindowTitle("Define Experiment")


        self.cb_control = QComboBox()
        self.cb_control.addItems(self.classes)

        self.cb_test = QComboBox()
        self.cb_test.addItems(self.classes)
        
        classes = QGridLayout()
        classes.addWidget( QLabel('Control:'), 1, 1)
        classes.addWidget( self.cb_control, 1, 2)

        classes.addWidget( QLabel('Test:'), 2, 1)
        classes.addWidget( self.cb_test, 2, 2)
        
        if 'control' in parent.experiment and 'test' in parent.experiment:
            self.cb_control.setCurrentIndex( self.cb_control.findText( parent.experiment['control'] ) )
            self.cb_test.setCurrentIndex( self.cb_test.findText( parent.experiment['test'] ) )
        else:
            self.cb_control.setCurrentIndex(0)
            self.cb_test.setCurrentIndex(0)

            
        self.le_timecourseRegExp = QLineEdit()
        self.le_timecourseRegExp.setText( parent.experiment['timecourse'] if 'timecourse' in parent.experiment else '' )
        self.le_timecourseRegExp.textChanged.connect(self.filter_classes_by_timecourse_regexp)
            
        self.layout.addLayout(classes)
        self.layout.addWidget(QLabel('Timecourse filter (regexp:'))
        self.layout.addWidget(self.le_timecourseRegExp)

        if 'timecourse' in parent.experiment:
            self.filter_classes_by_timecourse_regexp( parent.experiment['timecourse'] )

        # Build dialog layout
        self.dialogFinalise()
        



class toolBoxItemDelegate(QAbstractItemDelegate):

    def __init__(self, parent=None,**kwargs):
        super(toolBoxItemDelegate, self).__init__(parent, **kwargs)
        self._elidedwrappedtitle = {} #Cache
            
    def paint( self, painter, option, index):
        # GET TITLE, DESCRIPTION AND ICON
        icon = index.data(Qt.DecorationRole)
        title = index.data(Qt.DisplayRole) #.toString()
        #description = index.data(Qt.UserRole) #.toString()
        #notice = index.data(Qt.UserRole+1) #.toString()

        if option.state & QStyle.State_Selected:
            painter.setPen( QPalette().highlightedText().color() )
            painter.fillRect(option.rect, QBrush(QPalette().highlight().color()) )
        else:
            painter.setPen( QPalette().text().color() )
            
        
        icon.paint(painter, option.rect.adjusted(2,2,-2,-34), Qt.AlignVCenter|Qt.AlignLeft)

        text_rect = option.rect.adjusted(0,64,0,0)
        font=QFont()
        font.setPointSize(11)
        painter.setFont(font)     
        
        if title not in self._elidedwrappedtitle:   
             self._elidedwrappedtitle[title] = self.elideWrapText( painter, title, text_rect )

        painter.drawText(text_rect, Qt.AlignTop|Qt.AlignHCenter|Qt.TextWordWrap, self._elidedwrappedtitle[title]) 
        #painter.drawText(text_rect.x(), text_rect.y(), text_rect.width(), text_rect.height(),, 'Hello this is a long title', boundingRect=text_rect)

    def elideWrapText(self,painter, text, text_rect):
        text = textwrap.wrap(text, 10, break_long_words=False)
        wrapped_text = []
        for l in text[:2]: # Max 2 lines
            l = painter.fontMetrics().elidedText(l, Qt.ElideRight, text_rect.width() )
            wrapped_text.append( l )
        wrapped_text = '\n'.join(wrapped_text)
        return wrapped_text

    def sizeHint( self, option, index ):
        return QSize(64,96)   

class ToolBoxItem(QListWidgetItem):
    def __init__(self, data=None, parent=None,**kwargs):
        super(ToolBoxItem, self).__init__(parent, **kwargs)
        self.data = data
        
class ToolPanel(QListWidget):

    def __init__(self, parent, tools=[], **kwargs):
        super(ToolPanel, self).__init__(parent, **kwargs)

        self.setViewMode( QListView.IconMode )
        self.setGridSize( QSize(64,96) )
        #self._columns = 4 
        self.setItemDelegate(toolBoxItemDelegate())
        
        self.tools = tools   
        self.addTools()
        
        #self.setLayout(self.vlayout)
        #self.vlayout.addLayout( self.grid )
        #self.vlayout.addItem( QSpacerItem(10, 10, QSizePolicy.Maximum) )
        
    def addTools(self):
        
        
        for n, tool in enumerate(self.tools):
            #col = n % self._columns
            #row = n // self._columns
            
            #print tool
            t = ToolBoxItem(data=tool)
            #t.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            t.setIcon( tool['plugin'].icon )
            #t.setIconSize( QSize(32, 32) )
            t.setText( getattr(tool['app'], 'name', tool['plugin'].name) )
            self.addItem(t)
            
            #t = ToolItem(QIcon( tool['icon']), tool['name'], data=tool)
            #self.grid.addWidget( t, row, col )
            
            
    def colX(self, col):
        return col * self._tool_width 

    def rowY(self, row):
        return row * self._tool_width 

    def mouseMoveEvent(self, e):

        item = self.currentItem()

        mimeData = QMimeData()
        mimeData.setData('application/x-pathomx-app', item.data['id']);

        drag = QDrag(self)
        drag.setMimeData(mimeData)
        drag.setPixmap(item.data['plugin'].pixmap.scaled( QSize(64,64), transformMode = Qt.SmoothTransformation ) )
        drag.setHotSpot(e.pos() - self.visualItemRect(item).topLeft())
        
        dropAction = drag.exec_(Qt.MoveAction)
     
     
class MainWindow(QMainWindow):

    workspace_updated = pyqtSignal()

    def __init__(self, app):
        super(MainWindow, self).__init__()
        
        self.app = app
        # Central variable for storing application configuration (load/save from file?
        self.config = QSettings()
        
        # Create database accessor
        self.db = db.databaseManager()
        self.data = None #deprecated
        self.datasets = [] #List of instances of data.datasets() // No data loaded by default

        self.experiment = dict()
        self.layout = None # No map by default

        # The following holds tabs & pathway objects for gpml imported pathways
        self.gpmlpathways = [] 
        self.tab_handlers = []
        self.url_handlers = defaultdict(list)
        self.app_launchers = {}
        self.app_launcher_categories = defaultdict(list)
        self.file_handlers = {}

        # Create templating engine
        self.templateEngine = Engine(
            loader=FileLoader( [os.path.join( utils.scriptdir,'html')] ),
            extensions=[CoreExtension(),CodeExtension()]
        )
        self.templateEngine.global_vars.update({'tr': tr})

        self.update_view_callback_enabled = True

        self.printer = QPrinter()
        
        QNetworkProxyFactory.setUseSystemConfiguration(True)

        #  UI setup etc
        menubar = self.menuBar()
        self.menuBar = {
            'file': menubar.addMenu( tr('&File') ),
            'plugins': menubar.addMenu( tr('&Plugins') ),
            'database': menubar.addMenu( tr('&Database') ),
            'help': menubar.addMenu( tr('&Help') ),
        }

        # FILE MENU 
        aboutAction = QAction(QIcon.fromTheme("help-about"), 'About', self)
        aboutAction.setStatusTip( tr('About Pathomx') )
        aboutAction.triggered.connect(self.onAbout)
        self.menuBar['file'].addAction(aboutAction)

        newAction = QAction( QIcon( os.path.join( utils.scriptdir, 'icons', 'document.png') ), tr('&New Blank Workspace'), self)
        newAction.setShortcut('Ctrl+N')
        newAction.setStatusTip( tr('Create new blank workspace') )
        newAction.triggered.connect(self.onClearWorkspace)
        self.menuBar['file'].addAction(newAction)
        

        openAction = QAction( QIcon( os.path.join( utils.scriptdir, 'icons', 'folder-open-document.png') ), tr('&Open…'), self)
        openAction.setShortcut('Ctrl+O')
        openAction.setStatusTip( tr('Open previous analysis workspace') )
        openAction.triggered.connect(self.onOpenWorkspace)
        #self.menuBar['file'].addAction(openAction)

        openAction = QAction( QIcon( os.path.join( utils.scriptdir, 'icons', 'folder-open-document.png') ), tr('&Open Workflow…'), self)
        openAction.setStatusTip( tr('Open an analysis workflow') )
        openAction.triggered.connect(self.onOpenWorkflow)
        self.menuBar['file'].addAction(openAction)

        self.menuBar['file'].addSeparator()
                
        saveAction = QAction( QIcon( os.path.join( utils.scriptdir, 'icons', 'disk.png') ), tr('&Save'), self)
        saveAction.setShortcut('Ctrl+S')
        saveAction.setStatusTip( tr('Save current workspace for future use') )
        saveAction.triggered.connect(self.onSaveWorkspace)
        #self.menuBar['file'].addAction(saveAction)

        saveAsAction = QAction( QIcon( os.path.join( utils.scriptdir, 'icons', 'disk--pencil.png') ), tr('Save &As…'), self)
        saveAsAction.setShortcut('Ctrl+A')
        saveAsAction.setStatusTip( tr('Save current workspace for future use') )
        saveAsAction.triggered.connect(self.onSaveWorkspaceAs)
        #self.menuBar['file'].addAction(saveAsAction)

        saveAsAction = QAction( QIcon( os.path.join( utils.scriptdir, 'icons', 'disk--pencil.png') ), tr('Save Workflow As…'), self)
        saveAsAction.setStatusTip( tr('Save current workflow for future use') )
        saveAsAction.triggered.connect(self.onSaveWorkflowAs)
        self.menuBar['file'].addAction(saveAsAction)


        self.menuBar['file'].addSeparator()        

        printAction = QAction( QIcon( os.path.join( utils.scriptdir, 'icons', 'printer.png') ), tr('&Print…'), self)
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
        load_identitiesAction = QAction( QIcon( os.path.join( utils.scriptdir,'icons','database-import.png') ), tr('&Load database unification…'), self)
        load_identitiesAction.setStatusTip('Load additional unification mappings into database')
        load_identitiesAction.triggered.connect(self.onLoadIdentities)
        self.menuBar['database'].addAction(load_identitiesAction)
        
        self.menuBar['database'].addSeparator()
        
        reload_databaseAction = QAction( QIcon( os.path.join( utils.scriptdir,'icons','exclamation-red.png') ), tr('&Reload database'), self)
        reload_databaseAction.setStatusTip('Reload pathway & metabolite database')
        reload_databaseAction.triggered.connect(self.onReloadDB)
        self.menuBar['database'].addAction(reload_databaseAction)
        
        
        # PLUGINS MENU
        
        change_pluginsAction = QAction( tr('&Manage plugins…'), self)
        change_pluginsAction.setStatusTip('Find, activate, deactivate and remove plugins')
        change_pluginsAction.triggered.connect(self.onChangePlugins)
        self.menuBar['plugins'].addAction(change_pluginsAction)
    
        check_pluginupdatesAction = QAction( tr('&Check for updated plugins'), self)
        check_pluginupdatesAction.setStatusTip('Check for updates to installed plugins')
        check_pluginupdatesAction.triggered.connect(self.onCheckPluginUpdates)
        #self.menuBar['plugins'].addAction(check_pluginupdatesAction)  FIXME: Add a plugin-update check  

        aboutAction = QAction(QIcon.fromTheme("help-about"), 'Introduction', self)
        aboutAction.setStatusTip( tr('About Pathomx') )
        aboutAction.triggered.connect(self.onAbout)
        self.menuBar['help'].addAction(aboutAction)

        goto_pathomx_websiteAction = QAction( tr('&Pathomx website'), self)
        goto_pathomx_websiteAction.setStatusTip('Go to the Pathomx website')
        goto_pathomx_websiteAction.triggered.connect(self.onGoToPathomxWeb)
        self.menuBar['help'].addAction(goto_pathomx_websiteAction)

        goto_pathomx_demosAction = QAction( tr('&Pathomx demos'), self)
        goto_pathomx_demosAction.setStatusTip('Watch Pathomx demo videos')
        goto_pathomx_demosAction.triggered.connect(self.onGoToPathomxDemos)
        self.menuBar['help'].addAction(goto_pathomx_demosAction)


        # GLOBAL WEB SETTINGS
        QNetworkProxyFactory.setUseSystemConfiguration( True )

        QWebSettings.setMaximumPagesInCache( 0 )
        QWebSettings.setObjectCacheCapacities(0, 0, 0)
        QWebSettings.clearMemoryCaches()

        # Display a introductory helpfile 
        self.mainBrowser = ui.QWebViewExtend( None, onNavEvent=self.onBrowserNav )
        
        self.plugins = {} # Dict of plugin shortnames to data
        self.plugins_obj = {} # Dict of plugin name references to objs (for load/save)
        self.pluginManager = PluginManagerSingleton.get()
        self.pluginManager.m = self
        
        self.plugin_places = []
        self.core_plugin_path = os.path.join( utils.scriptdir,'plugins')
        self.plugin_places.append( self.core_plugin_path )
        
        user_application_data_paths = QStandardPaths.standardLocations( QStandardPaths.DataLocation )
        if user_application_data_paths:
            self.user_plugin_path = os.path.join(user_application_data_paths[0], 'plugins' )
            utils.mkdir_p( self.user_plugin_path ) 
            self.plugin_places.append( self.user_plugin_path )
            
            self.application_data_path = os.path.join(user_application_data_paths[1])
            
        print "Search for plugins..."
        print ', '.join( self.plugin_places )

        self.tools = defaultdict(list)
            
        self.pluginManager.setPluginPlaces(self.plugin_places)
        self.pluginManager.setPluginInfoExtension( 'pathomx-plugin' )
        categories_filter = {
               "Import" : plugins.ImportPlugin,
               "Processing" : plugins.ProcessingPlugin,
               "Identification": plugins.IdentificationPlugin,
               "Analysis" : plugins.AnalysisPlugin,
               "Visualisation" : plugins.VisualisationPlugin,
               "Export" : plugins.ExportPlugin,
               }
        self.pluginManager.setCategoriesFilter(categories_filter)
        self.pluginManager.collectPlugins()

        plugin_categories = ["Import","Processing","Identification","Analysis","Visualisation","Export"] #categories_filter.keys()
        apps = defaultdict(list)
        self.appBrowsers = {}
        self.plugin_names = dict()
        self.plugin_metadata = dict()
        
        
        # Loop round the plugins and print their names.
        for category in plugin_categories:
            for plugin in self.pluginManager.getPluginsOfCategory(category):
                
                plugin_image = os.path.join( os.path.dirname(plugin.path), 'icon.png' )

                if not os.path.isfile( plugin_image ):
                    plugin_image = None
                    
                plugin_path = plugin._PluginInfo__details.get('Core','Module')

                metadata = {
                    'id': plugin.plugin_object.__class__.__name__, #__module__, 
                    'image': plugin_image,    
                    'image_forward_slashes': plugin_image.replace('\\','/'), # Slashes fix for CSS in windows
                    'name': plugin.name,
                    'version': plugin.version,
                    'description': plugin.description,
                    'info': plugin, 
                    'path': os.path.dirname(plugin_path),
                    'module': os.path.basename(plugin_path),
                    'shortname': os.path.basename(plugin_path),
                    'is_core_plugin': plugin_path.startswith(self.core_plugin_path)
                }

                self.plugins[ metadata['shortname'] ] = metadata
                self.plugin_names[ id( plugin.plugin_object ) ] = plugin.name
                
                plugin.plugin_object.post_setup(path=os.path.dirname(plugin.path), name=plugin.name )
                
                apps[category].append(metadata)


        self.stack = QStackedWidget()
        self.apps = []
        
        self.threadpool = QThreadPool()
        print "Multithreading with maximum %d threads" % self.threadpool.maxThreadCount()
        
        #self.stack.addWidget(self.mainBrowser)
        
        self.setCentralWidget(self.stack)

        self.stack.setCurrentIndex(0)
        
        self.workspace_count = 0 # Auto-increment
        self.workspace_parents = {}
        self.workspace_index = {} # id -> obj
        
        self.workspace = QTreeWidget()
        self.workspace.setColumnCount(4)
        self.workspace.expandAll()
        
        #∞Σ⌘⁉★⌘↛⇲Σ▼◎♥⚑☺⬚↛⑃        
        self.workspace.setHeaderLabels(['','ID',' ◎',' ⚑']) #,'#'])
        self.workspace.setUniformRowHeights(True)
        self.workspace.hideColumn(1)

        self.editor = WorkspaceEditor(self)   
        self.setCentralWidget(self.editor)
        
        app_category_icons = {
               "Import": QIcon( os.path.join( utils.scriptdir,'icons','disk--arrow.png' ) ),
               "Processing": QIcon( os.path.join( utils.scriptdir,'icons','ruler-triangle.png' ) ),
               "Identification": QIcon( os.path.join( utils.scriptdir,'icons','target.png' ) ),
               "Analysis": QIcon( os.path.join( utils.scriptdir,'icons','calculator.png' ) ),
               "Visualisation": QIcon( os.path.join( utils.scriptdir,'icons','star.png' ) ),
               "Export": QIcon( os.path.join( utils.scriptdir,'icons','disk--pencil.png' ) ),
               }
    
        template = self.templateEngine.get_template('apps.html')
        for category in plugin_categories:
            self.addWorkspaceItem( None, None, category, app_category_icons[category] )

        self.workspace.setSelectionMode( QAbstractItemView.SingleSelection )
        self.workspace.currentItemChanged.connect( self.onWorkspaceStackChange)

        #self.dbBrowser = ui.QWebViewExtend( self.dataDock, onNavEvent=self.onBrowserNav )
        #self.dbBrowser.setHtml(template.render( {'htmlbase': os.path.join( utils.scriptdir,'html')} ),QUrl('~')) 

        self.toolbox = QToolBox(self)
        for category in plugin_categories:
            panel = ToolPanel(self, tools=self.tools[category])
            self.toolbox.addItem( panel, app_category_icons[category], category )
            
        self.toolDock = QDockWidget( tr('Toolkit') )
        self.toolDock.setWidget(self.toolbox)

        self.workspaceDock = QDockWidget( tr('Workspace') )
        self.workspaceDock.setWidget(self.workspace)
        self.workspace.setHorizontalScrollBarPolicy( Qt.ScrollBarAlwaysOff )
        self.workspace.setColumnWidth(0, 298-25*2) 
        self.workspace.setColumnWidth(2, 24) 
        self.workspace.setColumnWidth(3, 24) 
        self.workspaceDock.setMinimumWidth(300)
        self.workspaceDock.setMaximumWidth(300)

        self.dataView = QTreeView(self)
        self.dataModel = data.DataTreeModel(self.datasets)
        self.dataView.setModel(self.dataModel);
        self.dataView.hideColumn(0)

        self.dataDock = QDockWidget( tr('Data') )
        self.dataDock.setWidget(self.dataView)
        self.dataDock.setMinimumWidth(300)
        self.dataDock.setMaximumWidth(300)

        self.addDockWidget(Qt.LeftDockWidgetArea, self.dataDock)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.workspaceDock)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.toolDock)

        self.tabifyDockWidget( self.toolDock, self.workspaceDock)
        self.tabifyDockWidget( self.workspaceDock, self.dataDock)
        self.toolDock.raise_()

        if self.config.value('/Pathomx/Is_Setup') != True:
            print "Setting up initial configuration..."
            self.onResetConfig()
        
            print 'Done'
        
        self.onResetConfig()

        self.setWindowTitle( tr('Pathomx') )
        
        self.progressBar = QProgressBar(self.statusBar())      
        self.progressBar.setMaximumSize( QSize(170,19) )
        self.progressBar.setRange(0,100)
        self.statusBar().addPermanentWidget( self.progressBar )
        self.progressTracker = {} # Dict storing values for each view/object

        self.statusBar().showMessage( tr('Ready') )
        self.showMaximized()

    
    def onChangePlugins(self):
        dialog = plugins.dialogPluginManagement(self)
        if dialog.exec_():
            pass
        
    def onCheckPluginUpdates(self):
        pass
        
    # Init application configuration
    def onResetConfig(self):
        # Defaults not set, apply now and save complete config file
        self.config.setValue('Pathomx/Is_Setup', True)
        self.config.setValue('Plugins/Active', [])
        self.config.setValue('Plugins/Disabled', [])
        self.config.setValue('Plugins/Available', [])
        self.config.setValue('Plugins/Paths', [])
        
    
    # UI Events        
    
    def onGoToPathomxWeb(self):
        QDesktopServices.openUrl( QUrl('http://pathomx.org') )

    def onGoToPathomxDemos(self):
        QDesktopServices.openUrl( QUrl('http://pathomx.org/demos') )
   

    def onPrint(self):
        dialog = QPrintDialog(self.printer, self)
        if dialog.exec_():
            self.mainBrowser.print_(self.printer)
                    
    def onZoomOut(self):
        zf = self.mainBrowser.zoomFactor()
        zf = max(0.5, zf - 0.1)
        self.mainBrowser.setZoomFactor( zf )

    def onZoomIn(self):
        zf = self.mainBrowser.zoomFactor()
        zf = min(1.5, zf + 0.1)
        self.mainBrowser.setZoomFactor( zf )

    def onBrowserNav(self, url):
        # Interpret internal URLs for message passing to display Compound, Reaction, Pathway data in the sidebar interface
        # then block the continued loading
        if url.isRelative() and url.hasFragment():
            # Local #url; pass to default handler
            pass

        if url.scheme() == 'pathomx':
            # Take string from pathomx:// onwards, split on /
            app = url.host()
            if app == 'app-manager':
                app, action = url.path().strip('/').split('/')
                if action == 'add':
                    a = self.app_launchers[ app ]()


                # Update workspace viewer
                self.workspace_updated.emit() # Notify change to workspace layout        
                        

            elif app == 'db':
                kind, id, action = url.path().strip('/').split('/')
                            # View an object
                if action == 'view':
                    if kind == 'pathway' and id in self.db.pathways:
                        pathway = self.db.pathways[id]
                        self.generatedbBrowserView(template='db/pathway.html', data={
                            'title': pathway.name,
                            'object': pathway,
                            })
                    elif kind == 'reaction' and id in self.db.reactions:
                        reaction = self.db.reactions[id]
                        self.generatedbBrowserView(template='db/reaction.html', data={
                            'title': reaction.name,
                            'object': reaction,
                            })
                    elif kind == 'compound' and id in self.db.compounds:
                        compound = self.db.compounds[id]
                        self.generatedbBrowserView(template='db/compound.html', data={
                            'title': compound.name,
                            'object': compound,
                            })
                    elif kind == 'protein' and id in self.db.proteins:
                        protein = self.db.proteins[id]
                        self.generatedbBrowserView(template='db/protein.html', data={
                            'title': protein.name,
                            'object': protein,
                            })
                    elif kind == 'gene' and id in self.db.genes:
                        gene = self.db.genes[id]
                        self.generatedbBrowserView(template='db/gene.html', data={
                            'title': gene.name,
                            'object': gene,
                            })
                            
                    # Focus the database dock
                    self.dataDock.raise_()

            #metaviz/compound/%s/view            
            elif app in self.url_handlers:
                for handler in self.url_handlers[app]:
                    handler( url.path().strip('/') )

            # Store URL so we can reload the sidebar later
            self.dbBrowser_CurrentURL = url

        else:
            # It's an URL open in default browser
            QDesktopServices.openUrl(url)
             
    def onBrowserLoadDone(self, ok):
        # Reload the sidebar on main window refresh: this is only bound to the main window so no need to check for action
        pass
        #if isinstance(self.dbBrowser_CurrentURL, QUrl): # We've got an url, reload
        #    self.onBrowserNav(self.dbBrowser_CurrentURL)

    def onLoadIdentities(self):
        """ Open a data file"""
        filename, _ = QFileDialog.getOpenFileName(self, 'Load compound identities file', '')
        if filename:
            self.db.load_synonyms(filename)
            # Re-translate the datafile if there is one and refresh
            if self.data:
                self.data.translate(self.db)
                self.generateGraphView(regenerate_analysis=True)                

    
    def onSaveAs(self):
        """ Save a copy of the graph as one of the supported formats"""
        # Note this will regenerate the graph with the current settings, with output type specified appropriately
        filename, _ = QFileDialog.getSaveFileName(self, 'Save current metabolic pathway map', '')
        if filename:
            fn, ext = os.path.splitext(filename)
            format = ext.replace('.','')
            # Check format is supported
            if format in ['bmp', 'canon', 'dot', 'xdot', 'cmap', 'eps', 'fig', 'gd', 'gd2', 'gif', 'gtk', 'ico', 'imap', 'cmapx', 'imap_np', 'cmapx_np', 'ismap', 'jpg', 'jpeg', 'jpe', 'pdf', 'plain', 'plain-ext', 'png', 'ps', 'ps2', 'svg', 'svgz', 'tif', 'tiff', 'vml', 'vmlz', 'vrml', 'wbmp', 'webp', 'xlib']:
                self.generateGraph( filename, format)
            else:
                # Unsupported format error
                pass

    def onAbout(self):
        dlg = DialogAbout(self)
        dlg.exec_()


    def onExit(self):
        self.Close(True)  # Close the frame.

    def onReloadDB(self):
        self.db=db.databaseManager()

    def onRefresh(self):
        self.generateGraphView()
 
 
    def generatedbBrowserView(self, template='base.html', data={'title':'', 'object':{}, 'data':{} }):
        metadata = {
            'htmlbase': os.path.join( utils.scriptdir,'html'),
            # Current state data
            'current_pathways': [], #self.config.value('/Pathways/Show').split(','),
            'data': self.data,
            # Color schemes
            # 'rdbu9':['b2182b', 'd6604d', 'f4a582', '33a02c', 'fddbc7', 'f7f7f7', 'd1e5f0', '92c5de', '4393c3', '2166ac']
        }
            
        template = self.templateEngine.get_template(template)
        self.dbBrowser.setHtml(template.render( dict( data.items() + metadata.items() ) ),QUrl("~")) 
     

    def onWorkspaceStackChange(self, item, previous):
        widget = self.workspace_index[ item.text(1) ]
        if widget:
            widget.show()
            widget.raise_()

    def addWorkspaceItem(self, widget, section, title, icon = None):

        tw = QTreeWidgetItem()
        wid = str( id( tw ) )
        tw.setText(0, tr(title) )
        tw.setText(1, wid )

        if widget:        
            widget._workspace_index = wid
            
        self.workspace_index[ wid ] = widget
        
        if icon:
            tw.setIcon(0, icon )
        
        if section:
            self.workspace_parents[ section ].addChild(tw)
            widget._workspace_section = self.workspace_parents[ section ]
            widget._workspace_tree_widget = tw
        else:
            self.workspace.addTopLevelItem(tw) 
            self.workspace_parents[ title ] = tw
            tw.setExpanded(True)

        return tw
        
    def removeWorkspaceItem(self, widget):
        del self.workspace_index[ widget._workspace_index ] 
        widget._workspace_section.removeChild( widget._workspace_tree_widget )

    
    def setWorkspaceStatus(self, workspace_item, status):
        status_icons = {
            'active':  QIcon( os.path.join( utils.scriptdir,'icons','flag-green.png' ) ),
            'render':  QIcon( os.path.join( utils.scriptdir,'icons','flag-purple.png' ) ),
            'waiting': QIcon( os.path.join( utils.scriptdir,'icons','flag-yellow.png' ) ),
            'error':   QIcon( os.path.join( utils.scriptdir,'icons','flag-red.png' ) ),
            'paused':  QIcon( os.path.join( utils.scriptdir,'icons','flag-white.png' ) ),
            'done':    QIcon( os.path.join( utils.scriptdir,'icons','flag-checker.png' ) ),
            'clear':   QIcon(None)
        }
            
        if status not in status_icons.keys():
            status = 'clear'

        workspace_item.setIcon(3, status_icons[status] )
        self.workspace.update( self.workspace.indexFromItem( workspace_item ) )
    
        # Keep things ticking
        QCoreApplication.processEvents()
        
        if status == 'active': # Starting
            self.updateProgress( workspace_item, 0)
        
        elif status == 'clear' or status == 'error':
            self.updateProgress( workspace_item, None)
        
        elif status == 'done': # Flash done then clear in a bit
            self.updateProgress( workspace_item, 1)
            statusclearCallback = functools.partial(self.setWorkspaceStatus, workspace_item, 'clear')            
            workspace_item.status_timeout =  QTimer.singleShot(1000, statusclearCallback)
            
        
    def clearWorkspaceStatus(self, workspace_item):
        self.setWorkspaceStatus(workspace_item, 'clear')      
          
        
    def updateProgress(self, workspace_item, progress):

        if progress == None:
            if workspace_item in self.progressTracker:
                del( self.progressTracker[ workspace_item ] )
            if len(self.progressTracker) == 0:
                self.progressBar.reset()
                return
        else:
            self.progressTracker[ workspace_item ] = progress
    
        m = 100.0/len( self.progressTracker )
        pt = sum([n*m for n in self.progressTracker.values()])

        if self.progressBar.value() < pt: # Don't go backwards it's annoying FIXME: once hierarchical prediction; stack all things that 'will' start
            self.progressBar.setValue(pt)
            
        # Keep things ticking
        #QCoreApplication.processEvents()


    def register_url_handler( self, identifier, url_handler ):
        self.url_handlers[ identifier ].append( url_handler )
        
    ### OPEN/SAVE WORKSPACE
            
    def onOpenWorkspace(self):
        self.openWorkspace('/Users/mxf793/Desktop/test.mpw')
        
    def openWorkspace(self):
        pass        
        
    def onSaveWorkspace(self):
        self.saveWorkspace('/Users/mxf793/Desktop/test.mpw')

    def onSaveWorkspaceAs(self):
        self.saveWorkspace('/Users/mxf793/Desktop/test.mpw')
    
    def saveWorkspace(self, fn):
        pass
        
    ### RESET WORKSPACE
    
    def onClearWorkspace(self):
        reply = QMessageBox.question(self, "Clear Workspace", "Are you sure you want to clear the workspace? Everything will be deleted.",
                            QMessageBox.Yes|QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.clearWorkspace()
    
    def clearWorkspace(self):
        for v in self.apps[:]: # Copy as v.delete modifies the self.apps list
            v.delete()
            
        # Remove all workspace datasets
        del self.datasets[:]

        self.workspace_updated.emit()    
    

    ### OPEN/SAVE WORKFLOWS

    def onSaveWorkflowAs(self):
        filename, _ = QFileDialog.getSaveFileName(self, 'Save current workflow', '',  "Pathomx Workflow Format (*.mpf)")
        if filename:
            self.saveWorkflow(filename)
            
        
    def saveWorkflow(self, fn):
        
        root = et.Element("Workflow")
        root.set('xmlns:mpwfml', "http://pathomx.org/schema/Workflow/2013a")
    
        # Build a JSONable object representing the entire current workspace and write it to file
        for v in self.apps:
            app = et.SubElement(root, "App")
            app.set("id", v.id)
            
            name = et.SubElement(app, "Name")
            name.text = v.name
            
            plugin = et.SubElement(app, "Plugin")
            plugin.set("version", '1.0')
            plugin.text = v.plugin.__class__.__name__

            plugin_class = et.SubElement(app, "Launcher")
            plugin_class.text = v.__class__.__name__

            position = et.SubElement(app, "EditorXY")
            position.set("x", str( v.editorItem.x() ))
            position.set("y", str( v.editorItem.y() ))

            config = et.SubElement(app, "Config")
            print v.config.config
            for ck,cv in v.config.config.items():
                co = et.SubElement(config, "ConfigSetting")
                co.set("id", ck)
                co.set("type", type(cv).__name__)
                co.text = str(cv)

            datasources = et.SubElement(app, "DataInputs")
            # Build data inputs table (outputs are pre-specified by the object; this == links)
            for sk,si in v.data.i.items():
                if si: # Something on this interface
                    cs = et.SubElement(datasources, "Input")
                    cs.set("id", sk)
                    cs.set("manager", si.manager.id)
                    cs.set("interface", si.manager_interface)

        tree = et.ElementTree(root)
        tree.write(fn)#, pretty_print=True)

        
    def onOpenWorkflow(self):
        """ Open a data file"""
        filename, _ = QFileDialog.getOpenFileName(self, 'Open new workflow', '',  "Pathomx Workflow Format (*.mpf)")
        if filename:
            self.openWorkflow(filename)

    def openWorkflow(self, fn):
        print "Loading workflow..."
        # Wipe existing workspace
        self.clearWorkspace()
        # Load from file 
        tree = et.parse(fn)
        workflow = tree.getroot()
        
        type_converter = {
            'int': int,
            'float': float,
            'bool': bool,
        }
        
        appref = {}
        print "...Loading apps."
        for xapp in workflow.findall('App'):
            # FIXME: This does not work with multiple launchers/plugin - define as plugin.class?
            # Check plugins loaded etc.
            print '- %s' % xapp.find('Name').text
            app = self.app_launchers[ "%s.%s" % ( xapp.find("Plugin").text, xapp.find("Launcher").text ) ](auto_consume_data=False, name=xapp.find('Name').text)
            editorxy = xapp.find('EditorXY')
            app.editorItem.setPos( QPointF( float(editorxy.get('x') ), float(editorxy.get('y') ) ) )
            #app = self.app_launchers[ item.find("launcher").text ]()
            #app.set_name(  )
            appref[ xapp.get('id') ] = app

            config = {}
            for xconfig in xapp.findall('Config/ConfigSetting'):
                #id="experiment_control" type="unicode" value="monocyte at intermediate differentiation stage (GDS2430_2)"/>
                v = xconfig.text
                if xconfig.get('type') in type_converter:
                    v = type_converter[ xconfig.get('type') ](v)
                config[ xconfig.get('id') ] = v

            app.config.set_many( config, trigger_update=False )


        print "...Linking objects."
        # Now build the links between objects; we need to force these as data is not present
        for xapp in workflow.findall('App'):
            app = appref[ xapp.get('id') ]
            
            for idef in xapp.findall('DataInputs/Input'):
                app.data._consume_action(  idef.get('id'), appref[ idef.get('manager') ].data.o[ idef.get('interface') ] )
            
        print "Load complete."
        # Focus the home tab & refresh the view
        self.workspace_updated.emit()
    

     
      
def main():
    # Create a Qt application
    app = QApplication(sys.argv)
    app.setStyle('fusion')
    app.setOrganizationName("Pathomx")
    app.setOrganizationDomain("pathomx.org")
    app.setApplicationName("Pathomx")

    locale = QLocale.system().name()
    #locale = 'nl'
    
    # Load base QT translations from the normal place (does not include _nl, or _it)
    translator_qt = QTranslator()
    if translator_qt.load("qt_%s" % locale, QLibraryInfo.location(QLibraryInfo.TranslationsPath)):
        print "Loaded Qt translations for locale: %s" % locale
        app.installTranslator(translator_qt)  
          
    # See if we've got a default copy for _nl, _it or others
    elif translator_qt.load("qt_%s" % locale, os.path.join(utils.scriptdir,'translations')):
        print "Loaded Qt (self) translations for locale: %s" % locale
        app.installTranslator(translator_qt)    
        
    # Load Pathomx specific translations
    translator_mp = QTranslator()
    if translator_mp.load( "pathomx_%s" % locale, os.path.join(utils.scriptdir,'translations') ):
        print "Loaded Pathomx translations for locale: %s" % locale
    app.installTranslator(translator_mp)    
    
    # Set Matplotlib defaults for nice looking charts
    mpl.rcParams['figure.facecolor'] = 'white'
    mpl.rcParams['figure.autolayout'] = True
    mpl.rcParams['lines.linewidth'] = 0.25
    mpl.rcParams['lines.color'] =  'black'
    mpl.rcParams['lines.markersize'] = 10
    mpl.rcParams['axes.linewidth'] = 0.5
    mpl.rcParams['axes.color_cycle'] = utils.category10
    mpl.rcParams['font.size'] = 8
    mpl.rcParams['font.sans-serif'] = ['Helvetica','Arial','Bitstream Vera Sans','Lucida Grande','Verdana','Geneva','Lucid','Arial']
    mpl.rcParams['patch.linewidth'] = 0

    window = MainWindow(app)
    app.exec_()
    # Enter Qt application main loop
    sys.exit()
    
if __name__ == "__main__":
    main()
