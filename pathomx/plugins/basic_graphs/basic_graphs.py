# -*- coding: utf-8 -*-
import os
import copy

import numpy as np

import pathomx.ui as ui
import pathomx.db as db
import pathomx.utils as utils

from pathomx.plugins import VisualisationPlugin
from pathomx.data import DataSet, DataDefinition
from pathomx.views import D3SpectraView, D3DifferenceView, MplSpectraView, MplCategoryBarView, MplDifferenceView


# Graph data as a bar chart
class BarTool(ui.AnalysisApp):
    name = "Bar"
    notebook = 'basic_plot_category_bar.ipynb'
    legacy_inputs = {'input': 'input_data'}
    legacy_outputs = {'output': 'output_data'}

    def __init__(self, *args, **kwargs):
        super(BarTool, self).__init__(*args, **kwargs)

        self.addDataToolBar()
        self.addFigureToolBar()

        self.data.add_input('input_data')  # Add input slot
        self.data.add_output('output_data', is_public=False)  # Hidden

        # Setup data consumer options
        self.data.consumer_defs.append(
            DataDefinition('input_data', {
            'entities_t': (None, None),
            })
        )

        self.toolbars['bar'] = self.addToolBar('Bar')


# Graph a spectra
class SpectraTool(ui.IPythonApp):

    name = "Spectra"
    notebook = 'basic_plot_spectra.ipynb'

    legacy_inputs = {'input': 'input_data'}
    legacy_outputs = {'output': 'output_data'}

    def __init__(self, *args, **kwargs):
        super(SpectraTool, self).__init__(*args, **kwargs)

        self.addDataToolBar()
        self.addFigureToolBar()

        self.data.add_input('input_data')  # Add input slot        

        # Setup data consumer options
        self.data.consumer_defs.append(
            DataDefinition('input_data', {
            'labels_n': ('>0', None),
            'entities_t': (None, None),
            #'scales_t': (None, ['float']),
            })
        )

    
class BasicGraph(VisualisationPlugin):

    def __init__(self, *args, **kwargs):
        super(BasicGraph, self).__init__(*args, **kwargs)
        self.register_app_launcher(BarTool)
        self.register_app_launcher(SpectraTool)
