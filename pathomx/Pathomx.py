# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import sys
import logging

VERSION_STRING = '3.0.0a2'

frozen = getattr(sys, 'frozen', None)
if frozen:
    logging.basicConfig(level=logging.INFO)
else:
    logging.basicConfig(level=logging.DEBUG)

import os
import re
import math
import codecs
import locale
import json
import importlib
import functools
from copy import copy

sys.setcheckinterval(1000)

if sys.version_info < (3, 0):  # Python 2 only
    UTF8Writer = codecs.getwriter('utf8')
    sys.stdout = UTF8Writer(sys.stdout)
    reload(sys).setdefaultencoding('utf8')

from .qt import *
# pyqtSignal, Qt, QTreeWidgetItem, QIcon, QColor, QBrush, QObject, \
# QPixmap, QComboBox, QLineEdit, QLabel, QAbstractItemDelegate, QStyle, \
# QPalette, QListView, QDrag, QMimeData, QSettings, QSize,

import textwrap

from IPython.nbformat.current import write as write_notebook, NotebookNode
from IPython.nbconvert.exporters import export as IPyexport
from IPython.nbconvert.exporters.export import exporter_map as IPyexporter_map

from IPython.utils.ipstruct import Struct
from IPython.nbformat.v3 import new_code_cell


try:
    from urllib.request import urlopen
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse
    from urllib import urlopen

from optparse import Values
from collections import defaultdict

import numpy as np

from biocyc import biocyc

from yapsy.PluginManager import PluginManager, PluginManagerSingleton

try:
    import xml.etree.cElementTree as et
except ImportError:
    import xml.etree.ElementTree as et

from .globals import styles, notebook_queue, \
                     current_tools, current_tools_by_id, installed_plugin_names, current_datasets, \
                     settings, url_handlers, app_launchers

from . import data
from . import utils
from . import ui
from . import views
from . import custom_exceptions
from . import plugins  # plugin helper/manager
from . import threads
from .editor.editor import WorkspaceEditorView, EDITOR_MODE_NORMAL, EDITOR_MODE_TEXT, EDITOR_MODE_REGION

#from multiprocessing import Process, Pool, Queue

# Translation (@default context)
from .translate import tr

from distutils.version import StrictVersion
from runipy.notebook_runner import NotebookRunner

DEFAULT_PATHWAYS = ["PWY-5340", "PWY-5143", "PWY-5754", "PWY-6482", "PWY-5905",
        "SER-GLYSYN-PWY-1", "PWY-4983", "ASPARAGINE-BIOSYNTHESIS", "ASPARTATESYN-PWY",
        "PWY-3982", "PWY-6292", "HOMOCYSDEGR-PWY", "GLUTAMATE-SYN2-PWY", "PWY-5921",
        "GLNSYN-PWY", "GLYSYN-PWY", "GLYSYN-ALA-PWY", "ADENOSYLHOMOCYSCAT-PWY",
        "PWY-6755", "ARGININE-SYN4-PWY", "PWY-5331", "PWY-4921", "PROSYN-PWY",
        "SERSYN-PWY", "PWY-6281", "TRNA-CHARGING-PWY", "PWY66-399", "PWY-6138",
        "PWY-5659", "PWY-66", "PWY-6", "PWY-5661-1", "PWY-4821",
        "MANNOSYL-CHITO-DOLICHOL-BIOSYNTHESIS", "PWY-5067", "PWY-6564", "PWY-6568",
        "PWY-6558", "PWY-6567", "PWY-6571", "PWY-6557", "PWY-6566", "PWY-6569",
        "PWY-5512", "PWY-5514", "PWY-5963", "PWY-6012-1", "PWY-7250", "SAM-PWY",
        "COA-PWY-1", "PWY0-522", "PWY0-1275", "PWY-6823", "NADPHOS-DEPHOS-PWY-1",
        "NADSYN-PWY", "NAD-BIOSYNTHESIS-III", "PWY-5653", "PWY-5123", "PWY-5910",
        "PWY-5120", "PWY-5920", "HEME-BIOSYNTHESIS-II", "PWY-5872", "PWY-4041",
        "GLUTATHIONESYN-PWY", "THIOREDOX-PWY", "GLUT-REDOX-PWY", "PWY-4081", "PWY-5663",
        "PWY-5189", "PWY-6076", "PWY-2161", "PWY-2161B", "PWY-2201", "PWY-6613",
        "PWY-6872", "PWY-6857", "PWY-6875", "PWY-6861", "PWY66-366", "PWY-6898",
        "PLPSAL-PWY", "PWY-6030", "PWY-6241", "PWY-7299", "PWY-7305", "PWY-7306",
        "PWY66-301", "PWY66-374", "PWY66-375", "PWY66-377", "PWY66-378", "PWY66-380",
        "PWY66-381", "PWY66-382", "PWY66-392", "PWY66-393", "PWY66-394", "PWY66-395",
        "PWY66-397", "PWY-5148", "PWY-6129", "PWY0-1264", "PWY3DJ-11281", "TRIGLSYN-PWY",
        "FASYN-ELONG-PWY", "PWY-5966-1", "PWY-6000", "PWY-5996", "PWY-5994", "PWY-5972",
        "PWY-7049", "PWY-6352", "PWY-6367", "PWY-6371", "PWY-7501", "PWY-5667",
        "PWY-5269", "PWY3O-450", "PWY4FS-6", "PWY3DJ-12", "PWY-6061", "PWY-6074",
        "PWY-6132", "PWY-7455", "PWY66-3", "PWY66-341", "PWY66-4", "PWY66-5",
        "PWY-6158", "PWY-6100", "PWY-6405", "PWY66-420", "PWY66-423", "PWY66-421",
        "PWY66-385", "PWY-7227", "PWY-7226", "PWY-7184", "PWY-7211", "PWY-6689",
        "PWY-7375-1", "PWY-7286", "PWY-7283", "PWY-6121", "PWY-7228", "PWY-841",
        "PWY-7219", "PWY-7221", "PWY-6124", "PWY-7224", "PWY66-409", "P121-PWY",
        "PWY-6619", "PWY-6609", "PWY-6620", "PWY-7176", "PWY-5686", "PWY0-162",
        "PWY-7210", "PWY-7197", "PWY-7199", "PWY-7205", "PWY-7193", "PWY-7200",
        "PWY-5389", "PWY-5670", "PWY-6481", "PWY-6498", "PWY66-425", "PWY66-426",
        "PWY0-662", "PWY-5695", "ARGSPECAT-PWY", "GLYCGREAT-PWY", "PWY-6173",
        "CHOLINE-BETAINE-ANA-PWY", "PWY-40", "PWY-46", "BSUBPOLYAMSYN-PWY",
        "UDPNACETYLGALSYN-PWY", "PWY-5270", "PWY-6133", "PWY-6358", "PWY-6365",
        "PWY-6369", "PWY-6351", "PWY-6364", "PWY-6363", "PWY-6366", "PWY-2301",
        "PWY-6554", "PWY-6362", "PWY-922", "2PHENDEG-PWY", "PWY-6181", "PWY66-414",
        "PWY6666-2", "GLUDEG-I-PWY", "PWY-6535", "PWY-3661-1", "GLUAMCAT-PWY",
        "PWY-6517", "PWY-0", "PWY-6117", "PWY66-389", "PWY66-21", "PWY66-162",
        "PWY66-161", "PWY-4261", "PWY-5453", "PWY-5386", "MGLDLCTANA-PWY", "PWY-5046",
        "PWY-5084", "PWY-6334", "HYDROXYPRODEG-PWY", "ALANINE-DEG3-PWY",
        "ASPARAGINE-DEG1-PWY", "MALATE-ASPARTATE-SHUTTLE-PWY", "BETA-ALA-DEGRADATION-I-PWY",
        "PWY-5329", "CYSTEINE-DEG-PWY", "GLUTAMINDEG-PWY", "GLYCLEAV-PWY", "PWY-5030",
        "ILEUDEG-PWY", "LEU-DEG2-PWY", "LYSINE-DEG1-PWY", "PWY-5328", "METHIONINE-DEG1-PWY",
        "PHENYLALANINE-DEG1-PWY", "PROUT-PWY", "SERDEG-PWY", "PWY66-428", "PWY66-401",
        "TRYPTOPHAN-DEGRADATION-1", "PWY-6309", "PWY-5651", "PWY-6307", "TYRFUMCAT-PWY",
        "VALDEG-PWY", "PWY-1801", "PWY-5177", "PWY-5652", "PWY0-1313", "PYRUVDEHYD-PWY",
        "PWY-5130", "PROPIONMET-PWY", "PWY-5525", "PWY-6370", "PWY-5874", "MANNCAT-PWY",
        "PWY-7180", "PWY66-422", "BGALACT-PWY", "PWY66-373", "PWY0-1182", "PWY-6576",
        "PWY-6573", "PWY-5941-1", "LIPAS-PWY", "LIPASYN-PWY", "PWY-6111", "PWY-6368",
        "PWY3DJ-11470", "PWY6666-1", "PWY-5451", "PWY-5137", "PWY66-391", "FAO-PWY",
        "PWY66-388", "PWY66-387", "PWY-6313", "PWY-6342", "PWY-6688", "PWY-6398",
        "PWY-6402", "PWY-6400", "PWY-6399", "PWY-6261", "PWY-6260", "PWY-6756",
        "PWY-6353", "PWY-7179-1", "PWY0-1296", "SALVADEHYPOX-PWY", "PWY-6608",
        "PWY-7209", "PWY-6430", "PWY-7181", "PWY-7177", "PWY0-1295", "PWY-7185",
        "PWY-4984", "PWY-5326", "PWY-5350", "PWY-4061", "PWY-7112", "PWY-6377",
        "PWY66-241", "PWY66-201", "PWY66-221", "PWY-4101", "DETOX1-PWY", "PWY-6502",
        "PWY0-1305", "PWY-4202", "PWY-6938", "PWY66-407", "PWY-5172", "PWY-5481",
        "PWY66-400", "PWY66-368", "PWY66-367", "PWY-6118", "PENTOSE-P-PWY",
        "OXIDATIVEPENT-PWY-1", "NONOXIPENT-PWY", "PWY66-398", "PWY-7437", "PWY-7434",
        "PWY-7433", "PWY66-14", "PWY66-11", "PYRUVDEH-RXN"]


