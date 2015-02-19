# -*- coding: utf-8 -*-
from pathomx.tools import ExportDataTool
from pathomx.data import DataDefinition
from pathomx.plugins import ExportPlugin


class ExportDataframe(ExportDataTool):

    name = "Export dataframe"
    export_filename_filter = "Comma separated values (*.csv);;Hierarchical Data Format (*.hdf);;Pickle (*.pickle);;JavaScript Object Notation (*.json)"
    export_description = "Export data frame"
    export_type = "data"
    icon = 'export.png'

    notebook = 'export_dataframe.ipynb'
    shortname = 'export_dataframe'

    def __init__(self, *args, **kwargs):
        super(ExportDataframe, self).__init__(*args, **kwargs)

        self.config.set_defaults({
            'filename': None,
        })

        self.data.add_input('input_data')  # Add output slot

        self.data.consumer_defs.append(
            DataDefinition('input_data', {
            'labels_n': ('>0', None),
            'entities_t': (None, None),
            'scales_t': (None, ['float']),
            })
        )


class PasteToClipboard(ExportDataTool):

    name = "Export to clipboard"
    icon = 'clipboard.png'

    notebook = 'export_clipboard.ipynb'
    shortname = 'export_clipboard'

    def __init__(self, *args, **kwargs):
        super(PasteToClipboard, self).__init__(*args, **kwargs)
        self.data.add_input('input_data')  # Add output slot

        self.data.consumer_defs.append(
            DataDefinition('input_data', {
            'labels_n': ('>0', None),
            'entities_t': (None, None),
            'scales_t': (None, ['float']),
            })
        )

    def addExportDataToolbar(self):
        pass

    def onExportData(self):
        pass


class Export(ExportPlugin):

    def __init__(self, *args, **kwargs):
        super(Export, self).__init__(*args, **kwargs)
        self.register_app_launcher(ExportDataframe)
        self.register_app_launcher(PasteToClipboard)
