# -*- coding: utf-8 -*-


#import nmrglue as ng

import csv
import os
import pprint
import xml.etree.cElementTree as et
from collections import defaultdict

import numpy as np
import scipy as sp

import pathomx.ui as ui
import pathomx.db as db
import pathomx.utils as utils

from pathomx.data import DataSet
from pathomx.plugins import ImportPlugin
from pathomx.qt import *

import nmrglue as ng


class BrukerImport(ui.ImportDataApp):

    notebook = 'bruker_import.ipynb'
    legacy_launchers = ['NMRGlue.NMRApp']
    legacy_outputs = {'output': 'output_data'}
    icon = 'bruker.png'

    def __init__(self, *args, **kwargs):
        super(BrukerImport, self).__init__(*args, **kwargs)

        self.config.set_defaults({
            'filename': None,
        })

        self.data.add_output('output_data')  # Add output slot        
        self.data.add_output('output_dic')  # Add output slot        

    def addImportDataToolbar(self):
        t = self.getCreatedToolbar('External Data', 'external-data')

        import_dataAction = QAction(QIcon(os.path.join(self.plugin.path, 'bruker.png')), 'Import spectra from Bruker spectra\u2026', self.w)
        import_dataAction.setStatusTip('Import spectra from Bruker format')
        import_dataAction.triggered.connect(self.onImportBruker)
        t.addAction(import_dataAction)

    def onImportBruker(self):
        """ Open a data file"""
        Qd = QFileDialog()
        Qd.setFileMode(QFileDialog.Directory)
        Qd.setOption(QFileDialog.ShowDirsOnly)

        folder = Qd.getExistingDirectory(self.w, 'Open parent folder for your Bruker NMR experiments')
        if folder:
            self.config.set('filename', folder)
            self.config.set('datatype', 'bruker')
            self.autogenerate()


class BrukerExport(ui.ExportDataApp):

    name = "Export Bruker"
    export_description = "Export Bruker fid format spectra"
    export_type = "data"

    notebook = 'bruker_export.ipynb'
    icon = 'bruker.png'


    def __init__(self, *args, **kwargs):
        super(BrukerExport, self).__init__(*args, **kwargs)

        self.config.set_defaults({
            'filename': None,
        })

        self.data.add_input('input_data')
        self.data.add_input('dic_list')

    def addExportDataToolbar(self):
        t = self.getCreatedToolbar('External Data', 'external-data')

        export_dataAction = QAction(QIcon(os.path.join(self.plugin.path, 'bruker.png')), 'Export spectra in Bruker format\u2026', self.w)
        export_dataAction.setStatusTip('Export spectra in Bruker format')
        export_dataAction.triggered.connect(self.onExportBruker)
        t.addAction(export_dataAction)

    def onExportBruker(self):
        """ Open a data file"""
        Qd = QFileDialog()
        Qd.setFileMode(QFileDialog.Directory)
        Qd.setOption(QFileDialog.ShowDirsOnly)

        folder = Qd.getExistingDirectory(self.w, 'Open parent folder for your Bruker NMR experiments')
        if folder:
            self.config.set('filename', folder)
            self.autogenerate()



class NMRGlue(ImportPlugin):

    def __init__(self, *args, **kwargs):
        super(NMRGlue, self).__init__(*args, **kwargs)
        self.register_app_launcher(BrukerImport)
        self.register_app_launcher(BrukerExport)
