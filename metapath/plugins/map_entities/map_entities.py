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

import data, ui, db, utils

class MapEntityView( ui.GenericView ):
    def __init__(self, plugin, parent, **kwargs):
        super(MapEntityView, self).__init__(plugin, parent, **kwargs)

        # Define automatic mapping (settings will determine the route; allow manual tweaks later)
                
        self.addDataToolBar()
        self.addFigureToolBar()
        self.data.addo('output')
        
        #t.addAction(load_wikipathwaysAction)
        self.browser = ui.QWebViewExtend(self, self.m.onBrowserNav)
        self.tabs.addTab(self.browser, 'Entities')

        #self.a = QMainWindow()
        #self.a.setCentralWidget(self)
        #self.a.show()
        #self.show()
        
        # Setup data consumer options
        self.data.consumer_defs.append( 
            data.DataDefinition('input', {
            'labels_n':     (None, '>1'),
            'entities_t':   (None, None), 
            })
        )
        
        self.data.consume_any_of( self.m.datasets[::-1] ) # Try consume any dataset; work backwards

        self.data.source_updated.connect( self.generate ) # Auto-regenerate if the source data is modified
        self.generate()

        
    
    def generate(self):
        self.setWorkspaceStatus('active')
    
        self.data.o['output'].import_data( self.data.i['input'] )
        self.data.o['output'] = self.translate( self.data.o['output'], self.m.db)

        metadata = {
            'entities':zip( self.data.o['output'].labels[1], self.data.o['output'].entities[1] ),
        
        }
        metadata['htmlbase'] = os.path.join( utils.scriptdir,'html')

        template = self.m.templateEngine.get_template( os.path.join(self.plugin.path, 'entities.html') )
        self.browser.setHtml(template.render( metadata ),QUrl("~")) 
        self.browser.exposeQtWebView()
        
        self.setWorkspaceStatus('done')
        self.data.refresh_consumers()
        self.clearWorkspaceStatus()



###### TRANSLATION to METACYC IDENTIFIERS
                        
    def translate(self, data, db):
        # Translate loaded data names to metabolite IDs using provided database for lookup
        for n,m in enumerate(data.labels[1]):
            if m.lower() in db.synrev:
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
