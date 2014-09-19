import logging
logging.debug('Loading globals.py')

import os
import sys
import platform

from collections import defaultdict

from .qt import *
from .runqueue import NotebookRunnerQueue
from pyqtconfig import QSettingsManager

import matplotlib as mpl
from . import utils

# Pathomx global variables
current_tools = []
current_tools_by_id = {}

available_tools_by_category = defaultdict(list)

plugin_categories = ["Import", "Processing", "Filter", "Identification", "Analysis", "Visualisation", "Export"]  # categories_filter.keys()

installed_plugin_names = {}
current_datasets = []
app_launchers = {}
file_handlers = {}
url_handlers = defaultdict(list)

logging.debug('Loading settings...')

ON_RTD = os.environ.get('READTHEDOCS', None) == 'True'
if not ON_RTD:

    from mplstyler import StylesManager, MATCH_EXACT, MATCH_CONTAINS, MATCH_START, MATCH_END, \
                        MATCH_REGEXP, MARKERS, LINESTYLES, FILLSTYLES, HATCHSTYLES, \
                        StyleDefinition, ClassMatchDefinition

    # Manager objects
    logging.debug('Setting up managers...')
    styles = StylesManager()
    notebook_queue = NotebookRunnerQueue()

    settings = QSettingsManager()
    settings.set_defaults({
        'Pathomx/Is_setup': False,
        'Pathomx/Current_version': '0.0.1',
        'Pathomx/Update/Latest_version': '0.0.1',
        'Pathomx/Update/Last_checked': None,
        'Pathomx/Offered_registration': False,

        'Plugins/Active': [],
        'Plugins/Disabled': [],
        'Plugins/Available': [],
        'Plugins/Paths': [],

        'Resources/MATLAB_path': 'matlab',

        'Editor/Snap_to_grid': False,
        'Editor/Show_grid': True,
    })    
    
    
    mono_fontFamilies = {'Windows':'Courier New',
                    'Darwin': 'Menlo'}
    mono_fontFamily = mono_fontFamilies.get(platform.system(), 'Monospace')
    

else:
    styles = None
    notebook_queue = None
    settings = None
    mono_fontFamily = None

    StylesManager = None
    MATCH_EXACT, MATCH_CONTAINS, MATCH_START, MATCH_END, MATCH_REGEXP = [None]*5
    MARKERS, LINESTYLES, FILLSTYLES, HATCHSTYLES = [[],[],[],[]]
    StyleDefinition, ClassMatchDefinition = None, None
