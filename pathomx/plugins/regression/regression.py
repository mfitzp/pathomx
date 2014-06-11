# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from pathomx.plugins import AnalysisPlugin

from collections import defaultdict

import os, time
from copy import copy

from itertools import combinations

import numpy as np
import scipy as sp

import pathomx.ui as ui
import pathomx.db as db
import pathomx.utils as utils


from pathomx.data import DataSet, DataDefinition
from pathomx.views import MplScatterView, MplSpectraView
from pathomx.qt import *

def make_label_for_entry(x):
    return '\t'.join( map(str, [s for s in x if s != None]) )

# Dialog box for Metabohunter search options
class RegressionDialog(ui.GenericDialog):
    
    def __init__(self, parent, *args, **kwargs):
        super(RegressionDialog, self).__init__(parent.w, *args, **kwargs)        

        self.v = parent

        # Correlation variables
        gb = QGroupBox('Define variables')
        vbox = QVBoxLayout()
        # Populate the list boxes
        self.lw_variables = QListWidget()
        self.lw_variables.setSelectionMode(QAbstractItemView.ExtendedSelection)
        vbox.addWidget(self.lw_variables)

        self.lw_regexp = QLineEdit()
        vbox.addWidget(self.lw_regexp)
        vbox.addWidget(QLabel('Select/deselect matching pathways by name:'))
        vboxh = QHBoxLayout()

        vboxh.addWidget(self.lw_regexp)

        addfr = QPushButton('-')
        addfr.clicked.connect(self.onRegexpRemove)
        addfr.setFixedWidth(24)

        remfr = QPushButton('+')
        remfr.clicked.connect(self.onRegexpAdd)
        remfr.setFixedWidth(24)

        vboxh.addWidget(addfr)
        vboxh.addWidget(remfr)
        vbox.addLayout(vboxh)

        gb.setLayout(vbox)
        self.layout.addWidget(gb)


        dsi = self.v.data.get('input')
        self.lw_variables.clear()
        
        self.scale_label_entity_table = zip(range(1, len(dsi.scales[1])+1), dsi.scales[1], dsi.labels[1], dsi.entities[1])
        self.lw_variables.addItems( [make_label_for_entry(x) for x in self.scale_label_entity_table] )        

        self.dialogFinalise()        
        


    def onRegexpAdd(self):
        items = self.lw_variables.findItems(self.lw_regexp.text(), Qt.MatchContains)
        block = self.lw_variables.blockSignals(True)
        for i in items:
            i.setSelected(True)
        self.lw_variables.blockSignals(block)
        self.lw_variables.itemSelectionChanged.emit()

    def onRegexpRemove(self):
        items = self.lw_variables.findItems(self.lw_regexp.text(), Qt.MatchContains)
        block = self.lw_variables.blockSignals(True)
        for i in items:
            i.setSelected(False)
        self.lw_variables.blockSignals(block)
        self.lw_variables.itemSelectionChanged.emit()


