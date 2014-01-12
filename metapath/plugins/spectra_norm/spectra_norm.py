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

import ui, db, utils, threads
from data import DataSet, DataDefinition
from views import MplSpectraView, MplDifferenceView

class SpectraNormApp( ui.DataApp ):
    def __init__(self, auto_consume_data=True, **kwargs):
        super(SpectraNormApp, self).__init__(**kwargs)
        
        self.addDataToolBar()
        self.addFigureToolBar()
        
        self.data.add_input('input') # Add input slot        
        self.data.add_output('output')
        self.table.setModel(self.data.o['output'].as_table)

        self.views.addView( MplSpectraView(self), 'View')
        self.views.addView( MplDifferenceView(self), 'Difference')
        
        # Setup data consumer options
        self.data.consumer_defs.append( 
            DataDefinition('input', {
            'labels_n':     ('>1', None),
            'entities_t':   (None, None), 
            'scales_t': (None, ['float']),
            })
        )
        
        th = self.addToolBar('Spectra normalisation')

        self.algorithms = {
            'PQN':self.pqn,
            'TSA':self.tsa,
        }

        self.config.set_defaults({
            'algorithm':'PQN',
        })
        
        self.algorithm_cb = QComboBox()
        self.algorithm_cb.addItems( [k for k,v in self.algorithms.items() ] )
        self.config.add_handler('algorithm', self.algorithm_cb)

        tl = QLabel('Algorithm')
        tl.setIndent(5)
        th.addWidget(tl)
        th.addWidget(self.algorithm_cb)        

        self.data.source_updated.connect( self.autogenerate ) # Auto-regenerate if the source data is modified        
        if auto_consume_data:
            self.data.consume_any_of( self.m.datasets[::-1] ) # Try consume any dataset; work backwards
        self.config.updated.connect( self.autogenerate ) # Auto-regenerate if the configuration is changed


    def generate(self, input=None):
        return {'output': self.normalise(dsi=input),
                'input': input }

    def prerender(self, input=None, output=None):
        return {'View':{'dso':output},
                'Difference':{'dso_a':input, 'dso_b':output},
                }

    def tsa(self,data):
        # Abs the data (so account for negative peaks also)
        data_a = np.abs(data)
        # Sum each spectra (TSA)
        data_as = np.sum(data_a, axis=1)
        # Identify median
        median_s = np.median(data_as)
        # Scale others to match (*(median/row))
        scaling = median_s / data_as
        # Scale the spectra        
        return data * scaling.reshape(-1,1)

    def pqn(self,data): # 10.1021/ac051632c
        # Perform TSA normalization
        data = self.tsa(data)
        # Calculate median spectrum (median of each variable)
        median_s = np.median(data, axis=0)
        # For each variable of each spectrum, calculate ratio between median spectrum variable and that of the considered spectrum
        spectra_r = median_s / np.abs(data)
        # Take the median of these scaling factors and apply to the entire considered spectrum
        return data * spectra_r
        
    # Normalise using scaling method
    def normalise(self, dsi):
        # Generate bin values for range start_scale to end_scale
        # Calculate the number of bins at binsize across range
        dso = DataSet( size=dsi.shape )
        dso.import_data(dsi)
        
        dso.data = self.algorithms[ self.config.get('algorithm') ](dso.data)

        # -- optionally use the line widths and take max within each of these for each spectra (peak shiftiness)
        # Filter the original data with those locations and output\
        
        return dso

 
class SpectraNorm(ProcessingPlugin):

    def __init__(self, **kwargs):
        super(SpectraNorm, self).__init__(**kwargs)
        SpectraNormApp.plugin = self
        self.register_app_launcher( SpectraNormApp )
