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

from pathomx.plugins import ImportPlugin
from pathomx.qt import *

import nmrglue as ng



# Dialog box for Metabohunter search options
class BrukerImportConfigPanel(ui.ConfigPanel):

    autophase_algorithms = {
        'None': False,
        'Peak minima': 'Peak_minima',
        'ACME': 'ACME',
    }

    def __init__(self, parent, *args, **kwargs):
        super(BrukerImportConfigPanel, self).__init__(parent, *args, **kwargs)

        self.v = parent
        self.config = parent.config
        gb = QGroupBox('Parent folder')
        grid = QGridLayout()
        self.filename = ui.QFolderLineEdit(description = 'Import spectra from Bruker format files')
        grid.addWidget(QLabel('Path'), 0, 0)
        grid.addWidget(self.filename, 0, 1)
        self.config.add_handler('filename', self.filename)
        gb.setLayout(grid)
        self.layout.addWidget(gb)
        
        gb = QGroupBox('Phase correction')
        grid = QGridLayout()

        self.cb_phasealg = QComboBox()
        self.cb_phasealg.addItems(self.autophase_algorithms.keys())
        grid.addWidget(QLabel('Algorithm'), 2, 0)
        grid.addWidget(self.cb_phasealg, 2, 1)
        self.config.add_handler('autophase_algorithm', self.cb_phasealg, self.autophase_algorithms)

        gb.setLayout(grid)
        self.layout.addWidget(gb)

        gb = QGroupBox('Advanced')
        grid = QGridLayout()
        self.cb_delimag = QCheckBox()
        grid.addWidget(QLabel('Delete imaginaries'), 0, 0)
        grid.addWidget(self.cb_delimag, 0, 1)
        self.config.add_handler('delete_imaginaries', self.cb_delimag)

        self.cb_reverse = QCheckBox()
        grid.addWidget(QLabel('Reverse spectra'), 1, 0)
        grid.addWidget(self.cb_reverse, 1, 1)
        self.config.add_handler('reverse_spectra', self.cb_reverse)

        self.cb_remdf = QCheckBox()
        grid.addWidget(QLabel('Remove digital filter'), 2, 0)
        grid.addWidget(self.cb_remdf, 2, 1)
        self.config.add_handler('remove_digital_filter', self.cb_remdf)

        self.cb_zf = QCheckBox()
        grid.addWidget(QLabel('Zero fill'), 3, 0)
        grid.addWidget(self.cb_zf, 3, 1)
        self.config.add_handler('zero_fill', self.cb_zf)

        self.le_zf_to = QLineEdit()
        grid.addWidget(self.le_zf_to, 4, 1)
        self.config.add_handler('zero_fill_to', self.le_zf_to, mapper=(lambda x: int(x), lambda x: str(x) ))

        gb.setLayout(grid)

        self.layout.addWidget(gb)

        self.finalise()


class BrukerImport(ui.GenericTool):

    name = "Import Bruker"
    shortname = 'bruker_import'
    autoconfig_name = "{filename}"
    
    legacy_launchers = ['NMRGlue.NMRApp']
    legacy_outputs = {'output': 'output_data'}
    icon = 'bruker.png'

    def __init__(self, *args, **kwargs):
        super(BrukerImport, self).__init__(*args, **kwargs)

        self.config.set_defaults({
            'filename': None,
            'autophase_algorithm': 'Peak_minima',
            'remove_digital_filter': True,
            'delete_imaginaries': True,
            'reverse_spectra': True,
            'zero_fill': True,
            'zero_fill_to': 32768,
        })

        self.addConfigPanel(BrukerImportConfigPanel, 'Settings')

        self.data.add_output('output_data')  # Add output slot        
        self.data.add_output('output_dic')  # Add output slot        


    def onImportBruker(self):
        """ Open a data file"""
        Qd = QFileDialog()
        Qd.setFileMode(QFileDialog.Directory)
        Qd.setOption(QFileDialog.ShowDirsOnly)

        folder = Qd.getExistingDirectory(self.w, 'Open parent folder for your Bruker NMR experiments')
        if folder:
            self.config.set('filename', folder)
            self.autogenerate()


class BrukerExport(ui.ExportDataApp):

    name = "Export Bruker"
    export_description = "Export Bruker fid format spectra"
    export_type = "data"

    notebook = 'bruker_export.ipynb'
    shortname = 'bruker_export'
    
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
        self.register_app_launcher(BrukerImport, workspace_category='Import')
        self.register_app_launcher(BrukerExport, workspace_category='Export')
