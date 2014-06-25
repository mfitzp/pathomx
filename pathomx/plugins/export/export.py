# -*- coding: utf-8 -*-

import os
import csv
import xml.etree.cElementTree as et
from collections import defaultdict

import numpy as np
import zipfile
import tempfile

import pathomx.ui as ui
import pathomx.db as db
import pathomx.utils as utils

from pathomx.data import DataDefinition
from pathomx.plugins import ExportPlugin
from pathomx.qt import *


class ExportDataframe(ui.ExportDataApp):

    name = "Export dataframe"
    export_filename_filter = "Comma separated values (*.csv);;Hierarchical Data Format (*.hdf);;Pickle (*.pickle);;JavaScript Object Notation (*.json)"
    export_description = "Export data frame"
    icon = 'export.png'

    notebook = 'export_dataframe.ipynb'

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



class PasteToClipboard(ui.ExportDataApp):

    name = "Paste to clipboard"
    notebook = 'export_clipboard.ipynb'
    icon = 'clipboard.png'

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
