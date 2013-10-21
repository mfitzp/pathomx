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



class NOOPView( ui.GenericView ):

    def __init__(self, plugin, parent, **kwargs):
        super(NOOPView, self).__init__(plugin, parent, **kwargs)

        self.addDataToolBar()

        self.data.add_interface('output') # Add output slot
        # We need an input filter for this type; accepting *anything*
        self.data.consumer_defs.append( 
            DataDefinition('input', {
                'labels_n': ('>0','>0')
            
            })
        )
        
        self.data.source_updated.connect( self.autogenerate ) # Auto-regenerate if the source data is modified
        self.data.consume_any_of( self.m.datasets[::-1] ) # Try consume any dataset; work backwards

        
    def generate(self):
        self.setWorkspaceStatus('active')
    
        dso = self.data.get('input')
        self.data.put('output',dso)

        self.setWorkspaceStatus('done')
        self.clearWorkspaceStatus()                


class NOOP(ProcessingPlugin):

    def __init__(self, **kwargs):
        super(NOOP, self).__init__(**kwargs)
        self.register_app_launcher( self.app_launcher )

    def app_launcher(self):
        #self.load_data_file()
        self.instances.append( NOOPView( self, self.m ) )
