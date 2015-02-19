# -*- coding: utf-8 -*-

from pathomx.tools import BaseTool
import pathomx.ui as ui

from pathomx.plugins import VisualisationPlugin
from pathomx.data import DataDefinition


# Graph data as a bar chart
class BarTool(BaseTool):

    name = "Bar"
    notebook = 'basic_plot_category_bar.ipynb'
    shortname = 'basic_plot_category_bar'

    legacy_inputs = {'input': 'input_data'}
    legacy_outputs = {'output': 'output_data'}

    def __init__(self, *args, **kwargs):
        super(BarTool, self).__init__(*args, **kwargs)

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
class SpectraTool(BaseTool):

    name = "Spectra"
    notebook = 'basic_plot_spectra.ipynb'
    shortname = 'basic_plot_spectra'

    legacy_inputs = {'input': 'input_data'}
    legacy_outputs = {'output': 'output_data'}

    def __init__(self, *args, **kwargs):
        super(SpectraTool, self).__init__(*args, **kwargs)

        self.data.add_input('input_data')  # Add input slot        

        # Setup data consumer options
        self.data.consumer_defs.append(
            DataDefinition('input_data', {
            'labels_n': ('>0', None),
            'entities_t': (None, None),
            #'scales_t': (None, ['float']),
            })
        )


# Heatmap
class HeatmapTool(BaseTool):

    name = "Heatmap"
    notebook = 'basic_plot_heatmap.ipynb'
    shortname = 'basic_plot_heatmap'

    def __init__(self, *args, **kwargs):
        super(HeatmapTool, self).__init__(*args, **kwargs)

        self.data.add_input('input_data')  # Add input slot        

        # Setup data consumer options
        self.data.consumer_defs.append(
            DataDefinition('input_data', {
            'labels_n': ('>0', None),
            'entities_t': (None, None),
            #'scales_t': (None, ['float']),
            })
        )


# Graph a spectra
class HistogramTool(BaseTool):

    name = "Histogram"
    notebook = 'basic_plot_histogram.ipynb'
    shortname = 'basic_plot_histogram'

    legacy_inputs = {'input': 'input_data'}
    legacy_outputs = {'output': 'output_data'}

    def __init__(self, *args, **kwargs):
        super(HistogramTool, self).__init__(*args, **kwargs)

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
        self.register_app_launcher(HeatmapTool)
        self.register_app_launcher(HistogramTool)
