#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os, sys, re, math, codecs, locale

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

import urllib2#, sip

from optparse import Values
from collections import defaultdict

import numpy as np

from yapsy.PluginManager import PluginManager

# wheezy templating engine
from wheezy.template.engine import Engine
from wheezy.template.ext.core import CoreExtension
from wheezy.template.ext.code import CodeExtension
from wheezy.template.loader import FileLoader

try:
    import xml.etree.cElementTree as et
except ImportError:
    import xml.etree.ElementTree as et


# MetaPath classes
import db, data, utils, ui # core, layout - removed to plugin MetaViz, figure -deprecated in favour of d3
import plugins # plugin helper/manager

METAPATH_MINING_TYPE_CODE = ('c', 'u', 'd', 'm')
METAPATH_MINING_TYPE_TEXT = (
    'Compound change scores for pathway',
    'Compound up-regulation scores for pathway', 
    'Compound down-regulation scores for pathway',
    'Number compounds with data per pathway',
)


import logging
logging.basicConfig(level=logging.DEBUG)

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

            
class dialogPathwaysShow(ui.genericDialog):

    def onRegexpAdd(self):
        tab = self.sender().objectName()
        items = self.tab[ tab ]['lw_pathways'].findItems( self.tab[tab]['lw_regExp'].text(), Qt.MatchContains )
        for i in items:
            i.setSelected( True )            
    
    def onRegexpRemove(self):
        tab = self.sender().objectName()
        items = self.tab[ tab ]['lw_pathways'].findItems( self.tab[tab]['lw_regExp'].text(), Qt.MatchContains )
        for i in items:
            i.setSelected( False )            
    
    def setupTabPage(self, tab, selected_pathways = []):
        # SHOW PATHWAYS
        page = QWidget()
        vbox = QVBoxLayout()
        # Populate the list boxes
        self.tab[tab]['lw_pathways'] = QListWidget()
        self.tab[tab]['lw_pathways'].setSelectionMode( QAbstractItemView.ExtendedSelection)
        self.tab[tab]['lw_pathways'].addItems( self.all_pathways )

        for p in selected_pathways:
            self.tab[tab]['lw_pathways'].findItems(p, Qt.MatchExactly)[0].setSelected(True)
        self.tab[tab]['lw_regExp'] = QLineEdit()

        vbox.addWidget(self.tab[tab]['lw_pathways'])
        vbox.addWidget( QLabel('Select/deselect matching pathways by name:') )   
        vboxh = QHBoxLayout()
        vboxh.addWidget(self.tab[tab]['lw_regExp'])
        addfr = QPushButton('-')
        addfr.clicked.connect( self.onRegexpRemove )
        addfr.setObjectName(tab)
        remfr = QPushButton('+')
        remfr.clicked.connect( self.onRegexpAdd)
        remfr.setObjectName(tab)

        vboxh.addWidget( addfr )
        vboxh.addWidget( remfr )
        vbox.addLayout(vboxh)   

        page.setLayout(vbox)
        
        return page

    def __init__(self, parent, **kwargs):
        super(dialogPathwaysShow, self).__init__(parent, **kwargs)
        
        self.setWindowTitle("Select Pathways to Display")

        #all_pathways = parent.db.pathways.keys()
        self.all_pathways = sorted( [p.name for p in parent.db.pathways.values()] )

        self.tabs = QTabWidget()
        self.tab = defaultdict(dict)
        selected_pathways = str( parent.config.value('/Pathways/Show') ).split(',')
        page1 = self.setupTabPage('show', selected_pathways=[p.name for p in parent.db.pathways.values() if p.id in selected_pathways] )
        selected_pathways = str( parent.config.value('/Pathways/Hide') ).split(',')
        page2 = self.setupTabPage('hide', selected_pathways=[p.name for p in parent.db.pathways.values() if p.id in selected_pathways] )

        self.tabs.addTab(page1, 'Show')
        self.tabs.addTab(page2, 'Hide')

        self.layout.addWidget(self.tabs)
        
        # Stack it all up, with extra buttons
        self.dialogFinalise()


  
        
