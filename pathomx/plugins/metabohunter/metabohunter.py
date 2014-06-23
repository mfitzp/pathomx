# -*- coding: utf-8 -*-


# Renderer for GPML as SVG
from gpml2svg import gpml2svg

import os
import sys
import re
import math
import logging

import pathomx.ui as ui
import pathomx.utils as utils

from pathomx.plugins import IdentificationPlugin
from pathomx.data import DataSet, DataDefinition
from pathomx.views import MplSpectraView
from pathomx.qt import *

from collections import OrderedDict

import csv
import poster
#import urllib, urllib2, cookielib
import requests


# Dialog box for Metabohunter search options
class MetaboHunterConfigPanel(ui.ConfigPanel):

    options = {
    'Metabotype': {
        'All': 'All',
        'Drug': 'Drug',
        'Food additive': 'Food additive',
        'Mammalian': 'Mammalian',
        'Microbial': 'Microbial',
        'Plant': 'Plant',
        'Synthetic/Industrial chemical': 'Synthetic/Industrial chemical',
        },
    'Database Source': {
        'Human Metabolome Database (HMDB)': 'HMDB',
        'Madison Metabolomics Consortium Database (MMCD)': 'MMCD',
        },
    'Sample pH': {
        '10.00 - 10.99': 'ph7',
        '7.00 - 9.99': 'ph7',
        '6.00 - 6.99': 'ph6',
        '5.00 - 5.99': 'ph5',
        '4.00 - 4.99': 'ph4',
        '3.00 - 3.99': 'ph3',
    },
    'Solvent': {
        'All': 'all',
        'Water': 'water',
        'CDCl3': 'cdcl3',
        'CD3OD': '5d3od',
        '5% DMSO': '5dmso',
    },
    'Frequency': {
        'All': 'all',
        '600 MHz': '600',
        '500 MHz': '500',
        '400 MHz': '400',
    },
    'Method': {
        'MH1: Highest number of matched peaks': 'HighestNumber',
        'MH2: Highest number of matched peaks with shift tolerance': 'HighestNumberNeighbourhood',
        'MH3: Greedy selection of metabolites with disjoint peaks': 'Greedy2',
        'MH4: Highest number of matched peaks with intensities': 'HighestNumberHeights',
        'MH5: Greedy selection of metabolites with disjoint peaks and heights': 'Greedy2Heights',
    },
    }

    def __init__(self, *args, **kwargs):
        super(MetaboHunterConfigPanel, self).__init__(*args, **kwargs)

        self.lw_combos = {}

        for o in ['Metabotype', 'Database Source', 'Sample pH', 'Solvent', 'Frequency', 'Method']:
            row = QVBoxLayout()
            cl = QLabel(o)
            cb = QComboBox()

            cb.addItems(list(self.options[o].keys()))
            row.addWidget(cl)
            row.addWidget(cb)
            self.config.add_handler(o, cb, self.options[o])

            self.layout.addLayout(row)

        row = QGridLayout()
        self.lw_spin = {}
        for n, o in enumerate(['Noise Threshold', 'Confidence Threshold', 'Tolerance']):
            cl = QLabel(o)
            cb = QDoubleSpinBox()
            cb.setDecimals(2)
            cb.setRange(0, 0.5)
            cb.setSingleStep(0.01)
            cb.setValue(float(self.config.get(o)))
            row.addWidget(cl, 0, n)
            row.addWidget(cb, 1, n)

            self.config.add_handler(o, cb)

        self.layout.addLayout(row)

        self.finalise()


class MetaboHunterApp(ui.IPythonApp):

    name = "MetaboHunter"
    legacy_inputs = {'input': 'input_data'}
    legacy_outputs = {'output': 'output_data'}

    notebook = "metabohunter.ipynb"

    def __init__(self, *args, **kwargs):
        super(MetaboHunterApp, self).__init__(*args, **kwargs)
        #Define automatic mapping (settings will determine the route; allow manual tweaks later)

        self.addDataToolBar(default_pause_analysis=True)
        self.addFigureToolBar()

        self.data.add_input('input_data')  # Add input slot
        self.data.add_output('output_data')

        self.config.set_defaults({
            'Metabotype': 'All',
            'Database Source': 'HMDB',
            'Sample pH': 'ph7',
            'Solvent': 'water',
            'Frequency': 'all',
            'Method': 'HighestNumberNeighbourhood',
            'Noise Threshold': 0.0,
            'Confidence Threshold': 0.4,
            'Tolerance': 0.1,
        })

        self.addConfigPanel(MetaboHunterConfigPanel, 'MetaboHunter')

        # Setup data consumer options
        self.data.consumer_defs.append(
            DataDefinition('input_data', {
            'scales_t': (None, ['float']),
            'entities_t': (None, None),
            })
        )


class MetaboHunter(IdentificationPlugin):

    def __init__(self, *args, **kwargs):
        super(MetaboHunter, self).__init__(*args, **kwargs)
        MetaboHunterApp.plugin = self
        self.register_app_launcher(MetaboHunterApp)
