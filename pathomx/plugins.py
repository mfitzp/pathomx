# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
logging.debug('Loading plugins.py')

from .qt import *

# Yapsy classes
from yapsy.IPlugin import IPlugin
from yapsy.PluginManager import PluginManagerSingleton

from distutils.version import StrictVersion
from collections import defaultdict

import re
import requests
import hashlib
import os
import inspect
import shutil
from . import utils
from . import ui
from .globals import app_launchers, file_handlers, url_handlers, available_tools_by_category, plugin_manager, plugin_objects, plugin_metadata

from zipfile import ZipFile

# Translation (@default context)
from .translate import tr








class pluginListDelegate(QAbstractItemDelegate):

    def paint(self, painter, option, index):
        # GET TITLE, DESCRIPTION AND ICON
        ic = QIcon(index.data(Qt.DecorationRole))
        title = index.data(Qt.DisplayRole)  # .toString()
        description = index.data(Qt.UserRole)  # .toString()
        author = index.data(Qt.UserRole + 1)  # .toString()
        notice = index.data(Qt.UserRole + 2)  # .toString()

        if option.state & QStyle.State_Selected:
            painter.setPen(QPalette().highlightedText().color())
            painter.fillRect(option.rect, QBrush(QPalette().highlight().color()))
        else:
            painter.setPen(QPalette().text().color())

        imageSpace = 10
        if not ic.isNull():
            # ICON
            r = option.rect.adjusted(5, 10, -10, -10)
            ic.paint(painter, r, Qt.AlignVCenter | Qt.AlignLeft)
            imageSpace = 55

        # TITLE
        r = option.rect.adjusted(imageSpace, 5, 0, 0)
        pen = QPen()
        pen.setColor(QColor('black'))
        painter.setPen(pen)
        painter.drawText(r.left(), r.top(), r.width(), r.height(), Qt.AlignLeft, title)

        # DESCRIPTION
        r = option.rect.adjusted(imageSpace, 22, 0, 0)
        painter.drawText(r.left(), r.top(), r.width(), r.height(), Qt.AlignLeft, description)

        # AUTHORS
        r = option.rect.adjusted(imageSpace, 39, 0, 0)
        pen = QPen()
        pen.setColor(QColor('#888888'))
        painter.setPen(pen)
        painter.drawText(r.left(), r.top(), r.width(), r.height(), Qt.AlignLeft, author)

        r = option.rect.adjusted(imageSpace, 0, -10, -30)
        painter.setPen(QPalette().mid().color())
        painter.drawText(r.left(), r.top(), r.width(), r.height(), Qt.AlignBottom | Qt.AlignRight, notice)

    def sizeHint(self, option, index):
        return QSize(200, 60)

            
class dialogPluginManagement(ui.GenericDialog):


    def __init__(self, parent, **kwargs):
        super(dialogPluginManagement, self).__init__(parent, **kwargs)

        self.setWindowTitle(tr("Manage Plugins"))

        self.plugins = get_available_plugins()

        self.m = parent
        self.setFixedSize(self.sizeHint())

        self.installed_plugins = plugin_metadata

        self.tabs = QTabWidget()
        self.tab = defaultdict(dict)

        self.plugins_lw = QListWidget()
        self.plugins_lw.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.plugins_lw.setItemDelegate(pluginListDelegate(self.plugins_lw))

        self.populate_plugin_list(self.plugins_lw, self.installed_plugins)

        page1 = QWidget()
        box = QGridLayout()
        box.addWidget(self.plugins_lw, 0, 0)

        buttons = QVBoxLayout()
        upgrade_btn = QPushButton('Upgrade')
        upgrade_btn.clicked.connect(self.onUpgrade)
        buttons.addWidget(upgrade_btn)

        uninstall_btn = QPushButton('Uninstall')
        uninstall_btn.clicked.connect(self.onUninstall)
        buttons.addWidget(uninstall_btn)
        buttons.addStretch()

        box.addLayout(buttons, 0, 1)
        page1.setLayout(box)

        self.plugins_search_lw = QListWidget()
        self.plugins_search_lw.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.plugins_search_lw.setItemDelegate(pluginListDelegate(self.plugins_search_lw))

        page2 = QWidget()
        box = QGridLayout()
        self.searchbox = QLineEdit()
        querybutton = QPushButton('↺')
        querybutton.clicked.connect(self.find_plugins_query)
        box.addWidget(self.searchbox, 0, 0)
        box.addWidget(querybutton, 0, 1)
        box.addWidget(self.plugins_search_lw, 1, 0)

        buttons = QVBoxLayout()
        install_btn = QPushButton('Install')
        install_btn.clicked.connect(self.onInstall)
        buttons.addWidget(install_btn)

        refresh_btn = QPushButton('Refresh')
        refresh_btn.clicked.connect(self.onRefresh)
        buttons.addWidget(refresh_btn)
        buttons.addStretch()

        box.addLayout(buttons, 1, 1)
        page2.setLayout(box)

        self.tabs.addTab(page1, tr('Installed'))
        self.tabs.addTab(page2, tr('Available'))

        self.layout.addWidget(self.tabs)

        # Stack it all up, with extra buttons
        self.dialogFinalise()

    def sizeHint(self):
        return QSize(600, 300)


