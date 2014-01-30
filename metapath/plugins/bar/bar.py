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
from views import D3BarView, MplCategoryBarView


# Class for data visualisations using GPML formatted pathways
# Supports loading from local file and WikiPathways
class BarApp(ui.AnalysisApp):
    def __init__(self, **kwargs):
        super(BarApp, self).__init__(**kwargs)
         
        self.addDataToolBar()
        self.addFigureToolBar()
            
        self.data.add_input('input') # Add input slot
        self.data.add_output('output', is_public=False) # Hidden
        
        self.views.addView(MplCategoryBarView(self), 'View')
        
        # Setup data consumer options
        self.data.consumer_defs.append( 
            DataDefinition('input', {
            'entities_t':   (None,['Compound']), 
            })
        )
        
            
        t = self.addToolBar('Bar')
        self.toolbars['bar'] = t
        
        self.finalise()
        
    def generate(self, input=None):
        return {'dso': self.data.get('input') }
        
    def prerender(self, dso=None):
        dso_mean = dso.as_summary( fn=np.mean, dim=0, match_attribs=['classes']) # Get mean dataset/ Classes only
        dso_std = dso.as_summary( fn=np.std, dim=0, match_attribs=['classes']) # Get std_dev/ Classes only

        dso = dso_mean
        dso.statistics['error']['stddev'] = dso_std.data
        
        return {'View':{'dso':dso} }
        
class Bar(VisualisationPlugin):

    def __init__(self, **kwargs):
        super(Bar, self).__init__(**kwargs)
        BarApp.plugin = self
        self.register_app_launcher( BarApp )
