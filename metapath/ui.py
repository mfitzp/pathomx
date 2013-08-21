#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# Import PySide classes
from PySide.QtGui import *
from PySide.QtCore import *
from PySide.QtWebKit import *
from PySide.QtNetwork import *

import os, urllib, urllib2

# MetaPath classes
import utils


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
        
        self.data = {}
        self.select = QListWidget()
        self.query_target = query_target
        
        self.layout.addLayout( queryboxh )
        self.layout.addWidget( self.select )
        
        self.dialogFinalise()


class QWebPageJSLog(QWebPage):
    """
    Makes it possible to use a Python logger to print javascript console messages
    """
    def __init__(self, parent=None, **kwargs):
        super(QWebPageJSLog, self).__init__(parent, **kwargs)

    def javaScriptConsoleMessage(self, msg, lineNumber, sourceID):
        print "JsConsole(%s:%d): %s" % (sourceID, lineNumber, msg)


class QWebViewExtend(QWebView):

    def __init__(self, onNavEvent=None, **kwargs):
        super(QWebViewExtend, self).__init__(**kwargs)        

        #self.js_page_object = QWebPageJSLog()
        #self.setPage( self.js_page_object)
        self.page().setContentEditable(False)
        self.page().setLinkDelegationPolicy( QWebPage.DelegateExternalLinks )
        # Override links for internal link cleverness
        if onNavEvent:
            self.onNavEvent = onNavEvent
            self.linkClicked.connect( self.onNavEvent )

        self.setContextMenuPolicy(Qt.CustomContextMenu) # Disable right-click


    def exposeQtWebView(self):
        frame = self.page().mainFrame()
        frame.addToJavaScriptWindowObject("QtWebView", self);

    @Slot(str)
    def delegateLink(self, url):
        self.onNavEvent( QUrl(url) )
        return True


class QWebViewScrollFix(QWebViewExtend):

    def __init__(self, onNavEvent=None, **kwargs):
        super(QWebViewScrollFix, self).__init__(onNavEvent,**kwargs)        

        self.resetTimer()
         
        self.wheelBugDirAccumulator = dict()
        self.wheelBugDirAccumulator[ Qt.Orientation.Horizontal ] = 0
        self.wheelBugDirAccumulator[ Qt.Orientation.Vertical ] = 0
        
        self.wheelBugLatest = None
    
    def resetTimer(self):
        self.wheelBugTimer = QTimer.singleShot(25, self.wheelTrigger)

    def wheelEvent(self, e):

        if self.wheelBugTimer is None:
            self.resetTimer()

        self.wheelBugDirAccumulator[ e.orientation() ] += e.delta()
        self.wheelBugLatest = {
                'pos': e.pos(),
                'buttons': e.buttons(),
                'modifiers': e.modifiers(),
            }

        if e.buttons() or e.modifiers():
            self.wheelTrigger()
            
        e.setAccepted(True)
        return

    def wheelTrigger(self):

        # class PySide.QtGui.QWheelEvent(pos, globalPos, delta, buttons, modifiers[, orient=Qt.Vertical])
        # class PySide.QtGui.QWheelEvent(pos, delta, buttons, modifiers[, orient=Qt.Vertical])
        if self.wheelBugLatest:

            for o,d in self.wheelBugDirAccumulator.items():
               event = QWheelEvent( self.wheelBugLatest['pos'], d, self.wheelBugLatest['buttons'], self.wheelBugLatest['modifiers'], o )
               QWebView.wheelEvent(self, event)
               self.wheelBugDirAccumulator[ o ] = 0


#We ran into the same issue. We worked around the problem by overriding QWebView::wheelEvent, and doing the following:
#When a wheelEvent comes in, we start a 25 ms single-shot timer and process the wheelEvent. For any future wheelEvent's that come in while the timer is active, we just accumulate the event->delta( )'s (and pos & globalPos values, too). When the timer finally fires, the accumulated deltas are packaged into a QWheelEvent and delivered to QWebView::wheelEvent. (One further refinement is that we only do this for wheelEvents that have NoButton and NoModifier.)


