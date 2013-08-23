# Import PySide classes
from PySide.QtGui import *
from PySide.QtCore import *
from PySide.QtWebKit import *
from PySide.QtNetwork import *

# Yapsy classes

from yapsy.IPlugin import IPlugin
from yapsy.PluginManager import PluginManagerSingleton


class BasePlugin(IPlugin):

    def __init__(self, **kwargs):
        super(BasePlugin, self).__init__()

        # Pass in reference to the main window
        manager = PluginManagerSingleton.get()
        self.m = manager.m

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


class InputPlugin(BasePlugin):
    pass

class ProcessingPlugin(BasePlugin):
    pass

class AnalysisPlugin(BasePlugin):
    pass

class VisualisationPlugin(BasePlugin):
    pass

class OutputPlugin(BasePlugin):
    pass

class MiscPlugin(BasePlugin):
    pass
