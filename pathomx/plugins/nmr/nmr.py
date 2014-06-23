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


class NMRApp(ui.ImportDataApp):

    notebook = 'nmr_import.ipynb'
    legacy_outputs = {'output': 'output_data'}

    def __init__(self, *args, **kwargs):
        super(NMRApp, self).__init__(*args, **kwargs)

        self.config.set_defaults({
            'datatype': 'bruker',
            'filename': None,
        })

        self.data.add_output('output_data')  # Add output slot        

    def addImportDataToolbar(self):
        t = self.getCreatedToolbar('External Data', 'external-data')

        import_dataAction = QAction(QIcon(os.path.join(self.plugin.path, 'bruker.png')), 'Import spectra from Bruker spectra\u2026', self.m)
        import_dataAction.setStatusTip('Import spectra from Bruker format')
        import_dataAction.triggered.connect(self.onImportBruker)
        t.addAction(import_dataAction)
        #self.addExternalDataToolbar()

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


class NMRGlue(ImportPlugin):

    def __init__(self, *args, **kwargs):
        super(NMRGlue, self).__init__(*args, **kwargs)
        self.register_app_launcher(NMRApp)
