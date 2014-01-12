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
from views import MplSpectraView, MplDifferenceView

class IcoshiftApp( ui.DataApp ):
    def __init__(self, auto_consume_data=True, **kwargs):
        super(IcoshiftApp, self).__init__(**kwargs)
        
        self.addDataToolBar()
        self.addFigureToolBar()
        
        self.data.add_input('input') # Add input slot        
        self.data.add_output('output')
        self.table.setModel(self.data.o['output'].as_table)
        self.difference =  ui.QWebViewExtend(self)

        self.views.addView( MplSpectraView(self), 'Spectra' )
        self.views.addView( MplDifferenceView(self), 'Shift' )
        
        
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
    
    def generate(self, input=None):
        return {
            'output': self.icoshift( self.data.get('input') ),
            'input': self.data.get('input')
            }
    
    def prerender(self, output=None, input=None):
        return {'Spectra': {'dso':output}, 'Shift': {'dso_a':input, 'dso_b':output} }


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
        IcoshiftApp.plugin = self
        self.register_app_launcher( IcoshiftApp )
