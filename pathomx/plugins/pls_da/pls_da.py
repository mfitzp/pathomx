# -*- coding: utf-8 -*-

from pathomx.plugins import AnalysisPlugin

from collections import defaultdict

import os
from copy import copy

import numpy as np
from sklearn.cross_decomposition import PLSRegression

import pathomx.ui as ui
import pathomx.db as db
import pathomx.utils as utils
import pathomx.threads as threads

from pathomx.data import DataSet, DataDefinition
from pathomx.views import MplScatterView, MplSpectraView
from pathomx.qt import *

         
# Dialog box for Metabohunter search options
class PLSDAConfigPanel(ui.ConfigPanel):


    
    def __init__(self, *args, **kwargs):
        super(PLSDAConfigPanel, self).__init__(*args, **kwargs)        
    
        #row = QVBoxLayout()
        #cl = QLabel('Algorithm')
        #cb = QComboBox()
        #cb.addItems( ['NIPALS','SVD'] )
        #row.addWidget(cl)
        #row.addWidget(cb)
        #self.config.add_handler('algorithm', cb)
        #self.layout.addLayout(row)
        
        cb = QCheckBox('Autoscale input data')
        self.config.add_handler('autoscale', cb)
        self.layout.addWidget(cb)

        row = QVBoxLayout()
        cl = QLabel('Number of components')
        cb = QSpinBox()
        cb.setRange(0,10)
        row.addWidget(cl)
        row.addWidget(cb)
        self.config.add_handler('number_of_components', cb)
        self.layout.addLayout(row)
                    
        self.finalise()
    



