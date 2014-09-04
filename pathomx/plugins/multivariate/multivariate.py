# -*- coding: utf-8 -*-

from pathomx.plugins import AnalysisPlugin

from collections import defaultdict

import os
from copy import copy

import numpy as np

import pathomx.ui as ui
import pathomx.db as db
import pathomx.utils as utils

from pathomx.data import DataSet, DataDefinition
from pathomx.views import MplScatterView, MplSpectraView
from pathomx.qt import *


# Dialog box for Metabohunter search options
class PLSDAConfigPanel(ui.ConfigPanel):

    def __init__(self, *args, **kwargs):
        super(PLSDAConfigPanel, self).__init__(*args, **kwargs)
        #row = QVBoxLayout()
        #cl = QLabel('Algorithm')
        #cb = QComboBox()
        #cb.addItems( ['NIPALS','SVD'] )
        #row.addWidget(cl)
        #row.addWidget(cb)
        #self.config.add_handler('algorithm', cb)
        #self.layout.addLayout(row)

        cb = QCheckBox('Autoscale input data')
        self.config.add_handler('autoscale', cb)
        self.layout.addWidget(cb)

        row = QVBoxLayout()
        cl = QLabel('Number of components')
        cb = QSpinBox()
        cb.setRange(0, 10)
        row.addWidget(cl)
        row.addWidget(cb)
        self.config.add_handler('number_of_components', cb)
        self.layout.addLayout(row)

        self.finalise()


class PLSDATool(ui.AnalysisApp):

    name = "PLSDA"
    notebook = 'pls_da.ipynb'

    legacy_launchers = ['PLSDAPlugin.PLSDAApp']
    legacy_inputs = {'input': 'input_data'}

    def __init__(self, *args, **kwargs):
        super(PLSDATool, self).__init__(*args, **kwargs)
        # Define automatic mapping (settings will determine the route; allow manual tweaks later)

        self.addDataToolBar()
        self.addExperimentConfigPanel()
        self.addFigureToolBar()

        self.data.add_input('input_data')  # Add input slot

        self.config.set_defaults({
            'number_of_components': 2,
            'autoscale': False,
            'algorithm': 'NIPALS',
        })

        self.addConfigPanel(PLSDAConfigPanel, 'PLSDA')

        # Setup data consumer options
        self.data.consumer_defs.append(
            DataDefinition('input_data', {})
        )


# Dialog box for Metabohunter search options
class PCAConfigPanel(ui.ConfigPanel):

    def __init__(self, *args, **kwargs):
        super(PCAConfigPanel, self).__init__(*args, **kwargs)

        row = QVBoxLayout()
        cl = QLabel('Number of components')
        cb = QSpinBox()
        cb.setRange(0, 10)
        row.addWidget(cl)
        row.addWidget(cb)
        self.config.add_handler('number_of_components', cb)
        self.layout.addLayout(row)

        self.finalise()


class PCATool(ui.IPythonApp):

    name = "PCA"
    notebook = 'pca.ipynb'

    legacy_launchers = ['PCAPlugin.PCAApp']
    legacy_inputs = {'input_data': 'input_data'}

    def __init__(self, *args, **kwargs):
        super(PCATool, self).__init__(*args, **kwargs)
        # Define automatic mapping (settings will determine the route; allow manual tweaks later)

        self.addDataToolBar()
        self.addFigureToolBar()

        self.data.add_input('input_data')  # Add input slot

        self.data.add_output('scores')
        self.data.add_output('weights')

        # Setup data consumer options
        self.data.consumer_defs.append(
            DataDefinition('input_data', {
#            'labels_n':   (None,['Pathway']),
            })
        )

        self.config.set_defaults({
            'number_of_components': 2,
        })

        self.addConfigPanel(PCAConfigPanel, 'PCA')


class Multivariate(AnalysisPlugin):

    def __init__(self, *args, **kwargs):
        super(Multivariate, self).__init__(*args, **kwargs)
        self.register_app_launcher(PLSDATool)
        self.register_app_launcher(PCATool)
