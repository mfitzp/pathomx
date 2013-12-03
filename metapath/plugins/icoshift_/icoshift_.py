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
from icoshift import icoshift

import ui, db, utils
from data import DataSet, DataDefinition


class IcoshiftView( ui.DataView ):
    def __init__(self, plugin, parent, auto_consume_data=True, **kwargs):
        super(IcoshiftView, self).__init__(plugin, parent, **kwargs)
        
        self.addDataToolBar()
        self.addFigureToolBar()
        
        self.data.add_input('input') # Add input slot        
        self.data.add_output('output')
        self.table.setModel(self.data.o['output'].as_table)
        self.difference =  ui.QWebViewExtend(self)

        self.tabs.addTab(self.difference, 'Shifted')
        
        
        # Setup data consumer options
        self.data.consumer_defs.append( 
            DataDefinition('input', {
            'labels_n':     ('>1', None),
            'entities_t':   (None, None), 
            'scales_t': (None, ['float']),
            })
        )

        self.data.source_updated.connect( self.autogenerate ) # Auto-regenerate if the source data is modified        
        self.data.consume_any_of( self.m.datasets[::-1] ) # Try consume any dataset; work backwards
    
    def generate(self):
        dso = self.icoshift( self.data.get('input') ) #, self._bin_size, self._bin_offset)
        if dso:
            self.data.put('output',dso)
            self.render({})
        else:
            self.setWorkspaceStatus('error')

        

    def render(self, metadata):
        super(IcoshiftView, self).render({})
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
        
            f = open('/Users/mxf793/Desktop/test8.svg','w')
            f.write( template.render( metadata ) )
            f.close()        

    def onChangeBinParameters(self):
        self._bin_size = float( self.binsize_spin.value() )
        self._bin_offset = float( self.binoffset_spin.value() )
        self.generate()



###### TRANSLATION to METACYC IDENTIFIERS

    

    def icoshift(self, dsi):               
        # Generate bin values for range start_scale to end_scale
        # Calculate the number of bins at binsize across range
        spectra = dsi.data
        print spectra
        xCS,ints,ind,target = icoshift.icoshift('average', spectra)
        dsi.data = xCS
        return dsi
        

 
class Icoshift(ProcessingPlugin):

    def __init__(self, **kwargs):
        super(Icoshift, self).__init__(**kwargs)
        self.register_app_launcher( self.app_launcher )

    def app_launcher(self, **kwargs):
        return IcoshiftView( self, self.m, **kwargs )
