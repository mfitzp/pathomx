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
        self.algorithm_cb.addItems([k for k, v in list(self.v.algorithms.items())])
        self.config.add_handler('algorithm', self.algorithm_cb)

        tl = QLabel('Scaling algorithm')
        tl.setIndent(5)
        self.layout.addWidget(tl)
        self.layout.addWidget(self.algorithm_cb)

        self.finalise()


class SpectraNormApp(ui.DataApp):
    def __init__(self, **kwargs):
        super(SpectraNormApp, self).__init__(**kwargs)

        self.addDataToolBar()
        self.addFigureToolBar()

        self.data.add_input('input')  # Add input slot
        self.data.add_output('output')
        self.table.setModel(self.data.o['output'].as_table)

        self.views.addView(MplSpectraView(self), 'View')
        self.views.addView(MplDifferenceView(self), 'Difference')

        # Setup data consumer options
        self.data.consumer_defs.append(
            DataDefinition('input', {
            'labels_n': ('>1', None),
            'entities_t': (None, None),
            'scales_t': (None, ['float']),
            })
        )

        th = self.addToolBar('Spectra normalisation')

        self.algorithms = {
            'PQN': self.pqn,
            'TSA': self.tsa,
        }

        self.config.set_defaults({
            'algorithm': 'PQN',
        })

        self.addConfigPanel(SpectraNormConfigPanel, 'Settings')

        self.finalise()

    def generate(self, input=None):
        return {'output': self.normalise(input),
                'input': input}

    def prerender(self, input=None, output=None):
        return {'View': {'dso': output},
                'Difference': {'dso_a': input, 'dso_b': output},
                }

    def tsa(self, data):
        # Abs the data (so account for negative peaks also)
        data_a = np.abs(data)
        # Sum each spectra (TSA)
        data_as = np.sum(data_a, axis=1)
        # Identify median
        median_s = np.median(data_as)
        # Scale others to match (*(median/row))
        scaling = median_s / data_as
        # Scale the spectra
        return data * scaling.reshape(-1, 1)

    def pqn(self, data):  # 10.1021/ac051632c
        # Perform TSA normalization
        data = self.tsa(data)
        # Calculate median spectrum (median of each variable)
        median_s = np.median(data, axis=0)
        # For each variable of each spectrum, calculate ratio between median spectrum variable and that of the considered spectrum
        spectra_r = median_s / np.abs(data)
        # Take the median of these scaling factors and apply to the entire considered spectrum
        return data * np.median(spectra_r, axis=1).reshape(-1, 1)

    # Normalise using scaling method
    def normalise(self, dso):
        # Generate bin values for range start_scale to end_scale
        # Calculate the number of bins at binsize across range
        dso.data = self.algorithms[self.config.get('algorithm')](dso.data)
        # -- optionally use the line widths and take max within each of these for each spectra (peak shiftiness)
        # Filter the original data with those locations and output\
        print dso.data
        return dso

 
class SpectraNorm(ProcessingPlugin):

    def __init__(self, **kwargs):
        super(SpectraNorm, self).__init__(**kwargs)
        SpectraNormApp.plugin = self
        self.register_app_launcher(SpectraNormApp)
