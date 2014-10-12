# -*- coding: utf-8 -*-

import os

from pathomx.ui import GenericTool
from pathomx.plugins import ScriptingPlugin
from pathomx.data import DataDefinition
from pathomx.qt import *


class CustomScriptTool(GenericTool):
    def __init__(self, *args, **kwargs):
        super(CustomScriptTool, self).__init__(*args, **kwargs)

        for i in range(1, 6):
            # We need an input filter for this type; accepting *anything*
            self.data.add_input('input_%d' % i)  # Add input slot
            self.data.add_output('output_%d' % i)  # Add output slot
            self.data.consumer_defs.append(DataDefinition('input_%d' % i, {}))


class PythonScriptTool(CustomScriptTool):
    name = "Python"
    shortname = 'python_script'
    icon = 'python.png'


class RScriptTool(CustomScriptTool):
    name = "R"
    shortname = 'r_script'
    icon = 'r.png'
    language = 'r'


class MATLABScriptTool(CustomScriptTool):
    name = "MATLAB"
    shortname = 'matlab_script'
    icon = 'matlab.png'
    language = 'matlab'


class CustomScript(ScriptingPlugin):

    def __init__(self, *args, **kwargs):
        super(CustomScript, self).__init__(*args, **kwargs)
        self.register_app_launcher(PythonScriptTool)
        self.register_app_launcher(RScriptTool)
        self.register_app_launcher(MATLABScriptTool)
