# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
logging.debug('Loading plugins.py')

# Import PyQt5 classes
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWebKit import *
from PyQt5.QtNetwork import *
from PyQt5.QtWidgets import *
from PyQt5.QtWebKitWidgets import *
from PyQt5.QtPrintSupport import *

# Yapsy classes
from yapsy.IPlugin import IPlugin
from yapsy.PluginManager import PluginManagerSingleton

from distutils.version import StrictVersion

from collections import defaultdict

try:
    from urllib.request import urlopen
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse
    from urllib import urlopen

import re
import requests
import hashlib
import os
import inspect
import shutil
from . import utils
from . import ui
from .globals import app_launchers, file_handlers, url_handlers

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
    # Store a local copy of plugins.list in case not available at time of requesting
    # On startup perform an async request to get weekly update of available plugins
    # Start plugin management trigger a request if no plugins.list file available locally

    def get_available_plugins(self):
        # Download the plugin list if not updated <1 day ago
        f = urlopen('http://plugins.pathomx.org/plugins.list')
        plugin_list = f.readlines()
        f.close()

        available_plugins = {}
        # 'Name','Author','Version','Description','Website','Updated'
        mapping = ['shortname', 'name', 'author', 'version', 'description', 'website', 'update']
        for line in plugin_list:
            data = line.split('\t')
            available_plugins[data[0]] = dict(list(zip(mapping, data[0:])))
            available_plugins[data[0]]['_'] = line
        self.available_plugins = available_plugins

    def find_plugins_query(self):
        s = self.searchbox.text()

        if not self.available_plugins:
            self.get_available_plugins()

        plugin_matches = {}

        for k, v in list(self.available_plugins.items()):
            if re.match("(.*)%s(.*)" % s, v['_']):
                plugin_matches[k] = v

        self.populate_plugin_list(self.plugins_search_lw, plugin_matches, show_installed=True)

    def populate_plugin_list(self, listwidget, plugins, show_installed=False):

        while listwidget.count() > 0:  # Empty list
            listwidget.takeItem(0)

        for id, plugin in list(plugins.items()):
            item = QListWidgetItem()

            item.plugin_shortname = id

            if 'image' in plugin:
                item.setData(Qt.DecorationRole, plugin['image'])

            item.setData(Qt.DisplayRole, "%s (v%s)" % (plugin['name'], plugin['version']))
            item.setData(Qt.UserRole, plugin['description'])
            item.setData(Qt.UserRole + 1, plugin['author'])
            if self.is_upgradeable(id):  # id in self.available_plugins and ( StrictVersion( str(plugin['version']) ) < StrictVersion( str(self.available_plugins[id]['version']) ) ):
                item.setData(Qt.UserRole + 2, "v%s available" % self.available_plugins[id]['version'])
            elif id in self.installed_plugins and show_installed:
                item.setData(Qt.UserRole + 2, "Installed")

            listwidget.addItem(item)

    def do_install(self, plugin_shortname, is_upgrade=False):
        # Check if already installed
        if plugin_shortname in self.installed_plugins and not is_upgrade:
            return False
        # Perform an install of the selected plugin
        # Download and unzip the zip file to the user-specific plugins location
        # Trigger plugin-install hook (need to implement; define out of main)
        plugin_version = self.available_plugins[plugin_shortname]['version']
        url = 'http://plugins.pathomx.org/downloads/%s/%s-%s.zip' % (plugin_shortname, plugin_shortname, plugin_version)
        plugin_save_path = self.m.user_plugin_path
        local_filename = os.path.join(QDir.tempPath(), 'pathomx-temp-download.zip')

        try:
            # NOTE the stream=True parameter
            r = requests.get(url, stream=True)
            with open(local_filename, 'wb') as fd:
                for chunk in r.iter_content(1024):
                    fd.write(chunk)

            with ZipFile(local_filename, 'r') as zip:
                zip.extractall(plugin_save_path)
        except:
            return False
        else:
            return True
        #http://plugins.pathomx.org/downloads/zeitgeist/zeitgeist-0.0.1.tgz

    def do_uninstall(self, plugin_shortname):
        if plugin_shortname in self.installed_plugins and not self.installed_plugins[plugin_shortname]['is_core_plugin']:
            #shutil.rmtree(self.installed_plugins[plugin_shortname]['path'])
            try:
                shutil.rmtree(self.installed_plugins[plugin_shortname]['path'])
            except:
                return False
            else:
                return True

    def do_upgrade(self, plugin_shortname):
        if self.is_upgradeable(plugin_shortname):  # Can only upgrade installed (bit semantic currently)
            return self.do_install(plugin_shortname, is_upgrade=True)
            # Tidy up everything post-upgrade/re-init
            # Need to ensure that on loading the latest version of each plugin is always pulled

    def toggle_enable(self, plugin_shortname):
        pass

    def is_upgradeable(self, plugin_shortname):
        return plugin_shortname in self.available_plugins and plugin_shortname in self.installed_plugins \
                 and (StrictVersion(str(self.installed_plugins[plugin_shortname]['version'])) < StrictVersion(str(self.available_plugins[plugin_shortname]['version'])))

    def onInstall(self):
        successful_count = 0
        for widget in self.plugins_search_lw.selectedItems():
            s = self.do_install(widget.plugin_shortname)
            if s:
                successful_count += 1

        msgBox = QMessageBox(self)
        if successful_count > 0:
            msgBox.setText(tr("%d plugin(s) installed. To complete installation please restart Pathomx" % successful_count))
        else:
            msgBox.setText(tr("No plugins installed."))

        msgBox.exec_()

    def onUpgrade(self):
        successful_count = 0
        for widget in self.plugins_lw.selectedItems():
            s = self.do_upgrade(widget.plugin_shortname)
            if s:
                successful_count += 1

        msgBox = QMessageBox(self)
        if successful_count > 0:
            msgBox.setText(tr("%d plugin(s) upgraded. To complete upgrade please restart Pathomx" % successful_count))
        else:
            msgBox.setText(tr("No plugins upgraded."))
        msgBox.exec_()

    def onUninstall(self):
        successful_count = 0
        for widget in self.plugins_lw.selectedItems():
            s = self.do_uninstall(widget.plugin_shortname)
            if s:
                successful_count += 1

        msgBox = QMessageBox(self)
        if successful_count > 0:
            msgBox.setText(tr("%d plugin(s) uninstalled. To complete uninstallation please restart Pathomx" % successful_count))
        else:
            msgBox.setText(tr("No plugins uninstalled."))
        msgBox.exec_()

    def onRefresh(self):
        self.get_available_plugins()

    def __init__(self, parent, **kwargs):
        super(dialogPluginManagement, self).__init__(parent, **kwargs)

        self.setWindowTitle(tr("Manage Plugins"))

        self.get_available_plugins()

        self.m = parent
        self.setFixedSize(self.sizeHint())

        self.installed_plugins = self.m.plugins

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
        self.m.plugins_obj[self.id] = self
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

    def register_app_launcher(self, app, workspace_category=None):
        app.plugin = self
        key = "%s.%s" % (self.id, app.__name__)
        app_launchers[key] = app

        if workspace_category == None:
            workspace_category = self.default_workspace_category

        self.m.tools[workspace_category].append({
            'id': key,
            'app': app,
            'plugin': self,
        })

        # Support legacy app launchers (so moving apps between plugins doesn't kill them)
        for lkey in app.legacy_launchers:
            app_launchers[lkey] = app

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