class MainWindowUI(QMainWindow):

    def __init__(self):

        super(MainWindowUI, self).__init__()


        menubar = self.menuBar()

        # FILE MENU 
        fileMenu = menubar.addMenu('&File')

        aboutAction = QAction(QIcon.fromTheme("help-about"), 'About', self)
        aboutAction.setStatusTip('About MetaPath')
        aboutAction.triggered.connect(self.onAbout)
        fileMenu.addAction(aboutAction)

        saveAction = QAction(QIcon.fromTheme("document-save", QIcon( os.path.join( utils.scriptdir, 'icons', 'document-save-as.png') )), u'&Save As\u2026', self)
        saveAction.setShortcut('Ctrl+S')
        saveAction.setStatusTip('Save current metabolic pathway map in multiple formats')
        saveAction.triggered.connect(self.onSaveAs)
        fileMenu.addAction(saveAction)

        printAction = QAction(QIcon.fromTheme("document-print", QIcon( os.path.join( utils.scriptdir, 'icons', 'document-print.png') )), u'&Print\u2026', self)
        printAction.setShortcut('Ctrl+P')
        printAction.setStatusTip('Print current metabolic pathway')
        printAction.triggered.connect(self.onPrint)
        fileMenu.addAction(printAction)

        resetAction = QAction(QIcon.fromTheme("system-restart-panel", QIcon( os.path.join( utils.scriptdir,'icons','system-restart-panel.png') )), u'&Reset configuration', self)
        resetAction.setStatusTip('Reset config to systm defaults')
        resetAction.triggered.connect(self.onResetConfig)
        fileMenu.addAction(resetAction)

        #fileMenu.addAction(exitAction)

        # PATHWAY MENU
        
        pathwayMenu = menubar.addMenu('&Pathways')
        
        show_pathwaysAction = QAction(QIcon.fromTheme("document-open", QIcon( os.path.join( utils.scriptdir,'icons','document-open.png') )), '&Show Selected Pathways\u2026', self)
        show_pathwaysAction.setStatusTip('Show and hide specific metabolic pathways')
        show_pathwaysAction.triggered.connect(self.onPathwaysShow)
        pathwayMenu.addAction(show_pathwaysAction)
        
        show_pathway_linksAction = QAction(QIcon.fromTheme("document-page-setup", QIcon( os.path.join( utils.scriptdir,'icons','document-page-setup.png') )), 'Show Links to Hidden Pathways', self)
        show_pathway_linksAction.setStatusTip('Show links to pathways currently not visible')
        show_pathway_linksAction.setCheckable( True )
        show_pathway_linksAction.setChecked( bool( self.config.value('/Pathways/ShowLinks' ) ) )
        show_pathway_linksAction.toggled.connect(self.onPathwayLinksToggle)
        pathwayMenu.addAction(show_pathway_linksAction)
        
        pathwayMenu.addSeparator()

        load_layoutAction = QAction('&Load predefined layout\u2026', self)
        load_layoutAction.setStatusTip('Load a pre-defined layout map file e.g KGML')
        load_layoutAction.triggered.connect(self.onLoadLayoutFile)
        pathwayMenu.addAction(load_layoutAction)

        pathwayMenu.addSeparator()

        load_gpml_pathwayAction = QAction('&Load GPML pathway\u2026', self)
        load_gpml_pathwayAction.setStatusTip('Load a GPML pathway file')
        load_gpml_pathwayAction.triggered.connect(self.onLoadGPMLPathway)
        pathwayMenu.addAction(load_gpml_pathwayAction)

        load_gpml_wikipathwaysAction = QAction('&Load GPML pathway via WikiPathways\u2026', self)
        load_gpml_wikipathwaysAction.setStatusTip('Load a GPML pathway from WikiPathways service')
        load_gpml_wikipathwaysAction.triggered.connect(self.onLoadGPMLWikiPathways)
        pathwayMenu.addAction(load_gpml_wikipathwaysAction)


        # PATHWAYS Menu
        
        
        # DATA MENU
        dataMenu = menubar.addMenu('&Data')
        
        load_dataAction = QAction(QIcon.fromTheme("document-open", QIcon( os.path.join( utils.scriptdir,'icons','document-open.png') )), 'Load metabolite dataset\u2026', self)
        load_dataAction.setShortcut('Ctrl+Q')
        load_dataAction.setStatusTip('Load metabolite datfile')
        load_dataAction.triggered.connect(self.onLoadDataFile)
        dataMenu.addAction(load_dataAction)

        define_experimentAction = QAction(QIcon.fromTheme("document-page-setup", QIcon( os.path.join( utils.scriptdir,'icons','document-page-setup.png') )), 'Define experiment\u2026', self)
        define_experimentAction.setShortcut('Ctrl+Q')
        define_experimentAction.setStatusTip('Define experiment control, test and timecourse settings')
        define_experimentAction.triggered.connect(self.onDefineExperiment)
        dataMenu.addAction(define_experimentAction)
        
        dataMenu.addSeparator()
        
        enable_pathway_miningAction = QAction(QIcon.fromTheme("visualization", QIcon( os.path.join( utils.scriptdir,'icons','visualization.png') )), 'Enable pathway mining', self)
        enable_pathway_miningAction.setShortcut('Ctrl+Q')
        enable_pathway_miningAction.setStatusTip('Enable algorithmic mining of key pathways')
        enable_pathway_miningAction.setCheckable( True )
        enable_pathway_miningAction.setChecked( bool( self.config.value('/Data/MiningActive' ) ) )
        enable_pathway_miningAction.toggled.connect(self.onPathwayMiningToggle)
        dataMenu.addAction(enable_pathway_miningAction)

        pathway_mining_settingsAction = QAction(QIcon.fromTheme("visualization", QIcon( os.path.join( utils.scriptdir,'icons', 'visualization.png') )), 'Pathway mining settings\u2026', self)
        pathway_mining_settingsAction.setStatusTip('Define pathway mining settings')
        pathway_mining_settingsAction.triggered.connect(self.onMiningSettings)
        dataMenu.addAction(pathway_mining_settingsAction)

        # VIEW MENU 
        viewMenu = menubar.addMenu('&View')
        
        showenzymesAction = QAction('Show proteins/enzymes', self)
        showenzymesAction.setStatusTip('Show protein/enzymes on reactions')
        showenzymesAction.setCheckable( True )
        showenzymesAction.setChecked( bool( self.config.value('/View/ShowEnzymes' ) ) )
        showenzymesAction.toggled.connect(self.onShowEnzymesToggle)
        viewMenu.addAction(showenzymesAction)
        
        show2ndAction = QAction('Show 2° metabolites', self)
        show2ndAction.setStatusTip('Show 2° metabolites on reaction paths')
        show2ndAction.setCheckable( True )
        show2ndAction.setChecked( bool( self.config.value('/View/Show2nd' ) ) )
        show2ndAction.toggled.connect(self.onShow2ndToggle)
        viewMenu.addAction(show2ndAction)

        showmolecularAction = QAction('Show molecular structures', self)
        showmolecularAction.setStatusTip('Show molecular structures instead of names on pathway maps')
        showmolecularAction.setCheckable( True )
        showmolecularAction.setChecked( bool( self.config.value('/View/ShowMolecular' ) ) )
        showmolecularAction.toggled.connect(self.onShowMolecularToggle)
        viewMenu.addAction(showmolecularAction)

        showanalysisAction = QAction('Show network analysis', self)
        showanalysisAction.setStatusTip('Show network analysis hints and molecular importance')
        showanalysisAction.setCheckable( True )
        showanalysisAction.setChecked( bool( self.config.value('/View/ShowMolecular' ) ) )
        showanalysisAction.toggled.connect(self.onShowAnalysisToggle)
        viewMenu.addAction(showanalysisAction)

        viewMenu.addSeparator()
        
        highlightcolorsAction = QAction(QIcon.fromTheme("visualization", QIcon( os.path.join( utils.scriptdir,'icons','visualization.png') )), 'Highlight Reaction Pathways', self)
        highlightcolorsAction.setStatusTip('Highlight pathway reactions by color')
        highlightcolorsAction.setCheckable( True )
        highlightcolorsAction.setChecked( bool( self.config.value('/View/HighlightPathways' ) ) )
        highlightcolorsAction.toggled.connect(self.onHighlightPathwaysToggle)
        viewMenu.addAction(highlightcolorsAction)

        highlightregionAction = QAction(QIcon.fromTheme("visualization", QIcon( os.path.join( utils.scriptdir,'icons','visualization.png') )), 'Highlight pathway/compartment regions', self)
        highlightregionAction.setStatusTip('Highlight pathway/cell compartment regions')
        highlightregionAction.setCheckable( True )
        highlightregionAction.setChecked( bool( self.config.value('/View/HighlightRegions' ) ) )
        highlightregionAction.toggled.connect(self.onHighlightRegionsToggle)
        viewMenu.addAction(highlightregionAction)

        viewMenu.addSeparator()
        
        refreshAction = QAction(QIcon.fromTheme("view-refresh", QIcon( os.path.join( utils.scriptdir,'icons', 'view-refresh.png') )), u'&Refresh', self)
        refreshAction.setShortcut('Ctrl+R')
        refreshAction.setStatusTip('Refresh metabolic pathway map')
        refreshAction.triggered.connect(self.onRefresh)
        viewMenu.addAction(refreshAction)
        
        zoominAction = QAction(QIcon.fromTheme("zoom-in", QIcon( os.path.join( utils.scriptdir,'icons', 'zoom-in.png') )), u'&Zoom in', self)
        zoominAction.setShortcut('Ctrl++')
        zoominAction.setStatusTip('Zoom in')
        zoominAction.triggered.connect(self.onZoomIn)
        viewMenu.addAction(zoominAction)

        zoomoutAction = QAction(QIcon.fromTheme("zoom-out", QIcon( os.path.join( utils.scriptdir,'icons', 'zoom-out.png') )), u'&Zoom out', self)
        zoomoutAction.setShortcut('Ctrl+-')
        zoomoutAction.setStatusTip('Zoom out')
        zoomoutAction.triggered.connect(self.onZoomOut)
        viewMenu.addAction(zoomoutAction)
        
        

        # DATABASE MENU
        
        databaseMenu = menubar.addMenu('&Database')
        
        load_identitiesAction = QAction(QIcon.fromTheme("document-import", QIcon( os.path.join( utils.scriptdir,'icons','document-import.png') )), u'&Load metabolite identities\u2026', self)
        load_identitiesAction.setStatusTip('Load additional metabolite identities/synonyms')
        load_identitiesAction.triggered.connect(self.onLoadIdentities)
        databaseMenu.addAction(load_identitiesAction)
        
        databaseMenu.addSeparator()
        
        reload_databaseAction = QAction(QIcon.fromTheme("system-restart-panel", QIcon( os.path.join( utils.scriptdir,'icons','system-restart-panel.png') )), u'&Reload database', self)
        reload_databaseAction.setStatusTip('Reload pathway & metabolite database')
        reload_databaseAction.triggered.connect(self.onReloadDB)
        databaseMenu.addAction(reload_databaseAction)
        
        # TOOLBARS
        self.setToolButtonStyle( Qt.ToolButtonFollowStyle ) #Qt.ToolButtonTextUnderIcon

        self.fileToolbar = self.addToolBar('File')
        self.fileToolbar.addAction(saveAction)
        self.fileToolbar.addAction(printAction)
        self.fileToolbar.addAction(printAction)
        
        self.viewToolbar = self.addToolBar('View')
        self.viewToolbar.addAction(zoominAction)

        self.viewToolbar.addAction(zoomoutAction)
        self.viewToolbar.addAction(refreshAction)
        
        self.cluster_control = QComboBox()
        self.cluster_control.addItems(['pathway','compartment'])
        self.cluster_control.currentIndexChanged.connect(self.onModifyCluster)

        self.viewToolbar.addWidget(self.cluster_control)

        

        self.experimentToolbar = self.addToolBar('Experiment')
        #self.experimentToolbar.addWidget( QLabel('Experiment') )
        spacerWidget = QWidget()
        spacerWidget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        spacerWidget.setVisible(True)
        self.experimentToolbar.addWidget(spacerWidget)

        self.experimentToolbar.addAction(load_dataAction)
        self.experimentToolbar.addAction(define_experimentAction)

        
        self.cb_control = QComboBox()
        self.cb_control.addItems(['Control'])
        self.cb_control.currentIndexChanged.connect(self.onModifyExperiment)

        self.cb_test = QComboBox()
        self.cb_test.addItems(['Test'])
        self.cb_test.currentIndexChanged.connect(self.onModifyExperiment)

        self.experimentToolbar.addWidget(self.cb_control)
        self.experimentToolbar.addWidget(self.cb_test)

        self.sb_miningDepth = QSpinBox()
        self.sb_miningDepth.setMinimum(1)
        self.sb_miningDepth.setValue( int( self.config.value('/Data/MiningDepth') ) )
        self.sb_miningDepth.valueChanged.connect(self.onModifyMiningDepth)
        
        
        
        self.experimentToolbar.addAction(enable_pathway_miningAction)
        self.experimentToolbar.addWidget(self.sb_miningDepth)

        #self.vboxlayout.addWidget(self.mainBrowser)
        QNetworkProxyFactory.setUseSystemConfiguration( True )

        #QWebSettings.globalSettings().setAttribute( QWebSettings.PluginsEnabled, True)
        #QWebSettings.globalSettings().setAttribute( QWebSettings.LocalContentCanAccessRemoteUrls, True)
        #QWebSettings.globalSettings().setAttribute( QWebSettings.LocalContentCanAccessFileUrls, True)

        QWebSettings.setMaximumPagesInCache( 0 )
        QWebSettings.setObjectCacheCapacities(0, 0, 0)
        QWebSettings.clearMemoryCaches()
        QWebSettings.globalSettings().setAttribute( QWebSettings.WebAttribute.DeveloperExtrasEnabled, True)
        
        self.mainBrowser = QWebViewScrollFix( onNavEvent=self.onBrowserNav )
        self.appBrowser = QWebViewScrollFix( onNavEvent=self.onBrowserNav )


        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setDocumentMode(True)
        self.tabs.addTab(self.appBrowser, '★') 
        self.tabs.addTab(self.mainBrowser, '?')

        self.setCentralWidget(self.tabs)
        
        # Hide close button from the homepage
        self.tabs.tabBar().setTabButton(1, self.tabs.tabBar().ButtonPosition(), None)
        self.tabs.tabBar().setTabButton(0, self.tabs.tabBar().ButtonPosition(), None)

