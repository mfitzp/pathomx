# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import sys
import logging

frozen = getattr(sys, 'frozen', False)
ON_RTD = os.environ.get('READTHEDOCS', None) == 'True'

if sys.platform == 'win32' and sys.executable.split('\\')[-1] == 'pythonw.exe':
    # Dump all output when running without a console; otherwise will hang
    sys.stdout = open(os.devnull, 'w')
    sys.stderr = open(os.devnull, 'w')
    frozen = True

elif sys.version_info < (3, 0) and ON_RTD is False:  # Python 2 only; unicode output fixes
    import codecs
    UTF8Writer = codecs.getwriter('utf8')
    sys.stdout = UTF8Writer(sys.stdout)
    reload(sys).setdefaultencoding('utf8')

if frozen:
    logging.basicConfig(level=logging.INFO)
    os.environ['QT_API'] = 'pyqt5'
else:
    logging.basicConfig(level=logging.DEBUG)

from .qt import *
from copy import copy

# Console widget
from IPython.qt.console.rich_ipython_widget import RichIPythonWidget

from collections import defaultdict

try:
    import xml.etree.cElementTree as et
except ImportError:
    import xml.etree.ElementTree as et

import requests
import time

from .globals import styles, notebook_queue, \
                     current_tools, current_tools_by_id, installed_plugin_names, current_datasets, \
                     settings, url_handlers, app_launchers, mono_fontFamily, available_tools_by_category, \
                     plugin_categories, plugin_manager, plugin_metadata

from . import utils
from . import ui
from . import plugins  # plugin helper/manager
from .editor.editor import WorkspaceEditorView  # EDITOR_MODE_NORMAL, EDITOR_MODE_TEXT, EDITOR_MODE_REGION

# Translation (@default context)
from .translate import tr

from distutils.version import StrictVersion

__version__ = open(os.path.join(utils.basedir, 'VERSION'), 'rU').read()

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

PATHWAY_ROOTS = ['Activation-Inactivation-Interconversion', 'Biosynthesis', 'Degradation', 'Detoxification', 'Energy-Metabolism', 'Macromolecule-Modification', 'Metabolic-Clusters', 'Signaling-Pathways', 'Super-Pathways']


class ToolTreeWidget(QTreeWidget):

    def __init__(self, *args, **kwargs):
        super(ToolTreeWidget, self).__init__(*args, **kwargs)
        self.itemDoubleClicked.connect(self.double_click_launcher)

    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.LeftButton:  # Possible fix for Windows hang bug https://bugreports.qt-project.org/browse/QTBUG-10180
            logging.debug('Starting drag-drop of workspace item.')
            item = self.currentItem()

            mimeData = QMimeData()
            mimeData.setData('application/x-pathomx-app', item.data['id'])

            e.accept()

            drag = QDrag(self)
            drag.setMimeData(mimeData)
            drag.setPixmap(item.data['icon'].pixmap(64, 64))
            drag.setHotSpot(QPoint(32, 32))  # - self.visualItemRect(item).top())

            drag.exec_(Qt.CopyAction)
            logging.debug('Drag-drop complete.')

        else:
            e.ignore()

    def double_click_launcher(self, item):
        app_id = item.data['id']
        self.m.editor.createApp(app_id)


