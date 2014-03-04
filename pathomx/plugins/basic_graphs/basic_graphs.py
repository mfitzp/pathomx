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

import numpy as np

import pathomx.ui as ui
import pathomx.db as db
import pathomx.utils as utils
import pathomx.threads as threads

from pathomx.plugins import VisualisationPlugin
from pathomx.data import DataSet, DataDefinition
from pathomx.views import D3SpectraView, D3DifferenceView, MplSpectraView, MplDifferenceView


# Graph data as a bar chart
class BarTool(ui.AnalysisApp):
    name = "Bar"

    def __init__(self, **kwargs):
        super(BarTool, self).__init__(**kwargs)

        self.addDataToolBar()
        self.addFigureToolBar()

        self.data.add_input('input')  # Add input slot
        self.data.add_output('output', is_public=False)  # Hidden

        self.views.addView(MplCategoryBarView(self), 'View')

        # Setup data consumer options
        self.data.consumer_defs.append(
            DataDefinition('input', {
            'entities_t': (None, ['Compound']),
            })
        )

        t = self.addToolBar('Bar')
        self.toolbars['bar'] = t

        self.finalise()

    def generate(self, input=None):
        return {'dso': self.data.get('input')}

    def prerender(self, dso=None):
        dso_mean = dso.as_summary(fn=np.mean, dim=0, match_attribs=['classes'])  # Get mean dataset/ Classes only
        dso_std = dso.as_summary(fn=np.std, dim=0, match_attribs=['classes'])  # Get std_dev/ Classes only

        dso = dso_mean
        dso.statistics['error']['stddev'] = dso_std.data

        return {'View': {'dso': dso}}


# Graph a spectra
class SpectraTool(ui.DataApp):
    name = "Spectra"

    def __init__(self, **kwargs):
        super(SpectraTool, self).__init__(**kwargs)

        self.addDataToolBar()
        self.addFigureToolBar()

        self.data.add_input('input')  # Add input slot        

        self.views.addTab(MplSpectraView(self), 'View')

        # Setup data consumer options
        self.data.consumer_defs.append(
            DataDefinition('input', {
            'labels_n': ('>1', None),
            'entities_t': (None, None),
            'scales_t': (None, ['float']),
            })
        )

        self.finalise()

    def generate(self, input=None):
        return {'input': input}

    def prerender(self, input=None):
        return {
            'View': {'dso': input},
            }

    
class Spectra(VisualisationPlugin):

    def __init__(self, **kwargs):
        super(Spectra, self).__init__(**kwargs)
        self.register_app_launcher(BarTool)
        self.register_app_launcher(SpectraTool)
