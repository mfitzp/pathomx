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
from .globals import settings, app_launchers, file_handlers, url_handlers, available_tools_by_category, \
                     plugin_categories, plugin_manager, plugin_objects, plugin_metadata, installed_plugin_names

# Translation (@default context)
from .translate import tr

from pyqtconfig import ConfigManager


def get_available_plugins(plugin_places=None, include_deactivated=False):
    global available_tools_by_category

    if plugin_places is None:
        plugin_places = settings.get('Plugins/Paths')[:]

    disabled_plugins = settings.get('Plugins/Disabled')

    # Append the core path search so always available; but custom takes preference (allows downloaded
    # updates to override)
    core_plugin_path = os.path.join(utils.scriptdir, 'plugins')
    plugin_places.append(core_plugin_path)

    if '' in plugin_places:
        plugin_places.remove('')  # Strip the empty string

    logging.info("Searching for plugins...")

    plugin_manager.setPluginPlaces(plugin_places)
    plugin_manager.setPluginInfoExtension('pathomx-plugin')
    categories_filter = {
           "Import": ImportPlugin,
           "Processing": ProcessingPlugin,
           "Filter": FilterPlugin,
           "Identification": IdentificationPlugin,
           "Analysis": AnalysisPlugin,
           "Visualisation": VisualisationPlugin,
           "Export": ExportPlugin,
           "Scripting": ScriptingPlugin,
           }
    plugin_manager.setCategoriesFilter(categories_filter)
    plugin_manager.collectPlugins()

    available_tools_by_category = defaultdict(list)

    # Loop round the plugins and print their names.
    for plugin in plugin_manager.getAllPlugins():
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
            'shortname': os.path.basename(os.path.dirname(plugin.path)),
        }

        plugin_metadata[metadata['shortname']] = metadata
        installed_plugin_names[id(plugin.plugin_object)] = plugin.name

        plugin.plugin_object.post_setup(path=os.path.dirname(plugin.path), name=plugin.name, metadata=metadata)


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

    def populate_plugin_list(self):

        disabled_plugins = self.config.get('Plugins/Disabled')

        while self.plugins_lw.count() > 0:  # Empty list
            self.plugins_lw.takeItem(0)

        for id, plugin in plugin_metadata.items():
            item = QListWidgetItem()

            item.plugin_metadata = plugin
            item.plugin_shortname = id

            if 'image' in plugin:
                item.setData(Qt.DecorationRole, plugin['image'])

            item.setData(Qt.DisplayRole, "%s (v%s)" % (plugin['name'], plugin['version']))
            item.setData(Qt.UserRole, plugin['description'])
            item.setData(Qt.UserRole + 1, plugin['author'])
            if plugin['path'] not in disabled_plugins:
                item.setData(Qt.UserRole + 2, "Active")

            self.plugins_lw.addItem(item)

    def onActivate(self):
        items = self.plugins_lw.selectedItems()
        disabled_plugins = self.config.get('Plugins/Disabled')

        for i in items:
            plugin_path = plugin_metadata[i.plugin_shortname]['path']
            if plugin_path in disabled_plugins:
                disabled_plugins.remove(plugin_path)

        self.config.set('Plugins/Disabled', disabled_plugins)
        self.populate_plugin_list()

    def onDeactivate(self):
        items = self.plugins_lw.selectedItems()
        disabled_plugins = self.config.get('Plugins/Disabled')

        for i in items:
            plugin_path = plugin_metadata[i.plugin_shortname]['path']
            if plugin_path not in disabled_plugins:
                disabled_plugins.append(plugin_path)

        self.config.set('Plugins/Disabled', disabled_plugins)
        self.populate_plugin_list()

    def onRefresh(self):
        get_available_plugins(self.config.get('Plugins/Paths')[:], include_deactivated=True)
        self.populate_plugin_list()

    def __init__(self, parent, **kwargs):
        super(dialogPluginManagement, self).__init__(parent, **kwargs)

        self.setWindowTitle(tr("Manage Plugins"))

        self.config = ConfigManager()
        self.config.defaults = {
            'Plugins/Paths': settings.get('Plugins/Paths'),
            'Plugins/Disabled': settings.get('Plugins/Disabled'),
        }

        self.m = parent
        self.setFixedSize(self.sizeHint())

        self.plugins_lw = QListWidget()
        self.plugins_lw.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.plugins_lw.setItemDelegate(pluginListDelegate(self.plugins_lw))
        self.plugins_lw.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)

        page = QWidget()
        box = QGridLayout()
        paths = QHBoxLayout()

        self.pathlist = QLineEdit()
        self.config.add_handler('Plugins/Paths', self.pathlist, (lambda x: x.split(';'), lambda x: ';'.join(x)))

        paths.addWidget(QLabel('Search Paths:'))
        paths.addWidget(self.pathlist)

        box.addLayout(paths, 0, 0)
        box.addWidget(self.plugins_lw, 1, 0)

        buttons = QVBoxLayout()

        refresh_btn = QPushButton('Refresh')
        refresh_btn.clicked.connect(self.onRefresh)
        buttons.addWidget(refresh_btn)

        activate_btn = QPushButton('Activate')
        activate_btn.clicked.connect(self.onActivate)
        buttons.addWidget(activate_btn)

        deactivate_btn = QPushButton('Dectivate')
        deactivate_btn.clicked.connect(self.onDeactivate)
        buttons.addWidget(deactivate_btn)

        buttons.addStretch()

        box.addLayout(buttons, 1, 1)
        page.setLayout(box)

        self.layout.addWidget(page)

        # Stack it all up, with extra buttons
        self.dialogFinalise()

        # Refresh the list of available plugins
        self._init_timer = QTimer.singleShot(0, self.onRefresh)

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

        if workspace_category is None:
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
            if entry is None:
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
