from plugins import DataPlugin

import ui, data

class InputDataView( ui.dataView ):
    def __init__(self, plugin, parent, **kwargs):
        super(InputDataView, self).__init__(plugin, parent, **kwargs)

class InputData(DataPlugin):

    def __init__(self, **kwargs):
        super(InputData, self).__init__(**kwargs)
        self.register_app_launcher( self.app_launcher )

    def app_launcher(self):
        #self.load_data_file()
        self.instances.append( InputDataView( self, self.m ) )