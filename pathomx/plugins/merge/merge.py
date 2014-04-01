# -*- coding: utf-8 -*-
#from __future__ import unicode_literals

import os, copy
import numpy as np

import pathomx.ui as ui
import pathomx.db as db
import pathomx.utils as utils

from pathomx.data import DataSet, DataDefinition
from pathomx.utils import UnicodeReader, UnicodeWriter
from pathomx.plugins import ProcessingPlugin


class MergeApp( ui.DataApp ):

    def __init__(self, **kwargs):
        super(MergeApp, self).__init__(**kwargs)

        self.addDataToolBar()
        self.data.add_input('input_1') # Add input slot        
        self.data.add_input('input_2') # Add input slot                
        self.data.add_output('output') # Add output slot
        self.table.setModel(self.data.o['output'].as_table)

        # Setup data consumer options
        self.data.consumer_defs.extend([ 
            DataDefinition('input_1', {
            'labels_n':     (None, '>1'),
            'entities_t':   (None, None), 
            }),
            DataDefinition('input_2', {
            'labels_n':     (None, '>1'),
            'entities_t':   (None, None), 
            }),
            ]
        )
        
        self.finalise()

    def generate(self, **kwargs):
        
        dsos = []
        for n,dsi in list(kwargs.items()):
            if dsi:
                dsos.append(dsi)

        # We now have a list of dsos to work on
        # Take the first one as the basis; then iterate the remainder
        # check for existence of each available entity (label)
        # If it is not in the current working model add all columns for it to the end and continue
        # NOTE: NEED TO CHECK DIMENSIONALITY & SAMPLE IDs 
        
        dsw = dsos[0]
        todo = dsos[1:]
        todo_n = len(todo)
        for n,dso in enumerate(todo):
            self.progress.emit( float(n)/todo_n )

            print(dso.name)
            # Check if we have sample ids; if yes then build index to the working dso
            if dso.labels_n[0] != dso.shape[0]: # Need labels for everything
                self.setWorkspaceStatus('error')
                print("Shape/label failure...")
                continue
            
            eos = dso.entities_l[1] # List of entities
            for eo in eos:
                print(eo)
                if eo not in dsw.entities[1] and eo != None:
                    print("...")
                    # We found something not in the base dataset; add it
                    # Get mask
                    mask = np.array(dso.entities[1]) == eo
                    anno = [(e,l,s) for e,l,s in zip(dso.entities[1], dso.labels[1], dso.scales[1]) if e == eo]
                    
                    # Add the annotations for these things
                    for e,l,s in anno:
                        dsw.entities[1].append(e)
                        dsw.labels[1].append(l)
                        dsw.scales[1].append(s)


                    # Check we match the reverse (will need to delete rows- optional?)
                    idx_r_bool = np.array([True if l in dso.labels[0] else False for l in dsw.labels[0] ])
                    dsw.data = dsw.data[idx_r_bool, :]
                    dsw.classes[0]=list( np.array( dsw.classes[0] )[ idx_r_bool ] )
                    dsw.labels[0]=list( np.array( dsw.labels[0] )[ idx_r_bool ] )
                    dsw.entities[0]=list( np.array( dsw.entities[0] )[ idx_r_bool ] )
                    dsw.scales[0]=list( np.array( dsw.scales[0] )[ idx_r_bool ] )

                    # Build vertical mask using sample labels
                    idx_bool = np.array([True if l in dsw.labels[0] else False for l in dso.labels[0] ])
                    idx = np.array([dsw.labels[0].index(l) for l in dso.labels[0] if l in dsw.labels[0] ])
                    
                    print('idx_bool', idx_bool.shape)
                    print(idx_bool)
                    print('mask', mask.shape)
                    print(mask[mask==True])
                    print('dsw.data', dsw.data.shape)
                    print('dso.data', dso.data.shape)
                    
                    data = dso.data[ idx_bool, :] # 2 step if mask disagrees
                    data = data[:, mask]
                    data = np.reshape(data, ( data.shape[0], data.shape[1] if len(data.shape) > 1 else 1) ) 
                    
                    # Build nans the size of the working dataset
                    new_data = np.empty( (dsw.shape[0], data.shape[1]) )
                    new_data[:] = np.nan
                    np.set_printoptions(threshold='nan')


                    # Apply the data into this shape (will match) using indexes
                    new_data[idx,:] = data
                    print(new_data)
                    # Append data to the end of the dsw
                    dsw.data = np.concatenate( (dsw.data, new_data), axis=1)

        return {'output':dso}

 
class Merge(ProcessingPlugin):

    def __init__(self, **kwargs):
        super(Merge, self).__init__(**kwargs)
        MergeApp.plugin = self
        self.register_app_launcher( MergeApp )
