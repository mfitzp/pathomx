#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# Import PySide classes
from PySide.QtGui import *
from PySide.QtCore import *
from PySide.QtWebKit import *
from PySide.QtNetwork import *

import os, sys, re, math, codecs, locale

import pydot
import urllib2

from optparse import Values
from collections import defaultdict

import numpy as np

# wheezy templating engine
from wheezy.template.engine import Engine
from wheezy.template.ext.core import CoreExtension
from wheezy.template.ext.code import CodeExtension
from wheezy.template.loader import FileLoader

try:
    import xml.etree.cElementTree as et
except ImportError:
    import xml.etree.ElementTree as et

from gpml2svg import gpml2svg

# MetaPath classes
import db, data, core, utils, layout, ui, figure


METAPATH_MINING_TYPE_CODE = ('c', 'u', 'd', 'm')
METAPATH_MINING_TYPE_TEXT = (
    'Metabolite change scores for pathway',
    'Metabolite up-regulation scores for pathway', 
    'Metabolite down-regulation scores for pathway',
    'Number metabolites with data per pathway',
)

reload(sys).setdefaultencoding('utf8')

# Class for analysis views, using graph-based visualisations of defined datasets
# associated layout and/or analysis
class analysisView(object):
    def __init__(self, parent):
        self.parent = parent
        self.browser = ui.QWebViewScrollFix( parent.onBrowserNav )
        
        parent.tab_handlers.append( self )
    
    def render(self, metadata):
        template = self.parent.templateEngine.get_template('figure.html')
        self.browser.setHtml(template.render( metadata ),"~") 
        
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


