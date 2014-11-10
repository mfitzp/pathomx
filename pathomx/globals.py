import logging
logging.debug('Loading globals.py')

import platform
import os

from collections import defaultdict

from .qt import *
from .runqueue import RunManager
from pyqtconfig import QSettingsManager
from yapsy.PluginManager import PluginManagerSingleton

import matplotlib as mpl
from . import utils

# Pathomx global variables
current_tools = []
current_tools_by_id = {}
current_datasets = []

plugin_categories = ["Import", "Processing", "Filter", "Identification", "Analysis", "Visualisation", "Export", "Scripting"]
installed_plugin_names = {}
available_tools_by_category = defaultdict(list)

app_launchers = {}
file_handlers = {}
url_handlers = defaultdict(list)

logging.debug('Loading settings...')

# ReadTheDocs
ON_RTD = os.environ.get('READTHEDOCS', None) == 'True'
if not ON_RTD:

    from mplstyler import StylesManager, MATCH_EXACT, MATCH_CONTAINS, MATCH_START, MATCH_END, \
                    MATCH_REGEXP, MARKERS, LINESTYLES, FILLSTYLES, HATCHSTYLES, \
                    StyleDefinition, ClassMatchDefinition

    # Manager objects
    logging.debug('Setting up managers...')
    styles = StylesManager()
    notebook_queue = RunManager()

    settings = QSettingsManager()
    settings.set_defaults({
        'Pathomx/Is_setup': False,
        'Pathomx/Current_version': '0.0.1',
        'Pathomx/Update/Latest_version': '0.0.1',
        'Pathomx/Update/Last_checked': 0,

        'Pathomx/Offered_registration': False,

        'Plugins/Paths': [os.path.join(os.path.expanduser("~"), 'PathomxPlugins')],
        'Plugins/Disabled': [],

        'Resources/MATLAB_path': 'matlab',

        'Editor/Snap_to_grid': False,
        'Editor/Show_grid': True,
        'Editor/Auto_position': False,
    })

    mono_fontFamilies = {'Windows': 'Courier New',
                    'Darwin': 'Menlo'}
    mono_fontFamily = mono_fontFamilies.get(platform.system(), 'Monospace')

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

    plugin_manager = PluginManagerSingleton.get()
    plugin_objects = {}
    plugin_metadata = {}


    def _get_QLineEdit(self):
        return self._get_map(self.text())


    def _set_QLineEdit(self, v):
        self.setText(unicode(self._set_map(v)))


    def _event_QLineEdit(self):
        return self.textChanged

    custom_pyqtconfig_hooks = {
        'QFileOpenLineEdit': (_get_QLineEdit, _set_QLineEdit, _event_QLineEdit),
        'QFileSaveLineEdit': (_get_QLineEdit, _set_QLineEdit, _event_QLineEdit),
        'QFolderLineEdit': (_get_QLineEdit, _set_QLineEdit, _event_QLineEdit),
    }

else:

    styles = None
    notebook_queue = None

    settings = None
    mono_fontFamily = None
    MATCH_EXACT, MATCH_CONTAINS, MATCH_START, MATCH_END, MATCH_REGEXP = None, None, None, None, None
    MARKERS, LINESTYLES, FILLSTYLES, HATCHSTYLES = [], [], [], []
    StyleDefinition = None
    ClassMatchDefinition = None

    plugin_manager = None
    plugin_objects = None
    plugin_metadata = None
