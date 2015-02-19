# -*- coding: utf-8 -*-

import os

from pathomx.tools import BaseTool
from pathomx.plugins import FilterPlugin
from pathomx.data import DataDefinition


class NOOPApp(BaseTool):

    name = "NOOP"
    notebook = 'noop.ipynb'
    shortname = 'noop'

    legacy_launchers = ['NOOP.NOOPApp']
    legacy_inputs = {'input': 'input_data'}
    legacy_outputs = {'output': 'output_data'}

    def __init__(self, *args, **kwargs):
        super(NOOPApp, self).__init__(*args, **kwargs)

        self.data.add_input('input_data')  # Add input slot
        self.data.add_output('output_data')  # Add output slot
        # We need an input filter for this type; accepting *anything*
        self.data.consumer_defs.append(
            DataDefinition('input_data', {
                'labels_n': ('>0', '>0')
            
            })
        )


class NOOP(FilterPlugin):

    def __init__(self, *args, **kwargs):
        super(NOOP, self).__init__(*args, **kwargs)
        NOOPApp.plugin = self
        self.register_app_launcher(NOOPApp)
