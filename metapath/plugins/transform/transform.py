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

import ui, db, threads
from data import DataSet, DataDefinition

class TransformView( ui.DataView ):

    def __init__(self, plugin, parent, auto_consume_data=True,  **kwargs):
        super(TransformView, self).__init__(plugin, parent, **kwargs)
        
        self.addDataToolBar()
        self.addFigureToolBar()

        self.data.add_input('input') # Add input slot
        self.data.add_output('output') # Add output slot
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
            'Global minima':self._global_minima,
            'Local minima':self._local_minima,
            'Remove invalid data':self._remove_invalid_data,
        }

        self.config.set_defaults({
            'apply_transform': self.transform_options.keys()[0],
        })
                        
        self.hm_control.addItems( [h for h in self.transform_options.keys()] )
        self.hm_control.currentIndexChanged.connect(self.onChangeTransform) # Updates name only

        self.config.add_handler('apply_transform', self.hm_control)

        
        self.data.source_updated.connect( self.autogenerate ) # Auto-regenerate if the source data is modified
        if auto_consume_data:
            self.data.consume_any_of( self.m.datasets[::-1] ) # Try consume any dataset; work backwards
        self.config.updated.connect( self.autogenerate ) # Regenerate if the configuration is changed

    
    def onChangeTransform(self):
        self.set_name( self.hm_control.currentText() )
        #self.config.set('apply_transform', self.hm_control.currentText())
               
    # Data file import handlers (#FIXME probably shouldn't be here)
    def generate(self):
        dso = self.data.get('input') # Get the dataset
        self.worker = threads.Worker(self.transform_options[ self.config.get('apply_transform') ], dso=dso)
        self.start_worker_thread(self.worker)

    def generated(self, dso):
        self.data.put('output',dso)
        self.render({})
               

    # Apply log2 transform to dataset
    def _log2(self, dso):
        dso.data = np.log2( dso.data )
        return {'dso':dso}
        
    # Apply log10 transform to dataset
    def _log10(self, dso):
        dso.data = np.log10( dso.data )
        return {'dso':dso}
        
    def _zero_baseline(self, dso):
        minima = np.min( dso.data )
        dso.data = dso.data + -minima
        return {'dso':dso}

    def _global_minima(self,dso):
        minima = np.min( dso.data[ dso.data > 0 ] ) / 2 # Half the smallest value by default
        # Get the dso filtered by class
        dso.data[ dso.data <= 0] = minima
        return {'dso':dso}

    # Minima on column by column basis (should have optional axis here)
    def _local_minima(self,dso):
        #dso.data[dso.data==0] = np.nan
        dmin = np.ma.masked_less_equal(dso.data,0).min(0)/2
        inds = np.where( np.logical_and( dso.data==0, np.logical_not( np.ma.getmask(dmin) ) ) )
        dso.data[inds]=np.take(dmin,inds[1])
        return {'dso':dso}
        
    def _mean_center(self, dso):
        center = np.mean( dso.data, axis=0) # Assume it
        dso.data = dso.data -center
        return {'dso':dso}
        
    def _remove_invalid_data(self,dso):
        # Remove invalid data (Nan/inf) from the data
        # and adjust rest of the data object to fit
        dso.remove_invalid_data()
        return {'dso':dso}
                
        
    def _transpose(self, dso):
        pass
        

class Transform(ProcessingPlugin):

    def __init__(self, **kwargs):
        super(Transform, self).__init__(**kwargs)
        self.register_app_launcher( self.app_launcher )


    def app_launcher(self, **kwargs):
        return TransformView( self, self.m, **kwargs )
