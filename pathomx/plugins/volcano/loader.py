# -*- coding: utf-8 -*-
from __future__ import division

from pathomx.ui import ConfigPanel
from pathomx.tools import BaseTool

from pathomx.data import DataDefinition
from pathomx.plugins import AnalysisPlugin
from pathomx.qt import *


class VolcanoConfigPanel(ConfigPanel):

    def __init__(self, *args, **kwargs):
        super(VolcanoConfigPanel, self).__init__(*args, **kwargs)

        self.config.add_handler('method', self.cb_method, METHOD_TYPES)

        self.layout.addWidget(self.cb_method)

        self.finalise()


class VolcanoTool(BaseTool):

    name = "Volcano Plot"
    shortname = 'volcano'

    def __init__(self, *args, **kwargs):
        super(VolcanoTool, self).__init__(*args, **kwargs)

        self.data.add_input('input_data')  # Add input slot

        # Setup data consumer options
        self.data.consumer_defs.append(
            DataDefinition('input_data', {
            })
        )

        self.config.set_defaults({
            'method': 'complete',
        })

        self.addExperimentConfigPanel()


class Volcano(AnalysisPlugin):

    def __init__(self, *args, **kwargs):
        super(Volcano, self).__init__(*args, **kwargs)
        self.register_app_launcher(VolcanoTool)
