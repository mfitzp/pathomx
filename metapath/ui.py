#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# Import PySide classes
from PySide.QtGui import *
from PySide.QtCore import *
from PySide.QtWebKit import *
from PySide.QtNetwork import *

from collections import defaultdict

from yapsy.PluginManager import PluginManager, PluginManagerSingleton
import plugins

import os, urllib, urllib2

# MetaPath classes
import utils

import numpy as np



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


#### View Object Prototypes (Data, Assignment, Processing, Analysis, Visualisation) e.g. used by plugins

# Data view prototypes

class dataView(object):
    def __init__(self, plugin, parent, gpml=None, svg=None, **kwargs):
    
        self.plugin = plugin
        self.m = parent
        self.id = str( id( self ) )

        self.w = QMainWindow()
        t = self.w.addToolBar('Data')
        t.setIconSize( QSize(16,16) )
        
        self.summary = QWebViewScrollFix()
        self.table = QTableView()
        #self.table.setRowCount(10)
        #self.table.setColumnCount(5)
        
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setTabsClosable(False)
        self.tabs.setTabPosition( QTabWidget.South )
        self.tabs.addTab(self.summary, 'Summary')
        self.tabs.addTab(self.table,'Table')
        
        self.w.setCentralWidget(self.tabs)
         
        #self.o.show() 
        #self.plugin.register_url_handler( self.id, self.url_handler )
        self.workspace_item = self.m.addWorkspaceItem(self.w, self.plugin.default_workspace_category, 'Data', is_selected=True) #, icon = None)
            
    def render(self, metadata):
        return
        



# Analysis/Visualisation view prototypes


# Class for analysis views, using graph-based visualisations of defined datasets
# associated layout and/or analysis
class analysisView(object):
    def __init__(self, parent, **kwargs):
        self.parent = parent
        self.browser = QWebViewScrollFix( parent.onBrowserNav )
        self.id = str( id( self ) )
                
        #parent.tab_handlers.append( self )
    
    def render(self, metadata):
        metadata['htmlbase'] = os.path.join( utils.scriptdir,'html')

        template = self.parent.templateEngine.get_template('d3/figure.html')
        self.browser.setHtml(template.render( metadata ),"~") 
        self.browser.exposeQtWebView()
        
        #f = open('/Users/mxf793/Desktop/test.html','w')
        #f.write( template.render( metadata ) )
        #f.close()
        
    def build_log2_change_table_of_classtypes(self, objects, classes):
        data = np.zeros( (len(objects), len(classes))  )
        
        for y,os in enumerate(objects):
            for x,ost in enumerate(os):
                #for n,c in enumerate(classes):
                if ost in self.parent.data.quantities.keys():
                    n = self.parent.data.get_log2(ost, self.parent.experiment['test']) - self.parent.data.get_log2( ost , self.parent.experiment['control'] )
                    data[y,x] = n
                else:
                    data[y,x] = np.nan

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




# Class for analysis views, using graph-based visualisations of defined datasets
# associated layout and/or analysis
class analysisd3View(analysisView):
    def __init__(self, parent, **kwargs):
        super(analysisd3View, self).__init__(parent, **kwargs)        
    
        self.parent = parent
        self.browser = QWebViewExtend( parent.onBrowserNav )
        
    def render(self, metadata, debug=False):
        metadata['htmlbase'] = os.path.join( utils.scriptdir,'html')
    
        template = self.parent.templateEngine.get_template('d3/figure.html')
        self.browser.setHtml(template.render( metadata ),"~")
        self.browser.exposeQtWebView()

                    
        
# Class for analysis views, using graph-based visualisations of defined datasets
# associated layout and/or analysis
class d3View(analysisView):
    def __init__(self, parent, **kwargs):
        super(d3View, self).__init__(parent, **kwargs)        
    
        self.parent = parent
        self.browser = QWebViewExtend( parent.onBrowserNav )
    
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
        template = self.parent.templateEngine.get_template('d3/force.html')

        self.browser.setHtml(template.render( metadata ),"~") 
        self.browser.exposeQtWebView()

      

