# -*- coding: utf-8 -*-

from pathomx.plugins import AnalysisPlugin

from collections import defaultdict

import os
import pathomx.ui as ui
import pathomx.utils as utils

from pathomx.data import DataDefinition
from pathomx.views import TableView
from pathomx.qt import *

import numpy as np
from biocyc import biocyc
biocyc.secondary_cache_paths.append( os.path.join(utils.scriptdir, 'database', 'biocyc') )

METAPATH_MINING_TYPE_CODE = ('c', 'u', 'd', 'm', 't')
METAPATH_MINING_TYPES = {
    'Change scores': 'c',
    'Up-regulation scores': 'u',
    'Down-regulation scores': 'd',
    'Number compounds with data': 'm',
    'Overall tendency': 't',
}

METAPATH_MINING_TARGETS = {
    'Pathways': 0,
    'Reactions': 1,
    # 'Compartments':2,
}


# Dialog box for Metabohunter search options
class PathwayMiningInExPathwayConfigPanel(ui.ConfigPanel):

    def __init__(self, *args, **kwargs):
        super(PathwayMiningInExPathwayConfigPanel, self).__init__(*args, **kwargs)

        self.label = defaultdict(dict)
        self.setupSection('Include', 'include_pathways')
        self.setupSection('Exclude', 'exclude_pathways')

        self.finalise()

    def onRegexpAdd(self):
        label = self.sender().objectName()
        items = self.label[label]['lw_pathways'].findItems(self.label[label]['lw_regExp'].text(), Qt.MatchContains | Qt.MatchRecursive)
        block = self.label[label]['lw_pathways'].blockSignals(True)
        for i in items:
            i.setCheckState(0, Qt.Checked)
        self.label[label]['lw_pathways'].blockSignals(block)
        self.label[label]['lw_pathways'].itemSelectionChanged.emit()

    def onRegexpRemove(self):
        label = self.sender().objectName()
        items = self.label[label]['lw_pathways'].findItems(self.label[label]['lw_regExp'].text(), Qt.MatchContains | Qt.MatchRecursive)
        block = self.label[label]['lw_pathways'].blockSignals(True)
        for i in items:
            i.setCheckState(0, Qt.Unchecked)
        self.label[label]['lw_pathways'].blockSignals(block)
        self.label[label]['lw_pathways'].itemSelectionChanged.emit()

    def setupSection(self, label, pathway_config):
        # SHOW PATHWAYS
        gb = QGroupBox(label)
        vbox = QVBoxLayout()
        # Populate the list boxes
        self.label[label]['lw_pathways'] = ui.QBioCycPathwayTreeWidget([
            'Biosynthesis',
            'Degradation',
            'Energy-Metabolism',
            ])

        fwd_map = lambda x: biocyc.find_pathway_by_name(x).id
        rev_map = lambda x: biocyc.get(x).name
        
        self.config.hooks['QBioCycPathwayTreeWidget'] = self.config.hooks['QCheckTreeWidget'] # Works the same
        self.config.add_handler(pathway_config, self.label[label]['lw_pathways'], (fwd_map, rev_map))

        self.label[label]['lw_regExp'] = QLineEdit()

        vbox.addWidget(self.label[label]['lw_pathways'])
        vbox.addWidget(QLabel('Select/deselect matching pathways by name:'))
        vboxh = QHBoxLayout()

        vboxh.addWidget(self.label[label]['lw_regExp'])

        addfr = QPushButton('-')
        addfr.clicked.connect(self.onRegexpRemove)
        addfr.setObjectName(label)
        addfr.setFixedWidth(24)

        remfr = QPushButton('+')
        remfr.clicked.connect(self.onRegexpAdd)
        remfr.setObjectName(label)
        remfr.setFixedWidth(24)

        vboxh.addWidget(addfr)
        vboxh.addWidget(remfr)
        vbox.addLayout(vboxh)

        gb.setLayout(vbox)
        self.layout.addWidget(gb)

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
    shortname = 'pathway_mining'

    def __init__(self, *args, **kwargs):
        super(PathwayMiningApp, self).__init__(*args, **kwargs)

        self.config.set_defaults({
            '/Data/MiningTarget': 0,
            '/Data/MiningDepth': 5,
            '/Data/MiningType': 'c',
            '/Data/MiningRelative': False,
            '/Data/MiningShared': True,
            'include_pathways': [],
            'exclude_pathways': [],
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

        self.addConfigPanel(PathwayMiningInExPathwayConfigPanel, 'Include/Exclude')
        self.addConfigPanel(PathwayMiningConfigPanel, 'Pathway Mining')


        
class PathwayMining(AnalysisPlugin):

    def __init__(self, *args, **kwargs):
        super(PathwayMining, self).__init__(*args, **kwargs)
        self.register_app_launcher(PathwayMiningApp)