class MainWindow(QMainWindow):

    workspace_updated = pyqtSignal()

    def __init__(self):
        super(MainWindow, self).__init__()

        # Initiate logging
        self.logView = QTextEdit()
        self.logView.setReadOnly(True)
        self.logView.setFont(QFont(mono_fontFamily))

        logHandler = ui.Logger(self, self.logView)
        logging.getLogger().addHandler(logHandler)
        logging.info('Welcome to Pathomx v%s' % (__version__))

        # Central variable for storing application configuration (load/save from file?
        if settings.get('Pathomx/Is_setup') is False:
            logging.info("Setting up initial configuration...")
            # Defaults are now set in the globals; but we can auto-create the plugin folder
            try:
                utils.mkdir_p(os.path.join(os.path.expanduser("~"), 'PathomxPlugins'))
            except:
                # Ignore all errors
                pass
            logging.info('Done')

        # Do version upgrade availability check
        # FIXME: Do check for new download here; if not done > 1 weeks
        if settings.get('Pathomx/Update/Last_checked') < (int(time.time()) - 604800):  # 1 week in seconds
            try:
                r = requests.get('https://raw.githubusercontent.com/pathomx/pathomx/master/VERSION')

            except:
                pass

            else:
                if r.status_code == 200:
                    settings.set('Pathomx/Update/Latest_version', r.text)

            settings.set('Pathomx/Update/Last_checked', int(time.time()))

        self.fonts = QFontDatabase()

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
            #'database': self.menuBar().addMenu(tr('&Database')),
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

        saveAsAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'disk--pencil.png')), tr('Save &As…'), self)
        saveAsAction.setShortcut('Ctrl+A')
        saveAsAction.setStatusTip(tr('Save current workspace for future use'))
        saveAsAction.triggered.connect(self.onSaveWorkspaceAs)

        saveAsAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'disk--pencil.png')), tr('Save Workflow As…'), self)
        saveAsAction.setStatusTip(tr('Save current workflow for future use'))
        saveAsAction.triggered.connect(self.onSaveWorkflowAs)
        self.menuBars['file'].addAction(saveAsAction)
        #self.menuBars['file'].addSeparator()

        export_ipythonnbAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'ipython.png')), 'Export IPython notebook…', self)
        export_ipythonnbAction.setStatusTip('Export workflow as IPython notebook')
        export_ipythonnbAction.triggered.connect(self.onExportIPyNotebook)
        #self.menuBars['file'].addAction(export_ipythonnbAction)

        export_reportAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'report--pencil.png')), 'Export workflow report…', self)
        export_reportAction.setStatusTip('Export workflow as report')
        export_reportAction.triggered.connect(self.onExportReport)
        #self.menuBars['file'].addAction(export_reportAction)

        #printAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'printer.png')), tr('&Print…'), self)
        #printAction.setShortcut('Ctrl+P')
        #printAction.setStatusTip(tr('Print current figure'))
        #printAction.triggered.connect(self.onPrint)
        #self.menuBars['file'].addAction(printAction)

        self.menuBars['file'].addSeparator()

        # DATABASE MENU
        #explore_dbAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'database-explore.png')), tr('&Explore database…'), self)
        #explore_dbAction.setStatusTip('Explore database')
        #explore_dbAction.triggered.connect(self.onDBExplore)
        #self.menuBars['database'].addAction(explore_dbAction)

        #self.menuBars['database'].addSeparator()

        # PLUGINS MENU
        change_pluginsAction = QAction(tr('&Manage plugins…'), self)
        change_pluginsAction.setStatusTip('Manage plugin locations and activate/deactivate plugins')
        change_pluginsAction.triggered.connect(self.onChangePlugins)
        self.menuBars['plugins'].addAction(change_pluginsAction)

        refresh_pluginsAction = QAction(tr('&Rebuild toolbox'), self)
        refresh_pluginsAction.setStatusTip('Refresh toolbox with available plugins')
        refresh_pluginsAction.triggered.connect(self.buildToolbox)
        self.menuBars['plugins'].addAction(refresh_pluginsAction)

        linemarkerstyleAction = QAction('Line and marker styles…', self)
        linemarkerstyleAction.setStatusTip(tr('Set line and marker styles for data classes'))
        linemarkerstyleAction.triggered.connect(self.onDefineClassStyles)
        self.menuBars['appearance'].addAction(linemarkerstyleAction)

        aboutAction = QAction(QIcon.fromTheme("help-about"), 'About Pathomx', self)
        aboutAction.setStatusTip(tr('About Pathomx'))
        aboutAction.triggered.connect(self.onAbout)
        self.menuBars['help'].addAction(aboutAction)

        def do_open_web(href):
            return lambda: QDesktopServices.openUrl(QUrl(href))

        goto_pathomx_gettingstartedAction = QAction(tr('&Getting started'), self)
        goto_pathomx_gettingstartedAction.setStatusTip('See the getting started documentation')
        goto_pathomx_gettingstartedAction.triggered.connect(do_open_web('http://docs.pathomx.org/en/latest/getting_started.html'))
        self.menuBars['help'].addAction(goto_pathomx_gettingstartedAction)

        self.menuBars['help'].addSeparator()

        goto_pathomx_websiteAction = QAction(tr('&Homepage…'), self)
        goto_pathomx_websiteAction.setStatusTip('Go to the Pathomx website')
        goto_pathomx_websiteAction.triggered.connect(do_open_web('http://pathomx.org'))
        self.menuBars['help'].addAction(goto_pathomx_websiteAction)

        goto_pathomx_docsAction = QAction(tr('&Documentation…'), self)
        goto_pathomx_docsAction.setStatusTip('Read latest Pathomx documentation')
        goto_pathomx_docsAction.triggered.connect(do_open_web('http://docs.pathomx.org'))
        self.menuBars['help'].addAction(goto_pathomx_docsAction)

        goto_pathomx_docsSupport = QAction(tr('&Support…'), self)
        goto_pathomx_docsSupport.setStatusTip('Get support with Pathomx')
        goto_pathomx_docsSupport.triggered.connect(do_open_web('http://docs.pathomx.org/en/latest/support.html'))
        self.menuBars['help'].addAction(goto_pathomx_docsSupport)

        self.menuBars['help'].addSeparator()

        pathomx_demo_menu = self.menuBars['help'].addMenu(tr('Example &workflows'))

        self.menuBars['file'].addSeparator()
        pathomx_demo_menu_f = self.menuBars['file'].addMenu(tr('Example &workflows'))

        demofiles = os.listdir(os.path.join(utils.scriptdir, 'demos'))

        def do_open_demo(f):
            return lambda: self.onOpenDemoWorkflow(os.path.join(utils.scriptdir, 'demos', f))

        for f in demofiles:
            name, ext = f.split('.')
            if ext == 'mpf':
                name = name.replace('_', ' ')
                open_demo_file = QAction(name, self)
                open_demo_file.setStatusTip("Load the '%s' demo workflow" % name)
                open_demo_file.triggered.connect(do_open_demo(f))
                pathomx_demo_menu.addAction(open_demo_file)
                pathomx_demo_menu_f.addAction(open_demo_file)

        goto_pathomx_onlineDemos = QAction(tr('&Online demos && walkthroughs…'), self)
        goto_pathomx_onlineDemos.setStatusTip('See all demos available online')
        goto_pathomx_onlineDemos.triggered.connect(do_open_web('http://docs.pathomx.org/en/latest/demos/index.html'))
        self.menuBars['help'].addAction(goto_pathomx_onlineDemos)

        #self.menuBars['help'].addSeparator()
        #do_registerAction = QAction(tr('&Register Pathomx'), self)
        #do_registerAction.setStatusTip('Register Pathomx for release updates')
        #do_registerAction.triggered.connect(self.onDoRegister)
        #self.menuBars['help'].addAction(do_registerAction)

        # GLOBAL WEB SETTINGS
        QNetworkProxyFactory.setUseSystemConfiguration(True)

        QWebSettings.setMaximumPagesInCache(0)
        QWebSettings.setObjectCacheCapacities(0, 0, 0)
        QWebSettings.clearMemoryCaches()

        # INIT PLUGINS AND TOOLS

        # We pass a copy of main window object in to the plugin manager so it can
        # be available for loading
        plugin_manager.m = self

        self.toolbox = ToolTreeWidget(self)  # QToolBox(self)
        self.toolbox.setHeaderLabels(['Available tools'])
        self.toolbox.setUniformRowHeights(True)
        self.toolbox.m = self
        self.buildToolbox()

        self.toolDock = QDockWidget(tr('Toolbox'))
        self.toolDock.setWidget(self.toolbox)
        self.toolDock.setMinimumWidth(300)
        self.toolDock.setMaximumWidth(300)

        self.toolDock.raise_()
        #self.dbtool = ui.DbApp(self)
        #self.dbBrowser = self.dbtool.dbBrowser

        self.setWindowTitle(tr('Pathomx'))

        self.kernelStatus = ui.KernelStatusWidget()
        self.statusBar().addPermanentWidget(self.kernelStatus)

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
        self._progressBar_timer.start(500)  # Update the progress bar / thread-watcher every second

        self.progressTracker = {}  # Dict storing values for each view/object

        self.editView = WorkspaceEditorView(self)
        self.editor = self.editView.scene

        # IPython Widget for internal (user) console
        self.console = RichIPythonWidget()
        self.console._call_tip = lambda: None
        self.console.kernel_manager = notebook_queue.in_process_runner.kernel_manager
        self.console.kernel_client = notebook_queue.in_process_runner.kernel_client

        self.central = QTabWidget()
        self.central.setDocumentMode(True)
        self.central.setTabPosition(QTabWidget.South)

        self.central.addTab(self.editView, '&Editor')
        self.central.addTab(self.console, '&Console')
        self.central.addTab(self.logView, '&Log')

        self.workspaceDock = QDockWidget(tr('Workspace'))
        self.workspaceDock.setWidget(self.central)
        self.workspaceDock.setMinimumHeight(300)

        self.activetoolDock = QDockWidget(tr('Active'))
        self.activetoolDock.setWidget(QWidget(None))
        self.activetoolDock.setMinimumHeight(300)

        self.dummy = QWidget()
        self.dummy.hide()
        self.setCentralWidget(self.dummy)

        self.workspaceDock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetVerticalTitleBar)
        self.activetoolDock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetVerticalTitleBar)

        self.setCorner(Qt.TopLeftCorner, Qt.LeftDockWidgetArea)
        self.setCorner(Qt.BottomLeftCorner, Qt.LeftDockWidgetArea)

        self.setCorner(Qt.TopRightCorner, Qt.RightDockWidgetArea)
        self.setCorner(Qt.BottomRightCorner, Qt.RightDockWidgetArea)

        self.addDockWidget(Qt.LeftDockWidgetArea, self.toolDock)
        self.addDockWidget(Qt.RightDockWidgetArea, self.workspaceDock)
        self.addDockWidget(Qt.RightDockWidgetArea, self.activetoolDock)

        self.addFileToolBar()
        self.addEditorToolBar()
        self.addEditModeToolBar()
        self.addEditStyleToolBar()

        self.showMaximized()

        # Do version upgrade check
        if StrictVersion(settings.get('Pathomx/Current_version')) < StrictVersion(__version__):
            # We've got an upgrade
            logging.info('Upgraded Pathomx to %s' % __version__)
            self.onAbout()
            settings.set('Pathomx/Current_version', __version__)
        #if settings.value('/Pathomx/Offered_registration', False) != True:
        #    self.onDoRegister()
        #    settings.setValue('/Pathomx/Offered_registration', True)

        if StrictVersion(settings.get('Pathomx/Update/Latest_version')) > StrictVersion(__version__):
            # We've got an upgrade
            notify_version = 'A new version of Pathomx (v%s) is available' % settings.get('Pathomx/Update/Latest_version')
            logging.info(notify_version)
            self.statusBar().showMessage(notify_version)
        else:
            self.statusBar().showMessage(tr('Ready'))

    def buildToolbox(self):

        plugins.get_available_plugins()
        disabled_plugins = settings.get('Plugins/Disabled')

        tool_category_icons = {
               "Import": QIcon(os.path.join(utils.scriptdir, 'icons', 'folder-open-document.png')),
               "Processing": QIcon(os.path.join(utils.scriptdir, 'icons', 'ruler-triangle.png')),
               "Filter": QIcon(os.path.join(utils.scriptdir, 'icons', 'funnel.png')),
               "Identification": QIcon(os.path.join(utils.scriptdir, 'icons', 'target.png')),
               "Analysis": QIcon(os.path.join(utils.scriptdir, 'icons', 'calculator.png')),
               "Visualisation": QIcon(os.path.join(utils.scriptdir, 'icons', 'star.png')),
               "Export": QIcon(os.path.join(utils.scriptdir, 'icons', 'disk--pencil.png')),
               "Scripting": QIcon(os.path.join(utils.scriptdir, 'icons', 'scripts-text.png')),
               }

        self.toolbox.clear()
        for category in plugin_categories:
            item = QTreeWidgetItem()
            item.setText(0, category)
            item.setIcon(0, tool_category_icons[category])
            self.toolbox.addTopLevelItem(item)
            for tool in available_tools_by_category[category]:
                if tool['plugin'].metadata['path'] in disabled_plugins:
                    # Skip deactivated plugins
                    continue

                ti = QTreeWidgetItem()
                ti.setText(0, getattr(tool['app'], 'name', tool['plugin'].name))

                if tool['app'].icon:
                    icon_path = os.path.join(tool['plugin'].path, tool['app'].icon)
                else:
                    icon_path = os.path.join(tool['plugin'].path, 'icon.png')

                tool['icon'] = QIcon(icon_path)

                ti.setIcon(0, tool['icon'])
                ti.setToolTip(0, tool['plugin'].metadata['description'])
                ti.data = tool
                item.addChild(ti)
            item.sortChildren(0, Qt.AscendingOrder)

        self.toolbox.expandAll()

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
        #t.addAction(export_ipythonnbAction)

        export_reportAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'report--pencil.png')), 'Export report…', self)
        export_reportAction.setStatusTip('Export workflow as report')
        export_reportAction.triggered.connect(self.onExportReport)
        #t.addAction(export_reportAction)

        interrupt_kernelsAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'server--exclamation.png')), 'Restart cluster…', self)
        interrupt_kernelsAction.setStatusTip('Interrupt kernel(s), stop processing and restart cluster')
        interrupt_kernelsAction.triggered.connect(self.onInterruptKernels)
        t.addAction(interrupt_kernelsAction)

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

        auto_placementAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'lightning.png')), tr('Auto position'), self)
        auto_placementAction.setStatusTip('Automatically position tools in workflow editor')
        auto_placementAction.setCheckable(True)
        settings.add_handler('Editor/Auto_position', auto_placementAction)
        t.addAction(auto_placementAction)


    def addEditModeToolBar(self):
        t = self.addToolBar('Edit mode')
        t.setIconSize(QSize(16, 16))

        editormodeag = QActionGroup(self)

        normalAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'cursor.png')), tr('Edit mode'), self)
        normalAction.setCheckable(True)
        normalAction.setChecked(True)
        normalAction.setStatusTip('Default edit mode')
        normalAction.setActionGroup(editormodeag)
        t.addAction(normalAction)

        add_textAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'layer-shape-text.png')), tr('Add text annotation…'), self)
        add_textAction.setCheckable(True)
        add_textAction.setStatusTip('Add text annotations to workflow')
        add_textAction.setActionGroup(editormodeag)
        t.addAction(add_textAction)

        add_regionAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'zone.png')), tr('Add region annotation…'), self)
        add_regionAction.setCheckable(True)
        add_regionAction.setStatusTip('Add region annotations to workflow')
        add_regionAction.setActionGroup(editormodeag)
        t.addAction(add_regionAction)

        self.editor.config.add_handler('mode', editormodeag)

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
            settings.set('Plugins/Paths', dialog.config.get('Plugins/Paths'))
            settings.set('Plugins/Disabled', dialog.config.get('Plugins/Disabled'))
            self.buildToolbox()

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
        self.kernelStatus.update(notebook_queue)
        #self.threadCount.setText('%d' % (notebook_queue.no_of_active_runners, notebook_queue.no_of_runners))
        self.jobQueue.setText('%d' % len(notebook_queue.jobs))

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
        # Interpret internal URLs for message passing to display Compound, Reaction, Pathway data in the sidebar
        # interface then block the continued loading
        if url.isRelative() and url.hasFragment():
            # Local #url; pass to default handler
            pass

        if url.scheme() == 'pathomx':
            # Take string from pathomx:// onwards, split on /
            app = url.host()

            if app == 'db':
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

    def deselectTool(self):
        self.toolDock.setWidget(self.toolbox)

    def selectTool(self, t):
        t.show()

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

    def onOpenDemoWorkflow(self, fn):
        reply = QMessageBox.question(self, "Open demo workflow", "Are you sure you want to open the demo workflow? Your current workflow will be lost.",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.openWorkflow(fn)

    ### RESET WORKSPACE
    def onClearWorkspace(self):
        reply = QMessageBox.question(self, "Clear Workspace", "Are you sure you want to clear the workspace? Everything will be deleted.",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.clearWorkspace()

    def clearWorkspace(self):

        global current_tools, current_tools_by_id, current_datasets

        for t in current_tools[:]:
            try:
                t.deleteLater()
            except:
                pass

        for i in self.editor.items()[:]:  # Copy as i.delete modifies the list
            try:
                # If has a delete handler use it (for clean up) else just remove from the scene
                i.delete()
            except:
                self.editor.removeItem(i)

        # Really wipe everything
        current_tools = []
        current_tools_by_id = {}
        current_datasets = []

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
                    cs.set("manager", si[0].id)
                    cs.set("interface", si[1])

            if v.code != v.default_code:
                code = et.SubElement(app, "Code")
                code.text = v.code

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

            xcode = xapp.find('Code')
            if xcode is not None:
                code = xcode.text
            else:
                code = ""

            app = app_launchers["%s.%s" % (xapp.find("Plugin").text, xapp.find("Launcher").text)](self, code=code, auto_consume_data=False, name=xapp.find('Name').text)
            editorxy = xapp.find('EditorXY')
            app.editorItem.setPos(QPointF(float(editorxy.get('x')), float(editorxy.get('y'))))
            appref[xapp.get('id')] = app

            app.config.setXMLConfig(xapp)

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
        filename, _ = QFileDialog.getSaveFileName(self, 'Export workflow to IPython notebook', '', "IPython Notebook (*.ipynb)")
        if filename:
            notebook = self.export_to_notebook()
            with open(filename, 'w') as f:
                write_notebook(notebook, f, 'json')

    def onExportReport(self):
        filename, _ = QFileDialog.getSaveFileName(self, 'Export workflow report', '', "Portable Document Format (*.pdf);; Hypertext Markup Language (*.html);; ReStructured Text (*.rst);; Markdown (*.md);; Python script (*.py)")
        if filename:
            name, ext = os.path.splitext(filename)
            export_format = ext.strip('.')
            if export_format in ['pdf', 'rst', 'md', 'html', 'py']:

                notebook = self.export_to_notebook()
                output, resources = IPyexport(IPyexporter_map[export_format], notebook)
                with open(filename, 'w') as f:
                    f.write(output)

    def export_to_notebook(self, include_outputs=True):
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
            for i, sm in tool.data.i.items():
                if sm:
                    mo, mi = sm
                    input_shim.append("%s = %s_%s;" % (i, mi, id(mo.v)))

            if input_shim:
                c = new_code_cell(';\n'.join(input_shim))
                workbook_cells.append(c)

            # Now add the config as a dict definition
            c = new_code_cell("config = %s;" % tool.config.as_dict())
            workbook_cells.append(c)

            if include_outputs:
                worksheets = tool.nb.worksheets
            else:
                worksheets = tool.nb_source.worksheets

            # Output the notebook itself. Use the source Luke; not the mangled version
            for ws in worksheets:
                for cell in ws.cells:
                    # Output variables of each script are shim-suffixed with the id of the tool (unique)
                    # e.g. output_data_123 = output_data
                    # input_data = output_data_123
                    # We can skip this step if the following tool is the target of the data, but this
                    # will need the generator to be more intelligent
                    workbook_cells.append(cell)

            # Now add the output-shims from any sources.
            output_shim = []
            for o, d in tool.data.o.items():
                if d is not None:
                    output_shim.append("%s_%s = %s;" % (o, id(tool), o))

            if output_shim:
                c = new_code_cell(';\n'.join(output_shim))
                workbook_cells.append(c)

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
        return notebook

    def add_code_cell(self, nb, index, code):
        nb.insert(index, Struct(**{
            'cell_type': 'code',
            'language': 'python',
            'outputs': [],
            'collapsed': True,
            'prompt_number': 0,
            'input': code,
            'metadata': {},
        }))

    def onInterruptKernels(self):
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
    notebook_queue.create_user_kernel()
    notebook_queue.create_runners()
    notebook_queue.start_timers()

    MainWindow()
    logging.info('Ready.')
    app.exec_()  # Enter Qt application main loop

    notebook_queue.stop_cluster()

    logging.info('Exiting.')
