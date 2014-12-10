# -*- coding: utf-8 -*-
import os

import csv
import xml.etree.cElementTree as et
from collections import defaultdict

import numpy as np

import pathomx.ui as ui

import pathomx.utils as utils

from pathomx.plugins import ImportPlugin


class MaxQuantConfigPanel(ui.SimpleFileOpenConfigPanel):

    filename_filter = "All compatible files (*.csv *.txt *.tsv);;All files (*.*)"
    description = "Open a MaxQuant output file"


class MaxQuantApp(ui.GenericTool):

    shortname = 'maxquant'
    autoconfig_name = "{filename}"

    def __init__(self, *args, **kwargs):
        super(MaxQuantApp, self).__init__(*args, **kwargs)

        self.config.set_defaults({
            'filename': None,
        })

        self.data.add_output('output_data')  # Add output slot

        self.addConfigPanel(MaxQuantConfigPanel, 'Settings')


class MaxQuant(ImportPlugin):

    def __init__(self, *args, **kwargs):
        super(MaxQuant, self).__init__(*args, **kwargs)
        self.register_app_launcher(MaxQuantApp)
