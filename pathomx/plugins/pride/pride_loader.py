# -*- coding: utf-8 -*-
import os

import csv
import xml.etree.cElementTree as et
from collections import defaultdict

import numpy as np

import zipfile
import tempfile

import pathomx.utils as utils
import pathomx.ui as ui
import pathomx.db as db

from pathomx.plugins import ImportPlugin
from pathomx.data import DataSet


class ImportPRIDETool(ui.ImportDataApp):

    notebook = 'pride.ipynb'
    shortname = 'pride'
    
    import_filename_filter = "All compatible files (*.zip);;Zipped PRIDE data files (*.*);;All files (*.*)"
    import_description = "Import experimental data from PRIDE experimental datasets"
    legacy_outputs = {'output': 'output_data'}

    def __init__(self, *args, **kwargs):
        super(ImportPRIDETool, self).__init__(*args, **kwargs)

        self.config.set_defaults({
            'filename': None,
        })

        self.data.add_output('output_data')  # Add output slot

        
class ImportPRIDE(ImportPlugin):

    def __init__(self, *args, **kwargs):
        super(ImportPRIDE, self).__init__(*args, **kwargs)
        self.register_app_launcher(ImportPRIDETool)
