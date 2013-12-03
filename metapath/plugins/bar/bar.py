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



# Class for data visualisations using GPML formatted pathways
# Supports loading from local file and WikiPathways
class BarView(ui.AnalysisD3View):
    def __init__(self, plugin, parent, auto_consume_data=True, **kwargs):
        super(BarView, self).__init__(plugin, parent, **kwargs)
         
        self.addDataToolBar()
        self.addFigureToolBar()
            
        self.data.add_input('input') # Add input slot
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
        self.setWorkspaceStatus('active')

        
        dso = self.data.get('input')
        
        fd = np.mean( dso.data, axis=0 )

        fdm = zip( dso.labels[1], fd )
        sms = sorted(fdm,key=lambda x: abs(x[1]), reverse=True )
        metabolites = [m for m,s in sms]

        # Get mean version of dataset (or alternative; +/- error)
        # Requires compressing dataset >1 for each alternative information set

        dso_mean = dso.as_summary( fn=np.mean, dim=0, match_attribs=['classes']) # Get mean dataset/ Classes only
        dso_std = dso.as_summary( fn=np.std, dim=0, match_attribs=['classes']) # Get std_dev/ Classes only
        
        classes = dso_mean.classes[0]
        groups = metabolites[:10]

        data = []
        for g in groups:
            
            data.append(
                ( g, 
                    {c: dso_mean.data[n, dso_mean.labels[1].index(g)] for n,c in enumerate(classes)},
                    {c: dso_std.data[n, dso_std.labels[1].index(g)] for n,c in enumerate(classes)} #2sd?
                     )
            )
    
        self.render( {
            'htmlbase': os.path.join( utils.scriptdir,'html'),
            'figure':  {
                            'type':'bar',
                            'data': data,
                        },                        
        }, template_name='bar')

        self.setWorkspaceStatus('done')
        self.clearWorkspaceStatus()

        


class Bar(VisualisationPlugin):

    def __init__(self, **kwargs):
        super(Bar, self).__init__(**kwargs)
        self.register_app_launcher( self.app_launcher )
    
    # Create a new instance of the plugin viewer object to handle all behaviours
    def app_launcher(self, **kwargs):
        return BarView( self, self.m, **kwargs )