class dialogMiningSettings(ui.genericDialog):

    def __init__(self, parent=None, **kwargs):
        super(dialogMiningSettings, self).__init__(parent, **kwargs)        
        
        self.setWindowTitle("Setup for Data-based Pathway Mining")
        self.parent = parent

        self.cb_miningType = QComboBox()
        self.cb_miningType.addItems( METAPATH_MINING_TYPE_TEXT )
        self.cb_miningType.setCurrentIndex( METAPATH_MINING_TYPE_CODE.index( parent.config.value('/Data/MiningType') ) )

        self.xb_miningRelative = QCheckBox('Relative score to pathway size') 
        self.xb_miningRelative.setChecked( bool(parent.config.value('/Data/MiningRelative') ) )

        self.xb_miningShared = QCheckBox('Share compound scores between pathways') 
        self.xb_miningShared.setChecked( bool(parent.config.value('/Data/MiningShared') ) )
                        

        self.sb_miningDepth = QSpinBox()
        self.sb_miningDepth.setMinimum(1)
        self.sb_miningDepth.setValue( int( parent.config.value('/Data/MiningDepth') ) )
        
        self.layout.addWidget(self.cb_miningType)
        self.layout.addWidget(self.xb_miningRelative)
        self.layout.addWidget(self.xb_miningShared)
        self.layout.addWidget(self.sb_miningDepth)
        
        # Stack it all up, with extra buttons
        self.dialogFinalise()
         
