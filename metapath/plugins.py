# Import PyQt5 classes
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWebKit import *
from PyQt5.QtNetwork import *
from PyQt5.QtWidgets import *
from PyQt5.QtWebKitWidgets import *
from PyQt5.QtPrintSupport import *

# Yapsy classes
from yapsy.IPlugin import IPlugin
from yapsy.PluginManager import PluginManagerSingleton

# wheezy templating engine
from wheezy.template.engine import Engine
from wheezy.template.ext.core import CoreExtension
from wheezy.template.ext.code import CodeExtension
from wheezy.template.loader import FileLoader


import os, inspect
import utils

class BasePlugin(IPlugin):

    def __init__(self, **kwargs):
        super(BasePlugin, self).__init__()

        # Pass in reference to the main window
        manager = PluginManagerSingleton.get()
        self.m = manager.m
        self.instances = []
        self.id = self.__module__
        self.name = "%s %s " % (self.default_workspace_category, "Plugin")
        
        self.path = os.path.dirname( inspect.getfile(self.__class__) )
        
        # Plugin personal template engine
        self.templateEngine = Engine(
            loader=FileLoader( [self.path, os.path.join( utils.scriptdir,'html')] ),
            extensions=[CoreExtension(),CodeExtension()]
        )
        
        help_path = os.path.join( self.path, 'readme.html' )
        if os.path.exists( help_path ):
            self.help_tab_html_filename = 'readme.html'
        else:
            self.help_tab_html_filename = None
        
        

    @property
    def icon(self):
        icon_path = os.path.join( self.path, 'icon.png' )
        if os.path.exists( icon_path ):
            return QIcon( icon_path )
        else:
            return None

    @property
    def workspace_icon(self):
        icon_path = os.path.join( self.path, 'icon-16.png' )
        if os.path.exists( icon_path ):
            return QIcon( icon_path )
        else:
            return None
                       

                    
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

class IdentificationPlugin(BasePlugin):
    default_workspace_category = 'Identification'
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
