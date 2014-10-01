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

from pathomx.plugins import ImportPlugin


class PeakMLConfigPanel(ui.SimpleFileOpenConfigPanel):

    filename_filter = "PeakML (MzMatch) Data Files (*.peakml);;All files (*.*)"
    description = "Open experimental data from PeakML data files"



class ImportPeakMLApp(ui.GenericTool):

    shortname = 'import_peakml'
    autoconfig_name = "{filename}"

    legacy_outputs = {'output': 'output_data'}

    def __init__(self, *args, **kwargs):
        super(ImportPeakMLApp, self).__init__(*args, **kwargs)

        self.config.set_defaults({
            'filename': None,
        })

        self.data.add_output('output_data')  # Add output slot

        self.addConfigPanel(PeakMLConfigPanel, 'Settings')

class ImportPeakML(ImportPlugin):

    def __init__(self, *args, **kwargs):
        super(ImportPeakML, self).__init__(*args, **kwargs)
        self.register_app_launcher(ImportPeakMLApp)
