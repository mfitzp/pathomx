import os

from plugins import DataPlugin

# Import PySide classes
from PySide.QtGui import *
from PySide.QtCore import *
from PySide.QtWebKit import *
from PySide.QtNetwork import *

import data, ui

class ImportDataView( ui.dataView ):
    def __init__(self, plugin, parent, **kwargs):
        super(ImportDataView, self).__init__(plugin, parent, **kwargs)
    
        fn = self.load_data_file()
        if fn:
            self.workspace_item.setText(0, fn)
            
        self.table.setModel(self.data)

    def load_data_file(self):
        """ Open a data file"""
        filename, _ = QFileDialog.getOpenFileName(self.m, 'Open experimental metabolite data file', '')
        if filename:
            self.data = data.dataManager(filename)
            self.m.data = self.data # Pass up; temporary until handles list of data objects in memory
            # Re-translate the datafile
            self.m.data.translate(self.m.db)
            return os.path.basename(filename)
        return False

class ImportText(DataPlugin):

    def __init__(self, **kwargs):
        super(ImportText, self).__init__(**kwargs)
        self.register_app_launcher( self.app_launcher )

    def app_launcher(self):
        #self.load_data_file()
        self.instances.append( ImportDataView( self, self.m ) )