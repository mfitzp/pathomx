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
            'entities_t': (None, None),
            })
        )

        self.toolbars['bar'] = self.addToolBar('Bar')

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
class SpectraTool(ui.IPythonApp):

    name = "Spectra"
    notebook = 'basic_plot_spectra.ipynb'
    
    legacy_inputs = {'input': 'input_data'}
    legacy_outputs = {'output': 'output_data'}
    
    def __init__(self, **kwargs):
        super(SpectraTool, self).__init__(**kwargs)

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

        self.finalise()

    
class BasicGraph(VisualisationPlugin):

    def __init__(self, **kwargs):
        super(BasicGraph, self).__init__(**kwargs)
        self.register_app_launcher(BarTool)
        self.register_app_launcher(SpectraTool)
