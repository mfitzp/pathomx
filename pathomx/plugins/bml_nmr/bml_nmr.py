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

from pathomx.data import DataSet
from pathomx.plugins import ImportPlugin
from pathomx.qt import *


class BMLNMRApp(ui.ImportDataApp):

    import_filename_filter = "Compressed Files (*.zip);;All files (*.*)"
    import_description = "Open BML-NMR FIMA .zip output"

    notebook = 'bml_nmr.ipynb'

    def __init__(self, *args, **kwargs):
        super(BMLNMRApp, self).__init__(*args, **kwargs)

        self.config.set_defaults({
            'filename': None,
        })

        self.data.add_output('Raw')  # Add output slot
        self.data.add_output('PQN')  # Add output slot
        self.data.add_output('TSA')  # Add output slot


class BMLNMR(ImportPlugin):

    def __init__(self, *args, **kwargs):
        super(BMLNMR, self).__init__(*args, **kwargs)
        self.register_app_launcher(BMLNMRApp)