# Dialog box for Metabohunter search options
class RegressionConfigPanel(ui.ConfigPanel):
    
    def __init__(self, *args, **kwargs):
        super(RegressionConfigPanel, self).__init__(*args, **kwargs)        

        # Correlation variables
        gb = QGroupBox('Regressions')
        vbox = QVBoxLayout()
        # Populate the list boxes
        self.lw_variables = ui.QListWidgetAddRemove()
        self.lw_variables.setSelectionMode(QAbstractItemView.ExtendedSelection)
        vbox.addWidget(self.lw_variables)

        vboxh = QHBoxLayout()
        addfr = QPushButton('Remove')
        addfr.clicked.connect(self.onRegressionRemove)

        remfr = QPushButton('Add')
        remfr.clicked.connect(self.onRegressionAdd)

        vboxh.addWidget(addfr)
        vboxh.addWidget(remfr)
        vbox.addLayout(vboxh)

        gb.setLayout(vbox)
        self.layout.addWidget(gb)
                    
        self.config.add_handler('variables', self.lw_variables, (self.v.map_list_fwd, self.v.map_list_rev) )

        self.v.data.source_updated.connect( self.onRefreshData )
        self.finalise()        
        
    def onRegressionAdd(self):
        dlg = RegressionDialog(self.v)
        
        if dlg.exec_():
            l = self.config.get('variables')[:] # Copy
            i_list = []
            for item in dlg.lw_variables.selectedItems():
                i_list.append( dlg.lw_variables.row( item ) )# Get index
                #key = dlg.scale_label_entity_table[i]
                #label = make_label_for_entry(key)
                       

            for c in combinations( i_list, 2):
                #self.lw_variables.addItems( [self.v.map_list_rev( c )] )
                l.append( tuple(c) ) 
            self.config.set('variables', l)

    def onRegressionRemove(self):
        l = self.config.get('variables')[:]
        for i in self.lw_variables.selectedItems():
            l[self.lw_variables.row(i)] = None
    
        self.config.set('variables', [v for v in l if v is not None])
        
    def onRefreshData(self):
        v = self.config.get('variables')[:]
        self.config.set('variables', [])

        self.v.fwd_map_cache = {}
        self.config.set('variables', v)


class RegressionTool( ui.AnalysisApp ):
    def __init__(self, **kwargs):
        super(RegressionTool, self).__init__(**kwargs)

        self.fwd_map_cache = {}

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
            'variables': [],
        })
        self.addConfigPanel( RegressionConfigPanel, 'Settings' )
        
        for n in range(1, 8):
            self.views.addView(MplScatterView(self), '%s' % n)

        
        self.finalise()
        
    def generate(self, input=None):
        data = input.data
        
        vars = self.config.get('variables')

        correlations = {}
        for n, v in enumerate(self.config.get('variables')):
            a, b = v
            x = input.data[:, a ] 
            y = input.data[:, b ]  
            
            fit = np.polyfit(x,y,1)
            dso = DataSet( size=(len(x),2 ) )
            dso.data[:,0] = x
            dso.data[:,1] = y
            
            dso.labels[1][0] = make_label_for_entry( [input.scales[1][a], input.labels[1][a], input.entities[1][a] ] )
            dso.labels[1][1] = make_label_for_entry( [input.scales[1][b], input.labels[1][b], input.entities[1][b] ] )
            
            slope, intercept, r_value, p_value, std_err = sp.stats.linregress(x, y)
                        
            correlations[str(n+1)] = {
                'dso': dso,
                'fit': fit,
                'label': 'r²=%0.2f, p=%0.2f' % (r_value**2, p_value)
            }
        return {'correlations':correlations}
        
    def prerender(self, correlations={}, **kwargs):
        
        out = {}
    
        for k,c in correlations.items():
            x_data = np.linspace(np.min(c['dso'].data[:,0]), np.max(c['dso'].data[:,0]), 50)
            lines = [
                (x_data, np.polyval(c['fit'], x_data), c['label'])
            ]
            
            out[k] = {'dso': c['dso'], 'lines':lines}
        
        return out
        
    def map_list_fwd(self, s):
        " Receive text name, return the indexes "
        return self.fwd_map_cache[s]

    def map_list_rev(self, x):
        " Receive the indexes, return the label"
        dsi = self.data.get('input')
        x1, x2 = x
        x1l = make_label_for_entry( [x1, dsi.scales[1][x1], dsi.labels[1][x1], dsi.entities[1][x1]]  )
        x2l = make_label_for_entry( [x2, dsi.scales[1][x2], dsi.labels[1][x2], dsi.entities[1][x2]]  )
        s = "%s\t%s" % (x1l,x2l)
        # Auto cache to the fwd mapper so it'll work next time
        self.fwd_map_cache[s] = (x1,x2)
        return s
                

class RegressionPlugin(AnalysisPlugin):

    def __init__(self, **kwargs):
        super(RegressionPlugin, self).__init__(**kwargs)
        RegressionTool.plugin = self
        self.register_app_launcher( RegressionTool )
        
        
