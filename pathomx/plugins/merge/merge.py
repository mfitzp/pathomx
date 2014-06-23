import os
import copy
import numpy as np

import pathomx.ui as ui
import pathomx.db as db
import pathomx.utils as utils

from pathomx.data import DataSet, DataDefinition
from pathomx.utils import UnicodeReader, UnicodeWriter
from pathomx.plugins import FilterPlugin


class MergeApp(ui.IPythonApp):

    notebook = 'merge.ipynb'

    legacy_outputs = {'output': 'output_data'}

    def __init__(self, *args, **kwargs):
        super(MergeApp, self).__init__(*args, **kwargs)

        self.addDataToolBar()
        self.data.add_input('input_1')  # Add input slot
        self.data.add_input('input_2')  # Add input slot
        self.data.add_output('output_data')  # Add output slot

        # Setup data consumer options
        self.data.consumer_defs.extend([
            DataDefinition('input_1', {
            'labels_n': (None, '>0'),
            'entities_t': (None, None),
            }),
            DataDefinition('input_2', {
            'labels_n': (None, '>0'),
            'entities_t': (None, None),
            }),
            ]
        )


class Merge(FilterPlugin):

    def __init__(self, *args, **kwargs):
        super(Merge, self).__init__(*args, **kwargs)
        MergeApp.plugin = self
        self.register_app_launcher(MergeApp)
