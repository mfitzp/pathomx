# -*- coding: utf-8 -*-

import os, copy


import numpy as np
import nmrglue as ng

import pathomx.ui as ui
import pathomx.db as db
import pathomx.utils as utils
import pathomx.threads as threads

from pathomx.data import DataSet, DataDefinition
from pathomx.views import MplSpectraView
from pathomx.plugins import ProcessingPlugin
from pathomx.qt import *


# Dialog box for Metabohunter search options
class PeakPickConfigPanel(ui.ConfigPanel):
    
    def __init__(self, *args, **kwargs):
        super(PeakPickConfigPanel, self).__init__(*args, **kwargs)        


        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setDecimals(5)
        self.threshold_spin.setRange(0.0001,1)
        self.threshold_spin.setSuffix('rel')
        self.threshold_spin.setSingleStep(0.0001)
        tl = QLabel('Threshold')
        self.layout.addWidget(tl)
        self.layout.addWidget(self.threshold_spin)
        self.config.add_handler('peak_threshold', self.threshold_spin)

        self.separation_spin = QDoubleSpinBox()
        self.separation_spin.setDecimals(1)
        self.separation_spin.setRange(0,5)
        self.separation_spin.setSingleStep(0.5)
        tl = QLabel('Peak separation')
        self.layout.addWidget(tl)
        self.layout.addWidget(self.separation_spin)
        self.config.add_handler('peak_separation', self.separation_spin)

        self.algorithms = {
            'Connected':'connected',
            'Threshold':'thres',
            'Threshold (fast)':'thres-fast',
            'Downward':'downward',
        }

        self.algorithm_cb = QComboBox()
        self.algorithm_cb.addItems( [k for k,v in list(self.algorithms.items()) ] )
        tl = QLabel('Algorithm')
        self.layout.addWidget(tl)
        self.layout.addWidget(self.algorithm_cb)  
        self.config.add_handler('algorithm', self.algorithm_cb)

        self.finalise()
        

class NMRPeakPickingApp( ui.DataApp ):

    def __init__(self, **kwargs):
        super(NMRPeakPickingApp, self).__init__(**kwargs)
        
        self.addDataToolBar()
        self.addFigureToolBar()
        
        self.data.add_input('input') # Add input slot        
        self.data.add_output('output')
        self.table.setModel(self.data.o['output'].as_table)
        
        self.views.addView( MplSpectraView(self), 'View')
        
        # Setup data consumer options
        self.data.consumer_defs.append( 
            DataDefinition('input', {
            'labels_n':     ('>1', None),
            'entities_t':   (None, None), 
            'scales_t': (None, ['float']),
            })
        )
        
        
        self.config.set_defaults({
            'peak_threshold': 0.05,
            'peak_separation': 0.5,
            'peak_algorithm': 'Threshold',
        })

        self.addConfigPanel( PeakPickConfigPanel, 'Settings')


        self.finalise()

    def generate(self, input=None): #, config, algorithms):
        # Generate bin values for range start_scale to end_scale
        # Calculate the number of bins at binsize across range
        dso = DataSet( size=input.shape )
        dso.import_data(input)
        
        #ng.analysis.peakpick.pick(data, thres, msep=None, direction='both', algorithm='thres', est_params=True, lineshapes=None)
        
        threshold =  self.config.get('peak_threshold')
        algorithm = self.algorithms[ self.config.get('algorithm')]
        msep = ( self.config.get('peak_separation'),)
        
        # Take input dataset and flatten in first dimension (average spectra)
        data_avg = np.mean( input.data, axis=0)

        # pick peaks and return locations; 
        #nmrglue.analysis.peakpick.pick(data, pthres, nthres=None, msep=None, algorithm='connected', est_params=True, lineshapes=None, edge=None, diag=False, c_struc=None, c_ndil=0, cluster=True, table=True, axis_names=['A', 'Z', 'Y', 'X'])[source]¶
        locations, scales, amps = ng.analysis.peakpick.pick(data_avg, threshold, msep=msep, algorithm=algorithm, est_params = True, cluster=False, table=False)

        #n_cluster = max( cluster_ids )
        n_locations = len( locations )
        
        new_shape = list( input.shape )
        new_shape[1] = n_locations # correct number; tho will be zero indexed
        
        # Convert to numpy arrays so we can do clever things
        scales = [dso.scales[1][l[0]] for l in locations ]

        # Adjust the scales (so aren't lost in crop)
        dso.labels[1] = [ str(l) for l in scales]
        dso.scales[1] = scales
        
        dso.crop( new_shape )

        # Iterate over the clusters (1 to n)
        for n, l in enumerate(locations):
            #l = locations[ cluster_ids == n ]
            #peak_data = np.amax( peak_data, axis=1 ) # max across cols
            dso.data[:,n-1] = input.data[:, l[0]]
            
        # FIXME:
        # Extract the location numbers (positions in original spectra)
        # Get max value in each row for those regions
        # Append that to n position in new dataset
        
        # -- optionally use the line widths and take max within each of these for each spectra (peak shiftiness)
        # Filter the original data with those locations and output\

        return {'output':dso}

 
class NMRPeakPicking(ProcessingPlugin):

    def __init__(self, **kwargs):
        super(NMRPeakPicking, self).__init__(**kwargs)
        NMRPeakPickingApp.plugin = self
        self.register_app_launcher( NMRPeakPickingApp )
