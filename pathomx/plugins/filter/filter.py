# -*- coding: utf-8 -*-

import csv
import os
import re
import xml.etree.cElementTree as et
from collections import defaultdict

import numpy as np

import pathomx.ui as ui
import pathomx.db as db
import pathomx.utils as utils

from pathomx.data import DataSet, DataDefinition
from pathomx.plugins import FilterPlugin
from pathomx.qt import *


# Source data selection dialog
# Present a list of widgets (drop-downs) for each of the interfaces available on this plugin
# in each list show the data sources that can potentially file that slot.
# Select the currently used
class DialogDefineFilter(ui.GenericDialog):
    def __init__(self, parent=None, view=None, auto_consume_data=True, **kwargs):
        super(DialogDefineFilter, self).__init__(parent, **kwargs)

        self.v = view
        self.m = view.m

        self.setWindowTitle("Define filters targets(s)")

        # Build a list of dicts containing the widget
        # with target data in there
        self.lw_filteri = list()
        self.lw_filtert = list()
        dsi = self.v.data.get('input')

        
        for k, t in list(self.v.config.get('filters').items()):

            self.lw_filteri.append(QComboBox())
            cdw = self.lw_filteri[-1]  # Shorthand

            self.lw_filtert.append(QLineEdit())
            ctw = self.lw_filtert[-1]
            ctw.setText(t)

            selected_index = None
            idx = 0
            for n, i in enumerate(dsi.scales):
                for target in ['labels', 'classes', 'scales']:
                    s = '%s/%s' % (n, target)
                    cdw.addItem(s)
                    if s == k:
                        selected_index = idx
                    idx += 1

            if selected_index:
                cdw.setCurrentIndex(selected_index)

            self.layout.addWidget(cdw)
            self.layout.addWidget(ctw)

        self.setMinimumSize(QSize(600, 100))
        self.layout.setSizeConstraint(QLayout.SetMinimumSize)

        # Build dialog layout
        self.dialogFinalise()


class FilterApp(ui.DataApp):

    def __init__(self, **kwargs):
        super(FilterApp, self).__init__(**kwargs)

        self.addDataToolBar()
        self.addFigureToolBar()

        self.data.add_input('input')  # Add input slot
        self.data.add_output('output')  # Add output slot
        self.table.setModel(self.data.o['output'].as_table)

        # Setup data consumer options
        self.data.consumer_defs.append(
            DataDefinition('input', {  # Accept anything!
            })
        )

        th = self.addToolBar('Filter')

        filterAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'funnel--plus.png')), '&Define filter(s)…', self)
        filterAction.setStatusTip('Define filter(s) for dataset')
        filterAction.triggered.connect(self.onDefineFilter)
        th.addAction(filterAction)

        self.config.set_default('filters', {'': ''})

        self.finalise()

    def onDefineFilter(self):
        """ Open a data file"""
        dialog = DialogDefineFilter(parent=self.w, view=self)
        ok = dialog.exec_()
        if ok:
            # Extract the settings and store in the _annotations_targets settings
            # then run the annotation process
            filters = {}
            # dict of source = (target, axis)

            for n, cb in enumerate(dialog.lw_filteri):  # Get list of comboboxes
                target = cb.currentText()
                text = dialog.lw_filtert[n].text()

                filters[target] = text

            self.config.set('filters', filters)
            # Annotation name
            self.set_name(','.join(['%s:%s' % (k, v) for k, v in list(filters.items())]))
            self.generate()

    def apply_filters(self, dso):

        for target, text in list(self.config.get('filters').items()):
            axis, field = target.split('/')
            axis = int(axis)  # index to apply

            textre = re.compile(text)

            matches = []
            # field, axis, text
            for o in dso.__dict__[field][axis]:
                match = textre.search(o)
                if match:
                    matches.append(o)

            matches = set(matches)

            kwargs = {field: matches}
            # Apply the filter to regexp to get a filtered list
            dso = dso.as_filtered(dim=axis, **kwargs)

        return dso

    def generate(self, input=None):
        return {'output': self.apply_filters(input)}
        