class BasePlugin(IPlugin):
    '''
    Base plugin class.

    This base plugin class provides all setup and handling functions for all plugin types.
    Sub-classes simply override the default workspace category for each.
    '''

    default_workspace_category = None
    is_active = True

    def __init__(self, **kwargs):
        super(BasePlugin, self).__init__()

        # Pass in reference to the main window
        manager = PluginManagerSingleton.get()
        self.m = manager.m
        self.instances = []
        self.id = type(self).__name__  # self.__module__
        self.module = self.__module__
        plugin_objects[self.id] = self
        #self.name = "%s %s " % (self.default_workspace_category, "Plugin")

    def post_setup(self, path=None, name=None, metadata={}):  # Post setup hook

        if path:
            self.path = path
        else:
            self.path = os.path.dirname(inspect.getfile(self.__class__))

        if name:
            self.name = name
        else:
            self.name = "%s %s " % (self.default_workspace_category, "Plugin")

        self.name = name
        self.metadata = metadata

    @property
    def icon(self):
        '''
        Return the icon for this plugin.
        '''
        icon_path = os.path.join(self.path, 'icon.png')
        if os.path.exists(icon_path):
            return QIcon(icon_path)
        else:
            return None

    @property
    def pixmap(self):
        '''
        Return a pixmap of the icon for this plugin.
        '''
        icon_path = os.path.join(self.path, 'icon.png')
        if os.path.exists(icon_path):
            return QPixmap(icon_path)
        else:
            return None

    @property
    def workspace_icon(self):
        '''
        Return a small 16px icon for the workspace-list view.
        '''
        icon_path = os.path.join(self.path, 'icon-16.png')
        if os.path.exists(icon_path):
            return QIcon(icon_path)
        else:
            return None

    def register_app_launcher(self, *args, **kwargs):
        self.register_tool_launcher(*args, **kwargs)

    def register_tool_launcher(self, tool, workspace_category=None):
        tool.plugin = self
        key = "%s.%s" % (self.id, tool.__name__)
        app_launchers[key] = tool

        if workspace_category == None:
            workspace_category = self.default_workspace_category

        available_tools_by_category[workspace_category].append({
            'id': key,
            'app': tool,
            'plugin': self,
        })

        # Support legacy app launchers (so moving apps between plugins doesn't kill them)
        for lkey in tool.legacy_launchers:
            app_launchers[lkey] = tool

    def register_file_handler(self, app, ext):
        file_handlers[ext] = app

    def register_url_handler(self, url_handler):
        url_handlers[self.id].append(url_handler)

    def register_menus(self, menu, entries):

        for entry in entries:
            if entry == None:
                self.m.menuBars[menu].addSeparator()
            else:
                menuAction = QAction(entry['title'], self.m)
                if 'status' in entry:
                    menuAction.setStatusTip(entry['status'])
                menuAction.triggered.connect(entry['action'])
                self.m.menuBars[menu].addAction(menuAction)

    def generate_cache_key(self, o):
        return 'cache-' + hashlib.sha224(str(o)).hexdigest()

    def get_cache_item(self, key):
        path = os.path.join(QStandardPaths.standardLocations(QStandardPaths.CacheLocation)[0], self.id)
        hash = self.generate_cache_key(key)
        try:
            with open(os.path.join(path, hash), 'r') as f:
                return f.read()
        except:
            return None

    def put_cache_item(self, key, value):
        path = os.path.join(QStandardPaths.standardLocations(QStandardPaths.CacheLocation)[0], self.id)
        hash = self.generate_cache_key(key)
        utils.mkdir_p(path)
        with open(os.path.join(path, hash), 'w') as f:
            f.write(str(value))


class ImportPlugin(BasePlugin):
    '''
    Import plugin.
    '''
    default_workspace_category = 'Import'
    pass


class ProcessingPlugin(BasePlugin):
    '''
    Processing plugin.
    '''
    default_workspace_category = 'Processing'
    pass


class IdentificationPlugin(BasePlugin):
    '''
    Identification plugin.
    '''
    default_workspace_category = 'Identification'
    pass


class AnalysisPlugin(BasePlugin):
    '''
    Analysis plugin.
    '''
    default_workspace_category = 'Analysis'
    pass


class FilterPlugin(BasePlugin):
    '''
    Filter plugin.
    '''
    default_workspace_category = 'Filter'
    pass


class VisualisationPlugin(BasePlugin):
    '''
    Visualisation plugin.
    '''
    default_workspace_category = 'Visualisation'
    pass


class ExportPlugin(BasePlugin):
    '''
    Export plugin.
    '''
    default_workspace_category = 'Export'
    pass


class ScriptingPlugin(BasePlugin):
    '''
    Scripting plugin.
    '''
    default_workspace_category = 'Scripting'
    pass


class MiscPlugin(BasePlugin):
    '''
    Misc plugin.
    '''
    default_workspace_category = 'Misc'
    pass
