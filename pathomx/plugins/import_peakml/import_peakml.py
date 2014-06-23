# -*- coding: utf-8 -*-
import os

import csv
import xml.etree.cElementTree as et
from collections import defaultdict

import base64

import numpy as np

import pathomx.ui as ui
import pathomx.db as db
import pathomx.utils as utils

from pathomx.data import DataSet
from pathomx.plugins import ImportPlugin


class ImportPeakMLApp(ui.ImportDataApp):

    notebook = 'import_peakml.ipynb'

    import_filename_filter = "PeakML (MzMatch) Data Files (*.peakml);;All files (*.*)"
    import_description = "Open experimental data from PeakML data files"
    legacy_outputs = {'output': 'output_data'}

    def __init__(self, *args, **kwargs):
        super(ImportPeakMLApp, self).__init__(*args, **kwargs)

        self.config.set_defaults({
            'filename': None,
        })

        self.data.add_output('output_data')  # Add output slot


class ImportPeakML(ImportPlugin):

    def __init__(self, *args, **kwargs):
        super(ImportPeakML, self).__init__(*args, **kwargs)
        self.register_app_launcher(ImportPeakMLApp)
