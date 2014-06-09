# -*- coding: utf-8 -*-


# Import PyQt5 classes
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWebKit import *
from PyQt5.QtNetwork import *
from PyQt5.QtWidgets import *
from PyQt5.QtPrintSupport import *
import os
import copy

from pathomx.plugins import ProcessingPlugin

import numpy as np
import nmrglue as ng

import pathomx.ui as ui
import pathomx.db as db
import pathomx.threads as threads
import pathomx.utils as utils

from pathomx.data import DataSet, DataDefinition
from pathomx.views import MplSpectraView, MplDifferenceView
from pathomx.qt import *


# Dialog box for Metabohunter search options
class SpectraNormConfigPanel(ui.ConfigPanel):

    def __init__(self, *args, **kwargs):
        super(SpectraNormConfigPanel, self).__init__(*args, **kwargs)

        self.algorithm_cb = QComboBox()
        self.algorithm_cb.addItems(self.v.algorithms)
        self.config.add_handler('algorithm', self.algorithm_cb)

        tl = QLabel('Scaling algorithm')
        tl.setIndent(5)
        self.layout.addWidget(tl)
        self.layout.addWidget(self.algorithm_cb)

        self.finalise()


class SpectraNormApp(ui.IPythonApp):

    name = "Spectra normalisation"
    notebook = 'spectra_norm.ipynb'
    
    algorithms = ['PQN','TSA']

    legacy_inputs = {'input': 'input_data'}
    legacy_outputs = {'output': 'output_data'}

    def __init__(self, **kwargs):
        super(SpectraNormApp, self).__init__(**kwargs)

        self.addDataToolBar()
        self.addFigureToolBar()

        self.data.add_input('input_data')  # Add input slot
        self.data.add_output('output_data')

        # Setup data consumer options
        self.data.consumer_defs.append(
            DataDefinition('input_data', {
            'labels_n': ('>0', None),
            'entities_t': (None, None),
            'scales_t': (None, ['float']),
            })
        )

        self.config.set_defaults({
            'algorithm': 'PQN',
        })

        self.addConfigPanel(SpectraNormConfigPanel, 'Settings')

        self.finalise()



 
class SpectraNorm(ProcessingPlugin):

    def __init__(self, **kwargs):
        super(SpectraNorm, self).__init__(**kwargs)
        SpectraNormApp.plugin = self
        self.register_app_launcher(SpectraNormApp)