class Logger(logging.Handler):
    def __init__(self, parent, widget, out=None, color=None):
        super(Logger, self).__init__()
        self.m = parent
        """(edit, out=None, color=None) -> can write stdout, stderr to a
        QTextEdit.
        edit = QTextEdit
        out = alternate stream ( can be the original sys.stdout )
        color = alternate color (i.e. color stderr a different color)
        """
        self.widget = widget
        self.out = None
        self.color = color

    def emit(self, record):
        msg = self.format(record)

        item = QTreeWidgetItem()
        item.setText(0, record.name)
        item.setText(1, msg)

        bg = {
            logging.CRITICAL: QColor(164, 0, 0, 50),
            logging.ERROR: QColor(239, 41, 41, 50),
            logging.WARNING: QColor(252, 233, 79, 50),
            logging.INFO: None,
            logging.DEBUG: QColor(114, 159, 207, 50),
            logging.NOTSET: None,
        }[record.levelno]
        if bg:
            for c in range(3):
                item.setBackground(c, QBrush(bg))

        if record.name in current_tools_by_id:
            # This is a log entry from a plugin-app. We can get the info (icon, etc) from it
            item.tool = current_tools_by_id[record.name]
            item.setIcon(1, item.tool.plugin.workspace_icon)
        else:
            i = QPixmap(16, 16)
            i.fill(Qt.transparent)
            item.setIcon(1, QIcon(i))

        self.widget.addTopLevelItem(item)
        self.widget.scrollToBottom()

    def write(self, m):
        pass


class ToolTreeWidget(QTreeWidget):

    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.LeftButton:  # Possible fix for Windows hang bug https://bugreports.qt-project.org/browse/QTBUG-10180
            logging.debug('Starting drag-drop of workspace item.')
            item = self.currentItem()

            mimeData = QMimeData()
            mimeData.setData('application/x-pathomx-app', item.data['id'])

            e.accept()

            drag = QDrag(self)
            drag.setMimeData(mimeData)
            drag.setPixmap(item.data['plugin'].pixmap.scaled(QSize(64, 64), transformMode=Qt.SmoothTransformation))
            drag.setHotSpot(QPoint(32, 32))  # - self.visualItemRect(item).top())

            dropAction = drag.exec_(Qt.CopyAction)
            logging.debug('Drag-drop complete.')

        else:
            e.ignore()


