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

import os, copy

from plugins import IdentificationPlugin

import numpy as np

import ui, db, utils
from data import DataSet, DataDefinition


class MapEntityView( ui.GenericView ):

    def __init__(self, plugin, parent, **kwargs):
        super(MapEntityView, self).__init__(plugin, parent, **kwargs)

        # Define automatic mapping (settings will determine the route; allow manual tweaks later)
                
        self.addDataToolBar()
        self.addFigureToolBar()
        self.data.add_interface('output')
        
        self.browser = ui.QWebViewExtend(self.tabs, self.m.onBrowserNav)
        self.tabs.addTab(self.browser, 'Entities')
    
        t = self.addToolBar('Entity Mapping')
        t.setIconSize( QSize(16,16) )

        load_mappingAction = QAction( QIcon( os.path.join(  self.plugin.path, 'bruker.png' ) ), 'Import manual entity mapping\u2026', self.m)
        load_mappingAction.setStatusTip('Import manual mapping from names to MetaCyc entities')
        load_mappingAction.triggered.connect(self.onImportEntities)
        t.addAction(load_mappingAction)        
        
        self._entity_mapping_table = {}
        
        # Setup data consumer options
        self.data.consumer_defs.append( 
            DataDefinition('input', {
            'labels_n':     (None, '>1'),
            'entities_t':   (None, None), 
            })
        )
        
        self.data.consume_any_of( self.m.datasets[::-1] ) # Try consume any dataset; work backwards

        self.data.source_updated.connect( self.generate ) # Auto-regenerate if the source data is modified
        self.generate()

    def onImportEntities(self):
        """ Open a data file"""
        filename, _ = QFileDialog.getOpenFileName(self.m, self.import_description, 'Load CSV mapping for name <> identity', "All compatible files (*.csv);;Comma Separated Values (*.csv);;All files (*.*)")
        if filename:

            self._entity_mapping_table = {}
            # Load metabolite entities mapping from file (csv)
            reader = csv.reader( open( filename, 'rU'), delimiter='\t', dialect='excel')
    
            # Read each row in turn, build link between items on a row (multiway map)
            # If either can find an entity (via synonyms; make the link)
            for row in reader:
                for s in row:
                    if s in self.m.db.index:
                        e = self.m.db.index[ s ]
                        break
                else:
                    continue # next row if we find nothing
                    
                # break to here if we do
                for s in row:
                    self._entity_mapping_table[ s ] = e
                    
            
            print self._entity_mapping_table
                
    
    def generate(self):
        self.setWorkspaceStatus('active')
    
        dsi = self.data.get('input')
        #dso = DataSet( size=dsi.shape )
    
        dso = self.translate( dsi, self.m.db)

        self.data.put('output', dso)
        
        metadata = {
            'entities':zip( dso.labels[1], dso.entities[1] ),
        
        }
        metadata['htmlbase'] = os.path.join( utils.scriptdir,'html')

        template = self.m.templateEngine.get_template( os.path.join(self.plugin.path, 'entities.html') )
        self.browser.setHtml(template.render( metadata ),QUrl("~")) 
        
        self.setWorkspaceStatus('done')

        self.clearWorkspaceStatus()



###### TRANSLATION to METACYC IDENTIFIERS
                        
    def translate(self, data, db):
        # Translate loaded data names to metabolite IDs using provided database for lookup
        for n,m in enumerate(data.labels[1]):
        
            # Match first using entity mapping table if set (allows override of defaults)
            if m in self._entity_mapping_table:
                data.entities[1][ n ] = db.index[ self._entity_mapping_table[ m ] ]

            elif m.lower() in db.synrev:
                data.entities[1][ n ] = db.synrev[ m.lower() ]
                
                #self.quantities[ transid ] = self.quantities.pop( m )
        #print self.metabolites
        return data
        

 
class MapEntity(IdentificationPlugin):

    def __init__(self, **kwargs):
        super(MapEntity, self).__init__(**kwargs)
        self.register_app_launcher( self.app_launcher )

    def app_launcher(self):
        #self.load_data_file()
        self.instances.append( MapEntityView( self, self.m ) ) 
