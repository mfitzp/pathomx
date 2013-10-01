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

import ui, db
from data import DataSet, DataDefinition

class TransformView( ui.DataView ):

    def __init__(self, plugin, parent, **kwargs):
        super(TransformView, self).__init__(plugin, parent, **kwargs)
        
        self.addDataToolBar()
        self.addFigureToolBar()

        self.data.add_interface('output') # Add output slot
        self.table.setModel(self.data.o['output'].as_table)
                    
        # Setup data consumer options
        self.data.consumer_defs.append( 
            DataDefinition('input', { # Accept anything!
            })
        )
        
            
        th = self.addToolBar('Transform')
        self.hm_control = QComboBox()
        th.addWidget(self.hm_control)
        self.transform_options = {
            'log2':self._log2,
            'log10':self._log10,
            'Zero baseline':self._zero_baseline,
            'Mean center':self._mean_center,
            'Auto minima':self._zero_minima,
            'Remove invalid data':self._remove_invalid_data,
        }
        
        self.hm_control.addItems( [h for h in self.transform_options.keys()] )
        self._apply_transform = self.transform_options.keys()[0]
        self.hm_control.currentIndexChanged.connect(self.onChangeTransform)
        
        self.data.consume_any_of( self.m.datasets[::-1] ) # Try consume any dataset; work backwards

        self.data.source_updated.connect( self.generate ) # Auto-regenerate if the source data is modified
        self.generate()
    
    
    def onChangeTransform(self):
        self._apply_transform = self.hm_control.currentText()
        self.set_name( self._apply_transform )
        self.generate()
               
    # Data file import handlers (#FIXME probably shouldn't be here)
    def generate(self):
        self.setWorkspaceStatus('active')
        
        dso = self.data.get('input')
        dso = self.transform_options[ self._apply_transform ]( dso )

        self.data.put('output',dso)
        self.render({})
        
        self.setWorkspaceStatus('done')
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

    def _zero_minima(self,dso):
        minima = np.min( dso.data[ dso.data > 0 ] ) / 2 # Half the smallest value by default
        # Get the dso filtered by class
        dso.data[ dso.data <= 0] = minima
        return dso
        
    def _mean_center(self, dso):
        center = np.mean( dso.data, axis=0) # Assume it
        dso.data = dso.data -center
        return dso
        
    def _remove_invalid_data(self,dso):
        # Remove invalid data (Nan/inf) from the data
        # and adjust rest of the data object to fit
        dso.remove_invalid_data()
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
