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
from sklearn.cross_decomposition import PLSRegression

import ui, db, utils
from data import DataSet, DataDefinition


class PLSDAView( ui.AnalysisView ):
    def __init__(self, plugin, parent, **kwargs):
        super(PLSDAView, self).__init__(plugin, parent, **kwargs)

        # Define automatic mapping (settings will determine the route; allow manual tweaks later)
        
        self.addDataToolBar()
        self.addExperimentToolBar()
        self.addFigureToolBar()
        
        self.lv1 = ui.QWebViewExtend(self, onNavEvent=self.m.onBrowserNav)
        self.lv2 = ui.QWebViewExtend(self, onNavEvent=self.m.onBrowserNav)
        self.tabs.addTab(self.lv1,'1')
        self.tabs.addTab(self.lv2,'2')
        
        self.data.add_output('scores')
        self.data.add_output('weights')
        
        self.data.add_input('input') # Add input slot
        
        # Setup data consumer options
        self.data.consumer_defs.append( 
            DataDefinition('input', {})
        )

        self.data.source_updated.connect( self.autogenerate ) # Auto-regenerate if the source data is modified
        self.config.updated.connect( self.autogenerate ) # Auto-regenerate if the configuration is changed
        self.data.consume_any_of( self.m.datasets[::-1] ) # Try consume any dataset; work backwards
        
    # Do the PCA analysis
    def generate(self):    
        
        dso = self.data.get('input') # Get the dataset
        _experiment_test = self.config.get('experiment_test')
        _experiment_control = self.config.get('experiment_control')
                
        data = dso.data
        
        plsr = PLSRegression(n_components=2)
        Y = np.array([0 if c == _experiment_control else 1 for c in dso.classes[0] ])
        #Y = Y.reshape( (len(dso.classes[0]),1) )
        
        print _experiment_test
        print _experiment_control
        print data.shape
        print data.T.shape
        print Y.shape
        print data
        print Y
        
        plsr.fit(data, Y) # Transpose it, as vars need to along the top
        
        #weights = pca.transform(data.T) # Get weights?
        
        # Build a list object of class, x, y
        print 'Xs',plsr.x_scores_[:,0]
        print plsr.x_scores_.shape
        print 'Ys',plsr.y_scores_[0]
        print plsr.y_scores_.shape
        
        print 'Xw',plsr.x_weights_[0]
        print plsr.x_weights_.shape
        print 'Yw',plsr.y_weights_[0]
        print plsr.y_weights_.shape
        
        figure_data = zip( dso.classes[0], plsr.x_scores_[:,0], plsr.x_scores_[:,1])
        
        # PLS-DA regions; mean +- 95% confidence in each axis for each cluster
        cw_x = defaultdict(list)
        cw_y = defaultdict(list)
        figure_regions = []
        for c,x,y in figure_data:
            cw_x[c].append( x )
            cw_y[c].append( y )
            
        for c in cw_x.keys():
            # Calculate mean point
            cx = np.mean( cw_x[c] )
            cy = np.mean( cw_y[c] )
            
            # Calculate 95% CI
            rx = np.std( cw_x[c] ) *2 # 2sd = 95% #1.95 * ( / srn) # 1.95 * SEM => 95% confidence
            ry = np.std( cw_y[c] ) *2 #1.95 * ( / srn)
            
            # Calculate 95% CI
            #srn = np.sqrt( len( cw_x[c] ) ) # Sample numbers sqrt
            #rx = 1.95*(np.std( cw_x[c] )/srn ) # 2sd = 95% #1.95 * ( / srn) # 1.95 * SEM => 95% confidence
            #ry = 1.95*(np.std( cw_y[c] )/srn ) #1.95 * ( / srn)
            
            figure_regions.append( 
                (c, cx, cy, rx, ry)
            )
        
        metadata = {
            'figure':{
                'data':figure_data,
                'regions': figure_regions,
                'x_axis_label': 'Latent Variable 1 (%0.2f%%)' % (plsr.y_weights_[0][0]*100),
                'y_axis_label': 'Latent Variable 2 (%0.2f%%)' % (plsr.y_weights_[0][1]*100),
                },
        }
        
        self.render(metadata, template='d3/pca.svg')

        if 'NoneType' in dso.scales_t[1]:
            dso.scales[1] = range(0, len( dso.scales[1] ) )
            
        weights = plsr.x_weights_
        
        # Label up the top 50 (the values are retained; just for clarity)
        wmx = np.amax( np.absolute( weights), axis=1 )
        dso_z = zip( dso.scales[1], dso.entities[1], dso.labels[1] )
        dso_z = sorted( zip( dso_z, wmx ), key=lambda x: x[1])[-50:] # Top 50
        dso_z = [x for x, wmx in dso_z ]    

        metadata = {
            'figure':{
                'data': zip( dso.scales[1], weights[:,0:1] ),  
                'labels': self.build_markers( dso_z, 2, self._build_label_cmp ), #zip( xarange, xarange, dso.labels[1]), # Looks mental, but were' applying ranges
                'entities': self.build_markers( dso_z, 1, self._build_entity_cmp ),      
            }
        }        
        
        self.render(metadata, template='d3/line.svg', target=self.lv1)

        metadata = {
            'figure':{
                'data': zip( dso.scales[1], weights[:,1:2] ),  
                'labels': self.build_markers( dso_z, 2, self._build_label_cmp ), #zip( xarange, xarange, dso.labels[1]), # Looks mental, but were' applying ranges
                'entities': self.build_markers( dso_z, 1, self._build_entity_cmp ),      
            }
        }        
        
        self.render(metadata, template='d3/line.svg', target=self.lv2)
        
                

class PLSDAPlugin(AnalysisPlugin):

    def __init__(self, **kwargs):
        super(PLSDAPlugin, self).__init__(**kwargs)
        self.register_app_launcher( self.app_launcher )

    def app_launcher(self):
        return PLSDAView( self, self.m )
        
        
