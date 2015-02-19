# -*- coding: utf-8 -*-
from __future__ import division

from collections import defaultdict

import os
from copy import copy
import numpy as np

import pathomx.ui as ui
import pathomx.db as db
import pathomx.utils as utils

from pathomx.data import DataDefinition
from pathomx.plugins import AnalysisPlugin
from pathomx.qt import *


class VolcanoConfigPanel(ui.ConfigPanel):

    def __init__(self, *args, **kwargs):
        super(VolcanoConfigPanel, self).__init__(*args, **kwargs)

        self.config.add_handler('method', self.cb_method, METHOD_TYPES)

        self.layout.addWidget(self.cb_method)

        self.finalise()


class VolcanoTool(ui.AnalysisApp):

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
