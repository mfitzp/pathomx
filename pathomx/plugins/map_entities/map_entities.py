# -*- coding: utf-8 -*-
#from __future__ import unicode_literals

import os
import copy

import numpy as np

import pathomx.ui as ui
import pathomx.db as db
import pathomx.utils as utils

from pathomx.data import DataSet, DataDefinition
from pathomx.views import TableView
from pathomx.utils import UnicodeReader, UnicodeWriter
from pathomx.plugins import IdentificationPlugin
from pathomx.qt import *

TYPE_COLORS = {
    'compound': '#e2ebf5',
    'secondary': '#e2ebf5',
    'gene': '#e7f9d5',
    'protein': '#fefadb',
    }
#    729fcf, 8ae234, fce94f

MAP_TYPE_TABLE = [
    'Any',
    'Gene',
    'Protein',
    'Compound',
    # ------
    'BiGG',
    'BioPath',
    'BRENDA',
    'FIMA',
    'HMDB',
    'KEGG',
    'LIPID MAPS',
    'SEED',
    'UPA',
]


def legacy_map_fwd(x):
    if x in [0, 1, 2, 3]:
        return MAP_TYPE_TABLE[x]
    else:
        return x


def legacy_map_rev(x):
    return x


# Dialog box for Metabohunter search options
class MapEntityConfigPanel(ui.ConfigPanel):

    def __init__(self, *args, **kwargs):
        super(MapEntityConfigPanel, self).__init__(*args, **kwargs)

        self.cb_mapping_type = QComboBox()
        self.cb_mapping_type.addItems(MAP_TYPE_TABLE)
        self.cb_mapping_type.insertSeparator(4)

        self.config.add_handler('map_object_type', self.cb_mapping_type, (legacy_map_fwd, legacy_map_rev))

        self.layout.addWidget(self.cb_mapping_type)

        self.finalise()


class MapEntityApp(ui.IPythonApp):

    name = "Map to Biocyc"
    notebook = 'map_to_biocyc.ipynb'
    legacy_inputs = {'input': 'input_data'}
    legacy_outputs = {'output': 'output_data'}

    def __init__(self, *args, **kwargs):
        super(MapEntityApp, self).__init__(*args, **kwargs)
        # Define automatic mapping (settings will determine the route; allow manual tweaks later)

        self.addDataToolBar()
        self.addFigureToolBar()
        self.data.add_input('input_data')  # Add input slot
        self.data.add_output('output_data')

        t = self.getCreatedToolbar('Entity mapping', 'external-data')

        import_dataAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'disk--arrow.png')), 'Load annotations from file\\u2026', self.w)
        import_dataAction.setStatusTip('Load annotations from .csv. file')
        import_dataAction.triggered.connect(self.onImportEntities)
        t.addAction(import_dataAction)

        self.addExternalDataToolbar()  # Add standard source data options

        self.config.set_defaults({
            'map_object_type': 'Any',
        })

        self._entity_mapping_table = {}

        # Setup data consumer options
        self.data.consumer_defs.append(
            DataDefinition('input_data', {
            'labels_n': (None, '>0'),
            'entities_t': (None, None),
            })
        )

        self.addConfigPanel(MapEntityConfigPanel, 'Mapping')

    def onImportEntities(self):
        """ Open a data file"""
        filename, _ = QFileDialog.getOpenFileName(self.w, 'Load entity mapping from file', 'Load CSV mapping for name <> identity', "All compatible files (*.csv);;Comma Separated Values (*.csv);;All files (*.*)")
        if filename:
            self.load_datafile(filename)


class MapEntity(IdentificationPlugin):

    def __init__(self, *args, **kwargs):
        super(MapEntity, self).__init__(*args, **kwargs)
        #MapEntityApp.plugin = self
        self.register_app_launcher(MapEntityApp)
