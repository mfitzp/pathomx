# -*- coding: utf-8 -*-
from plugins import ImportPlugin

import ui
from data import DataSet


class InputDataView( ui.DataView ):
    def __init__(self, plugin, parent, **kwargs):
        super(InputDataView, self).__init__(plugin, parent, **kwargs)

class InputData(ImportPlugin):

    def __init__(self, **kwargs):
        super(InputData, self).__init__(**kwargs)
        self.register_app_launcher( self.app_launcher )

    def app_launcher(self):
        #self.load_data_file()
        self.instances.append( InputDataView( self, self.m ) )
