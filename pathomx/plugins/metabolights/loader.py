# -*- coding: utf-8 -*-
import os

import csv
import xml.etree.cElementTree as et
from collections import defaultdict

import numpy as np

import pathomx.utils as utils
import pathomx.ui as ui
import pathomx.db as db

from pathomx.plugins import ImportPlugin


class MetabolightsConfigPanel(ui.SimpleFileOpenConfigPanel):

    filename_filter = "All compatible files (*.csv);;Comma Separated Values (*.csv);;All files (*.*)"
    description = "Open experimental data from Metabolights experimental datasets"


class ImportMetabolightsApp(ui.GenericTool):

    shortname = 'metabolights'
    autoconfig_name = "{filename}"

    def __init__(self, *args, **kwargs):
        super(ImportMetabolightsApp, self).__init__(*args, **kwargs)

        self.config.set_defaults({
            'filename': None,
        })

        self.data.add_output('output_data')  # Add output slot        

        self.addConfigPanel(MetabolightsConfigPanel, 'Settings')


class ImportMetabolights(ImportPlugin):

    def __init__(self, *args, **kwargs):
        super(ImportMetabolights, self).__init__(*args, **kwargs)
        self.register_app_launcher(ImportMetabolightsApp)