class analysisEquilibriaView(analysisView):
    def __init__(self, *args, **kwargs):
        super(analysisEquilibriaView, self).__init__(*args, **kwargs)
    
        self.nucleosides = [
            ['AMP', 'ADP', 'ATP'],
            ['CMP', 'CDP', 'CTP'],
            ['GMP', 'GDP', 'GTP'],
            ['UMP', 'UDP', 'UTP'],
            ['TMP', 'TDP', 'TTP'],
            #---
            ['DAMP', 'DADP', 'DATP'],
            ['DCMP', 'DCDP', 'DCTP'],
            ['DGMP', 'DGDP', 'DGTP'],
            ['DUMP', 'DUDP', 'DUTP'],
            ['DTMP', 'DTDP', 'DTTP'],
            #---
            ['Pi', 'PPI', 'PI3','PI4'],
            #---
            ['NAD','NADP'],            
            ['NADH','NADPH'],
        ]
        
        self.proton = [
            ['NAD', 'NADH'],
            ['NADP','NADPH'],
            ['FAD','FADH','FADH2'],
        ]
        
        redox = [
            ['OXYGEN-MOLECULE', 'WATER'],
            ['', 'PROTON'],
            ['NAD', 'NADH'],
            ['NADP','NADPH'],
            ['FAD','FADH','FADH2'],
        ]
        
        proton_carriers = {'WATER':1,'PROTON':1,'NADH':1,'NADPH':1,'FADH':1,'FADH2':2} # Double count for H2

        phosphate_carriers = {
            'AMP':1, 'ADP':2, 'ATP':3,
            'GMP':1, 'GDP':2, 'GTP':4, 
            #---
            'Pi':1,  'PPI':2, 'PI3':3, 'PI4':4,
            #---
            'NADP':1, 'NADPH':1,
            }
                
        phosphate = [
            ['AMP', 'ADP'],
            ['ADP', 'ATP'],
            ['GMP', 'GDP'],
            ['GDP', 'GTP'],
            #---
            ['Pi',  'PPI'],
            ['PPI', 'PI3'],
            ['PI3', 'PI4'],
            #---
            ['NAD','NADP'],            
            ['NADH','NADPH'],
        ]
        
        # Build redox reaction table
        # Iterate database, find any reactions with a PROTON in left/right reaction
        # - or NAD->NADH or, or, or
        # If on left, swap
        # Store entry for Min,Mout
        self.redox = self.equilibrium_table_builder( proton_carriers ) 
        self.phosphate = self.equilibrium_table_builder( phosphate_carriers ) 

    def equilibrium_table_builder(self, objs):
        result = []
        for rk,r in self.parent.db.reactions.items():
            inH = sum( [objs[m.id] for m in r.smtins if m.id in objs] )
            outH = sum( [objs[m.id] for m in r.smtouts if m.id in objs] )


            balance = inH-outH
            add_it = False
            if balance > 0:
                add_it = ( r.mtins, r.mtouts )
            elif balance < 0: # Reverse
                add_it = ( r.mtouts, r.mtins )
                
            if add_it:
                for mtin in add_it[0]:
                    for mtout in add_it[1]:
                        result.append( [mtin.id, mtout.id] )  
        return result               

    def cofactor_table_builder(self, objs):
        result = []
        for p in objs:
            pin = self.parent.db.metabolites[ p[0] ] if p[0] in self.parent.db.metabolites.keys() else False
            pout = self.parent.db.metabolites[ p[1] ] if p[1] in self.parent.db.metabolites.keys() else False

            if pin and pout:
                for rk,r in self.parent.db.reactions.items():
                    add_it = False
                    if pin in r.smtins and pout in r.smtouts:
                        add_it = ( r.mtins, r.mtouts )
                    elif pout in r.smtins and pin in r.smtouts:
                        add_it = ( r.mtouts, r.mtins )

                    if add_it:
                        for mtin in add_it[0]:
                            for mtout in add_it[1]:
                                result.append( [mtin.id, mtout.id] )  

        return result

    def generate(self):

        labelsX=[ 'Phosphorylated','Dephosphorylated' ]
        labelsY=['→'.join(n) for n in self.phosphate]

        data_phosphate = self.build_log2_change_table_of_classtypes( self.phosphate, labelsX )
        phosphatefig = self.get_fig_tempfile( figure.heatmap( data_phosphate, labelsX=labelsX, labelsY=labelsY) )

        labelsX=[ 'Pi','PPI','PI3','PI4' ]
        labelsY=['→'.join(n) for n in self.nucleosides]

        data_nuc = self.build_log2_change_table_of_classtypes( self.nucleosides, labelsX )
        nucelosidefig = self.get_fig_tempfile( figure.heatmap( data_nuc, labelsX=labelsX, labelsY=labelsY) )

        labelsX=[ 'Reduced','Oxidised' ]
        labelsY=['→'.join(n) for n in self.redox]

        data_redox = self.build_log2_change_table_of_classtypes( self.redox, labelsX )
        redoxfig = self.get_fig_tempfile( figure.heatmap( data_redox, labelsX=labelsX, labelsY=labelsY) )

        labelsX=[ '-','H','H2' ]
        labelsY=['→'.join(n) for n in self.proton]

        data_proton = self.build_log2_change_table_of_classtypes( self.proton, labelsX )
        protonfig = self.get_fig_tempfile( figure.heatmap( data_proton, labelsX=labelsX, labelsY=labelsY) )
  
        self.render( {
            'htmlbase': os.path.join( utils.scriptdir,'html'),
            'figures': {
                    'Oxidative/Reductive State':[[
                        {
                            'figure':redoxfig.fileName(), 
                            'legend':('Redox reaction balance.','Relative quantities of metabolites on oxidative and reductive reaction. \
                            Left-to-right is oxidative.'),
                        },
                        {
                            'figure':protonfig.fileName(), 
                            'legend':('Redox carrier  balance.','Relative quantities of redox potential carriers. \
                            Left-to-right shows increasing reduction.'),
                        },]],
                    'Phosphorylation and Phosphate carriers':[[
                        {
                            'figure':phosphatefig.fileName(), 
                            'legend':('Redox reaction balance.','Relative quantities of metabolites on oxidative and reductive reaction. \
                            Left-to-right is oxidative.'),
                        },
                        {
                            'figure':nucelosidefig.fileName(), 
                            'legend':('Nucleoside phosphorylation balance.','Relative quantities of nucleosides in each experimental class grouping. \
                            Left-to-right shows increasing phosphorylation.'),
                        },

                    ]],
                    }, 
        })
        


