# -*- coding: utf-8 -*-

import os

import pathomx.ui as ui
from pathomx.plugins import ProcessingPlugin
from pathomx.data import DataSet, DataDefinition
from pathomx.qt import *


class NOOPApp(ui.GenericApp):

    def __init__(self, **kwargs):
        super(NOOPApp, self).__init__(**kwargs)

        self.addDataToolBar()

        self.data.add_input('input')  # Add input slot
        self.data.add_output('output')  # Add output slot
        # We need an input filter for this type; accepting *anything*
        self.data.consumer_defs.append(
            DataDefinition('input', {
                'labels_n': ('>0', '>0')
            
            })
        )

        self.finalise()

    def generate(self, input=None):
        return {'output': input}


class NOOP(ProcessingPlugin):

    def __init__(self, **kwargs):
        super(NOOP, self).__init__(**kwargs)
        NOOPApp.plugin = self
        self.register_app_launcher(NOOPApp)
