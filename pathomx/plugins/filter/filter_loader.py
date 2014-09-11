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


class FilterConfigPanel(ui.ConfigPanel):

    def __init__(self, *args, **kwargs):
        super(FilterConfigPanel, self).__init__(*args, **kwargs)

        # Correlation variables
        gb = QGroupBox('Regexp search and replace')
        vbox = QVBoxLayout()
        # Populate the list boxes
        self.lw_regexp = QLineEdit()
        vbox.addWidget(QLabel('Search:'))

        self.lw_matchfield = QComboBox()
        self.lw_matchfield.addItems(['Class', 'Sample'])  # FIXME: Should auto-populate by source indexes
        vbox.addWidget(self.lw_matchfield)
        self.config.add_handler('target', self.lw_matchfield)

        vbox.addWidget(self.lw_regexp)
        self.config.add_handler('match', self.lw_regexp)

        gb.setLayout(vbox)
        self.layout.addWidget(gb)

        self.dialogFinalise()


class FilterApp(ui.IPythonApp):

    name = "Filter"
    notebook = 'filter.ipynb'

    legacy_inputs = {'input': 'input_data'}
    legacy_outputs = {'output': 'output_data'}

    def __init__(self, *args, **kwargs):
        super(FilterApp, self).__init__(*args, **kwargs)

        self.addDataToolBar()
        self.addFigureToolBar()

        self.data.add_input('input_data')  # Add input slot
        self.data.add_output('output_data')  # Add output slot

        # Setup data consumer options
        self.data.consumer_defs.append(
            DataDefinition('input_data', {  # Accept anything!
            })
        )

        self.config.set_defaults({
            'target': 'Class',
            'match': '.*',
        })

        self.addConfigPanel(FilterConfigPanel, 'Settings')


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
        vbox.addWidget(QLabel('Search:'))

        self.lw_matchfield = QComboBox()
        self.lw_matchfield.addItems(['Class', 'Sample'])  # FIXME: Should auto-populate by source indexes
        vbox.addWidget(self.lw_matchfield)
        vbox.addWidget(self.lw_regexp)

        self.lw_replace = QLineEdit()
        vbox.addWidget(QLabel('Replace:'))
        vbox.addWidget(self.lw_replace)

        gb.setLayout(vbox)
        self.layout.addWidget(gb)

        self.dialogFinalise()


# Dialog box for Metabohunter search options
class ReclassifyImportDialog(ui.GenericDialog):

    def __init__(self, parent=None, view=None, *args, **kwargs):
        super(ReclassifyImportDialog, self).__init__(parent=parent, *args, **kwargs)

        self.v = view

        # Correlation variables
        gb = QGroupBox('Match on field')
        vbox = QVBoxLayout()
        self.lw_matchfield = QComboBox()
        self.lw_matchfield.addItems(['Class', 'Sample'])  # FIXME: Should auto-populate by source indexes
        vbox.addWidget(self.lw_matchfield)
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

        loadr = QPushButton()
        loadr.setIcon(QIcon(os.path.join(utils.scriptdir, 'icons', 'folder-open-document.png')))
        loadr.clicked.connect(self.onFilterImport)

        vboxh.addWidget(addfr)
        vboxh.addWidget(remfr)
        vboxh.addWidget(loadr)
        vbox.addLayout(vboxh)

        gb.setLayout(vbox)
        self.layout.addWidget(gb)

        self.config.add_handler('filters', self.lw_filters, (self.map_list_fwd, self.map_list_rev))
        self.finalise()

    def onFilterAdd(self):
        dlg = ReclassifyDialog(parent=self.v.w, view=self.v)

        if dlg.exec_():
            l = self.config.get('filters')[:]  # Copy
            if dlg.lw_regexp.text() != '' and dlg.lw_replace.text() != '':
                l.append((dlg.lw_regexp.text(), dlg.lw_replace.text(), dlg.lw_matchfield.currentText()))
            self.config.set('filters', l)

    def onFilterRemove(self):
        l = self.config.get('filters')[:]
        for i in self.lw_filters.selectedItems():
            l[self.lw_filters.row(i)] = (None, None, None)

        self.config.set('filters', [(k, v, m) for k, v, m in l if v is not None])

    def onFilterImport(self):
        filename, _ = QFileDialog.getOpenFileName(self.m, 'Load reclassifications from file', '', "All compatible files (*.csv *.txt *.tsv);;Comma Separated Values (*.csv);;Plain Text Files (*.txt);;Tab Separated Values (*.tsv);;All files (*.*)")
        if filename:

            with open(filename, 'rU') as f:
                dlg = ReclassifyImportDialog(parent=self.v.w, view=self.v)

                if dlg.exec_():
                    match_field = dlg.lw_matchfield.currentText()
                    reader = csv.reader(f, delimiter=',', dialect='excel')
                    l = []
                    for row in reader:
                        l.append((row[0], row[1], match_field))
                    self.config.set('filters', l)

    def map_list_fwd(self, s):
        " Receive text label, return the filter"
        return tuple(s.split('\t'))

    def map_list_rev(self, f):
        " Receive the filter, return the label"
        if f:
            return '\t'.join(f)
        else:
            return "\t\t"

        
class ReclassifyTool(ui.IPythonApp):

    name = "Reclassify"
    notebook = 'reclassify.ipynb'

    legacy_inputs = {'input': 'input_data'}
    legacy_outputs = {'output': 'output_data'}

    def __init__(self, *args, **kwargs):
        super(ReclassifyTool, self).__init__(*args, **kwargs)

        self.addDataToolBar()
        self.addFigureToolBar()

        self.data.add_input('input_data')  # Add input slot
        self.data.add_output('output_data')  # Add output slot

        # Setup data consumer options
        self.data.consumer_defs.append(
            DataDefinition('input_data', {  # Accept anything!
            })
        )

        self.config.set_default('filters', [])

        self.addConfigPanel(ReclassifyConfigPanel, 'Settings')


class Filter(FilterPlugin):

    def __init__(self, *args, **kwargs):
        super(Filter, self).__init__(*args, **kwargs)
        self.register_app_launcher(FilterApp)
        self.register_app_launcher(ReclassifyTool)