class analysisMetaboliteView(analysisView):
    def generate(self):
        # Sort by scores
        ms = [ (k,v['score']) for k,v in self.parent.data.analysis.items() ]
        sms = sorted(ms,key=lambda x: abs(x[1]), reverse=True )
        metabolites = [m for m,s in sms]

        labelsY = metabolites[:30]
        labelsX = sorted( self.parent.data.quantities[labelsY[0]].keys() )

        data1 = self.build_log2_change_control_vs_multi(labelsY, labelsX)
        filename1 = self.get_fig_tempfile( figure.heatmap( data1, labelsX=labelsX, labelsY=labelsY) )

        data2 = self.build_raw_change_control_vs_multi(labelsY, labelsX)
        filename2 = self.get_fig_tempfile( figure.heatmap( data2, labelsX=labelsX, labelsY=labelsY) )
  
        self.render( {
            'htmlbase': os.path.join( utils.scriptdir,'html'),
            'figures': {'Key Metabolites':[[
                        {
                            'figure':filename1.fileName(), 
                            'legend':('Relative change in metabolite concentration vs. control (%s) under each experimental condition.' % self.parent.experiment['control'],
                                      'Scale indicates Log2 concentration change in original units, mean centered to zero. Red up, blue down.'),
                        },
                        {
                            'figure':filename2.fileName(), 
                            'legend':('Raw metabolite concentration changes vs. control (%s) under each experimental condition.' % self.parent.experiment['control'],
                                    'Scale indicates linear concentration change in original unites, mean centered to zero. Red up, blue down.'),
                        },
                    ]]},
        })
        


class analysisEnergyWasteView(analysisView):
    def generate(self):
        # Standard energy sources (CHO)
        m_energy = ['GLC','GLN',
        # Standard energy modulators (co-factors, carriers, etc.)
                    'CARNITINE',
        # Standard waste metabolites
                    'L-LACTATE',]

        # Build table of metabolic endpoints
        # i.e. metabolites not at the 'in' point of any reactions (or in a bidirectional)
        endpoints = []
        for k,m in self.parent.db.metabolites.items():
            if m.type == 'compound':
                for r in m.reactions:
                    if m in r.mtins or r.dir == 'both':
                        break    
                else:
                    # Only if we find no reactions
                    endpoints.append(m.id)


        labelsY = endpoints
        labelsX = sorted( self.parent.data.quantities[labelsY[0]].keys() ) 
        endpoint_data = self.build_log2_change_control_vs_multi( labelsY, labelsX)
        endpoint_fig = self.get_fig_tempfile( figure.heatmap( endpoint_data, labelsX=labelsX, labelsY=labelsY) )

        labelsY = m_energy
        energy_data = self.build_log2_change_control_vs_multi( labelsY, labelsX)
        energy_fig = self.get_fig_tempfile( figure.heatmap( energy_data, labelsX=labelsX, labelsY=labelsY) )
  
        self.render( {
            'htmlbase': os.path.join( utils.scriptdir,'html'),
            'figures': {'Metabolic Endpoints & Energy':[[
                        {
                            'figure':endpoint_fig.fileName(), 
                            'legend':('Relative change in concentration of metabolic endpoints vs. control (%s) under each experimental condition.' % self.parent.experiment['control'],
                                      'Scale indicates Log2 concentration change in original units, mean centered to zero. Red up, blue down. Metabolic endpoint in this context refers to \
                                      metabolites for which there exists no onward reaction in the database.'),
                        },
                        {
                            'figure':energy_fig.fileName(), 
                            'legend':('Relative change in concentration of common energy sources, carriers and sinks vs. control (%s) under each experimental condition.' % self.parent.experiment['control'],
                                      'Scale indicates Log2 concentration change in original units, mean centered to zero. Red up, blue down.'),
                        }                    
                    ]]},
        })