class MainWindow(ui.MainWindowUI):

    def __init__(self, app):

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
        self.url_handlers = {}
        self.app_launchers = {}

        # Create templating engine
        self.templateEngine = Engine(
            loader=FileLoader( [os.path.join( utils.scriptdir,'html')] ),
            extensions=[CoreExtension(),CodeExtension()]
        )

        self.update_view_callback_enabled = True

        self.printer = QPrinter()

        # Inhereted from ui; UI setup etc
        super(MainWindow, self).__init__()


        if self.config.value('/MetaPath/Is_Setup') != True:
            print "Setting up initial configuration..."
            self.onResetConfig()
        
            print 'Done'
        
        self.onResetConfig()
        

        # Additional tabs; data analysis, data summary, identification, etc.
        #analysisv = d3View( self )
        #analysisv.generate()
        #self.tabs.addTab( analysisv.browser, '&d3' )

        # Additional tabs; data analysis, data summary, identification, etc.
        #analysisc = analysisCircosView( self )
        #analysisc.generate()
        #self.tabs.addTab( analysisc.browser, '&Circo' )


        self.setWindowTitle('MetaPath: Metabolic pathway visualisation and analysis')
        self.statusBar().showMessage('Ready')


        self.showMaximized()


        
    # Init
    
    def onResetConfig(self):
        # Defaults not set, apply now and save complete config file
        self.config.setValue('/Pathways/Show', 'GLYCOLYSIS') 
        self.config.setValue('/Pathways/ShowLinks', False)

        self.config.setValue('/Data/MiningActive', False)
        self.config.setValue('/Data/MiningDepth', 5)
        self.config.setValue('/Data/MiningType', 'c')

        self.config.setValue('/Data/MiningRelative', False)
        self.config.setValue('/Data/MiningShared', True)

        self.config.setValue('/View/ShowEnzymes', True)
        self.config.setValue('/View/Show2nd', True)
        self.config.setValue('/View/ShowMolecular', True)
        self.config.setValue('/View/ShowAnalysis', True)

        self.config.setValue('/View/HighlightPathways', True)
        self.config.setValue('/View/HighlightRegions', True)

        self.config.setValue('/View/ClusterBy', 'pathway')
        
        self.config.setValue('/MetaPath/Is_Setup', True)

        #self.generateGraphView()


    
    # UI Events           

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

    def onPathwaysShow(self):
        dialog = dialogPathwaysShow(self)
        ok = dialog.exec_()
        if ok:
            # Show
            idx = dialog.tab['show']['lw_pathways'].selectedItems()
            pathways = [self.db.synrev[ x.text() ].id for x in idx]
            self.config.setValue('/Pathways/Show', ','.join(pathways) )
            # Hide
            idx = dialog.tab['hide']['lw_pathways'].selectedItems()
            pathways = [self.db.synrev[ x.text() ].id for x in idx]
            self.config.setValue('/Pathways/Hide', ','.join(pathways) )
                  
            # Generate
            self.generateGraphView()

    def onBrowserNav(self, url):
        # Interpret internal URLs for message passing to display Compound, Reaction, Pathway data in the sidebar interface
        # then block the continued loading
        if url.scheme() == 'metapath':
            # Take string from metapath:// onwards, split on /
            app = url.host()
            if app == 'app-manager':
                app, action = url.path().strip('/').split('/')
                if action == 'add':

                    self.app_launchers[ app ]()

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
                    elif kind == 'gene' and id in self.db.gene:
                        gene = self.db.genes[id]
                        self.generatedbBrowserView(template='db/gene.html', data={
                            'title': gene.name,
                            'object': gene,
                            })
                            
                    # Focus the database dock
                    self.dataDock.raise_()

            
            

            #metaviz/compound/%s/view            
            elif app in self.url_handlers:
                self.url_handlers[app]( url.path().strip('/') )

                # Store URL so we can reload the sidebar later
                self.dbBrowser_CurrentURL = url

        else:
            # It's an URL open in default browser
            QDesktopServices.openUrl(url)
             
    def onBrowserLoadDone(self, ok):
        # Reload the sidebar on main window refresh: this is only bound to the main window so no need to check for action
        if isinstance(self.dbBrowser_CurrentURL, QUrl): # We've got an url, reload
            self.onBrowserNav(self.dbBrowser_CurrentURL)

    def onLoadIdentities(self):
        """ Open a data file"""
        filename, _ = QFileDialog.getOpenFileName(self, 'Load compound identities file', '')
        if filename:
            self.db.load_synonyms(filename)
            # Re-translate the datafile if there is one and refresh
            if self.data:
                self.data.translate(self.db)
                self.generateGraphView(regenerate_analysis=True)                

               
    def onLoadDataFile(self):
        """ Open a data file"""
        filename, _ = QFileDialog.getOpenFileName(self, 'Open experimental compound data file', '')
        if filename:
            self.data = data.dataManager(filename)
            # Re-translate the datafile
            self.data.translate(self.db)
            self.setWindowTitle('MetaPath: %s' % self.data.filename)
            self.onDefineExperiment()


    def onLoadLayoutFile(self):
        """ Open a layout file e.g. in KGML format"""
        # e.g. www.genome.jp/kegg-bin/download?entry=hsa00010&format=kgml
        filename, _ = QFileDialog.getOpenFileName(self, 'Open layout file (KEGG, etc.)', '')
        if filename:
            self.layout = layout.layoutManager(filename)
            # Re-translate the datafile
            self.layout.translate(self.db)
            # Regenerate the graph view
            self.generateGraphView()            
    
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
        QMessageBox.about(self,'About MetaPath', 
            'A visualisation and analysis tool for metabolomics data in the context of metabolic pathways.')

    def onExit(self):
        self.Close(True)  # Close the frame.

    def onReloadDB(self):
        self.db=db.databaseManager()
        self.generateGraphView()

    def onRefresh(self):
        self.generateGraphView()
 
 
 
 
    def generatedbBrowserView(self, template='base.html', data={'title':'', 'object':{}, 'data':{} }):
        
        metadata = {
            'htmlbase': os.path.join( utils.scriptdir,'html'),
            # Current state data
            'current_pathways': self.config.value('/Pathways/Show').split(','),
            'data': self.data,
            # Color schemes
            # 'rdbu9':['b2182b', 'd6604d', 'f4a582', '33a02c', 'fddbc7', 'f7f7f7', 'd1e5f0', '92c5de', '4393c3', '2166ac']
        }
            
        template = self.templateEngine.get_template(template)
        self.dbBrowser.setHtml(template.render( dict( data.items() + metadata.items() ) ),QUrl("~")) 
      
def main():
    # Create a Qt application
    app = QApplication(sys.argv)
    app.setStyle('fusion')
    app.setOrganizationName("Martin Fitzpatrick")
    app.setOrganizationDomain("martinfitzpatrick.name")
    app.setApplicationName("MetaPath")
    window = MainWindow(app)
    app.exec_()
    # Enter Qt application main loop
    sys.exit()
    
if __name__ == "__main__":
    main()