# Dialog box for Metabohunter search options
class ReclassifyDialog(ui.GenericDialog):
    
    def __init__(self, parent=None, view=None, *args, **kwargs):
        super(ReclassifyDialog, self).__init__(parent=parent, *args, **kwargs)        

        self.v = view

        # Correlation variables
        gb = QGroupBox('Regexp search and replace')
        vbox = QVBoxLayout()
        # Populate the list boxes
        self.lw_regexp = QLineEdit()
        vbox.addWidget(self.lw_regexp)
        vbox.addWidget(QLabel('Search:'))

        self.lw_replace = QLineEdit()
        vbox.addWidget(self.lw_replace)
        vbox.addWidget(QLabel('Replace:'))

        gb.setLayout(vbox)
        self.layout.addWidget(gb)

        self.dialogFinalise()        
        

# Dialog box for Metabohunter search options
class ReclassifyConfigPanel(ui.ConfigPanel):
    
    def __init__(self, *args, **kwargs):
        super(ReclassifyConfigPanel, self).__init__(*args, **kwargs)        

        # Correlation variables
        gb = QGroupBox('Reclassifications')
        vbox = QVBoxLayout()
        # Populate the list boxes
        self.lw_filters = ui.QListWidgetAddRemove()
        self.lw_filters.setSelectionMode(QAbstractItemView.ExtendedSelection)
        vbox.addWidget(self.lw_filters)

        vboxh = QHBoxLayout()
        addfr = QPushButton('Remove')
        addfr.clicked.connect(self.onFilterRemove)

        remfr = QPushButton('Add')
        remfr.clicked.connect(self.onFilterAdd)

        vboxh.addWidget(addfr)
        vboxh.addWidget(remfr)
        vbox.addLayout(vboxh)

        gb.setLayout(vbox)
        self.layout.addWidget(gb)
                    
        self.config.add_handler('filters', self.lw_filters, (self.v.map_list_fwd, self.v.map_list_rev) )
        self.finalise()        
        
    def onFilterAdd(self):
        dlg = ReclassifyDialog(parent=self.v.w, view=self.v)
        
        if dlg.exec_():
            l = self.config.get('filters')[:] # Copy
            if dlg.lw_regexp.text() !='' and dlg.lw_replace.text() !='':
                l.append( ( dlg.lw_regexp.text(), dlg.lw_replace.text() ) )
            self.config.set('filters', l)

    def onFilterRemove(self):
        l = self.config.get('filters')[:]
        for i in self.lw_filters.selectedItems():
            l[self.lw_filters.row(i)] = (None,None)
    
        self.config.set('filters', [(k,v) for k,v in l if v is not None])
  
        
        
class ReclassifyTool(ui.DataApp):

    name = "Reclassify"

    def __init__(self, **kwargs):
        super(ReclassifyTool, self).__init__(**kwargs)

        self.addDataToolBar()
        self.addFigureToolBar()

        self.data.add_input('input')  # Add input slot
        self.data.add_output('output')  # Add output slot
        self.table.setModel(self.data.o['output'].as_table)

        # Setup data consumer options
        self.data.consumer_defs.append(
            DataDefinition('input', {  # Accept anything!
            })
        )

        self.config.set_default('filters', [])

        self.addConfigPanel(ReclassifyConfigPanel, 'Settings')
        self.finalise()

    def apply_filters(self, dso):

        classes = dso.classes[0]
        for search, replace in self.config.get('filters'):
            classes_f = []
            for c in classes:   
                match = re.search(search, c)
                if match:
                   classes_f.append(replace)
                else:
                   classes_f.append(c)

            classes = classes_f
            
        dso.classes[0] = classes
        return dso

    def generate(self, input=None):
        return {'output': self.apply_filters(input)}        

        
    def map_list_fwd(self, s):
        " Receive text label, return the filter"
        return tuple( s.split('\t') )

    def map_list_rev(self, f):
        " Receive the filter, return the label"
        if f:
            return "%s\t%s" % tuple(f)
        else:
            return "\t"

class Filter(FilterPlugin):

    def __init__(self, **kwargs):
        super(Filter, self).__init__(**kwargs)
        self.register_app_launcher(FilterApp)
        self.register_app_launcher(ReclassifyTool)