# Class for data visualisations using GPML formatted pathways
# Supports loading from local file and WikiPathways
class gpmlPathwayView(analysisView):
    def __init__(self, parent, gpml=None, svg=None, **kwargs):
        super(gpmlPathwayView, self).__init__(parent, **kwargs)

        self.gpml = gpml # Source GPML file
        self.svg = svg # Rendered GPML file as SVG
        self.metadata = {}
        
        
    def load_gpml_file(self, filename):
        f = open(filename,'r')
        self.gpml = f.read()
        f.close()
        
    def load_gpml_wikipathways(self, pathway_id):
        f = urllib2.urlopen('http://www.wikipathways.org//wpi/wpi.php?action=downloadFile&type=gpml&pwTitle=Pathway:%s&revision=0' % pathway_id )
        self.gpml = f.read()
        f.close()
        
    def get_xref_via_unification(self, database, id):
        xref_translate = {
            'Kegg Compound': 'LIGAND-CPD',
            'Entrez Gene': 'ENTREZ',
            'HMDB': 'HMDB',
            'CAS': 'CAS',
            }
        if database in xref_translate:
            obj = self.parent.db.get_via_unification( xref_translate[database], id )
            if obj:
                return ('MetaCyc %s' % obj.type, obj.id )
        return None
            
    def get_extended_xref_via_unification_list(self, xrefs):
        if xrefs:
            for xref,id in xrefs.items():
                xref_extra = self.get_xref_via_unification( xref, id )
                if xref_extra:
                    xrefs[ xref_extra[0] ] = xref_extra[1]
        return xrefs
                
    def get_xref(self, obj):
        print obj, obj.type, obj.id
        
        return ('MetaCyc %s' % obj.type, obj.id)
        
    def generate(self):
    
        # Add our urls to the defaults
        xref_urls = {
            'MetaCyc compound': 'metapath://metabolite/%s/view',
            'MetaCyc gene': 'metapath://gene/%s/view',
            'MetaCyc protein': 'metapath://protein/%s/view',
            'WikiPathways': 'metapath://wikipathway/%s/import',
        }
        
        if self.parent.data and self.parent.data.analysis:
            # Build color_table
            node_colors = {}
            for m_id, analysis in self.parent.data.analysis.items():
                if m_id in self.parent.db.metabolites.keys():
                    node_colors[ self.get_xref( self.parent.db.metabolites[ m_id ] ) ] = ( core.rdbu9[ analysis['color'] ], core.rdbu9c[ analysis['color'] ] )
        else:
            node_colors = {}
            
        if self.gpml:
            self.svg, self.metadata = gpml2svg.gpml2svg( self.gpml, xref_urls=xref_urls, xref_synonyms_fn=self.get_extended_xref_via_unification_list, node_colors=node_colors ) # Add MetaPath required customisations here
            self.render()
            print self.svg
        else:
            self.svg = None
            
    def render(self):
        if self.svg is None:
            self.generate()
        
        if self.svg is None:
            html_source = ''
        else:
            html_source = '''<html><body><div id="svg%d" class="svg">''' + self.svg + '''</body></html>'''

        self.browser.setHtml(html_source)