class MainWindow(QMainWindow):

    workspace_updated = pyqtSignal()

    def __init__(self):
        super(MainWindow, self).__init__()

        # Initiate logging
        self.logView = QTreeWidget()
        self.logView.setColumnCount(2)
        self.logView.expandAll()
        self.logView.itemClicked.connect(self.onLogItemClicked)
        self.logView.itemDoubleClicked.connect(self.onLogItemDoubleClicked)

        self.logView.setHeaderLabels(['ID', 'Message'])
        self.logView.setUniformRowHeights(True)
        self.logView.hideColumn(0)

        logHandler = Logger(self, self.logView)
        logging.getLogger().addHandler(logHandler)
        logging.info('Welcome to Pathomx v%s' % (VERSION_STRING))

        # Central variable for storing application configuration (load/save from file?

        if settings.get('Pathomx/Is_setup') == False:
            logging.info("Setting up initial configuration...")
            #self.onResetConfig()
            logging.info('Done')

        # Do version upgrade availability check
        # FIXME: Do check here; if not done > 2 weeks
        if StrictVersion(settings.get('Pathomx/Update/Latest_version')) > StrictVersion(VERSION_STRING):
            # We've got an upgrade
            logging.warning('A new version (v%s) is available' % settings.get('Pathomx/Update/Latest_version'))

        self.fonts = QFontDatabase()

        self.datasets = []  # List of instances of data.datasets() // No data loaded by default

        self.layout = None  # No map by default

        self.url_handlers = defaultdict(list)
        self.app_launcher_categories = defaultdict(list)
        self.file_handlers = {}

        self.update_view_callback_enabled = True
        #self.printer = QPrinter()

        QNetworkProxyFactory.setUseSystemConfiguration(True)

        #  UI setup etc
        self.menuBars = {
            'file': self.menuBar().addMenu(tr('&File')),
            'plugins': self.menuBar().addMenu(tr('&Plugins')),
            'appearance': self.menuBar().addMenu(tr('&Appearance')),
            'resources': self.menuBar().addMenu(tr('&Resources')),
            'database': self.menuBar().addMenu(tr('&Database')),
            'help': self.menuBar().addMenu(tr('&Help')),
        }

        # FILE MENU
        aboutAction = QAction(QIcon.fromTheme("help-about"), 'About', self)
        aboutAction.setStatusTip(tr('About Pathomx'))
        aboutAction.triggered.connect(self.onAbout)
        self.menuBars['file'].addAction(aboutAction)

        newAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'document.png')), tr('&New Blank Workspace'), self)
        newAction.setShortcut('Ctrl+N')
        newAction.setStatusTip(tr('Create new blank workspace'))
        newAction.triggered.connect(self.onClearWorkspace)
        self.menuBars['file'].addAction(newAction)

        openAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'folder-open-document.png')), tr('&Open…'), self)
        openAction.setShortcut('Ctrl+O')
        openAction.setStatusTip(tr('Open previous analysis workspace'))
        openAction.triggered.connect(self.onOpenWorkspace)
        #self.menuBars['file'].addAction(openAction)

        openAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'folder-open-document.png')), tr('&Open Workflow…'), self)
        openAction.setStatusTip(tr('Open an analysis workflow'))
        openAction.triggered.connect(self.onOpenWorkflow)
        self.menuBars['file'].addAction(openAction)

        self.menuBars['file'].addSeparator()

        saveAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'disk.png')), tr('&Save'), self)
        saveAction.setShortcut('Ctrl+S')
        saveAction.setStatusTip(tr('Save current workspace for future use'))
        saveAction.triggered.connect(self.onSaveWorkspace)
        #self.menuBars['file'].addAction(saveAction)

        saveAsAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'disk--pencil.png')), tr('Save &As…'), self)
        saveAsAction.setShortcut('Ctrl+A')
        saveAsAction.setStatusTip(tr('Save current workspace for future use'))
        saveAsAction.triggered.connect(self.onSaveWorkspaceAs)
        #self.menuBars['file'].addAction(saveAsAction)

        saveAsAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'disk--pencil.png')), tr('Save Workflow As…'), self)
        saveAsAction.setStatusTip(tr('Save current workflow for future use'))
        saveAsAction.triggered.connect(self.onSaveWorkflowAs)
        self.menuBars['file'].addAction(saveAsAction)

        self.menuBars['file'].addSeparator()
        #printAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'printer.png')), tr('&Print…'), self)
        #printAction.setShortcut('Ctrl+P')
        #printAction.setStatusTip(tr('Print current figure'))
        #printAction.triggered.connect(self.onPrint)
        #self.menuBars['file'].addAction(printAction)

        self.menuBars['file'].addSeparator()

        # DATABASE MENU
        explore_dbAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'database-explore.png')), tr('&Explore database…'), self)
        explore_dbAction.setStatusTip('Explore database')
        explore_dbAction.triggered.connect(self.onDBExplore)
        self.menuBars['database'].addAction(explore_dbAction)
        #load_identitiesAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'database-import.png')), tr('&Load database unification…'), self)
        #load_identitiesAction.setStatusTip('Load additional unification mappings into database')
        #load_identitiesAction.triggered.connect(self.onLoadIdentities)
        #self.menuBars['database'].addAction(load_identitiesAction)

        self.menuBars['database'].addSeparator()

        # PLUGINS MENU
        change_pluginsAction = QAction(tr('&Manage plugins…'), self)
        change_pluginsAction.setStatusTip('Find, activate, deactivate and remove plugins')
        change_pluginsAction.triggered.connect(self.onChangePlugins)
        self.menuBars['plugins'].addAction(change_pluginsAction)

        check_pluginupdatesAction = QAction(tr('&Check for updated plugins'), self)
        check_pluginupdatesAction.setStatusTip('Check for updates to installed plugins')
        check_pluginupdatesAction.triggered.connect(self.onCheckPluginUpdates)
        #self.menuBars['plugins'].addAction(check_pluginupdatesAction)  FIXME: Add a plugin-update check

        linemarkerstyleAction = QAction('Line and marker styles…', self)
        linemarkerstyleAction.setStatusTip(tr('Set line and marker styles for data classes'))
        linemarkerstyleAction.triggered.connect(self.onDefineClassStyles)
        self.menuBars['appearance'].addAction(linemarkerstyleAction)

        aboutAction = QAction(QIcon.fromTheme("help-about"), 'Introduction', self)
        aboutAction.setStatusTip(tr('About Pathomx'))
        aboutAction.triggered.connect(self.onAbout)
        self.menuBars['help'].addAction(aboutAction)

        self.menuBars['help'].addSeparator()

        goto_pathomx_websiteAction = QAction(tr('&Pathomx homepage'), self)
        goto_pathomx_websiteAction.setStatusTip('Go to the Pathomx website')
        goto_pathomx_websiteAction.triggered.connect(self.onGoToPathomxWeb)
        self.menuBars['help'].addAction(goto_pathomx_websiteAction)

        goto_pathomx_docsAction = QAction(tr('&Pathomx documentation'), self)
        goto_pathomx_docsAction.setStatusTip('Read latest Pathomx documentation')
        goto_pathomx_docsAction.triggered.connect(self.onGoToPathomxDocs)
        self.menuBars['help'].addAction(goto_pathomx_docsAction)

        goto_pathomx_demosAction = QAction(tr('&Pathomx demos'), self)
        goto_pathomx_demosAction.setStatusTip('Watch Pathomx demo videos')
        goto_pathomx_demosAction.triggered.connect(self.onGoToPathomxDemos)
        self.menuBars['help'].addAction(goto_pathomx_demosAction)

        self.menuBars['help'].addSeparator()

        do_registerAction = QAction(tr('&Register Pathomx'), self)
        do_registerAction.setStatusTip('Register Pathomx for release updates')
        do_registerAction.triggered.connect(self.onDoRegister)
        self.menuBars['help'].addAction(do_registerAction)

        # GLOBAL WEB SETTINGS
        QNetworkProxyFactory.setUseSystemConfiguration(True)

        QWebSettings.setMaximumPagesInCache(0)
        QWebSettings.setObjectCacheCapacities(0, 0, 0)
        QWebSettings.clearMemoryCaches()

        self.plugins = {}  # Dict of plugin shortnames to data
        self.plugins_obj = {}  # Dict of plugin name references to objs (for load/save)
        self.pluginManager = PluginManagerSingleton.get()
        self.pluginManager.m = self

        self.plugin_places = []
        self.core_plugin_path = os.path.join(utils.scriptdir, 'plugins')
        self.plugin_places.append(self.core_plugin_path)

        user_application_data_paths = QStandardPaths.standardLocations(QStandardPaths.DataLocation)
        if user_application_data_paths:
            self.user_plugin_path = os.path.join(user_application_data_paths[0], 'plugins')
            utils.mkdir_p(self.user_plugin_path)
            self.plugin_places.append(self.user_plugin_path)

            self.application_data_path = os.path.join(user_application_data_paths[1])

        logging.info("Searching for plugins...")
        for place in self.plugin_places:
            logging.info(place)

        self.tools = defaultdict(list)

        self.pluginManager.setPluginPlaces(self.plugin_places)
        self.pluginManager.setPluginInfoExtension('pathomx-plugin')
        categories_filter = {
               "Import": plugins.ImportPlugin,
               "Processing": plugins.ProcessingPlugin,
               "Filter": plugins.FilterPlugin,
               "Identification": plugins.IdentificationPlugin,
               "Analysis": plugins.AnalysisPlugin,
               "Visualisation": plugins.VisualisationPlugin,
               "Export": plugins.ExportPlugin,
               }
        self.pluginManager.setCategoriesFilter(categories_filter)
        self.pluginManager.collectPlugins()

        plugin_categories = ["Import", "Processing", "Filter", "Identification", "Analysis", "Visualisation", "Export"]  # categories_filter.keys()
        apps = defaultdict(list)
        self.appBrowsers = {}
        self.plugin_names = dict()
        self.plugin_metadata = dict()


        # Loop round the plugins and print their names.
        for category in plugin_categories:
            for plugin in self.pluginManager.getPluginsOfCategory(category):

                plugin_image = os.path.join(os.path.dirname(plugin.path), 'icon.png')

                if not os.path.isfile(plugin_image):
                    plugin_image = None

                try:
                    resource_list = plugin.details.get('Documentation', 'Resources').split(',')
                except:
                    resource_list = []

                metadata = {
                    'id': type(plugin.plugin_object).__name__,  # __module__,
                    'image': plugin_image,
                    'image_forward_slashes': plugin_image.replace('\\', '/'),  # Slashes fix for CSS in windows
                    'name': plugin.name,
                    'version': plugin.version,
                    'description': plugin.description,
                    'author': plugin.author,
                    'resources': resource_list,
                    'info': plugin,
                    'path': os.path.dirname(plugin.path),
                    'module': os.path.basename(plugin.path),
                    'shortname': os.path.basename(plugin.path),
                    'is_core_plugin': plugin.path.startswith(self.core_plugin_path)
                }

                self.plugins[metadata['shortname']] = metadata
                installed_plugin_names[id(plugin.plugin_object)] = plugin.name

                plugin.plugin_object.post_setup(path=os.path.dirname(plugin.path), name=plugin.name, metadata=metadata)

                apps[category].append(metadata)

        self.workspace_count = 0  # Auto-increment
        self.workspace_parents = {}
        self.workspace_index = {}  # id -> obj

        self.workspace = QTreeWidget()
        self.workspace.setColumnCount(4)
        self.workspace.expandAll()

        self.workspace.setHeaderLabels(['', 'ID', ' ◎', ' ⚑'])  # ,'#'])
        self.workspace.setUniformRowHeights(True)
        self.workspace.hideColumn(1)

        app_category_icons = {
               "Import": QIcon(os.path.join(utils.scriptdir, 'icons', 'folder-open-document.png')),
               "Processing": QIcon(os.path.join(utils.scriptdir, 'icons', 'ruler-triangle.png')),
               "Filter": QIcon(os.path.join(utils.scriptdir, 'icons', 'funnel.png')),
               "Identification": QIcon(os.path.join(utils.scriptdir, 'icons', 'target.png')),
               "Analysis": QIcon(os.path.join(utils.scriptdir, 'icons', 'calculator.png')),
               "Visualisation": QIcon(os.path.join(utils.scriptdir, 'icons', 'star.png')),
               "Export": QIcon(os.path.join(utils.scriptdir, 'icons', 'disk--pencil.png')),
               }

        self.toolbox = ToolTreeWidget(self)  # QToolBox(self)
        self.toolbox.setHeaderLabels(['Installed tools'])
        self.toolbox.setUniformRowHeights(True)

        for category in plugin_categories:
            item = QTreeWidgetItem()
            item.setText(0, category)
            item.setIcon(0, app_category_icons[category])
            self.toolbox.addTopLevelItem(item)
            for tool in self.tools[category]:
                ti = QTreeWidgetItem()
                ti.setText(0, getattr(tool['app'], 'name', tool['plugin'].name))
                ti.setIcon(0, tool['plugin'].icon)
                ti.setToolTip(0, tool['plugin'].metadata['description'])
                ti.data = tool
                item.addChild(ti)
            item.sortChildren(0, Qt.AscendingOrder)

        self.toolbox.expandAll()

        self.toolDock = QDockWidget(tr('Toolkit'))
        self.toolDock.setWidget(self.toolbox)
        self.toolDock.setMinimumWidth(300)

        self.addDockWidget(Qt.LeftDockWidgetArea, self.toolDock)

        self.toolDock.raise_()
        #self.dbtool = ui.DbApp(self)
        #self.dbBrowser = self.dbtool.dbBrowser

        self.setWindowTitle(tr('Pathomx'))

        self.threadCount = QLabel(self.statusBar())
        font = self.threadCount.font()
        font.setPointSize(8)
        self.threadCount.setFont(font)
        self.statusBar().addPermanentWidget(self.threadCount)

        self.jobQueue = QLabel(self.statusBar())
        font = self.jobQueue.font()
        font.setPointSize(8)
        self.jobQueue.setFont(font)
        self.statusBar().addPermanentWidget(self.jobQueue)

        self.progressBar = QProgressBar(self.statusBar())
        self.progressBar.setMaximumSize(QSize(170, 19))
        self.progressBar.setRange(0, 100)

        self.statusBar().addPermanentWidget(self.progressBar)

        self._progressBar_timer = QTimer()
        self._progressBar_timer.timeout.connect(self.updateProgressBar)
        self._progressBar_timer.start(5000)  # Attempt queue start every 5 seconds

        self.progressTracker = {}  # Dict storing values for each view/object

        self.editView = WorkspaceEditorView(self)
        self.editor = self.editView.scene

        self.central = QTabWidget()
        self.central.setTabPosition(QTabWidget.South)

        self.central.addTab(self.editView, 'Editor')
        self.central.addTab(self.logView, 'Log')

        self.setCentralWidget(self.central)

        self.addFileToolBar()
        self.addEditorToolBar()
        self.addEditModeToolBar()
        self.addEditStyleToolBar()

        self.showMaximized()

        # Do version upgrade check
        if StrictVersion(settings.get('Pathomx/Current_version')) < StrictVersion(VERSION_STRING):
            # We've got an upgrade
            logging.info('Upgrade to %s' % VERSION_STRING)
            self.onAbout()
            settings.set('Pathomx/Current_version', VERSION_STRING)
        #if settings.value('/Pathomx/Offered_registration', False) != True:
        #    self.onDoRegister()
        #    settings.setValue('/Pathomx/Offered_registration', True)

        self.statusBar().showMessage(tr('Ready'))

    def addFileToolBar(self):
        t = self.addToolBar('File')
        t.setIconSize(QSize(16, 16))

        clear_workspaceAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'document.png')), 'New workspace…', self)
        clear_workspaceAction.setStatusTip('Create new workspace (clear current)')
        clear_workspaceAction.triggered.connect(self.onClearWorkspace)
        t.addAction(clear_workspaceAction)

        open_workflowAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'disk--arrow.png')), 'Open workflow…', self)
        open_workflowAction.setStatusTip('Open a saved workflow')
        open_workflowAction.triggered.connect(self.onOpenWorkflow)
        t.addAction(open_workflowAction)

        save_workflowAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'disk--pencil.png')), 'Save workflow As…', self)
        save_workflowAction.setStatusTip('Save workflow for future re-use')
        save_workflowAction.triggered.connect(self.onSaveWorkflowAs)
        t.addAction(save_workflowAction)

        export_ipythonnbAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'ipython.png')), 'Export IPython notebook…', self)
        export_ipythonnbAction.setStatusTip('Export workflow as IPython notebook')
        export_ipythonnbAction.triggered.connect(self.onExportIPyNotebook)
        t.addAction(export_ipythonnbAction)

        restart_kernelsAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'server--exclamation.png')), 'Restart kernels…', self)
        restart_kernelsAction.setStatusTip('Restart kernel runners')
        restart_kernelsAction.triggered.connect(self.onRestartKernels)
        t.addAction(restart_kernelsAction)

    def addEditorToolBar(self):
        t = self.addToolBar('Editor')
        t.setIconSize(QSize(16, 16))

        save_imageAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'image-export.png')), tr('Save workflow image…'), self)
        save_imageAction.setStatusTip('Show grid in workspace editor')
        save_imageAction.triggered.connect(self.editor.onSaveAsImage)
        t.addAction(save_imageAction)

        snap_gridAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'grid-snap.png')), tr('Snap to grid'), self)
        snap_gridAction.setStatusTip('Snap tools to grid')
        snap_gridAction.setCheckable(True)
        settings.add_handler('Editor/Snap_to_grid', snap_gridAction)
        t.addAction(snap_gridAction)

        show_gridAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'grid.png')), tr('Show grid'), self)
        show_gridAction.setStatusTip('Show grid in workspace editor')
        show_gridAction.setCheckable(True)
        settings.add_handler('Editor/Show_grid', show_gridAction)
        show_gridAction.triggered.connect(self.onGridToggle)
        t.addAction(show_gridAction)

    def addEditModeToolBar(self):
        t = self.addToolBar('Edit mode')
        t.setIconSize(QSize(16, 16))

        editormodeag = QActionGroup(self)

        normalAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'cursor.png')), tr('Edit mode'), self)
        normalAction.setCheckable(True)
        normalAction.setChecked(True)
        normalAction.setStatusTip('Default edit mode')
        normalAction.setActionGroup(editormodeag)
        #normalAction._px_value = EDITOR_MODE_NORMAL
        t.addAction(normalAction)

        add_textAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'layer-shape-text.png')), tr('Add text annotation…'), self)
        add_textAction.setCheckable(True)
        add_textAction.setStatusTip('Add text annotations to workflow')
        add_textAction.setActionGroup(editormodeag)
        #add_textAction._px_value = EDITOR_MODE_TEXT
        t.addAction(add_textAction)

        add_regionAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'zone.png')), tr('Add region annotation…'), self)
        add_regionAction.setCheckable(True)
        add_regionAction.setStatusTip('Add region annotations to workflow')
        add_regionAction.setActionGroup(editormodeag)
        #add_regionAction._px_value = EDITOR_MODE_REGION
        t.addAction(add_regionAction)

        self.editor.config.add_handler('mode', editormodeag)
        #self.editormodeag.triggered.connect( self.onEditorModeToggle )

    def addEditStyleToolBar(self):
    # ['font-family', 'font-size', 'text-bold', 'text-italic', 'text-underline', 'text-color', 'color-border', 'color-background']

        t = self.addToolBar('Style')
        t.setIconSize(QSize(16, 16))
        self.styletoolbarwidgets = {}

        font_listcb = QComboBox()
        font_listcb.addItems(self.fonts.families(QFontDatabase.Any))
        self.editor.config.add_handler('font-family', font_listcb)
        t.addWidget(font_listcb)
        self.styletoolbarwidgets['font-family'] = font_listcb

        font_sizecb = QComboBox()
        font_sizecb.addItems(['8', '9', '10', '11', '12', '14', '16', '18', '20', '22', '24', '26', '28', '36', '48', '72'])
        font_sizecb.setEditable(True)
        self.editor.config.add_handler('font-size', font_sizecb)
        t.addWidget(font_sizecb)
        self.styletoolbarwidgets['font-size'] = font_sizecb

        text_colorcb = ui.QColorButton()
        self.editor.config.add_handler('text-color', text_colorcb)
        t.addWidget(text_colorcb)
        self.styletoolbarwidgets['text-color'] = text_colorcb

        text_boldAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'edit-bold.png')), tr('Bold'), self)
        text_boldAction.setStatusTip('Set text bold')
        text_boldAction.setCheckable(True)
        self.editor.config.add_handler('text-bold', text_boldAction)
        t.addAction(text_boldAction)
        self.styletoolbarwidgets['text-bold'] = text_boldAction

        text_italicAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'edit-italic.png')), tr('Italic'), self)
        text_italicAction.setStatusTip('Set text italic')
        text_italicAction.setCheckable(True)
        self.editor.config.add_handler('text-italic', text_italicAction)
        t.addAction(text_italicAction)
        self.styletoolbarwidgets['text-italic'] = text_italicAction

        text_underlineAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'edit-underline.png')), tr('Underline'), self)
        text_underlineAction.setStatusTip('Set text underline')
        text_underlineAction.setCheckable(True)
        self.editor.config.add_handler('text-underline', text_underlineAction)
        t.addAction(text_underlineAction)
        self.styletoolbarwidgets['text-underline'] = text_underlineAction

        border_colorcb = ui.QColorButton()
        self.editor.config.add_handler('color-border', border_colorcb)
        t.addWidget(border_colorcb)
        self.styletoolbarwidgets['color-border'] = border_colorcb

        background_colorcb = ui.QColorButton()
        self.editor.config.add_handler('color-background', background_colorcb)
        t.addWidget(background_colorcb)
        self.styletoolbarwidgets['color-background'] = background_colorcb

    def onGridToggle(self):
        if settings.get('Editor/Show_grid'):
            self.editor.showGrid()
        else:
            self.editor.hideGrid()

    def onLogItemClicked(self, item):
        # When an item in the log viewer is clicked, center on the associated Tool
        # this will fail if there is none (i.e. non-tool log item) so wrapped in an try, except.
        try:
            item.tool.editorItem.centerSelf()
        except:
            pass

    def onLogItemDoubleClicked(self, item):
        # When an item in the log viewer is clicked, center on the associated Tool
        # this will fail if there is none (i.e. non-tool log item) so wrapped in an try, except.
        try:
            item.tool.show()
        except:
            pass

    def onChangePlugins(self):
        dialog = plugins.dialogPluginManagement(self)
        if dialog.exec_():
            pass

    def onCheckPluginUpdates(self):
        pass

    def onDBExplore(self):
        self.dbtool.show()

    # Init application configuration
    def onResetConfig(self):
        # Reset the QSettings object on the QSettings Manager (will auto-fallback to defined defaults)
        settings.settings.clear()
    # UI Events

    def updateProgressBar(self):
        self.threadCount.setText('%d/%d' % (notebook_queue.no_of_active_runners, notebook_queue.no_of_runners))
        self.jobQueue.setText('%d' % len(notebook_queue.jobs))

    def onGoToPathomxWeb(self):
        QDesktopServices.openUrl(QUrl('http://pathomx.org'))

    def onGoToPathomxDemos(self):
        QDesktopServices.openUrl(QUrl('http://pathomx.org/demos'))

    def onGoToPathomxDocs(self):
        QDesktopServices.openUrl(QUrl('http://docs.pathomx.org/'))

    def onDoRegister(self):
        # Pop-up a registration window; take an email address and submit to
        # register for update-announce.
        dlg = ui.DialogRegister(self)
        if dlg.exec_():
            # Perform registration
            data = {
                'name': dlg.name.text(),
                'email': dlg.email.text(),
                'country': dlg.country.currentText(),
                'research': dlg.research.text(),
                'institution': dlg.institution.text(),
                'type': dlg.type.currentText(),
                'register': dlg.register.checked(),
            }
            # Send data to server;
            # http://register.pathomx.org POST

    def onDefineClassStyles(self):
        dlg = ui.MatchStyleManagerDialog(self)
        if dlg.exec_():
            self.onRefreshAllViews()

    def onRefreshAllViews(self):
        for t in current_tools:
            t.views.style_updated.emit()

    def onBrowserNav(self, url):
        # Interpret internal URLs for message passing to display Compound, Reaction, Pathway data in the sidebar interface
        # then block the continued loading
        if url.isRelative() and url.hasFragment():
            # Local #url; pass to default handler
            pass

        if url.scheme() == 'pathomx':
            # Take string from pathomx:// onwards, split on /
            app = url.host()
            if app == 'app-manager':
                app, action = url.path().strip('/').split('/')
                if action == 'add':
                    a = app_launchers[app]()

                # Update workspace viewer
                self.workspace_updated.emit()  # Notify change to workspace layout

            elif app == 'db':
                kind, id, action = url.path().strip('/').split('/')
                            # View an object
                if action == 'view':
                    if kind == 'pathway' and db.dbm.pathway(id) is not None:
                        pathway = db.dbm.pathway(id)
                        self.generatedbBrowserView(template='db/pathway.html', data={
                            'title': pathway.name,
                            'object': pathway,
                            })
                    elif kind == 'reaction' and db.dbm.reaction(id) is not None:
                        reaction = db.dbm.reaction(id)
                        self.generatedbBrowserView(template='db/reaction.html', data={
                            'title': reaction.name,
                            'object': reaction,
                            })
                    elif kind == 'compound' and db.dbm.compound(id) is not None:
                        compound = db.dbm.compound(id)
                        self.generatedbBrowserView(template='db/compound.html', data={
                            'title': compound.name,
                            'object': compound,
                            })
                    elif kind == 'protein' and db.dbm.protein(id) is not None:
                        protein = db.dbm.protein(id)
                        self.generatedbBrowserView(template='db/protein.html', data={
                            'title': protein.name,
                            'object': protein,
                            })
                    elif kind == 'gene' and db.dbm.gene(id) is not None:
                        gene = db.dbm.gene(id)
                        self.generatedbBrowserView(template='db/gene.html', data={
                            'title': gene.name,
                            'object': gene,
                            })

                    # Focus the database window
                    self.dbtool.raise_()

            #metaviz/compound/%s/view
            elif app in self.url_handlers:
                for handler in self.url_handlers[app]:
                    handler(url.path().strip('/'))

            # Store URL so we can reload the sidebar later
            self.dbBrowser_CurrentURL = url

        else:
            # It's an URL open in default browser
            QDesktopServices.openUrl(url)

    def onAbout(self):
        dlg = ui.DialogAbout(self)
        dlg.exec_()

    def onExit(self):
        self.Close(True)  # Close the frame.

    def onRefresh(self):
        self.generateGraphView()

    '''
    def generatedbBrowserView(self, template='base.html', data={'title': '', 'object': {}, 'data': {}}):
        metadata = {
            'htmlbase': os.path.join(utils.scriptdir, 'html'),
            # Current state data
            'current_pathways': [],  # self.config.value('/Pathways/Show').split(','),
            'data': None #self.data,
            # Color schemes
            # 'rdbu9':['b2182b', 'd6604d', 'f4a582', '33a02c', 'fddbc7', 'f7f7f7', 'd1e5f0', '92c5de', '4393c3', '2166ac']
        }

        template = self.templateEngine.get_template(template)
        #self.dbBrowser.setHtml(template.render(dict(list(data.items()) + list(metadata.items()))), QUrl("~"))
    '''

    def register_url_handler(self, identifier, url_handler):
        url_handlers[identifier].append(url_handler)

    ### OPEN/SAVE WORKSPACE
    def onOpenWorkspace(self):
        self.openWorkspace('/Users/mxf793/Desktop/test.mpw')

    def openWorkspace(self, fn):
        pass

    def onSaveWorkspace(self):
        self.saveWorkspace('/Users/mxf793/Desktop/test.mpw')

    def onSaveWorkspaceAs(self):
        self.saveWorkspace('/Users/mxf793/Desktop/test.mpw')

    def saveWorkspace(self, fn):
        pass

    ### RESET WORKSPACE
    def onClearWorkspace(self):
        reply = QMessageBox.question(self, "Clear Workspace", "Are you sure you want to clear the workspace? Everything will be deleted.",
                            QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.clearWorkspace()

    def clearWorkspace(self):
        for t in current_tools[:]:
            t.deleteLater()

        for i in self.editor.items()[:]:  # Copy as i.delete modifies the list
            try:
                # If has a delete handler use it (for clean up) else just remove from the scene
                i.delete()
            except:
                self.editor.removeItem(i)

        # Remove all workspace datasets
        del self.datasets[:]

        # Completely wipe the scene
        self.editView.resetScene()
        self.editor = self.editView.scene

        self.workspace_updated.emit()

    ### OPEN/SAVE WORKFLOWS
    def onSaveWorkflowAs(self):
        filename, _ = QFileDialog.getSaveFileName(self, 'Save current workflow', '', "Pathomx Workflow Format (*.mpf)")
        if filename:
            self.saveWorkflow(filename)

    def saveWorkflow(self, fn):

        root = et.Element("Workflow")
        root.set('xmlns:mpwfml', "http://pathomx.org/schema/Workflow/2013a")

        s = et.SubElement(root, "Styles")
        s = styles.getXMLMatchDefinitionsStyles(s)

        s = et.SubElement(root, "Annotations")
        s = self.editor.getXMLAnnotations(s)

        # Build a JSONable object representing the entire current workspace and write it to file
        for v in current_tools:
            app = et.SubElement(root, "App")
            app.set("id", v.id)

            name = et.SubElement(app, "Name")
            name.text = v.name

            plugin = et.SubElement(app, "Plugin")
            plugin.set("version", '1.0')
            plugin.text = type(v.plugin).__name__

            plugin_class = et.SubElement(app, "Launcher")
            plugin_class.text = type(v).__name__

            position = et.SubElement(app, "EditorXY")
            position.set("x", str(v.editorItem.x()))
            position.set("y", str(v.editorItem.y()))

            app = v.config.getXMLConfig(app)

            datasources = et.SubElement(app, "DataInputs")
            # Build data inputs table (outputs are pre-specified by the object; this == links)
            for sk, si in list(v.data.i.items()):
                if si:  # Something on this interface
                    cs = et.SubElement(datasources, "Input")
                    cs.set("id", sk)
                    cs.set("manager", si.manager.id)
                    cs.set("interface", si.manager_interface)

        tree = et.ElementTree(root)
        tree.write(fn)  # , pretty_print=True)

    def onOpenWorkflow(self):
        """ Open a data file"""
        filename, _ = QFileDialog.getOpenFileName(self, 'Open new workflow', '', "Pathomx Workflow Format (*.mpf)")
        if filename:
            self.openWorkflow(filename)

    def openWorkflow(self, fn):
        logging.info("Loading workflow... %s" % fn)
        # Wipe existing workspace
        self.clearWorkspace()
        # Load from file
        tree = et.parse(fn)
        workflow = tree.getroot()

        s = workflow.find('Styles')
        if s is not None:
            styles.setXMLMatchDefinitionsStyles(s)

        a = workflow.find('Annotations')
        if a is not None:
            self.editor.setXMLAnnotations(a)

        appref = {}
        logging.info("...Loading apps.")
        for xapp in workflow.findall('App'):
            # FIXME: This does not work with multiple launchers/plugin - define as plugin.class?
            # Check plugins loaded etc.
            logging.info(('- %s' % xapp.find('Name').text))
            app = app_launchers["%s.%s" % (xapp.find("Plugin").text, xapp.find("Launcher").text)](self, auto_consume_data=False, name=xapp.find('Name').text)
            editorxy = xapp.find('EditorXY')
            app.editorItem.setPos(QPointF(float(editorxy.get('x')), float(editorxy.get('y'))))
            appref[xapp.get('id')] = app

        logging.info("...Linking objects.")
        # Now build the links between objects; we need to force these as data is not present
        for xapp in workflow.findall('App'):
            app = appref[xapp.get('id')]

            for idef in xapp.findall('DataInputs/Input'):
                source_app = appref[idef.get('manager')]
                source = idef.get('interface')
                if source in source_app.legacy_outputs.keys():
                    source = source_app.legacy_outputs[source]

                sink = idef.get('id')
                if sink in app.legacy_inputs.keys():
                    sink = app.legacy_inputs[sink]

                app.data._consume_action(source_app.data, source, sink)

        logging.info("Load complete.")
        # Focus the home tab & refresh the view
        self.workspace_updated.emit()

    def onExportIPyNotebook(self):
        filename, _ = QFileDialog.getSaveFileName(self, 'Export workflow to IPython notebook ', '', "Pathomx Workflow Format (*.ipynb)")
        if filename:
            self.export_to_notebook(filename)

    def export_to_notebook(self, filename):
        '''
        Export an IPython notebook representing the entire workflow
        '''
        if len(current_tools) == 0:
            return False
            
        # Start by finding tools with no inputs; these are the 'origins' of analysis
        # either by importing from files, or being standalone
        # We generate the remainder of the tree from these items
        workbook_cells = []
        process_queue = []
        tools_output_done = []

        for t in current_tools:
            # The following will give an empty list if there are no inputs, or they're all unassigned
            tw = [v for k, v in t.data.i.items() if v is not None]
            if not tw:
                # Empty
                process_queue.append((0, t))  # Depth 0

        '''
        The process is to iterate down all the watchers from the origin tools. At each point
        get the watchers and put them on a stack, with level+1. On each output check if 
        all the watchers have been 'done' (on the output stack) and if not, continue on.
        '''
        logging.debug("Starting export with %d origins" % len(process_queue))

        while len(process_queue) > 0:
            lvl, tool = process_queue.pop(0)  # From front
            # Check for what that this tool depends on
            parents = [s[0].v for i, s in tool.data.i.items() if s is not None]

            if len(parents) > 0 and len(set(parents) - set(tools_output_done)) > 0:
                # We're waiting on something here, push to the back of the list
                process_queue.append((lvl, tool))

            # We're good to go! 
            # First add the input-shims from any sources.
            input_shim = []
            for i,sm in tool.data.i.items():
                if sm:
                    mo, mi = sm
                    input_shim.append( "%s = %s_%s;" % ( i, mi, id(mo.v) ) )

            if input_shim:
                c = new_code_cell(  ';\n'.join(input_shim) )
                workbook_cells.append( c )
            
            # Now add the config as a dict definition
            c = new_code_cell( "config = %s;" % tool.config.as_dict() )
            workbook_cells.append( c )
            
            # Output the notebook itself. Use the source Luke; not the mangled version
            for ws in tool.nb_source.worksheets:
                for cell in ws.cells:
                    # Output variables of each script are shim-suffixed with the id of the tool (unique)
                    # e.g. output_data_123 = output_data
                    # input_data = output_data_123
                    # We can skip this step if the following tool is the target of the data, but this
                    # will need the generator to be more intelligent
                    workbook_cells.append(cell)
                    
            # Now add the output-shims from any sources.
            output_shim = []
            for o,d in tool.data.o.items():
                if d is not None:
                    output_shim.append( "%s_%s = %s;" % ( o, id(tool), o ) )

            if output_shim:
                c = new_code_cell( ';\n'.join(output_shim) )
                workbook_cells.append( c )
                    

            tools_output_done.append(tool)

            # Add watchers to the list
            watchers = [w.v for k, v in tool.data.watchers.items() for w in v]
            for w in watchers:
                if w not in tools_output_done:
                    process_queue.append((lvl + 1, w))

            logging.debug("- %d queued; %d done; %d cells" % (len(process_queue), len(tools_output_done), len(workbook_cells)))

        logging.debug("Finished: %d cells" % len(workbook_cells))
        # The resulting workbook in workbook_cells
        # Build an output one using an available structure; then re-json to save
        notebook = copy(tool.nb)
        notebook.worksheets[0].cells = workbook_cells
        with open(filename, 'w') as f:
            write_notebook(notebook, f, 'json')

    def onRestartKernels(self):
        notebook_queue.restart()

#class QApplicationExtend(QApplication):
    #def event(self, e):
    #    if e.type() == QEvent.FileOpen:
    #        fn, fe = os.path.splitext(e.file())
    #        formats = {  # Run specific loading function for different source data types
    #                '.ipynb': self.openIPythonNotebook,
    #            }
    #        if fe in list(formats.keys()):
    #            formats[fe](e.file())
    #
    #        return True
    #
    #    else:
    #        return super(QApplicationExtend, self).event(e)

def main():



    # Create a Qt application
    app = QApplication(sys.argv)
    app.setStyle('fusion')

    app.setOrganizationName("Pathomx")
    app.setOrganizationDomain("pathomx.org")
    app.setApplicationName("Pathomx")

    logging.debug('Setting up localisation...')

    locale = QLocale.system().name()
    #locale = 'nl'

    # Load base QT translations from the normal place (does not include _nl, or _it)
    translator_qt = QTranslator()
    if translator_qt.load("qt_%s" % locale, QLibraryInfo.location(QLibraryInfo.TranslationsPath)):
        logging.debug(("Loaded Qt translations for locale: %s" % locale))
        app.installTranslator(translator_qt)

    # See if we've got a default copy for _nl, _it or others
    elif translator_qt.load("qt_%s" % locale, os.path.join(utils.scriptdir, 'translations')):
        logging.debug(("Loaded Qt (self) translations for locale: %s" % locale))
        app.installTranslator(translator_qt)

    # Load Pathomx specific translations
    translator_mp = QTranslator()
    if translator_mp.load("pathomx_%s" % locale, os.path.join(utils.scriptdir, 'translations')):
        logging.debug(("Loaded Pathomx translations for locale: %s" % locale))
    app.installTranslator(translator_mp)

    # We've got a qApp instance going, set up timers
    notebook_queue.start_timers()

    MainWindow()
    logging.info('Ready.')
    app.exec_()  # Enter Qt application main loop
    logging.info('Exiting.')
    sys.exit()
