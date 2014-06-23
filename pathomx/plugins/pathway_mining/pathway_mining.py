# -*- coding: utf-8 -*-

from pathomx.plugins import AnalysisPlugin

from collections import defaultdict

import os
import pathomx.ui as ui
import pathomx.utils as utils

from pathomx.data import DataSet, DataDefinition
from pathomx.views import TableView
from pathomx.qt import *

import numpy as np

METAPATH_MINING_TYPE_CODE = ('c', 'u', 'd', 'm', 't')
METAPATH_MINING_TYPES = {
    'Compound change scores': 'c',
    'Compound up-regulation scores': 'u',
    'Compound down-regulation scores': 'd',
    'Number compounds with data': 'm',
    'Overall tendency': 't',
}

METAPATH_MINING_TARGETS = {
    'Pathways': 0,
    'Reactions': 1,
    # 'Compartments':2,
}


# Dialog box for Metabohunter search options
class PathwayMiningConfigPanel(ui.ConfigPanel):

    def __init__(self, *args, **kwargs):
        super(PathwayMiningConfigPanel, self).__init__(*args, **kwargs)

        self.cb_miningTarget = QComboBox()
        self.cb_miningTarget.addItems(list(METAPATH_MINING_TARGETS.keys()))
        self.config.add_handler('/Data/MiningTarget', self.cb_miningTarget, METAPATH_MINING_TARGETS)

        self.cb_miningType = QComboBox()
        self.cb_miningType.addItems(list(METAPATH_MINING_TYPES.keys()))
        self.config.add_handler('/Data/MiningType', self.cb_miningType, METAPATH_MINING_TYPES)

        self.xb_miningRelative = QCheckBox('Relative score to pathway size')
        self.config.add_handler('/Data/MiningRelative', self.xb_miningRelative)

        self.xb_miningShared = QCheckBox('Share compound scores between pathways')
        self.config.add_handler('/Data/MiningShared', self.xb_miningShared)

        self.sb_miningDepth = QSpinBox()
        self.sb_miningDepth.setMinimum(1)
        self.config.add_handler('/Data/MiningDepth', self.sb_miningDepth)

        self.layout.addWidget(self.cb_miningTarget)
        self.layout.addWidget(self.cb_miningType)
        self.layout.addWidget(self.xb_miningRelative)
        self.layout.addWidget(self.xb_miningShared)
        self.layout.addWidget(self.sb_miningDepth)

        self.finalise()


class PathwayMiningApp(ui.AnalysisApp):

    name = "Pathway Mining"
    legacy_inputs = {'input': 'input_1'}
    legacy_outputs = {'output': 'output_data'}

    notebook = "pathway_mining.ipynb"

    def __init__(self, *args, **kwargs):
        super(PathwayMiningApp, self).__init__(*args, **kwargs)

        # Define automatic mapping (settings will determine the route; allow manual tweaks later)
        self.addDataToolBar()

        self.config.set_defaults({
            '/Data/MiningTarget': 0,
            '/Data/MiningDepth': 5,
            '/Data/MiningType': 'c',
            '/Data/MiningRelative': False,
            '/Data/MiningShared': True,
        })

        self.data.add_input('input_1')  # Add input slot
        self.data.add_input('input_2')  # Add input slot
        self.data.add_input('input_3')  # Add input slot
        self.data.add_input('input_4')  # Add input slot
        self.data.add_output('output_data')

        # Setup data consumer options
        self.data.consumer_defs.extend([
            DataDefinition('input_1', {
            'entities_t': (None, ['Compound', 'Gene', 'Protein', 'Reaction']),
            }, title='Source compound, gene or protein data'),
            DataDefinition('input_2', {
            'entities_t': (None, ['Compound', 'Gene', 'Protein', 'Reaction']),
            }, title='Source compound, gene or protein data'),
            DataDefinition('input_3', {
            'entities_t': (None, ['Compound', 'Gene', 'Protein', 'Reaction']),
            }, title='Source compound, gene or protein data'),
            DataDefinition('input_4', {
            'entities_t': (None, ['Compound', 'Gene', 'Protein', 'Reaction']),
            }, title='Source compound, gene or protein data'),
        ])

        self.addConfigPanel(PathwayMiningConfigPanel, 'Pathway Mining')

        
class PathwayMining(AnalysisPlugin):

    def __init__(self, *args, **kwargs):
        super(PathwayMining, self).__init__(*args, **kwargs)
        self.register_app_launcher(PathwayMiningApp)