class dialogWikiPathways(ui.remoteQueryDialog):
    def __init__(self, parent=None, **kwargs):
        super(dialogWikiPathways, self).__init__(parent, **kwargs)        
        
        self.setWindowTitle("Load GPML pathway from WikiPathways")

    def parse(self, data):
        result = {}
        tree = et.fromstring( data.encode('utf-8') )
        pathways = tree.iterfind('{http://www.wso2.org/php/xsd}result')
        
        for p in pathways:
            result[ '%s (%s)' % (p.find('{http://www.wikipathways.org/webservice}name').text, p.find('{http://www.wikipathways.org/webservice}species').text ) ] = p.find('{http://www.wikipathways.org/webservice}id').text
            
        return result        
    
      
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

        self.xb_miningShared = QCheckBox('Share metabolite scores between pathways') 
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

    def __init__(self):


        # Central variable for storing application configuration (load/save from file?
        self.config = QSettings()
        
        if self.config.value('/MetaPath/Is_Setup') != True:
            print "Setting up initial configuration..."
            self.onResetConfig()
        
            print 'Done'

        # Create database accessor
        self.db = db.databaseManager()
        self.data = None #data.dataManager() No data loaded by default
        self.experiment = dict()
        self.layout = None # No map by default

        # The following holds tabs & pathway objects for gpml imported pathways
        self.gpmlpathways = [] 
        self.tab_handlers = []

        # Create templating engine
        self.templateEngine = Engine(
            loader=FileLoader( [os.path.join( utils.scriptdir,'html')] ),
            extensions=[CoreExtension(),CodeExtension()]
        )

        self.update_view_callback_enabled = True

        self.printer = QPrinter()

        # Inhereted from ui; UI setup etc
        super(MainWindow, self).__init__()

        self.setWindowTitle('MetaPath: Metabolic pathway visualisation and analysis')
        self.statusBar().showMessage('Ready')


        self.showMaximized()
        
    # Init
    
    def onResetConfig(self):
        # Defaults not set, apply now and save complete config file
        self.config.setValue('/Pathways/Show', '') 
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

        self.generateGraphView()


    
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
        # Interpret the (fake) URL to display Metabolite, Reaction, Pathway data in the sidebar interface
        # then block the continued loading

        # url is Qurl type
        if url.scheme() == 'metapath':

            # Take string from metapath:// onwards, split on /
            type = url.host()
            null, id, action = url.path().split('/') # FIXME: Can use split here once stop using pathwaynames           
            
            # Add an object to the current view
            if action == 'add':
    
                # FIXME: Hacky test of an idea
                if type == 'pathway':
                    # Add the pathway and regenerate
                    pathways = self.config.value('/Pathways/Show').split(',')
                    pathways.append( urllib2.unquote(id) )
                    self.config.setValue('/Pathways/Show', ','.join(pathways) )
                    self.generateGraphView()   

            # Remove an object to the current view
            if action == 'remove':
    
                # FIXME: Hacky test of an idea
                if type == 'pathway':
                    # Add the pathway and regenerate
                    pathways = self.config.value('/Pathways/Show').split(',')
                    pathways.remove( urllib2.unquote(id) )
                    self.config.setValue('/Pathways/Show', ','.join(pathways))
                    self.generateGraphView()

            # View an object
            if action == 'view':
                if type == 'pathway':
                    pathway = self.db.pathways[id]
                    self.generatedbBrowserView(template='pathway.html', data={
                        'title': pathway.name,
                        'object': pathway,
                        })
                elif type == 'reaction':
                    reaction = self.db.reactions[id]
                    self.generatedbBrowserView(template='reaction.html', data={
                        'title': reaction.name,
                        'object': reaction,
                        })
                elif type == 'metabolite':
                    metabolite = self.db.metabolites[id]
                    self.generatedbBrowserView(template='metabolite.html', data={
                        'title': metabolite.name,
                        'object': metabolite,
                        })
                elif type == 'protein':
                    protein = self.db.proteins[id]
                    self.generatedbBrowserView(template='protein.html', data={
                        'title': protein.name,
                        'object': protein,
                        })
                elif type == 'gene':
                    gene = self.db.genes[id]
                    self.generatedbBrowserView(template='gene.html', data={
                        'title': gene.name,
                        'object': gene,
                        })

            if action == 'import':
                if type == 'wikipathway':
                    gpmlpathway = gpmlPathwayView( self )
                    gpmlpathway.load_gpml_wikipathways(id)
                    gpmlpathway.generate()

                    self.gpmlpathways.append(gpmlpathway)
                    self.tabs.addTab( gpmlpathway.browser, gpmlpathway.metadata['Name'] )

                        
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
        filename, _ = QFileDialog.getOpenFileName(self, 'Load metabolite identities file', '')
        if filename:
            self.db.load_synonyms(filename)
            # Re-translate the datafile if there is one and refresh
            if self.data:
                self.data.translate(self.db)
                self.generateGraphView(regenerate_analysis=True)                

               
    def onLoadDataFile(self):
        """ Open a data file"""
        filename, _ = QFileDialog.getOpenFileName(self, 'Open experimental metabolite data file', '')
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

    def onLoadGPMLPathway(self):
        """ Open a GPML pathway file """
        filename, _ = QFileDialog.getOpenFileName(self, 'Open GPML pathway file', '')
        if filename:
        
            gpmlpathway = gpmlPathwayView( self )

            gpmlpathway.load_gpml_file(filename)
            gpmlpathway.generate()

            self.gpmlpathways.append(gpmlpathway)
            self.tabs.addTab( gpmlpathway.browser, gpmlpathway.metadata['Name'] )

    def onLoadGPMLWikiPathways(self):
        dialog = dialogWikiPathways(parent=self, query_target='http://www.wikipathways.org/wpi/webservice/webservice.php/findPathwaysByText?query=%s')
        ok = dialog.exec_()
        if ok:
            # Show
            idx = dialog.select.selectedItems()
            for x in idx:
                gpmlpathway = gpmlPathwayView( self )
                pathway_id = dialog.data[x.text()]
                
                gpmlpathway.load_gpml_wikipathways(pathway_id)
                gpmlpathway.generate()

                self.gpmlpathways.append(gpmlpathway)
                self.tabs.addTab( gpmlpathway.browser, gpmlpathway.metadata['Name'] )
            
    def onDefineExperiment(self):
        """ Open the experimental setup dialog to define conditions, ranges, class-comparisons, etc. """
        dialog = dialogDefineExperiment(parent=self)
        ok = dialog.exec_()
        if ok:
            # Regenerate the graph view
            self.experiment['control'] = dialog.cb_control.currentText()
            self.experiment['test'] = dialog.cb_test.currentText()      
        
            # Update toolbar to match any change caused by timecourse settings
            self.update_view_callback_enabled = False # Disable to stop multiple refresh as updating the list
            self.cb_control.clear()
            self.cb_test.clear()

            self.cb_control.addItems( [dialog.cb_control.itemText(i) for i in range(dialog.cb_control.count())] )
            self.cb_test.addItems( [dialog.cb_test.itemText(i) for i in range(dialog.cb_test.count())] )
            
            if dialog.le_timecourseRegExp.text() != '':
                self.experiment['timecourse'] = dialog.le_timecourseRegExp.text()
            elif 'timecourse' in self.experiment:                
                del(self.experiment['timecourse'])
        
            # Update the toolbar dropdown to match
            self.cb_control.setCurrentIndex( self.cb_control.findText( self.experiment['control'] ) )
            self.cb_test.setCurrentIndex( self.cb_test.findText( self.experiment['test'] ) )
                  
            self.update_view_callback_enabled = True    

            self.generateGraphView(regenerate_analysis=True)
            
            analysisv = analysisMetaboliteView( self )
            analysisv.generate()
            self.tabs.addTab( analysisv.browser, '&Metabolites' )
            
            analysise = analysisEquilibriaView( self )
            analysise.generate()
            self.tabs.addTab( analysise.browser, 'E&quilibria' )

            analysisw = analysisEnergyWasteView( self )
            analysisw.generate()
            self.tabs.addTab( analysisw.browser, '&Energy and Waste' )
            
            #self.tabs.addTab( analysisv.browser, 'Genes' )
            #self.tabs.addTab( analysisv.browser, 'Proteins' )            
    
        
    def onModifyExperiment(self):
        """ Change control or test settings from toolbar interaction """
        # Cheat a bit, simply change both - only one will be incorrect
        if self.update_view_callback_enabled:
            self.experiment['control'] = self.cb_control.currentText()
            self.experiment['test'] = self.cb_test.currentText()
            self.generateGraphView(regenerate_analysis=True)

    def onMiningSettings(self):
        """ Open the mining setup dialog to define conditions, ranges, class-comparisons, etc. """
        dialog = dialogMiningSettings(parent=self)
        ok = dialog.exec_()
        if ok:
            self.config.setValue('/Data/MiningDepth', dialog.sb_miningDepth.value() )
            self.config.setValue('/Data/MiningType', METAPATH_MINING_TYPE_CODE[ dialog.cb_miningType.currentIndex() ] )
            self.config.setValue('/Data/MiningRelative', dialog.xb_miningRelative.isChecked() )
            self.config.setValue('/Data/MiningShared', dialog.xb_miningShared.isChecked() )

            # Update the toolbar dropdown to match
            self.sb_miningDepth.setValue( dialog.sb_miningDepth.value() )        
            self.generateGraphView(regenerate_suggested=True)

    def onModifyMiningDepth(self):
        """ Change mine depth via toolbar spinner """    
        self.config.setValue('/Data/MiningDepth', self.sb_miningDepth.value())
        self.generateGraphView()
        
    def onModifyCluster(self):
        self.config.setValue('/View/ClusterBy', self.cluster_control.currentText() )
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
        
        
    def get_filename_with_counter(self, filename):
        fn, ext = os.path.splitext(filename)
        return fn + "-%s" + ext


    def generateGraph(self, filename, format = 'svg', regenerate_analysis = False, regenerate_suggested = False):
        # Build options-like structure for generation of graph
        # (compatibility with command line version, we need to fake it)
        options = Values()

        options._update_loose({
            'file':None,
            #'pathways': self.config.Read('/Pathways/Show'),
            #'not_pathways':'',
            'show_all': False, #self.config.ReadBool('/Pathways/ShowAll'),
            'control':'',
            'test':'',
            'search':'',
            'cluster_by': self.config.value('/View/ClusterBy'),
            'show_enzymes': bool( self.config.value('/View/ShowEnzymes') ), #self.config.ReadBool('/View/ShowEnzymes'),
            'show_secondary': bool( self.config.value('/View/Show2nd') ),
            'show_molecular': bool( self.config.value('/View/ShowMolecular') ),
            'show_network_analysis': bool( self.config.value('/View/ShowAnalysis') ),

            'highlightpathways': bool( self.config.value('/View/HighlightPathways') ),
            'highlightregions': bool( self.config.value('/View/HighlightRegions') ),

            'mining': bool( self.config.value('/Data/MiningActive') ),
            'mining_depth': int( self.config.value('/Data/MiningDepth') ),
            'mining_type': '%s%s%s' % ( self.config.value('/Data/MiningType'),
                                        'r' if bool( self.config.value('/Data/MiningRelative') ) else '',
                                        's' if bool( self.config.value('/Data/MiningShared') ) else '' ),
            'splines': 'spline',
            'focus':False,
            'show_pathway_links': bool( self.config.value('/Pathways/ShowLinks') ),
            # Always except when saving the file
            'output':format,

        })
        
        pathway_ids = self.config.value('/Pathways/Show').split(',')
        
        # If we have no analysis, or re-analysis is reqeusted
        if self.data and (self.data.analysis == None or regenerate_analysis):
            self.data.analyse( self.experiment )
            
            for t in self.tab_handlers:
                t.generate()
        
        # Add the selected pathways
        pathways = [self.db.pathways[pid] for pid in pathway_ids if pid in self.db.pathways.keys()]        
           
        # Add mining pathways
        if self.data and options.mining:
            # Regenerate pathway suggestions if none yet in place or requested (regenerating analysis will set suggested = None
            if self.data.analysis_suggested_pathways == None or regenerate_suggested:
                self.data.suggest( self.db, mining_type=options.mining_type, mining_depth=options.mining_depth)
            pathways += self.data.analysis_suggested_pathways[0:options.mining_depth]

        # Now remove the Hide pathways
        pathway_ids_hide = self.config.value('/Pathways/Hide').split(',')
        pathways = [p for p in pathways if p.id not in pathway_ids_hide]
        
            
        if self.data:
            if self.data.analysis_timecourse:
                # Generate the multiple views
                tps = sorted( self.data.analysis_timecourse.keys(), key=int )
                # Insert counter variable into the filename
                filename = self.get_filename_with_counter(filename) 
                print "Generate timecourse..."
                for tp in tps:
                    print "%s" % tp
                    graph = core.generator( pathways, options, self.db, analysis=self.data.analysis_timecourse[ tp ], layout=self.layout) 
                    graph.write(filename % tp, format=options.output, prog='neato')
                return tps
            else:
                print "Generate map for single control:test..."
                graph = core.generator( pathways, options, self.db, analysis=self.data.analysis, layout=self.layout) 
                graph.write(filename, format=options.output, prog='neato')
                return None
        else:
            graph = core.generator( pathways, options, self.db, layout=self.layout) 
            graph.write(filename, format=options.output, prog='neato')
            return None
        
    def generateGraphView(self, regenerate_analysis = False, regenerate_suggested = False):

        # By default use the generated metapath file to view
        filename = os.path.join(QDir.tempPath(),'metapath-generated-pathway.svg')

        tps = self.generateGraph(filename=filename, format='svg', regenerate_analysis=regenerate_analysis, regenerate_suggested=regenerate_suggested)

        if tps == None:
            svg_source = [ open(filename).read().decode('utf8') ]
            tps = [0]
        else:
            filename = self.get_filename_with_counter(filename) 
            svg_source = [ 
                open( os.path.join( QDir.tempPath(), filename % tp) ).read().decode('utf8')
                for tp in tps
                ]
                
        # Add file:// refs to image links (Graphviz bug?)
        svg_source = [s.replace('<image xlink:href="','<image xlink:href="file://') for s in svg_source ]

        scale = ''
        if self.data:
            scalet, scaleb = u'', u''
            for n,s in enumerate(self.data.scale):
                scalet = scalet + '<td><div class="datasq rdbu9-%d"></div></td>' % (9-n)
                scaleb = scaleb + '<td>%d</td>' % (s)
            scale = '<table><tr><td></td>' + scalet + '</tr><tr><td class="scale-type">%s</td>' % self.data.scale_type + scaleb + '</tr></table>'
        else:
            n = 1

        html_source = '''<html>
        <script>
            current_svg = 1;
            previous_svg = 2;
        
            function init(){
                increment_view();
                window.setInterval('increment_view();',2000);
            }
        
            function increment_view(){
                if (current_svg > %d ){ current_svg = 1; return; }
                            
                document.getElementById('svg' + current_svg).classList.add('visible');
                document.getElementById('svg' + current_svg).classList.remove('hidden');
                
                document.getElementById('svg' + previous_svg).classList.add('hidden');
                document.getElementById('svg' + previous_svg).classList.remove('visible');
                
                previous_svg = current_svg
                current_svg += 1;
            }
        </script>
        <link rel="stylesheet" href="file://%s/css/base.css">''' % (n, str( os.path.join( utils.scriptdir,'html') ) ) + '''
        <body onload="init();">
            <div class="scalebar scalebar-inset">''' + scale + '''</div>'''
        
        for n, svg in enumerate( svg_source ):   
            html_source += '''<div id="svg%d" class="svg"><div class="svgno"><span data-icon="&#xe000;" aria-hidden="true"></span> %s''' % (n+1, tps[n])  + '''</div>''' + svg + '''</div>'''

        html_source += '''</body></html>'''
        
        self.mainBrowser.setHtml(html_source) #,"~") 
        
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
        self.dbBrowser.setHtml(template.render( dict( data.items() + metadata.items() ) ),"~") 
      
def main():
    # Create a Qt application
    app = QApplication(sys.argv)
    app.setOrganizationName("Martin Fitzpatrick")
    app.setOrganizationDomain("martinfitzpatrick.name")
    app.setApplicationName("MetaPath")

    window = MainWindow()
    # Enter Qt application main loop
    sys.exit(app.exec_())
    
if __name__ == "__main__":
    main()
