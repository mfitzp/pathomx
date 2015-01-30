# -*- coding: utf-8 -*-
import os

import csv
import xml.etree.cElementTree as et
from collections import defaultdict

import numpy as np

import pathomx.ui as ui

import pathomx.utils as utils

from pathomx.plugins import ImportPlugin


class ChenomxConfigPanel(ui.SimpleFileOpenConfigPanel):

    filename_filter = "All compatible files (*.csv *.txt *.tsv);;All files (*.*)"
    description = "Open a mapped metabolite file from Chenomx"


class ChenomxApp(ui.GenericTool):

    shortname = 'chenomx'
    autoconfig_name = "{filename}"

    category = "Import"
    subcategory = "Metabolomics"

    def __init__(self, *args, **kwargs):
        super(ChenomxApp, self).__init__(*args, **kwargs)

        self.config.set_defaults({
            'filename': None,
        })

        self.data.add_output('output_data')  # Add output slot

        self.addConfigPanel(ChenomxConfigPanel, 'Settings')


class Chenomx(ImportPlugin):

    def __init__(self, *args, **kwargs):
        super(Chenomx, self).__init__(*args, **kwargs)
        self.register_app_launcher(ChenomxApp)
