# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# Import PyQt5 classes
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWebKit import *
from PyQt5.QtNetwork import *
from PyQt5.QtWidgets import *
from PyQt5.QtPrintSupport import *

import os, copy

from plugins import ProcessingPlugin

import numpy as np
import nmrglue as ng

import ui, db, utils
from data import DataSet, DataDefinition


class NMRPeakPickingView( ui.DataView ):
    def __init__(self, plugin, parent, **kwargs):
        super(NMRPeakPickingView, self).__init__(plugin, parent, **kwargs)
        
        self.addDataToolBar()
        self.addFigureToolBar()
        
        self.data.add_input('input') # Add input slot        
        self.data.add_output('output')
        self.table.setModel(self.data.o['output'].as_table)
        
        
        # Setup data consumer options
        self.data.consumer_defs.append( 
            DataDefinition('input', {
            'labels_n':     ('>1', None),
            'entities_t':   (None, None), 
            'scales_t': (None, ['float']),
            })
        )
        
        self._peak_threshold = 0.05
            
        th = self.addToolBar('Peak Picking')
        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setDecimals(3)
        self.threshold_spin.setRange(0.005,1)
        self.threshold_spin.setSuffix('rel')
        self.threshold_spin.setSingleStep(0.005)
        self.threshold_spin.setValue(self._peak_threshold)
        self.threshold_spin.valueChanged.connect(self.onChangePeakParameters)
        tl = QLabel('Threshold')
        th.addWidget(tl)
        th.addWidget(self.threshold_spin)

        self._peak_separation = 0.5
            
        self.separation_spin = QDoubleSpinBox()
        self.separation_spin.setDecimals(1)
        self.separation_spin.setRange(0,5)
        self.separation_spin.setSingleStep(0.5)
        self.separation_spin.setValue(self._peak_separation)
        self.separation_spin.valueChanged.connect(self.onChangePeakParameters)
        tl = QLabel('Separation')
        tl.setIndent(5)
        th.addWidget(tl)
        th.addWidget(self.separation_spin)


        self._peak_algorithm = 'Threshold'

        self.algorithms = {
#            'Connected':'connected',
            'Threshold':'thres',
            'Threshold (fast)':'thres-fast',
#            'Downward':'downward',
        }

        self.algorithm_cb = QComboBox()
        self.algorithm_cb.addItems( [k for k,v in self.algorithms.items() ] )
        self.algorithm_cb.currentIndexChanged.connect(self.onChangePeakParameters)
        tl = QLabel('Algorithm')
        tl.setIndent(5)
        th.addWidget(tl)
        th.addWidget(self.algorithm_cb)        

        #self.data.source_updated.connect( self.generate ) # Auto-regenerate if the source data is modified        
        self.data.consume_any_of( self.m.datasets[::-1] ) # Try consume any dataset; work backwards

        self.generate()
    
    def generate(self):
        dso = self.peakpick( self.data.get('input') ) #, self._bin_size, self._bin_offset)
        self.data.put('output',dso)
        self.render({})

    def onChangePeakParameters(self):
        self._peak_threshold = float( self.threshold_spin.value() )
        self._peak_separation = float( self.separation_spin.value() )
        self._peak_algorithm = self.algorithm_cb.currentText()
        self.generate()



    # Peak picking using NMR lab method
    def peakpick(self, dsi):
        # Generate bin values for range start_scale to end_scale
        # Calculate the number of bins at binsize across range
        dso = DataSet( size=dsi.shape )
        dso.import_data(dsi)
        
        #ng.analysis.peakpick.pick(data, thres, msep=None, direction='both', algorithm='thres', est_params=True, lineshapes=None)
        
        
        threshold = self._peak_threshold
        algorithm = self.algorithms[self._peak_algorithm]
        msep = (self._peak_separation,)
        
        # Take input dataset and flatten in first dimension (average spectra)
        data_avg = np.mean( dsi.data, axis=0)
       
        # pick peaks and return locations; 
        locations, cluster_ids, scales, amps = ng.analysis.peakpick.pick(data_avg, threshold, msep=msep, cluster=True, algorithm=algorithm, est_params = True, table=False)
        locations, scales, amps = ng.analysis.peakpick.pick(data_avg, threshold, msep=msep, cluster=False, algorithm=algorithm, est_params = True, table=False)

        n_cluster = max( cluster_ids )
        n_locations = len( locations )
        
        new_shape = list( dsi.shape )
        new_shape[1] = n_locations # correct number; tho will be zero indexed
        
        # Convert to numpy arrays so we can do clever things
        locations = np.array( [l[0] for l in locations ]) #wtf

        # Adjust the scales (so aren't lost in crop)
        dso.scales[1] = [ float(x) for x in np.array(dso.scales[1])[ locations ] ] # FIXME: The scale check on the plot is duff; doesn't recognise float64,etc.
        dso.labels[1] = [ str(x) for x in dso.scales[1] ] # FIXME: Label plotting on the scale plot
 
        print len(dso.scales[1])
        print new_shape
 
        dso.crop( new_shape )
    
        #cluster_ids = np.array( cluster_ids )

        # Iterate over the clusters (1 to n)
        for n, l in enumerate(locations):
            #l = locations[ cluster_ids == n ]
            peak_data = dsi.data[:, l]
            #peak_data = np.amax( peak_data, axis=1 ) # max across cols
            dso.data[:,n-1] = peak_data
            
            #print dsi.data[ :, l ] 
            
        # Extract the location numbers (positions in original spectra)
        # Get max value in each row for those regions
        # Append that to n position in new dataset
        

        # -- optionally use the line widths and take max within each of these for each spectra (peak shiftiness)
        # Filter the original data with those locations and output\
        
        return dso

 
class NMRPeakPicking(ProcessingPlugin):

    def __init__(self, **kwargs):
        super(NMRPeakPicking, self).__init__(**kwargs)
        self.register_app_launcher( self.app_launcher )

    def app_launcher(self):
        #self.load_data_file()
        self.instances.append( NMRPeakPickingView( self, self.m ) ) 
