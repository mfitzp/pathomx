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
    def __init__(self, plugin, parent, **kwargs):
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

        #State,Under 5 Years,5 to 13 Years,14 to 17 Years,18 to 24 Years,25 to 44 Years,45 to 64 Years,65 Years and Over
        #CA,2704659,4499890,2159981,3853788,10604510,8819342,4114496
        #TX,2027307,3277946,1420518,2454721,7017731,5656528,2472223
        #NY,1208495,2141490,1058031,1999120,5355235,5120254,2607672
        #FL,1140516,1938695,925060,1607297,4782119,4746856,3187797
        #IL,894368,1558919,725973,1311479,3596343,3239173,1575308
        #PA,737462,1345341,679201,1203944,3157759,3414001,1910571
        
        dso = self.data.get('input')
        
        fd = np.mean( dso.data, axis=0 )
        fdm = zip( dso.labels[1], fd )
        sms = sorted(fdm,key=lambda x: abs(x[1]), reverse=True )
        metabolites = [m for m,s in sms]

        
        classes = dso.classes[0]
        groups = metabolites[:10]

        data = []
        for g in groups:
            
            data.append(
                ( g, {c: dso.data[n, dso.labels[1].index(g)] for n,c in enumerate(classes)} )
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
    def app_launcher(self):
        self.instances.append( BarView( self, self.m ) )
