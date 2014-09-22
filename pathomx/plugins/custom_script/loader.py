# -*- coding: utf-8 -*-

import os

from pathomx.ui import GenericTool
from pathomx.plugins import FilterPlugin
from pathomx.data import DataDefinition
from pathomx.qt import *


class CustomScriptTool(GenericTool):

    name = "Script"
    shortname = 'custom_script'

    def __init__(self, *args, **kwargs):
        super(CustomScriptTool, self).__init__(*args, **kwargs)

        for i in range(1,6):
            # We need an input filter for this type; accepting *anything*
            self.data.add_input('input_%d' % i)  # Add input slot
            self.data.add_output('output_%d' %i)  # Add output slot
            self.data.consumer_defs.append( DataDefinition('input_%d' % i, {}) )


class CustomScript(FilterPlugin):

    def __init__(self, *args, **kwargs):
        super(CustomScript, self).__init__(*args, **kwargs)
        self.register_app_launcher(CustomScriptTool)
