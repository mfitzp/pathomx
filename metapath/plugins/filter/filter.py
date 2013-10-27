# -*- coding: utf-8 -*-
from plugins import ProcessingPlugin



# Import PyQt5 classes
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWebKit import *
from PyQt5.QtNetwork import *
from PyQt5.QtWidgets import *
from PyQt5.QtWebKitWidgets import *
from PyQt5.QtPrintSupport import *


import utils
import csv, os, re
import xml.etree.cElementTree as et
from collections import defaultdict

import numpy as np

import ui, db
from data import DataSet, DataDefinition





# Source data selection dialog
# Present a list of widgets (drop-downs) for each of the interfaces available on this plugin
# in each list show the data sources that can potentially file that slot. 
# Select the currently used 
class DialogDefineFilter(ui.genericDialog):
    def __init__(self, parent=None, view=None, **kwargs):
        super(DialogDefineFilter, self).__init__(parent, **kwargs)        
        
        self.v = view
        self.m = view.m
        
        self.setWindowTitle("Define filters targets(s)")

        # Build a list of dicts containing the widget
        # with target data in there
        self.lw_filteri = list()
        self.lw_filtert = list()
        dsi = self.v.data.get('input')
        
        
        for k,t in self.v._filters.items():
            
            self.lw_filteri.append( QComboBox() )
            cdw = self.lw_filteri[-1] # Shorthand

            self.lw_filtert.append( QLineEdit() )
            ctw = self.lw_filtert[-1]
            ctw.setText( t )

            selected_index = None
            idx = 0
            for n, i in enumerate(dsi.scales):
                for target in ['labels','classes','scales']:
                    s = '%s/%s' % (n,target)
                    cdw.addItem(s)
                    if s == k:
                        selected_index = idx
                    idx += 1
                        
            if selected_index:
                cdw.setCurrentIndex(selected_index)

            self.layout.addWidget(cdw)
            self.layout.addWidget(ctw)
            
        self.setMinimumSize( QSize(600,100) )
        self.layout.setSizeConstraint(QLayout.SetMinimumSize)
        
        # Build dialog layout
        self.dialogFinalise()
        


class FilterView( ui.DataView ):

    def __init__(self, plugin, parent, **kwargs):
        super(FilterView, self).__init__(plugin, parent, **kwargs)
        
        self.addDataToolBar()
        self.addFigureToolBar()

        self.data.add_input('input') # Add input slot
        self.data.add_output('output') # Add output slot
        self.table.setModel(self.data.o['output'].as_table)
                    
        # Setup data consumer options
        self.data.consumer_defs.append( 
            DataDefinition('input', { # Accept anything!
            })
        )
        
            
        th = self.addToolBar('Filter')
        
        filterAction = QAction( QIcon( os.path.join( utils.scriptdir, 'icons', 'funnel--plus.png') ), '&Define filter(s)…', self)
        filterAction.setStatusTip( 'Define filter(s) for dataset') 
        filterAction.triggered.connect(self.onDefineFilter)
        th.addAction(filterAction)
        
        self.config.set_default('filters',{'':''}) 
        
        self.data.consume_any_of( self.m.datasets[::-1] ) # Try consume any dataset; work backwards

        self.data.source_updated.connect( self.generate ) # Auto-regenerate if the source data is modified
        self.generate()
    
    
    def onDefineFilter(self):
        """ Open a data file"""
        dialog = DialogDefineFilter(parent=self, view=self)
        ok = dialog.exec_()
        if ok:
            # Extract the settings and store in the _annotations_targets settings
            # then run the annotation process
            filters = {}
            # dict of source = (target, axis)
            
            for n, cb in enumerate(dialog.lw_filteri): # Get list of comboboxes
                target = cb.currentText()
                text = dialog.lw_filtert[n].text()
                
                filters[ target ] = text
                
            self.config.set('filters',filters)
            # Annotation name
            self.set_name( ','.join([ '%s:%s' % (k,v) for k,v in filters.items()])  )
            self.generate()
        
    def apply_filters(self,dso):

        for target, text in self.config.get('filters').items():    
            axis,field = target.split('/')
            axis = int(axis) # index to apply
            
            textre = re.compile(text)
            
            matches = []
            # field, axis, text
            for o in dso.__dict__[field][axis]:
                match = textre.search(o)
                if match:
                    matches.append( o )

            matches = set(matches)

            kwargs = {field: matches}
            # Apply the filter to regexp to get a filtered list
            dso = dso.as_filtered(dim=axis, **kwargs)
        
        return dso
            

               
    # Data file import handlers (#FIXME probably shouldn't be here)
    def generate(self):
        self.setWorkspaceStatus('active')
        
        dso = self.data.get('input')
        dso = self.apply_filters( dso )

        self.data.put('output',dso)
        self.render({})
        
        self.setWorkspaceStatus('done')
        self.clearWorkspaceStatus()                


class Filter(ProcessingPlugin):

    def __init__(self, **kwargs):
        super(Filter, self).__init__(**kwargs)
        self.register_app_launcher( self.app_launcher )

    def app_launcher(self):
        return FilterView( self, self.m )
