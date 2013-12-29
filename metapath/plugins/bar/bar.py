# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# Import PyQt5 classes
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWebKit import *
from PyQt5.QtNetwork import *
from PyQt5.QtWidgets import *
from PyQt5.QtWebKitWidgets import *
from PyQt5.QtPrintSupport import *

import numpy as np

# Renderer for GPML as SVG
from gpml2svg import gpml2svg


from plugins import VisualisationPlugin

import os
import ui, utils
from data import DataSet, DataDefinition
from views import D3BarView


# Class for data visualisations using GPML formatted pathways
# Supports loading from local file and WikiPathways
class BarView(ui.AnalysisD3View):
    def __init__(self, plugin, parent, auto_consume_data=True, **kwargs):
        super(BarView, self).__init__(plugin, parent, **kwargs)
         
        self.addDataToolBar()
        self.addFigureToolBar()
            
        self.data.add_input('input') # Add input slot
        self.data.add_output('output', is_public=False) # Hidden
        
        self.tabs.add_view('View', D3BarView, 'output')
        # Setup data consumer options
        self.data.consumer_defs.append( 
            DataDefinition('input', {
            'entities_t':   (None,['Compound']), 
            })
        )
        
            
        t = self.addToolBar('Bar')
        self.toolbars['bar'] = t
        
        self.data.source_updated.connect( self.autogenerate ) # Auto-regenerate if the source data is modified
        self.data.consume_any_of( self.m.datasets[::-1] ) # Try consume any dataset; work backwards


    def generate(self):
        dso = self.data.get('input')
        self.data.put('output',dso)


class Bar(VisualisationPlugin):

    def __init__(self, **kwargs):
        super(Bar, self).__init__(**kwargs)
        self.register_app_launcher( self.app_launcher )
    
    # Create a new instance of the plugin viewer object to handle all behaviours
    def app_launcher(self, **kwargs):
        return BarView( self, self.m, **kwargs )
