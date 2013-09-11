# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# Import PySide classes
from PySide.QtGui import *
from PySide.QtCore import *
from PySide.QtWebKit import *
from PySide.QtNetwork import *

# Renderer for GPML as SVG
from gpml2svg import gpml2svg


from plugins import VisualisationPlugin

import os
import ui, utils




# Class for data visualisations using GPML formatted pathways


# Class for data visualisations using GPML formatted pathways
# Supports loading from local file and WikiPathways
class DynamicView(ui.analysisView):
    def __init__(self, plugin, parent, gpml=None, svg=None, **kwargs):
        super(DynamicView, self).__init__(parent, **kwargs)

        self.plugin = plugin
        self.m = parent
        self.gpml = gpml # Source GPML file
        self.svg = svg # Rendered GPML file as SVG
        self.metadata = {}

        load_layoutAction = QAction(QIcon.fromTheme("gpml-open", QIcon( os.path.join( utils.scriptdir,'icons','document-open-gpml.png') )), 'Load layout from KEGG or GPML file for layout\u2026', self.m)
        load_layoutAction.setStatusTip('Load a layout in KEGG or GPML format')
        load_layoutAction.triggered.connect(self.onLoadLayout)
        
        self.w = QMainWindow()
        t = self.w.addToolBar('GPML')
        t.setIconSize( QSize(16,16) )
        t.addAction(load_gpmlAction)
        t.addAction(load_wikipathwaysAction)
        self.w.setCentralWidget(self.browser)
         
        #self.o.show() 
        self.tab_index = self.m.tabs.addTab( self.w, 'WikiPathways') #gpmlpathway.metadata['Name'] )
        self.m.tabs.setCurrentIndex( self.tab_index )
        
        self.plugin.register_url_handler( self.id, i.url_handler )

   



class Dynamic(VisualisationPlugin):

    id = 'dynamic'

    def __init__(self, **kwargs):
        super(Dynamic, self).__init__(**kwargs)
        #self.register_url_handler( self.id, self.url_handler )
        #self.register_menus( 'pathways', [
        #    {'title': u'&Load GPML pathway\u2026', 'action': self.onLoadGPMLPathway, 'status': 'Load a GPML pathway file'},
        #    {'title': u'&Load GPML pathway via WikiPathways\u2026', 'action': self.onLoadGPMLPathway, 'status': 'Load a GPML pathway from WikiPathways service'},        
        #] )
        self.register_app_launcher( self.app_launcher )
    
    # Create a new instance of the plugin viewer object to handle all behaviours
    def app_launcher(self):
        self.instances.append( DynamicView( self, self.m ) )
