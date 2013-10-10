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

from plugins import AnalysisPlugin

from collections import defaultdict

import os
from copy import copy

import numpy as np
from sklearn.decomposition import PCA, KernelPCA

import ui, db, utils
from data import DataSet, DataDefinition


class PCAView( ui.AnalysisView ):
    def __init__(self, plugin, parent, **kwargs):
        super(PCAView, self).__init__(plugin, parent, **kwargs)

        # Define automatic mapping (settings will determine the route; allow manual tweaks later)
        
        self.addDataToolBar()
        self.addFigureToolBar()
        
        self.weights = ui.QWebViewExtend(self, onNavEvent=self.m.onBrowserNav)
        self.tabs.addTab(self.weights,'Weights')
        
        self.data.add_interface('scores')
        self.data.add_interface('weights')
        
        #self.table = QTableView()
        #self.table.setModel(self.data.o['output'].as_table)
        #self.tabs.addTab(self.table,'Table')
        
        # Setup data consumer options
        self.data.consumer_defs.append( 
            DataDefinition('input', {})
        )

        self.data.source_updated.connect( self.onDataChanged ) # Auto-regenerate if the source data is modified
        self.data.consume_any_of( self.m.datasets[::-1] ) # Try consume any dataset; work backwards


    def onDataChanged(self):
        self.generate()
        
    # Do the PCA analysis
    def generate(self):    
        
        dso = self.data.get('input') # Get the dataset
        
        data = dso.data
        
        pca = PCA(n_components=2)
        pca.fit(data.T) # Transpose it, as vars need to along the top
        
        weights = pca.transform(data.T) # Get weights?
        
        print pca.explained_variance_ratio_
        print pca.explained_variance_
        print pca.components_.shape
        
        # Build a list object of class, x, y
        
        
        figure_data = zip( dso.classes[0], pca.components_[0], pca.components_[1])
        metadata = {
            'figure':{
                'data':figure_data,
                'regions': [],
                'x_axis_label': 'Principal Component 1 (%0.2f%%)' % (pca.explained_variance_ratio_[0] * 100.),
                'y_axis_label': 'Principal Component 2 (%0.2f%%)' % (pca.explained_variance_ratio_[1] * 100.),
                },
        }
        
        self.render(metadata, template='d3/pca.svg')

        if 'NoneType' in dso.scales_t[1]:
            dso.scales[1] = range(0, len( dso.scales[1] ) )
        
        # Label up the top 10 (the values are retained; just for clarity)
        wmx = np.amax( np.absolute( weights), axis=1 )

        dso_z = zip( dso.scales[1], dso.entities[1], dso.labels[1] )
        dso_z = sorted( zip( dso_z, wmx ), key=lambda x: x[1])[-20:] # Top 20
        
        dso_z = [x for x, wmx in dso_z ]    
        
        metadata = {
            'figure':{
                'data': zip( dso.scales[1], weights ),  
                'labels': self.build_markers( dso_z, 2, self._build_label_cmp ), #zip( xarange, xarange, dso.labels[1]), # Looks mental, but were' applying ranges
                'entities': self.build_markers( dso_z, 1, self._build_entity_cmp ),      
            }
        }
        print weights.shape
        
        
        self.render(metadata, template='d3/line.svg', target=self.weights)
        
        # Do the weights plot
        
                

class PCAPlugin(AnalysisPlugin):

    def __init__(self, **kwargs):
        super(PCAPlugin, self).__init__(**kwargs)
        self.register_app_launcher( self.app_launcher )

    def app_launcher(self):
        #self.load_data_file()
        self.instances.append( PCAView( self, self.m ) ) 
        
        