#        self.inspect = QWebInspector()
#        self.tabs.addTab(self.inspect, 'Inspector')


        # Display a introductory helpfile 
        template = self.templateEngine.get_template('welcome.html')
        self.mainBrowser.setHtml(template.render( {'htmlbase': os.path.join( utils.scriptdir,'html')} ),"~") 
        self.mainBrowser.loadFinished.connect( self.onBrowserLoadDone )

        # Display the app browser
        metadata = {
            'htmlbase': os.path.join( utils.scriptdir,'html'),
            'categories':['Input','Processing','Analysis','Visualisation','Output','Misc'],
            'apps':{
                'Input':[
                    {'id':'import-text','name':'Text','description':'Load data from text files in various formats'},
                    {'id':'import-excel','name':'Excel','description':'Interactively import data from Excel files in various formats'},
                    {'id':'nmrglue','name':'NMR Glue','description':'Import raw NMR data from Bruker, Varian and more','image':'file:///Users/mxf793/Scripts/metapath/metapath/html/img/nmrglue.png'},
                
                ],
                'Processing':[
                    {'id':'nmrlab','name':'NMR Lab','description':'MATLAB based tool for the processing NMR spectra','image':'file:///Users/mxf793/Scripts/metapath/metapath/html/img/nmrlab.png'},
                    {'id':'nmr-peak','name':'Peak Picking','description':'Convert loaded data to metabolite quantities via peak picking'},

                ],
                'Analysis':[
                    {'id':'pca','name':'PCA','description':'Principle components analysis of data sets'},                
                    {'id':'net-analysis','name':'NET Analysis','description':'Network Embedded Thermodynamic analysis'},                
                ],
                'Visualisation':[
                    {'id':'metaviz','name':'MetaViz','description':'Automated pathway layouts, powered by Graphviz','image':'file:///Users/mxf793/Scripts/metapath/metapath/html/img/metaviz.png'},
                    {'id':'pathway-connections','name':'Pathway Connections','description':'Visualise data in pathway context, identify locales of regulation','image':'file:///Users/mxf793/Scripts/metapath/metapath/html/img/pathway-links.png'},
                ],
                'Output':[
                
                
                
                ],
                'Misc':[
                    {'id':'force-visualisation-test','name':'Force d3','description':'Force directed graph visualisation test'},
                
                ],
            
            }
        
        }
        
        
        from pymatbridge import Matlab
        mlab = Matlab('/Applications/MATLAB_R2011a_Student.app/bin/matlab')
        mlab.start()
        mlab.run_code('nmrlab')
        
        template = self.templateEngine.get_template('apps.html')
        self.appBrowser.setHtml(template.render( metadata ),"~") 
        self.appBrowser.loadFinished.connect( self.onBrowserLoadDone )
        
        f = open('/Users/mxf793/Desktop/testapps.html','w')
        f.write(template.render( metadata ))
        f.close()
        

        self.dbBrowser = QWebViewScrollFix( onNavEvent=self.onBrowserNav )
        # Display a sponsors
        template = self.templateEngine.get_template('sponsors.html')
        self.dbBrowser.setHtml(template.render( {'htmlbase': os.path.join( utils.scriptdir,'html')} ),"~") 
        self.dbBrowser_CurrentURL = None
        
        self.dataDock = QDockWidget('Database Viewer')
        self.dataDock.setMaximumWidth(300);
        self.dataDock.setWidget(self.dbBrowser)
        self.dataDock.setFeatures(QDockWidget.DockWidgetMovable)
        self.addDockWidget(Qt.RightDockWidgetArea, self.dataDock)
        

        # Data vis: visualisation of loaded dataset (spectra, etc.); peak picking; data->metabolite conversion
        # Identification: table view for each datatype, identifier -> metabolite link (mostly automatic, but allow tweaks); or simply show (combine with above/below?)
        
        # Data summary: global view overall dataset; characteristics information
        
        # Data analysis: graphs, plots
        
        # self.analysisBrowser = QWebView()
        # Display default no-data view; instructions for loading data etc.
        #template = self.templateEngine.get_template('data.html')
        #self.analysisBrowser.setHtml(template.render( {'htmlbase': os.path.join( utils.scriptdir,'html')} ),"~") 
        #self.analysisBrowser.page().setContentEditable(False)
        #self.analysisBrowser.page().setLinkDelegationPolicy( QWebPage.DelegateExternalLinks )
        #self.analysisBrowser.linkClicked.connect( self.onBrowserNav )
        #self.analysisBrowser.setContextMenuPolicy(Qt.CustomContextMenu) # Disable right-click

        

    # Simple menu toggles
    def onPathwayLinksToggle(self, checked):
        self.config.setValue( '/Pathways/ShowLinks', checked)
        self.generateGraphView()

    def onPathwayMiningToggle(self, checked):
        self.config.setValue( '/Data/MiningActive', checked)
        self.generateGraphView()

    def onShowEnzymesToggle(self, checked):
        self.config.setValue( '/View/ShowEnzymes', checked)
        self.generateGraphView()

    def onShow2ndToggle(self, checked):
        self.config.setValue( '/View/Show2nd', checked)
        self.generateGraphView()

    def onShowMolecularToggle(self, checked):
        self.config.setValue( '/View/ShowMolecular', checked)
        self.generateGraphView()

    def onShowAnalysisToggle(self, checked):
        self.config.setValue( '/View/ShowAnalysis', checked)
        self.generateGraphView()
        
    def onHighlightPathwaysToggle(self, checked):
        self.config.setValue( '/View/HighlightPathways', checked)
        self.generateGraphView()

    def onHighlightRegionsToggle(self, checked):
        self.config.setValue( '/View/HighlightRegions', checked)
        self.generateGraphView()