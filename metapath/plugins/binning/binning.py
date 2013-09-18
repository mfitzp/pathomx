# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# Import PyQt5 classes
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWebKit import *
from PyQt5.QtNetwork import *

import os, copy

from plugins import ProcessingPlugin

import numpy as np

import data, ui, db, utils

class BinningView( ui.DataView ):
    def __init__(self, plugin, parent, **kwargs):
        super(BinningView, self).__init__(plugin, parent, **kwargs)
        
        self.addDataToolBar()
        self.data.addo('output')
        
        self.set_name('Binning')
        self.workspace_item = self.m.addWorkspaceItem(self.w, self.plugin.default_workspace_category, self.name, is_selected=True, icon=self.plugin.workspace_icon ) #, icon = None)
        
        # Setup data consumer options
        self.data.consumer_defs.append( 
            data.DataDefinition('input', {
            'labels_n':     ('>1', None),
            'entities_t':   (None, None), 
            'scale_t': (None, 'float'),
            })
        )
        
        self.data.consume_any_of( self.m.datasets[::-1] ) # Try consume any dataset; work backwards

        self.data.source_updated.connect( self.generate ) # Auto-regenerate if the source data is modified
        self.generate()

        
    
    def generate(self):
        self.data.o['output'].import_data( self.data.i['input'] )
        self.data.o['output'] = self.binning( self.data.o['output'], binsize)

        self.data.refresh_consumers()

        metadata = {
            'entities':zip( self.data.o['output'].labels[0], self.data.o['output'].entities[0] ),
        
        }
        metadata['htmlbase'] = os.path.join( utils.scriptdir,'html')

        template = self.m.templateEngine.get_template( os.path.join(self.plugin.path, 'entities.html') )
        self.browser.setHtml(template.render( metadata ),"~") 
        self.browser.exposeQtWebView()



###### TRANSLATION to METACYC IDENTIFIERS
         
    def binning(self, data, binsize):               
        # Generate bin values for range start_scale to end_scale
        
        # Apply binning using numpy histogram function (2d)
        data = (numpy.histogram(data, bins, weights=data)[0] /
                     numpy.histogram(data, bins)[0])
        return data
        

 
class Binning(ProcessingPlugin):

    def __init__(self, **kwargs):
        super(Binning, self).__init__(**kwargs)
        self.register_app_launcher( self.app_launcher )

    def app_launcher(self):
        #self.load_data_file()
        self.instances.append( BinningView( self, self.m ) ) 
