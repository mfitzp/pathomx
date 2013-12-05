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

import ui, db, utils, threads
from data import DataSet, DataDefinition


class BinningView( ui.DataView ):
    def __init__(self, plugin, parent, auto_consume_data=True, **kwargs):
        super(BinningView, self).__init__(plugin, parent, **kwargs)
        
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

        self.config.set_defaults({
            'bin_size': 0.01,
            'bin_offset': 0,
        })
                        
            
        th = self.addToolBar( self.tr('Binning') )
        self.binsize_spin = QDoubleSpinBox()
        self.binsize_spin.setDecimals(3)
        self.binsize_spin.setRange(0.005,0.5)
        self.binsize_spin.setSuffix('ppm')
        self.binsize_spin.setSingleStep(0.005)
        tl = QLabel( self.tr('Size') )
        th.addWidget(tl)
        th.addWidget(self.binsize_spin)
        self.config.add_handler('bin_size', self.binsize_spin)

        self.binoffset_spin = QDoubleSpinBox()
        self.binoffset_spin.setDecimals(3)
        self.binoffset_spin.setRange(-0.5,0.5)
        self.binoffset_spin.setSuffix('ppm')
        self.binoffset_spin.setSingleStep(0.001)
        tl = QLabel( self.tr('Offset') )
        tl.setIndent(5)
        th.addWidget(tl)
        th.addWidget(self.binoffset_spin)
        self.config.add_handler('bin_offset', self.binoffset_spin)

        self.data.source_updated.connect( self.autogenerate ) # Auto-regenerate if the source data is modified        
        if auto_consume_data:
            self.data.consume_any_of( self.m.datasets[::-1] ) # Try consume any dataset; work backwards
        self.config.updated.connect( self.autogenerate ) # Regenerate if the configuration is changed
    
    def generate(self):
        self.status.emit('active')
        self.worker = threads.Worker(self.binning, dsi=self.data.get('input')) #, config=self.config)
        self.start_worker_thread(self.worker)

    def generated(self, dso):
        if dso:
            self.data.put('output',dso)
            self.status.emit('render')
            self.render({})
            self.status.emit('done')
        else:
            self.status.emit('error')
            
        self.status.emit('clear')
            
        
    
    def render(self, metadata):
        super(BinningView, self).render({})
        dsi = self.data.get('input')
        dso = self.data.o['output']

        if float in [type(t) for t in dso.scales[1]]:
            print "Difference plot"
            metadata['htmlbase'] = os.path.join( utils.scriptdir,'html')
            
            # Get common scales
            datai = np.mean( dsi.data, 0) # Mean flatten
            datao = np.mean( dso.data, 0) # Mean flatten
            
            # Interpolate the data for shorter set
            if len(datao) < len(datai):
                datao = np.interp( dsi.scales[1], dso.scales[1], datao)

            metadata['figure'] = {
                'data':zip( dsi.scales[1], datai.T, datao.T ), # (ppm, [dataa,datab])
            }


            template = self.m.templateEngine.get_template('d3/difference.svg')
            self.difference.setSVG(template.render( metadata ))
    
    def binning(self, dsi):
        ###### BINNING USING CONFI
        # Generate bin values for range start_scale to end_scale
        # Calculate the number of bins at binsize across range
        dso = DataSet()
        dso.import_data( dsi )

        r = dsi.scales_r[1]
        self._bin_size, self._bin_offset = self.config.get('bin_size'), self.config.get('bin_offset')

        bins = np.arange(r[0]+self._bin_offset,r[1]+self._bin_offset,self._bin_size)
        number_of_bins = len(bins)-1
        
        # Can't increase the size of data, if bins > current size return the original
        if number_of_bins >= len( dso.scales[1] ):
            return {'dso':dso}

        # Resize (lossy) to the new shape
        old_shape, new_shape = list(dsi.data.shape), list(dso.data.shape)
        new_shape[1] = number_of_bins
        dso.crop(new_shape) # Lossy crop, but we'll be within the boundary below
        

        for n,d in enumerate( dsi.data ):
            binned_data = np.histogram(dsi.scales[1], bins=bins, weights=d)
            binned_num = np.histogram(dsi.scales[1], bins=bins) # Number of data points that ended up contributing to each bin
            dso.data[n,:] = binned_data[0] / binned_num[0] # Mean

        dso.scales[1] = [float(x) for x in binned_data[1][:-1]]
        dso.labels[1] = [str(x) for x in binned_data[1][:-1]]

        # Remove any NaNs that have crept in (due to the histogram)
        dso.remove_invalid_data()

        return {'dso':dso}
    
 
 
class Binning(ProcessingPlugin):

    def __init__(self, **kwargs):
        super(Binning, self).__init__(**kwargs)
        self.register_app_launcher( self.app_launcher )

    def app_launcher(self, **kwargs):
        return BinningView( self, self.m, **kwargs )