# Class for analysis views, using graph-based visualisations of defined datasets
# associated layout and/or analysis
class analysisHeatmapView(analysisd3View):
    def __init__(self, parent, **kwargs):
        super(analysisHeatmapView, self).__init__(parent, **kwargs)        
        self.parent = parent
        self.browser = QWebViewExtend( parent.onBrowserNav )
        
        parent.tab_handlers.append( self )
        
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



class analysisCircosView(analysisd3View):
    def __init__(self, parent, **kwargs):
        super(analysisCircosView, self).__init__(parent, **kwargs)        
        self.parent = parent
        self.browser = QWebViewExtend( parent.onBrowserNav )

    def build_matrix(self, targets, target_links):

        data = []
        for mx in targets:
            row = []
            for my in targets:
                n = len( list( target_links[my] & target_links[mx] ) )
                row.append( n )
    
            data.append( row )
        return data, targets







class analysisCircosPathwayView(analysisHeatmapView):
    def __init__(self, parent, **kwargs):
        super(analysisCircosPathwayView, self).__init__(parent, **kwargs)        

        self.parent = parent
        self.browser = QWebViewExtend( parent.onBrowserNav )


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


        # PATHWAYS Menu
        
        
        # DATA MENU
        load_dataAction = QAction(QIcon.fromTheme("document-open", QIcon( os.path.join( utils.scriptdir,'icons','blue-folder-open-table.png') )), 'Load metabolite dataset\u2026', self)
        load_dataAction.setShortcut('Ctrl+Q')
        load_dataAction.setStatusTip('Load metabolite datfile')
        load_dataAction.triggered.connect(self.onLoadDataFile)
        self.menuBar['data'].addAction(load_dataAction)

        define_experimentAction = QAction(QIcon.fromTheme("layout-design", QIcon( os.path.join( utils.scriptdir,'icons','layout-design.png') )), 'Define experiment\u2026', self)
        define_experimentAction.setShortcut('Ctrl+Q')
        define_experimentAction.setStatusTip('Define experiment control, test and timecourse settings')
        define_experimentAction.triggered.connect(self.onDefineExperiment)
        self.menuBar['data'].addAction(define_experimentAction)
        
        self.menuBar['data'].addSeparator()
        
        enable_pathway_miningAction = QAction(QIcon.fromTheme("visualization", QIcon( os.path.join( utils.scriptdir,'icons','hard-hat-mine.png') )), 'Enable pathway mining', self)
        enable_pathway_miningAction.setShortcut('Ctrl+Q')
        enable_pathway_miningAction.setStatusTip('Enable algorithmic mining of key pathways')
        enable_pathway_miningAction.setCheckable( True )
        enable_pathway_miningAction.setChecked( bool( self.config.value('/Data/MiningActive' ) ) )
        enable_pathway_miningAction.toggled.connect(self.onPathwayMiningToggle)
        self.menuBar['data'].addAction(enable_pathway_miningAction)

        pathway_mining_settingsAction = QAction(QIcon.fromTheme("visualization", QIcon( os.path.join( utils.scriptdir,'icons', 'hard-hat-mine.png') )), 'Pathway mining settings\u2026', self)
        pathway_mining_settingsAction.setStatusTip('Define pathway mining settings')
        pathway_mining_settingsAction.triggered.connect(self.onMiningSettings)
        self.menuBar['data'].addAction(pathway_mining_settingsAction)

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
        

        self.experimentToolbar = self.addToolBar('Experiment')
        #self.experimentToolbar.addWidget( QLabel('Experiment') )
        #spacerWidget = QWidget()
        #spacerWidget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        #spacerWidget.setVisible(True)
        #self.experimentToolbar.addWidget(spacerWidget)

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


        self.addToolBarBreak()


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

        #self.tabs = QTabWidget()
        #self.tabs.setTabsClosable(True)
        #self.tabs.setDocumentMode(True)
        #self.tabs.setMovable(True)
        #self.tabs.setTabPosition( QTabWidget.South )
        #self.tabs.setTabShape( QTabWidget.Triangular )
        #∞Σ⌘
        
        
        
        # Hide close button from the homepage
        #self.tabs.addTab(self.mainBrowser, '⁉') #Help  ↛⇲▼◎♥⚑☺⬚
        #self.tabs.tabBar().setTabButton(0, self.tabs.tabBar().ButtonPosition(), None)

        #self.tabs.addTab(self.appBrowser, '★') #Apps
        #self.tabs.tabBar().setTabButton(1, self.tabs.tabBar().ButtonPosition(), None)
        #self.tabs.tabBar().setTabTextColor(1, QColor(237,212,0))

        #self.tabs.addTab(QWidget(), '⌘') #Database
        #self.tabs.tabBar().setTabButton(2, self.tabs.tabBar().ButtonPosition(), None)
        #self.tabs.tabBar().setTabTextColor(2, QColor(115,210,22))

        #self.tabs.addTab(QWidget(), 'Σ') #Data (&Analysis)
        #self.tabs.tabBar().setTabButton(3, self.tabs.tabBar().ButtonPosition(), None)
        #self.tabs.tabBar().setTabTextColor(3, QColor(52,101,164))

        #self.tabs.addTab(QWidget(), '↛') #Routefinder: Track analysis pathways?
        #self.tabs.tabBar().setTabButton(4, self.tabs.tabBar().ButtonPosition(), None)
        #self.tabs.tabBar().setTabTextColor(4, QColor(117,80,123))



        #self.setCentralWidget(self.tabs)

