# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from pathomx.plugins import AnalysisPlugin
from itertools import combinations
import pandas as pd

import pathomx.ui as ui

from pathomx.data import DataDefinition
from pathomx.qt import *


def make_label_for_entry(*args):
    return '\t'.join(map(str, [s for s in args if s != None]))


# Dialog box for Metabohunter search options
class RegressionDialog(ui.GenericDialog):

    def __init__(self, tool, *args, **kwargs):
        super(RegressionDialog, self).__init__(tool.w, *args, **kwargs)

        self.t = tool

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

        input_data = self.t.data.get('input_data')

        l = []
        if type(input_data.columns) == pd.MultiIndex:

            for n, name in enumerate(input_data.columns.names):
                l.append([v[n] for v in input_data.columns.values])

            self.scale_label_entity_table = zip(*l)

        else:  # pd.Index
            self.scale_label_entity_table = [input_data.columns.values]

        self.lw_variables.clear()

        self.lw_variables.addItems([make_label_for_entry(*x) for x in self.scale_label_entity_table])

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

        self.fwd_map_cache = {}
        self.l = [[], [], []]

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

        self.config.add_handler('variables', self.lw_variables, (self.map_list_fwd, self.map_list_rev))

        self.tool.data.source_updated.connect(self.onRefreshData)
        self.finalise()

    def onRegressionAdd(self):
        dlg = RegressionDialog(self.tool)

        if dlg.exec_():
            l = self.config.get('variables')[:]  # Copy
            i_list = []
            for item in dlg.lw_variables.selectedItems():
                i_list.append(dlg.lw_variables.row(item))  # Get index

            for c in combinations(i_list, 2):
                l.append(tuple(c))

            self.config.set('variables', l)

    def onRegressionRemove(self):
        l = self.config.get('variables')[:]
        for i in self.lw_variables.selectedItems():
            l[self.lw_variables.row(i)] = None

        self.config.set('variables', [v for v in l if v is not None])

    def onRefreshData(self, *args):  # Ignore source_updated interface param
        input_data = self.tool.data.get('input_data')
        l = []
        if type(input_data.columns) == pd.MultiIndex:

            for n, name in enumerate(input_data.columns.names):
                l.append([v[n] for v in input_data.columns.values])

        else:  # pd.Index
            l = [input_data.columns.values]

        self.l = l

        v = self.config.get('variables')[:]
        self.config.set('variables', [])

        self.fwd_map_cache = {}
        self.config.set('variables', v)

    def map_list_fwd(self, s):
        " Receive text name, return the indexes "
        return self.fwd_map_cache[s]

    def map_list_rev(self, x):
        " Receive the indexes, return the label"
        if not self.l:
            self.onRefreshData()

        x1, x2 = x
        x1l = make_label_for_entry(*[li[x1] for li in self.l])
        x2l = make_label_for_entry(*[li[x2] for li in self.l])
        s = "%s\t%s" % (x1l, x2l)
        # Auto cache to the fwd mapper so it'll work next time
        self.fwd_map_cache[s] = (x1, x2)
        return s


class RegressionTool(ui.AnalysisApp):

    name = "Regression"
    legacy_inputs = {'input': 'input_data'}
    legacy_outputs = {'output': 'output_data'}

    notebook = 'regression.ipynb'
    shortname = 'regression'

    def __init__(self, *args, **kwargs):
        super(RegressionTool, self).__init__(*args, **kwargs)

        self.data.add_input('input_data')  # Add input slot

        # Setup data consumer options
        self.data.consumer_defs.append(
            DataDefinition('input_data', {
#            'labels_n':   (None,['Pathway']),
            })
        )

        self.config.set_defaults({
            'variables': [],
        })
        self.addConfigPanel(RegressionConfigPanel, 'Settings')


class RegressionPlugin(AnalysisPlugin):

    def __init__(self, *args, **kwargs):
        super(RegressionPlugin, self).__init__(*args, **kwargs)
        RegressionTool.plugin = self
        self.register_app_launcher(RegressionTool)
