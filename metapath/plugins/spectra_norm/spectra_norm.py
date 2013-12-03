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


class SpectraNormView( ui.DataView ):
    def __init__(self, plugin, parent, auto_consume_data=True, **kwargs):
        super(SpectraNormView, self).__init__(plugin, parent, **kwargs)
        
        self.addDataToolBar()
        self.addFigureToolBar()
        
        self.data.add_input('input') # Add input slot        
        self.data.add_output('output')
        self.table.setModel(self.data.o['output'].as_table)

        self.difference =  ui.QWebViewExtend(self)
        self.tabs.addTab(self.difference, 'Difference')
        
        # Setup data consumer options
        self.data.consumer_defs.append( 
            DataDefinition('input', {
            'labels_n':     ('>1', None),
            'entities_t':   (None, None), 
            'scales_t': (None, ['float']),
            })
        )
        
        self._peak_threshold = 0.05
            
        th = self.addToolBar('Spectra normalisation')
        self._norm_algorithm = 'PQN'

        self.algorithms = {
            'PQN':self.pqn,
            'TSA':self.tsa,
        }

        self.algorithm_cb = QComboBox()
        self.algorithm_cb.addItems( [k for k,v in self.algorithms.items() ] )
        self.algorithm_cb.currentIndexChanged.connect(self.onChangePeakParameters)
        tl = QLabel('Algorithm')
        tl.setIndent(5)
        th.addWidget(tl)
        th.addWidget(self.algorithm_cb)        

        self.data.source_updated.connect( self.autogenerate ) # Auto-regenerate if the source data is modified        
        self.data.consume_any_of( self.m.datasets[::-1] ) # Try consume any dataset; work backwards


    def render(self, metadata):
        super(SpectraNormView, self).render({})
        dsi = self.data.get('input')
        dso = self.data.o['output']

        if float in [type(t) for t in dso.scales[1]]:
            metadata['htmlbase'] = os.path.join( utils.scriptdir,'html')
            
            # Get common scales
            datai = np.mean( dsi.data, 0) # Mean flatten
            datao = np.mean( dso.data, 0) # Mean flatten

            metadata['figure'] = {
                'data':zip( dsi.scales[1], datai.T, datao.T ), # (ppm, [dataa,datab])
            }

            template = self.m.templateEngine.get_template('d3/difference.svg')
            self.difference.setSVG(template.render( metadata ))

    
    def generate(self):
        dso = self.normalise( self.data.get('input') ) #, self._bin_size, self._bin_offset)
        self.data.put('output',dso)
        self.render({})

    def onChangePeakParameters(self):
        self._norm_algorithm = self.algorithm_cb.currentText()
        self.generate()

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
        
        dso.data = self.algorithms[ self._norm_algorithm ](dso.data)

        # -- optionally use the line widths and take max within each of these for each spectra (peak shiftiness)
        # Filter the original data with those locations and output\
        
        return dso

 
class SpectraNorm(ProcessingPlugin):

    def __init__(self, **kwargs):
        super(SpectraNorm, self).__init__(**kwargs)
        self.register_app_launcher( self.app_launcher )

    def app_launcher(self, **kwargs):
        return SpectraNormView( self, self.m, **kwargs )
