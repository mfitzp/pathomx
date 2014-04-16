# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from pathomx.plugins import AnalysisPlugin

from collections import defaultdict

import os, time
from copy import copy

import numpy as np
import scipy as sp

import pathomx.ui as ui
import pathomx.db as db
import pathomx.utils as utils
import pathomx.threads as threads

from pathomx.data import DataSet, DataDefinition
from pathomx.views import MplScatterView, MplSpectraView
from pathomx.qt import *

# Dialog box for Metabohunter search options
class RegressionConfigPanel(ui.ConfigPanel):


    
    def __init__(self, *args, **kwargs):
        super(PCAConfigPanel, self).__init__(*args, **kwargs)        

        row = QVBoxLayout()
        cl = QLabel('Number of components')
        cb = QSpinBox()
        cb.setRange(0,10)
        row.addWidget(cl)
        row.addWidget(cb)
        self.config.add_handler('number_of_components', cb)
        self.layout.addLayout(row)
                    
        self.finalise()
    


class RegressionTool( ui.AnalysisApp ):
    def __init__(self, **kwargs):
        super(RegressionTool, self).__init__(**kwargs)

        self.views.addView(MplScatterView(self),'Regression')

        self.addDataToolBar()
        self.addFigureToolBar()
                
        self.data.add_input('input') # Add input slot
        
        # Setup data consumer options
        self.data.consumer_defs.append( 
            DataDefinition('input', {
#            'labels_n':   (None,['Pathway']), 
            })
        )
        
        self.config.set_defaults({
            'number_of_components': 2,
        })

        #self.addConfigPanel( PCAConfigPanel, 'PCA')
        
        self.finalise()
        
    def generate(self, input=None):
        data = input.data
        
        # Dummy get first two rows
        x = input.data[0,:] 
        y = input.data[1,:] 

        fit = np.polyfit(x,y,1)
        
        dso = DataSet( size=(len(x),2 ) )
        dso.data[:,0] = x
        dso.data[:,1] = y
        
        slope, intercept, r_value, p_value, std_err = sp.stats.linregress(x, y)
        
        return dict( list({
            'dso': dso,
            'fit': fit,
            'label': 'r²=%0.2f, p=%0.2f' % (r_value**2, p_value)
        }.items() ) )
        
    def prerender(self, dso=None, fit=None, label='', **kwargs):
        x_data = np.linspace(np.min(dso.data[:,0]), np.max(dso.data[:,0]), 50)
        lines = [
            (x_data, np.polyval(fit, x_data), label)
        ]
        
        return {
            'Regression':{'dso': dso, 'lines':lines}, 
            }
    
        
                

class RegressionPlugin(AnalysisPlugin):

    def __init__(self, **kwargs):
        super(RegressionPlugin, self).__init__(**kwargs)
        RegressionTool.plugin = self
        self.register_app_launcher( RegressionTool )
        
        