class PLSDAApp( ui.AnalysisApp ):

    def __init__(self, **kwargs):
        super(PLSDAApp, self).__init__(**kwargs)

        # Define automatic mapping (settings will determine the route; allow manual tweaks later)
        
        self.addDataToolBar()
        self.addExperimentToolBar()
        self.addFigureToolBar()

        self.views.addView(MplScatterView(self),'Scores')

        self.views.addView(MplSpectraView(self),'LV1')
        self.views.addView(MplSpectraView(self),'LV2')
        
        self.data.add_output('scores')
        self.data.add_output('weights')
        
        self.data.add_input('input') # Add input slot
        
        self.config.set_defaults({
            'number_of_components': 2,
            'autoscale': False,
            'algorithm':'NIPALS',
        })

        self.addConfigPanel( PLSDAConfigPanel, 'PLSDA')
        
        # Setup data consumer options
        self.data.consumer_defs.append( 
            DataDefinition('input', {})
        )
        
        self.finalise()
                
    # Do the PCA analysis
    def generate(self, input=None):   
        dso = input
        
        _experiment_test = self.config.get('experiment_test')
        _experiment_control = self.config.get('experiment_control')
                
        data = dso.data
        
        plsr = PLSRegression(n_components=self.config.get('number_of_components'), scale=self.config.get('autoscale')) #, algorithm=self.config.get('algorithm'))
        Y = np.array([0 if c == _experiment_control else 1 for c in dso.classes[0] ])
        #Y = Y.reshape( (len(dso.classes[0]),1) )

        plsr.fit(data, Y) # Transpose it, as vars need to along the top
        
        #figure_data = zip( dso.classes[0], plsr.x_scores_[:,0], plsr.x_scores_[:,1])
        
        # Build scores into a dso no_of_samples x no_of_principal_components
        scored = DataSet(size=(len(plsr.x_scores_),len(plsr.x_scores_[0])))  
        scored.labels[0] = input.labels[0]
        scored.classes[0] = input.classes[0]
        
        print(plsr.x_scores_.shape)
        print(scored.data.shape)
        
        for n,s in enumerate(plsr.x_scores_.T):
            scored.data[:,n] = s
            scored.labels[1][n] = 'Latent Variable %d (%0.2f%%)' % (n+1, plsr.y_weights_[0][0]*100)
                
        
        # PLS-DA regions; mean +- 95% confidence in each axis for each cluster
        cw_x = defaultdict(list)
        cw_y = defaultdict(list)
        #figure_regions = []
        #for c,x,y in figure_data:
        #    cw_x[c].append( x )
        #    cw_y[c].append( y )
            
        for c in list(cw_x.keys()):
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

        
            
        # Label up the top 50 (the values are retained; just for clarity)
        wmx = np.amax( np.absolute( plsr.x_weights_), axis=1 )
        dso_z = list(zip( dso.scales[1], dso.entities[1], dso.labels[1] ))
        dso_z = sorted( zip( dso_z, wmx ), key=lambda x: x[1])[-50:] # Top 50
        dso_z = [x for x, wmx in dso_z ]    

        weightsd = DataSet(size=plsr.x_weights_.T.shape)
        weightsd.data = plsr.x_weights_.T
        weightsd.scales[1] = input.scales[1]

        dso_lv = {}
        for n in range(0, plsr.x_weights_.shape[1] ):
            lvd =  DataSet( size=(1, input.shape[1] ) )
            lvd.entities[1] = input.entities[1]
            lvd.labels[1] = input.labels[1]
            lvd.scales[1] = input.scales[1]
            lvd.data = plsr.x_weights_[:,n:n+1].T
            dso_lv['lv%s' % (n+1)] = lvd
            weightsd.labels[0][n] = "Weights on LV %s" % (n+1)
            weightsd.classes[0][n] = "LV %s" % (n+1)
                    
        return dict(list({
            'dso': dso,
            'scores':scored,
            'weights':weightsd,
            #'figure_data': figure_data,
            #'figure_regions': figure_regions,
            'y_weights': plsr.y_weights_,
            'x_weights': plsr.x_weights_,
        }.items()) + list(dso_lv.items()) )
        
        
    def prerender(self, scores=None, lv1=None, lv2=None, **kwargs):
        return {
            'Scores':{'dso': scores}, 
            'LV1':{'dso':lv1},
            'LV2':{'dso':lv2}, #zip( dso.classes[0], pca.components_[0], pca.components_[1])}
            }
    
    
    def legacy_generated(self, dso, dso_z, figure_data, figure_regions, y_weights, x_weights):
        
        metadata = {
            'figure':{
                'data':figure_data,
                'regions': figure_regions,
                'x_axis_label': 'Latent Variable 1 (%0.2f%%)' % (y_weights[0][0]*100),
                'y_axis_label': 'Latent Variable 2 (%0.2f%%)' % (y_weights[0][1]*100),
                },
        }
        
        self.render(metadata, template='d3/pca.svg')

        if 'NoneType' in dso.scales_t[1]:
            dso.scales[1] = list(range(0, len( dso.scales[1] )))

        metadata = {
            'figure':{
                'data': list(zip( dso.scales[1], x_weights[:,0:1] )),  
                'labels': self.build_markers( dso_z, 2, self._build_label_cmp ), #zip( xarange, xarange, dso.labels[1]), # Looks mental, but were' applying ranges
                'entities': self.build_markers( dso_z, 1, self._build_entity_cmp ),      
            }
        }        
        
        self.render(metadata, template='d3/line.svg', target=self.lv1)

        metadata = {
            'figure':{
                'data': list(zip( dso.scales[1], x_weights[:,1:2] )),  
                'labels': self.build_markers( dso_z, 2, self._build_label_cmp ), #zip( xarange, xarange, dso.labels[1]), # Looks mental, but were' applying ranges
                'entities': self.build_markers( dso_z, 1, self._build_entity_cmp ),      
            }
        }        
        
        self.render(metadata, template='d3/line.svg', target=self.lv2)
        
                

class PLSDAPlugin(AnalysisPlugin):

    def __init__(self, **kwargs):
        super(PLSDAPlugin, self).__init__(**kwargs)
        PLSDAApp.plugin = self
        self.register_app_launcher( PLSDAApp )
        
        
