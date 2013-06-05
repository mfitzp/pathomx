#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# Import PySide classes
from PySide.QtGui import *
from PySide.QtCore import *
from PySide.QtWebKit import *
from PySide.QtNetwork import *

import os

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


class QWebViewScrollFix(QWebView):

    def __init__(self, **kwargs):
        super(QWebViewScrollFix, self).__init__(**kwargs)        

        self.wheelBugTimer = QTimer()
        self.wheelBugTimer.start(50)
        self.wheelBugTimer.timeout.connect(self.wheelTrigger);
         
        self.wheelBugDirAccumulator = dict()
        self.wheelBugDirAccumulator[ Qt.Orientation.Horizontal ] = 0
        self.wheelBugDirAccumulator[ Qt.Orientation.Vertical ] = 0

        self.wheelBugLatest = dict()

    def wheelEvent(self, e):

        self.wheelBugDirAccumulator[ e.orientation() ] += e.delta()
        self.wheelBugLatest[ e.orientation() ] = {
                'pos': e.pos(),
                'buttons': e.buttons(),
                'modifiers': e.modifiers(),
            }
        
        if e.buttons() or e.modifiers():
            self.wheelTrigger()
            
        if abs( self.wheelBugDirAccumulator[ e.orientation() ] ) > 1000:
            self.wheelTrigger()

        e.setAccepted(True)
        return

    def wheelTrigger(self):

        for o, e in self.wheelBugLatest.items():
            event = QWheelEvent( e['pos'], self.wheelBugDirAccumulator[ o ] , e['buttons'], e['modifiers'], o )
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
        self.mainBrowser = QWebViewScrollFix()
        self.setCentralWidget(self.mainBrowser)

        # Display a introductory helpfile 
        template = self.templateEngine.get_template('welcome.html')
        self.mainBrowser.setHtml(template.render( {'htmlbase': os.path.join( utils.scriptdir,'html')} ),"~") 
        self.mainBrowser.page().setContentEditable(False)
        self.mainBrowser.page().setLinkDelegationPolicy( QWebPage.DelegateExternalLinks )
        self.mainBrowser.linkClicked.connect( self.onBrowserNav )
        self.mainBrowser.setContextMenuPolicy(Qt.CustomContextMenu) # Disable right-click
        self.mainBrowser.loadFinished.connect( self.onBrowserLoadDone )

        self.dataBrowser = QWebView()
        # Display a sponsors
        template = self.templateEngine.get_template('sponsors.html')
        self.dataBrowser.setHtml(template.render( {'htmlbase': os.path.join( utils.scriptdir,'html')} ),"~") 
        self.dataBrowser.page().setContentEditable(False)
        self.dataBrowser.page().setLinkDelegationPolicy( QWebPage.DelegateExternalLinks )
        self.dataBrowser.linkClicked.connect( self.onBrowserNav )
        self.dataBrowser.setContextMenuPolicy(Qt.CustomContextMenu) # Disable right-click
        self.dataBrowser_CurrentURL = None
        
        self.dataDock = QDockWidget('Database Viewer')
        self.dataDock.setMaximumWidth(300);
        self.dataDock.setWidget(self.dataBrowser)
        self.dataDock.setFeatures(QDockWidget.DockWidgetMovable)
        self.addDockWidget(Qt.RightDockWidgetArea, self.dataDock)
        
        

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