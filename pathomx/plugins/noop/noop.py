# -*- coding: utf-8 -*-

import os

from plugins import ProcessingPlugin

# Import PyQt5 classes
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWebKit import *
from PyQt5.QtNetwork import *
from PyQt5.QtWidgets import *
from PyQt5.QtWebKitWidgets import *
from PyQt5.QtPrintSupport import *

import ui
from data import DataSet, DataDefinition


class NOOPApp( ui.GenericApp ):

    def __init__(self, **kwargs):
        super(NOOPApp, self).__init__(**kwargs)

        self.addDataToolBar()

        self.data.add_input('input') # Add input slot
        self.data.add_output('output') # Add output slot
        # We need an input filter for this type; accepting *anything*
        self.data.consumer_defs.append( 
            DataDefinition('input', {
                'labels_n': ('>0','>0')
            
            })
        )
        
        self.finalise()
          
    def generate(self, input=None):
        return {'output':input}

class NOOP(ProcessingPlugin):

    def __init__(self, **kwargs):
        super(NOOP, self).__init__(**kwargs)
        NOOPApp.plugin = self
        self.register_app_launcher( NOOPApp )
