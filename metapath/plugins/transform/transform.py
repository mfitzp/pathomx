# -*- coding: utf-8 -*-
from plugins import ProcessingPlugin


# Import PyQt5 classes
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWebKit import *
from PyQt5.QtNetwork import *
from PyQt5.QtWidgets import *
from PyQt5.QtWebKitWidgets import *
from PyQt5.QtPrintSupport import *


import utils
import csv
import xml.etree.cElementTree as et
from collections import defaultdict

import numpy as np

import data, ui, db

class TransformView( ui.DataView ):

    def __init__(self, plugin, parent, **kwargs):
        super(TransformView, self).__init__(plugin, parent, **kwargs)
        
        self.addDataToolBar()
        self.addFigureToolBar()

        self.data.addo('output') # Add output slot
        self.table.setModel(self.data.o['output'].as_table)
                    
        # Setup data consumer options
        self.data.consumer_defs.append( 
            data.DataDefinition('input', { # Accept anything!
            })
        )
        
            
        th = self.addToolBar('Transform')
        self.hm_control = QComboBox()
        th.addWidget(self.hm_control)
        self.transform_options = {
            'log2':self._log2,
            'log10':self._log10,
            'Zero baseline':self._zero_baseline,
        }
        
        self.hm_control.addItems( [h for h in self.transform_options.keys()] )
        self._apply_transform = self.transform_options.keys()[0]
        self.hm_control.currentIndexChanged.connect(self.onChangeTransform)
        
        self.data.consume_any_of( self.m.datasets[::-1] ) # Try consume any dataset; work backwards

        self.data.source_updated.connect( self.generate ) # Auto-regenerate if the source data is modified
        self.generate()
    
    
    def onChangeTransform(self):
        self._apply_transform = self.hm_control.currentText()
        self.generate()
               
    # Data file import handlers (#FIXME probably shouldn't be here)
    def generate(self):
        self.setWorkspaceStatus('active')
    
        self.data.o['output'].import_data( self.data.i['input'] )
        self.data.o['output'] = self.transform_options[ self._apply_transform ]( self.data.o['output'] )

        self.data.o['output'].as_table.refresh()
        self.render({})

        self.setWorkspaceStatus('done')
        self.data.refresh_consumers()
        self.clearWorkspaceStatus()                

    # Apply log2 transform to dataset
    def _log2(self, dso):
        dso.data = np.log2( dso.data )
        return dso
        
    # Apply log10 transform to dataset
    def _log10(self, dso):
        dso.data = np.log10( dso.data )
        return dso
        
    def _zero_baseline(self, dso):
        minima = np.min( dso.data )
        dso.data = dso.data + -minima
        return dso
        
        
    def _transpose(self, dso):
        pass
        

class Transform(ProcessingPlugin):

    def __init__(self, **kwargs):
        super(Transform, self).__init__(**kwargs)
        self.register_app_launcher( self.app_launcher )

    def app_launcher(self):
        #self.load_data_file()
        self.instances.append( TransformView( self, self.m ) )