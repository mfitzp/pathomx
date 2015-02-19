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

from pathomx.plugins import ImportPlugin
from pathomx.qt import *


class BMLNMRConfigPanel(ui.SimpleFileOpenConfigPanel):
    filename_filter = "Compressed Files (*.zip);;All files (*.*)"
    description = "Open BML-NMR FIMA .zip output"


class BMLNMRApp(ui.GenericTool):

    shortname = 'bml_nmr'
    autoconfig_name = "{filename}"

    category = "Import"
    subcategory = "Metabolomics"

    def __init__(self, *args, **kwargs):
        super(BMLNMRApp, self).__init__(*args, **kwargs)

        self.config.set_defaults({
            'filename': None,
        })

        self.data.add_output('raw')  # Add output slot
        self.data.add_output('pqn')  # Add output slot
        self.data.add_output('tsa')  # Add output slot

        self.addConfigPanel(BMLNMRConfigPanel, "Settings")


class BMLNMR(ImportPlugin):

    def __init__(self, *args, **kwargs):
        super(BMLNMR, self).__init__(*args, **kwargs)
        self.register_app_launcher(BMLNMRApp)
