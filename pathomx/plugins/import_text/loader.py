# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os

from pathomx.plugins import ImportPlugin

import csv
import xml.etree.cElementTree as et
from collections import defaultdict

import numpy as np

from pathomx.qt import *

import pathomx.ui as ui
import pathomx.db as db

import pathomx.utils as utils


# Dialog box for Metabohunter search options
class ImportDataConfigPanel(ui.ConfigPanel):

    config_quote_types = {
        'All': csv.QUOTE_ALL,
        'Minimal': csv.QUOTE_MINIMAL,
        'Non-numeric': csv.QUOTE_NONNUMERIC,
        'None': csv.QUOTE_NONE,
    }

    def __init__(self, parent, filename=None, *args, **kwargs):
        super(ImportDataConfigPanel, self).__init__(parent, *args, **kwargs)

        self.v = parent
        self.config = parent.config
        gb = QGroupBox('Open file')
        grid = QGridLayout()
        self.filename = ui.QFileOpenLineEdit(filename_filter="All compatible files (*.csv *.txt *.tsv);;Comma Separated Values (*.csv);;Plain Text Files (*.txt);;Tab Separated Values (*.tsv);;All files (*.*)",
                             description="Open experimental data from text file data file")
        grid.addWidget(QLabel('Path'), 0, 0)
        grid.addWidget(self.filename, 0, 1)
        self.config.add_handler('filename', self.filename)
        gb.setLayout(grid)

        self.layout.addWidget(gb)

        gb = QGroupBox('Layout')
        grid = QGridLayout()

        self.colh_sb = QSpinBox()
        self.colh_sb.setMinimum(0)
        grid.addWidget(QLabel('Column headers'), 0, 0)
        grid.addWidget(self.colh_sb, 0, 1)
        self.config.add_handler('column_headers', self.colh_sb)

        self.colh_def_le = QLineEdit()
        grid.addWidget(QLabel('Column defaults'), 1, 0)
        grid.addWidget(self.colh_def_le, 1, 1)
        self.config.add_handler('column_header_defaults', self.colh_def_le)

        self.rowh_sb = QSpinBox()
        self.rowh_sb.setMinimum(0)
        grid.addWidget(QLabel('Row headers'), 2, 0)
        grid.addWidget(self.rowh_sb, 2, 1)
        self.config.add_handler('row_headers', self.rowh_sb)

        self.rowh_def_le = QLineEdit()
        grid.addWidget(QLabel('Row defaults'), 3, 0)
        grid.addWidget(self.rowh_def_le, 3, 1)
        self.config.add_handler('row_header_defaults', self.rowh_def_le)


        self.transpose_cb = QCheckBox()
        grid.addWidget(QLabel('Transpose (samples across)'), 4, 0)
        grid.addWidget(self.transpose_cb, 4, 1)
        self.config.add_handler('transpose', self.transpose_cb)


        gb.setLayout(grid)

        self.layout.addWidget(gb)

        gb = QGroupBox('Autodetect')
        grid = QGridLayout()
        self.cb_autodetect = QCheckBox()
        grid.addWidget(QLabel('Autodetect format'), 0, 0)
        grid.addWidget(self.cb_autodetect, 0, 1)
        self.config.add_handler('autodetect_format', self.cb_autodetect)
        gb.setLayout(grid)

        self.layout.addWidget(gb)

        gb = QGroupBox('Basic configuration')
        grid = QGridLayout()

        self.cb_delimiter = QLineEdit()
        grid.addWidget(QLabel('Delimiter'), 0, 0)
        grid.addWidget(self.cb_delimiter, 0, 1)
        self.config.add_handler('delimiter', self.cb_delimiter)

        self.cb_quotechar = QLineEdit()
        grid.addWidget(QLabel('Quote character'), 1, 0)
        grid.addWidget(self.cb_quotechar, 1, 1)
        self.config.add_handler('quotechar', self.cb_quotechar)

        gb.setLayout(grid)
        self.layout.addWidget(gb)

        gb = QGroupBox('Advanced')
        grid = QGridLayout()

        self.cb_quoting = QComboBox()
        self.cb_quoting.addItems(list(self.config_quote_types.keys()))
        grid.addWidget(QLabel('Quote style'), 2, 0)
        grid.addWidget(self.cb_quoting, 2, 1)
        self.config.add_handler('quoting', self.cb_quoting, self.config_quote_types)

        self.cb_doublequote = QCheckBox()
        grid.addWidget(QLabel('Double quote?'), 3, 0)
        grid.addWidget(self.cb_doublequote, 3, 1)
        self.config.add_handler('doublequote', self.cb_doublequote)

        self.cb_escapechar = QLineEdit()
        grid.addWidget(QLabel('Escape character'), 4, 0)
        grid.addWidget(self.cb_escapechar, 4, 1)
        self.config.add_handler('escapechar', self.cb_escapechar)

        self.cb_skipinitialspace = QCheckBox()
        grid.addWidget(QLabel('Skip initial space?'), 5, 0)
        grid.addWidget(self.cb_skipinitialspace, 5, 1)
        self.config.add_handler('skipinitialspace', self.cb_skipinitialspace)

        gb.setLayout(grid)
        self.layout.addWidget(gb)

        self.finalise()


class ImportTextApp(ui.GenericTool):

    shortname = 'import_text'

    legacy_outputs = {'output': 'output_data'}
    autoconfig_name = "{filename}"

    def __init__(self, *args, **kwargs):
        super(ImportTextApp, self).__init__(*args, **kwargs)

        self.config.set_defaults({
            'filename': None,
            'autodetect_format': True,
            'delimiter': b',',
            'quotechar': b'"',
            'doublequote': True,
            'escapechar': b'',
            'quoting': csv.QUOTE_MINIMAL,
            'skipinitialspace': False,

            'transpose': False,
            'row_headers': 2,
            'row_header_defaults': 'Sample,Class',
            'column_headers': 1,
            'column_header_defaults': 'Label',

        })

        self.addConfigPanel(ImportDataConfigPanel, 'Settings')

        self.data.add_output('output_data')  # Add output slot


class ImportText(ImportPlugin):

    def __init__(self, *args, **kwargs):
        super(ImportText, self).__init__(*args, **kwargs)
        self.register_app_launcher(ImportTextApp)
        self.register_file_handler(ImportTextApp, 'csv')
