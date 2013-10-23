# -*- coding: utf-8 -*-
#from __future__ import unicode_literals

# Import PyQt5 classes
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWebKit import *
from PyQt5.QtNetwork import *
from PyQt5.QtWidgets import *
from PyQt5.QtWebKitWidgets import *
from PyQt5.QtPrintSupport import *

import os, copy

from utils import UnicodeReader, UnicodeWriter
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
        self.data.add_input('input') # Add input slot        
        self.data.add_output('output')
        
        self.browser = ui.QWebViewExtend(self.tabs, self.m.onBrowserNav)
        self.tabs.addTab(self.browser, 'Entities')
    
        t = self.getCreatedToolbar('Entity mapping','external-data')

        import_dataAction = QAction( QIcon( os.path.join(  utils.scriptdir, 'icons', 'disk--arrow.png' ) ), 'Load annotations from file\u2026', self.m)
        import_dataAction.setStatusTip('Load annotations from .csv. file')
        import_dataAction.triggered.connect(self.onImportEntities)
        t.addAction(import_dataAction)

        self.addExternalDataToolbar() # Add standard source data options

     
        
        self._entity_mapping_table = {}
        
        # Setup data consumer options
        self.data.consumer_defs.append( 
            DataDefinition('input', {
            'labels_n':     (None, '>1'),
            'entities_t':   (None, None), 
            })
        )
        
        self.data.source_updated.connect( self.autogenerate ) # Auto-regenerate if the source data is modified
        self.data.consume_any_of( self.m.datasets[::-1] ) # Try consume any dataset; work backwards


    def onImportEntities(self):
        """ Open a data file"""
        filename, _ = QFileDialog.getOpenFileName(self.m, 'Load entity mapping from file', 'Load CSV mapping for name <> identity', "All compatible files (*.csv);;Comma Separated Values (*.csv);;All files (*.*)")
        if filename:
            self.load_datafile(filename)
                
    def load_datafile(self,filename):

        self._entity_mapping_table = {}
        # Load metabolite entities mapping from file (csv)
        reader = UnicodeReader( open( filename, 'rU'), delimiter=',', dialect='excel')

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
        
            self.generate()
        
    
    def generate(self):
        self.setWorkspaceStatus('active')
    
        dsi = self.data.get('input')
        if dsi == False:
            self.setWorkspaceStatus('error')
            return False
    
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
                data.entities[1][ n ] = self._entity_mapping_table[ m ]

            # Use the internal database identities
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
        return MapEntityView( self, self.m ) 
