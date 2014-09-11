# -*- coding: utf-8 -*-
import os

import csv
import xml.etree.cElementTree as et
from collections import defaultdict

import numpy as np

import pathomx.ui as ui
import pathomx.db as db

import pathomx.utils as utils

from pathomx.data import DataSet
from pathomx.plugins import ImportPlugin
from pathomx.qt import *
from pathomx.utils import UnicodeReader


class GEOApp(ui.ImportDataApp):

    notebook = 'geo.ipynb'
    import_filename_filter = "All compatible files (*.soft);;Simple Omnibus Format in Text (*.soft);;All files (*.*)"
    import_description = "Open experimental data from downloaded data"
    legacy_outputs = {'output': 'output_data'}

    def __init__(self, *args, **kwargs):
        super(GEOApp, self).__init__(*args, **kwargs)

        self.config.set_defaults({
            'filename': None,
        })

        self.data.add_output('output_data')  # Add output slot


class GEO(ImportPlugin):

    def __init__(self, *args, **kwargs):
        super(GEO, self).__init__(*args, **kwargs)
        self.register_app_launcher(GEOApp)
        self.register_file_handler(GEOApp, 'soft')
