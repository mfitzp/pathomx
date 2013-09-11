# Import PySide classes
from PySide.QtGui import *
from PySide.QtCore import *
from PySide.QtWebKit import *
from PySide.QtNetwork import *

# Yapsy classes

from yapsy.IPlugin import IPlugin
from yapsy.PluginManager import PluginManagerSingleton

import os

class BasePlugin(IPlugin):

    def __init__(self, **kwargs):
        super(BasePlugin, self).__init__()

        # Pass in reference to the main window
        manager = PluginManagerSingleton.get()
        self.m = manager.m
        self.instances = []
        self.id = self.__module__
                
    def register_app_launcher(self, app_launcher):
        self.m.app_launchers[ self.id ] = app_launcher

    def register_url_handler(self, identifier, url_handler):
        self.m.url_handlers[ identifier ] = url_handler

    def register_menus(self, menu, entries):
        
        for entry in entries:
            if entry == None:
                self.m.menuBar[ menu ].addSeparator()
            else:            
                menuAction = QAction(entry['title'], self.m)
                if 'status' in entry:
                    menuAction.setStatusTip( entry['status'] )
                menuAction.triggered.connect( entry['action'] )
                self.m.menuBar[ menu ].addAction( menuAction )

class DataPlugin(BasePlugin):
    default_workspace_category = 'Data'
    pass

class ProcessingPlugin(BasePlugin):
    default_workspace_category = 'Processing'
    pass

class AssignmentPlugin(BasePlugin):
    default_workspace_category = 'Assignment'
    pass

class AnalysisPlugin(BasePlugin):
    default_workspace_category = 'Analysis'
    pass

class VisualisationPlugin(BasePlugin):
    default_workspace_category = 'Visualisation'
    pass

class OutputPlugin(BasePlugin):
    default_workspace_category = 'Output'
    pass

class MiscPlugin(BasePlugin):
    default_workspace_category = 'Misc'
    pass
