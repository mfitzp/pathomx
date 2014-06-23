import logging
logging.debug('Loading globals.py')

import os
import sys

from collections import defaultdict

from .qt import QApplication, QLocale, QTranslator, QThreadPool, QObject, QTimer, QLibraryInfo
from .runner_queue import NotebookRunnerQueue
from pyqtconfig import QSettingsManager
from mplstyler import StylesManager, MATCH_EXACT, MATCH_CONTAINS, MATCH_START, MATCH_END, \
                    MATCH_REGEXP, MARKERS, LINESTYLES, FILLSTYLES, HATCHSTYLES, \
                    StyleDefinition, ClassMatchDefinition

import matplotlib as mpl
from . import utils

logging.debug('Setting up Matplotlib defaults...')

# Set Matplotlib defaults for nice looking charts
mpl.rcParams['figure.facecolor'] = 'white'
mpl.rcParams['figure.autolayout'] = True
mpl.rcParams['lines.linewidth'] = 0.25
mpl.rcParams['lines.color'] = 'black'
mpl.rcParams['lines.markersize'] = 10
mpl.rcParams['axes.linewidth'] = 0.5
mpl.rcParams['axes.labelsize'] = 9
mpl.rcParams['xtick.labelsize'] = 9
mpl.rcParams['ytick.labelsize'] = 9

mpl.rcParams['legend.fontsize'] = 9

mpl.rcParams['axes.color_cycle'] = utils.category10
mpl.rcParams['font.size'] = 9
mpl.rcParams['font.family'] = 'sans-serif'
mpl.rcParams['font.serif'] = ['Computer Modern Roman', 'Times New Roman']
mpl.rcParams['font.sans-serif'] = ['Helvetica', 'Arial', 'Bitstream Vera Sans', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial']
mpl.rcParams['patch.linewidth'] = 0

# Manager objects
logging.debug('Setting up managers...')
styles = StylesManager()
notebook_queue = NotebookRunnerQueue()

# Pathomx global variables
current_tools = []
current_tools_by_id = {}
installed_plugin_names = {}
current_datasets = []
app_launchers = {}
file_handlers = {}
url_handlers = defaultdict(list)

logging.debug('Loading settings...')
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

logging.debug('Setting up templates...')