#        self.tabs.tabBar().setTabButton(3, self.tabs.tabBar().ButtonPosition(), None)

#        self.inspect = QWebInspector()
#        self.tabs.addTab(self.inspect, 'Inspector')
        self.dbBrowser_CurrentURL = None

        # Display a introductory helpfile 
        template = self.templateEngine.get_template('welcome.html')
        self.mainBrowser.setHtml(template.render( {'htmlbase': os.path.join( utils.scriptdir,'html')} ),"~") 
        self.mainBrowser.loadFinished.connect( self.onBrowserLoadDone )
        
        self.pluginManager = PluginManagerSingleton.get()
        self.pluginManager.m = self
        self.pluginManager.setPluginPlaces([os.path.join( utils.scriptdir,'plugins')])
        self.pluginManager.setCategoriesFilter({
               "Data" : plugins.DataPlugin,
               "Processing" : plugins.ProcessingPlugin,
               "Assignment": plugins.AssignmentPlugin,
               "Analysis" : plugins.AnalysisPlugin,
               "Visualisation" : plugins.VisualisationPlugin,
               "Output" : plugins.OutputPlugin,
               "Misc" : plugins.MiscPlugin,
               })
        self.pluginManager.collectPlugins()

        plugin_categories = ['Data','Processing','Assignment','Analysis','Visualisation']
        apps = defaultdict(list)
        self.appBrowsers = {}
        
        # Loop round the plugins and print their names.
        for category in plugin_categories:
            for plugin in self.pluginManager.getPluginsOfCategory(category):

                #plugin_id = os.path.basename( plugin.path )
                plugin_image = os.path.join( os.path.dirname(plugin.path), 'icon.png' )
                if not os.path.isfile( plugin_image ):
                    plugin_image = None
                
                apps[category].append({
                    'id': plugin.plugin_object.__module__, 
                    'image': plugin_image,          
                    'name': plugin.name,
                    'description': plugin.description,
                })
 

        self.dbBrowser = QWebViewScrollFix( onNavEvent=self.onBrowserNav )
        # Display a list of supporting orgs
        template = self.templateEngine.get_template('sponsors.html')
        self.dbBrowser.setHtml(template.render( {'htmlbase': os.path.join( utils.scriptdir,'html')} ),"~") 
        
        self.dataDock = QDockWidget('Database')
        self.dataDock.setWidget(self.dbBrowser)
        self.dataDock.setMinimumWidth(300)
        self.dataDock.setMaximumWidth(300)
        
        #self.dataDock.setFeatures(QDockWidget.NoDockWidgetFeatures)

        self.stack = QStackedWidget()
        #self.stack.addWidget(self.mainBrowser)
        #self.stack.addWidget(self.tabs)
        #self.stack.addWidget(self.appBrowser)

        self.setCentralWidget(self.stack)

        self.stack.setCurrentIndex(0)

        self.workspace_count = 0 # Auto-increment
        self.workspace_parents = {}
        
        self.workspace = QTreeWidget()
        self.workspace.setColumnCount(2)
        self.workspace.setHeaderLabels(['','ID']) #,'#'])
        self.workspace.setUniformRowHeights(True)
        self.workspace.hideColumn(1)
        #self.workspace.setIndentation(10)
        
        app_category_icons = {
               "Data" : QIcon.fromTheme("data", QIcon( os.path.join( utils.scriptdir,'icons','ruler.png' ) ) ),
               "Processing" : QIcon.fromTheme("processing", QIcon( os.path.join( utils.scriptdir,'icons','ruler-triangle.png' ) ) ),
               "Assignment" : QIcon.fromTheme("assignment", QIcon( os.path.join( utils.scriptdir,'icons','map.png' ) ) ),
               "Analysis" : QIcon.fromTheme("analysis", QIcon( os.path.join( utils.scriptdir,'icons','calculator.png' ) ) ),
               "Visualisation" : QIcon.fromTheme("visualisation", QIcon( os.path.join( utils.scriptdir,'icons','star.png' ) ) ),
               }
    
        template = self.templateEngine.get_template('apps.html')
        for category in plugin_categories:
            self.appBrowsers[ category ] = QWebViewScrollFix( onNavEvent=self.onBrowserNav )
            self.appBrowsers[ category ].setHtml(template.render( 
                {
                'htmlbase': os.path.join( utils.scriptdir,'html'),
                'category':category,
                'apps':apps[ category ],
                }                
             ),"~") 
                
            self.appBrowsers[ category ].loadFinished.connect( self.onBrowserLoadDone )
            self.appBrowsers[ category ].exposeQtWebView()
                
            self.addWorkspaceItem( self.appBrowsers[ category ], None, category, app_category_icons[category]   )


        #self.addWorkspaceItem( self.mainBrowser, 'Visualisation', "Hs_Glycolysis_and_Gluconeogenesis_WP534_51732",QIcon.fromTheme("save-workspace", QIcon( os.path.join( utils.scriptdir, 'icons', 'disk.png') ))  )
        #self.addWorkspaceItem( self.mainBrowser, 'Visualisation', "Hs_Glycolysis_and_Gluconeogenesis_WP534_51732",QIcon.fromTheme("save-workspace", QIcon( os.path.join( utils.scriptdir, 'icons', 'disk.png') ))  )

        self.workspace.setSelectionMode( QAbstractItemView.SingleSelection )

        self.workspace.currentItemChanged.connect( self.onWorkspaceStackChange)
        #QObject.connect(self.workspace, SIGNAL("itemActivated()"),
        #self.stack, SLOT("setCurrentIndex(int)"))

        self.workspaceDock = QDockWidget('Workspace')
        self.workspaceDock.setWidget(self.workspace)
        self.workspaceDock.setMinimumWidth(300)
        self.workspaceDock.setMaximumWidth(300)
        #self.workspaceDock.setMaximumWidth(200)
        #self.workspaceDock.setFeatures(QDockWidget.NoDockWidgetFeatures)

        self.addDockWidget(Qt.RightDockWidgetArea, self.dataDock)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.workspaceDock)

        #self.workspace.resizeColumnToContents(0)
        #self.tabifyDockWidget( self.workspaceDock, self.dataDock ) 
        

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
        
        
    def onPathwayMiningToggle(self, checked):
        self.config.setValue( '/Data/MiningActive', checked)
        self.generateGraphView()


