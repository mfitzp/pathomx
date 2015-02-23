# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
logging.debug('Loading ui.py')

import os

# Import PyQt5 classes
from .qt import *

from pyqtconfig import ConfigManager, RECALCULATE_VIEW, RECALCULATE_ALL
from . import utils
from . import data
from .ui import Logger, ToolConfigPanel, ExperimentConfigPanel

from .globals import styles, notebook_queue, \
                    current_tools, current_tools_by_id, installed_plugin_names, \
                    mono_fontFamily, custom_pyqtconfig_hooks

import tempfile

from .views import StaticHTMLView, ViewViewManager, DataViewManager
# Translation (@default context)
from .translate import tr
from .runqueue import ToolJob

from matplotlib import rcParams

import logging

css = os.path.join(utils.scriptdir, 'html', 'css', 'style.css')
from IPython.nbconvert.filters.markdown import markdown2html_mistune

try:
    from qutepart import Qutepart
except ImportError:
    Qutepart = None

try:
    unicode
except NameError:
    unicode = str

PX_INIT_SHOT = 50
PX_RENDER_SHOT = 500


class BaseTool(QObject):
    """
    Base definition for all tools.

    This is the base implementation for all tools. It is implemented as QMainWindow
    but this may change in future to further separate the interface from the tool
    functionality (e.g. subclass object, put a QMainWindow as an .window attribute
    and place the view handler within).

    Performs all the standard setup for the tools, flags and interfaces. Sub-classes are
    available to add further additional defaults (e.g. data tables, views, etc.)
    """
    help_tab_html_filename = None
    status = pyqtSignal(str)
    progress = pyqtSignal(float)
    complete = pyqtSignal()

    deleted = pyqtSignal()

    nameChanged = pyqtSignal(str)
    configNameChanged = pyqtSignal(str)
    change_name = pyqtSignal(str)

    pause_status_changed = pyqtSignal(bool)

    legacy_launchers = []
    legacy_inputs = {}
    legacy_outputs = {}

    autoconfig_name = None

    default_pause_analysis = False

    icon = None

    language = 'python'  # Script/function language (determines loading IPython helpers)

    def __init__(self, parent, name=None, code="", position=None, auto_focus=True, auto_consume_data=True, *args, **kwargs):
        super(BaseTool, self).__init__(parent)

        self.id = str(id(self))

        self.w = QMainWindow()
        self.w.t = self  # Pass through reference to self

        self._lock = False
        self._previous_size = None
        self._is_active = False

        self._is_auto_focusable = auto_focus

        current_tools.append(self)
        current_tools_by_id[self.id] = self

        self._pause_analysis_flag = False
        self._latest_dock_widget = None
        self._latest_generator_result = None
        self._auto_consume_data = auto_consume_data

        self.current_data_on_kernels = set([])

        # Set this to true to auto-start a new calculation after current (block multi-runs)
        self._is_job_active = False
        self._queued_start = False

        # Initiate logging
        self.log_viewer = QTextEdit()
        self.log_viewer.setReadOnly(True)
        self.log_viewer.setFont(QFont(mono_fontFamily))

        logHandler = Logger(self, self.log_viewer)

        self.logger = logging.getLogger(self.id)
        self.logger.addHandler(logHandler)

        if name is None:
            name = getattr(self, 'name', installed_plugin_names[id(self.plugin)])
        self.set_name(name)
        self.configname = None

        self.logger.debug('Creating tool: %s' % name)

        self.logger.debug('Setting up data manager...')
        self.data = data.DataManager(self.parent(), self)

        self.logger.debug('Setting up view manager...')

        self.views = ViewViewManager(self)
        self.views.addFigureToolBar()

        self.dataViews = DataViewManager(self)

        self.logger.debug('Setting up file watcher manager...')
        self.file_watcher = QFileSystemWatcher()
        self.file_watcher.fileChanged.connect(self.onFileChanged)

        self.toolbars = {}
        self.configPanels = ToolConfigPanel(None, tool=self)
        self.configpanels = {}

        self.logger.debug('Register internal url handler...')
        self.register_url_handler(self.default_url_handler)
        #self.w.setCentralWidget(self.views)

        self.logger.debug('Setup config manager...')
        self.config = ConfigManager()  # Configuration manager object; handle all get/setting, defaults etc.

        # Add hooks for custom widgets
        self.config.hooks.update(custom_pyqtconfig_hooks.items())

        self.logger.debug('Create editor icon...')
        self.editorItem = self.parent().editor.addApp(self, position=position)

        self.logger.debug('Add default toolbar...')
        self.addSelfToolBar()  # Everything has one

        self.change_name.connect(self.set_name)
        self.progress.connect(self.update_progress)

        self.logger.debug('Setting up paths...')
        self._working_path = os.path.join(tempfile.gettempdir(), str(id(self)))

        self.logger.debug('Completed default tool (%s) setup.' % name)

        self.notes_viewer = StaticHTMLView(self)
        if Qutepart:
            self.code_editor = Qutepart()
            self.code_editor.is_enhanced_editor = True
        else:
            class QTextEditExtra(QTextEdit):

                @property
                def text(self):
                    return self.toPlainText()

                @text.setter
                def text(self, text):
                    self.setPlainText(text)

            self.code_editor = QTextEditExtra()
            self.code_editor.setFont(QFont(mono_fontFamily))
            self.code_editor.is_enhanced_editor = False

        self.code = code

        # Trigger finalise once we're back to the event loop
        self._init_timer1 = QTimer.singleShot(PX_INIT_SHOT, self.init_auto_consume_data)
        self._init_timer2 = QTimer.singleShot(PX_INIT_SHOT, self.init_notebook)

    def init_auto_consume_data(self):
        self.logger.debug('Post-init: init_auto_consume_data')

        self._is_autoconsume_success = False
        if self._auto_consume_data:
            # Check if a particular tool is selected FIXME: Also check for a specific data frame
            tools_to_check = current_tools[::-1]
            active_tools = [t for t in tools_to_check if t._is_active]

            # If any tool is currently selected, add it to the front of the list
            tools_to_check = active_tools + tools_to_check

            # Try to autoconsume from current tools
            self._is_autoconsume_success = self.data.consume_any_app(tools_to_check)  # Try consume from any app; work backwards

        self.data.source_updated.connect(self.autogenerate)  # Auto-regenerate if the source data is modified
        self.config.updated.connect(self.autoconfig)  # Auto-regenerate if the configuration changes

        if self.autoconfig_name:
            self.config.updated.connect(self.autoconfig_rename)  # Auto-rename if it is set

        if self._is_auto_focusable:  # Needs to occur after the above
            self._init_timer3 = QTimer.singleShot(PX_INIT_SHOT, self.init_autofocus)

    def init_notebook(self):
        self.logger.debug('Post-init: init_notebook')


        # Initial display of the notebook
        if self.code_editor.is_enhanced_editor:
            self.code_editor.detectSyntax(language='Python')

        self.addEditorToolBar()

        self.load_notes()
        self.load_source()

        #self.views.addView(self.code_editor, '&#', unfocus_on_refresh=True)
        #self.views.addView(self.log_viewer, '&=', unfocus_on_refresh=True)
        #self.views.addView( self.logView, 'Log')

        if self._is_autoconsume_success is not False:
            # This will fire after the notebook has completed above
            self._init_timer = QTimer.singleShot(PX_INIT_SHOT, self.autogenerate)

        # Set the autoconfig name string
        self.autoconfig_rename()

        self.configPanels.tabs.addTab(self.notes_viewer, '&?')

    def init_autofocus(self):
        self.activate()

    def activate(self):
        for i in self.editorItem.scene().selectedItems():
            if i != self.editorItem:
                i.setSelected(False)
        self.editorItem.setSelected(True)
        self.editorItem.setFocus()

    def reload(self):
        self.load_notes()
        self.load_source()

    def load_notes(self):
        with open(os.path.join(self.plugin.path, "%s.md" % self.shortname), 'rb') as f:
            self.notes = f.read().decode('utf-8')

        self.notes_as_html = '''<html>
<head><title>About</title><link rel="stylesheet" href="{css}"></head>
<body>
<div class="container" id="notebook-container">
<div class="cell border-box-sizing text_cell rendered">
<div class="inner_cell">
<div class="text_cell_render border-box-sizing rendered_html">{html}</div>
</div>
</div>
</div>
</div>
        </body>
        </html>'''.format(**{'baseurl': 'file:///' + os.path.join(utils.scriptdir), 'css': 'file:///' + css, 'html': markdown2html_mistune(self.notes)})

    def load_source(self):
        with open(os.path.join(self.plugin.path, "%s.py" % self.shortname), 'rb') as f:
            self.default_code = f.read().decode('utf-8')

        if self.code == "":
            self.code = self.default_code

    @property
    def code(self):
        return self.code_editor.text

    @code.setter
    def code(self, text):
        self.code_editor.text = text

    @property
    def get_icon(self):
        if self.icon:
            icon_path = os.path.join(self.plugin.path, self.icon)
        else:
            icon_path = os.path.join(self.plugin.path, 'icon.png')
        return QIcon(icon_path)

    def get_parents(self):
        return [s[0].v for i, s in self.data.i.items() if s is not None]

    def get_children(self):
        return [d.v for i, ld in self.data.watchers.items() for d in ld]

    def autogenerate(self, *args, **kwargs):
        self.logger.debug("autogenerate %s" % self.name)
        if self._pause_analysis_flag:
            self.status.emit('paused')
            return False
        self.generate()

    def generate(self):
        self.logger.info("Running tool %s" % self.name)

        strip_rcParams = ['tk.pythoninspect', 'savefig.extension']
        global_varsi = {
            '_rcParams': {k: v for k, v in rcParams.items() if k not in strip_rcParams},
            '_styles': styles,
            '_pathomx_database_path': os.path.join(utils.scriptdir, 'database'),
        }

        self.status.emit('active')
        self.progress.emit(0.)

        notebook_queue.add(ToolJob(self, global_varsi, name=self.name))

    def _worker_result_callback(self, result):
        self.progress.emit(1.)

        if 'stdout' in result:
            self.logger.info(result['stdout'])

        if result['status'] == 0:
            self.logger.debug("Execute complete: %s" % self.name)
            self.status.emit('complete')
            varso = result['varso']

            if 'styles' in varso:
                global styles
                styles = varso['styles']

            if 'kernel' in result:
                # Only this kernel is now up to date
                self.current_data_on_kernels = set([result['kernel']])

        elif result['status'] == -1:
            self.logger.debug("Execute error: %s" % self.name)
            self.status.emit('error')
            self.logger.error(result['traceback'])
            varso = {}

        self.worker_cleanup(varso)

    def worker_cleanup(self, varso):
        # Copy the data for the views here; or we're sending the same data to the get (main thread)
        # as to the prerender loop (seperate thread) without a lock
        self.generated(**varso)
        self.autoprerender(varso)

        self._is_job_active = False

    # Callback function for threaded generators; see _worker_result_callback and start_worker_thread
    def generated(self, **kwargs):
        self.logger.debug("generated %s" % self.name)

        # Automated pass on generated data if matching output port names
        for o in list(self.data.o.keys()):
            if o in kwargs:
                self.data.put(o, kwargs[o])
            #else:
            #    self.data.put(o, None) # Clear up; but this triggers wasteful autogenerate 'firing' ?
            #                             will be fixed by setting status through downstream network once proper queue in effect

            # Set into the workspace of user kernel
            # notebook_queue.in_process_runner.kernel_manager.kernel.shell.push({'t%s' % self.id: PathomxTool(self.name, **kwargs)})

    def autoprerender(self, kwargs_dict):
        self.logger.debug("autoprerender %s" % self.name)
        kwargs_dict = self.dataViews.process(**kwargs_dict)
        kwargs_dict = self.views.process(**kwargs_dict)

        logging.info('%d variables were not displayed (%s)' % (len(kwargs_dict), kwargs_dict.keys()))

        # Delay this 1/2 second so next processing gets underway
        # FIXME: when we've got a better runner system
        QTimer.singleShot(PX_RENDER_SHOT, self.views.source_data_updated.emit)
        QTimer.singleShot(PX_RENDER_SHOT, self.dataViews.source_data_updated.emit)

    def onReloadScript(self):
        self.reload()

    def register_url_handler(self, url_handler):
        self.parent().register_url_handler(self.id, url_handler)

    def delete(self):
        self.hide()
        self.w.close()  # Close the window

        # Tear down the config and data objects
        self.data.reset()
        self.data.deleteLater()
        self.config.reset()
        self.config.deleteLater()
        current_tools.remove(self)

        # Trigger notification for state change
        self.editorItem = None  # Remove reference to the GraphicsItem
        self.deleteLater()

        self.deleted.emit()

    def update_progress(self, progress):
        #FIXME: Disabled for the time being til we have a proper global job queue
        # rather the event driven mess we have now
        pass
        # self.parent().update_progress( id(self), progress)

    def autoconfig(self, signal):
        if signal == RECALCULATE_ALL or self._latest_generator_result is None:
            self.autogenerate()

        elif signal == RECALCULATE_VIEW:
            self.autoprerender(self._latest_generator_result)

    def autoconfig_rename(self, signal=None):
        if self.autoconfig_name:
            self.configname = self.autoconfig_name.format(**self.config.as_dict())
            self.configNameChanged.emit(self.configname)

    def store_views_data(self, kwargs_dict):
        self.views.source_data = kwargs_dict

    def set_name(self, name):
        self.name = name
        self.nameChanged.emit(name)

    def show(self):
        self._is_active = True
        self.parent().viewerDock.setWidget(self.views)
        self.parent().dataDock.setWidget(self.dataViews)
        self.parent().toolDock.setWidget(self.configPanels)

    def raise_(self):
        self._is_active = True
        self.parent().viewerDock.setWidget(self.views)
        self.parent().dataDock.setWidget(self.dataViews)

    def hide(self):
        self._is_active = False
        #self.parent().toolDock.setWidget(self.parent().queue)
        #self.parent().viewerDock.setWidget(QWidget())  # Empty
        #self.parent().dataDock.setWidget(QWidget())  # Empty


    def addToolBar(self, *args, **kwargs):
        return self.w.addToolBar(*args, **kwargs)

    def onDelete(self):
        self.delete()

    def addConfigPanel(self, Panel, name):
        panel = Panel(self)
        self.configPanels.tabs.addTab(panel, name)
        self.configpanels[name] = panel

    def addSelfToolBar(self):

        pass

    def addEditorToolBar(self):
        if 'editor' in self.toolbars:
            return False

        t = self.w.addToolBar('Editor')
        t.setIconSize(QSize(16, 16))

        if self.code_editor.is_enhanced_editor:
            t.addAction(self.code_editor.copyLineAction)
            t.addAction(self.code_editor.pasteLineAction)
            t.addAction(self.code_editor.cutLineAction)
            t.addAction(self.code_editor.deleteLineAction)
            t.addSeparator()
            t.addAction(self.code_editor.increaseIndentAction)
            t.addAction(self.code_editor.decreaseIndentAction)
            t.addSeparator()
            t.addAction(self.code_editor.toggleBookmarkAction)
            t.addSeparator()

        reset_to_default_codeAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'receipt-shred.png')), tr('Reset code to tool default…'), self.w)
        reset_to_default_codeAction.setStatusTip('Reset code to tool default')
        reset_to_default_codeAction.triggered.connect(self.onResetDefaultCode)
        t.addAction(reset_to_default_codeAction)

        self.toolbars['editor'] = t

    def onResetDefaultCode(self):
        reply = QMessageBox.question(self.w, "Reset code to default", "Are you sure you want to reset your custom code to the tool default? Your work will be gone.",
                            QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.code = self.default_code

    def onSelectDataSource(self):
        # Basic add data source dialog. Extend later for multiple data sources etc.
        """ Open the mining setup dialog to define conditions, ranges, class-comparisons, etc. """
        dialog = DialogDataSource(parent=self.w, view=self)
        ok = dialog.exec_()
        if ok:
            for cb in dialog.lw_consumeri:  # Get list of comboboxes
                i = cb.currentIndex()  # Get selected item
                consumer_def = cb.consumer_def

                if i > 0:  # Something in the list (-1) and not 'No data'
                    source_manager, source_interface = cb.interfaces[i]
                    self.data.consume(source_manager, source_interface)

                else:  # Stop consuming through this interface
                    self.data.unget(consumer_def.target)

    def onViewDataOutput(self):
        # Basic add data source dialog. Extend later for multiple data sources etc.
        """ Open the mining setup dialog to define conditions, ranges, class-comparisons, etc. """
        dialog = DialogDataOutput(parent=self.w, view=self)
        dialog.exec_()

    def closeEvent(self, e):
        self._previous_size = self.size()
        super(GenericApp, self).closeEvent(e)

    def getCreatedToolbar(self, name, id):
        if id not in self.toolbars:
            self.toolbars[id] = self.w.addToolBar(name)
            self.toolbars[id].setIconSize(QSize(16, 16))

        return self.toolbars[id]

    def addExternalDataToolbar(self):
        t = self.getCreatedToolbar(tr('External Data'), 'external-data')

        watch_fileAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'eye--exclamation.png')), tr('Watch data file(s) for changes…'), self.w)
        watch_fileAction.setStatusTip(tr('Watch external data file(s) for changes and automatically refresh'))
        watch_fileAction.triggered.connect(self.onWatchSourceDataToggle)
        watch_fileAction.setCheckable(True)
        watch_fileAction.setChecked(False)
        t.addAction(watch_fileAction)
        self._autoload_source_files_on_change = False

    def onWatchSourceDataToggle(self, checked):
        self._autoload_source_files_on_change = checked

    def onAutoAnalysisToggle(self, checked):
        self._pause_analysis_flag = checked
        self.pause_status_changed.emit(checked)

    def onFileChanged(self, file):
        if self._autoload_source_files_on_change:
            self.load_datafile(file)

    def onRecalculate(self):
        self.generate()  # Bypass

    def onBrowserNav(self, url):
        self.parent().onBrowserNav(url)

    # Url handler for all default plugin-related actions; making these accessible to all plugins
    # from a predefined url structure: pathomx://<view.id>/default_actions/data_source/add
    def default_url_handler(self, url):

        kind, id, action = url.split('/')  # FIXME: Can use split here once stop using pathwaynames

        # url is Qurl kind
        # Add an object to the current view
        if kind == "default_actions":

            if action == 'add' and id == 'data_source':
                # Add the pathway and regenerate
                self.onSelectDataSource()

    def sizeHint(self):
        if self._previous_size:
            return self._previous_size
        return QSize(600 + 300, 400 + 100)


class ExportDataTool(BaseTool):
    def __init__(self, *args, **kwargs):
        super(ExportDataTool, self).__init__(*args, **kwargs)

        self.data.add_input('input_data')  # Add output slot

        self.addExportDataToolbar()
        #if filename:
        #    self.thread_load_datafile( filename )

    def addExportDataToolbar(self):
        t = self.getCreatedToolbar(tr('Export Data'), 'export-data')

        export_dataAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'disk--pencil.png')), 'Export %s file…' % self.export_type, self.w)
        export_dataAction.setStatusTip(self.export_description)
        export_dataAction.triggered.connect(self.onExportData)
        t.addAction(export_dataAction)

    def onExportData(self):
        """ Open a data file"""
        filename, _ = QFileDialog.getSaveFileName(self.w, self.export_description, '', self.export_filename_filter)
        if filename:
            self.config.set('filename', filename)
            self.autogenerate()


# FIXME: Automation of experimetal test class refresh; this should be removed/moved to the Base class
# or offered as a custom widget type
class AnalysisTool(BaseTool):
    def __init__(self, *args, **kwargs):
        super(AnalysisTool, self).__init__(*args, **kwargs)
        self.config.defaults['experiment_control'] = None
        self.config.defaults['experiment_test'] = None

    def get_fig_tempfile(self, fig):
        tf = QTemporaryFile()
        tf.open()
        fig.savefig(tf.fileName(), format='png', bbox_inches='tight')
        return tf

    def addExperimentConfigPanel(self):
        self.addConfigPanel(ExperimentConfigPanel, 'Experiment')
        self.data.source_updated.connect(self.repopulate_experiment_classes)  # Update the classes if data source changes

    def repopulate_experiment_classes(self, *args):
        _control = self.config.get('experiment_control')
        _test = self.config.get('experiment_test')

        data = self.data.get('input_data')
        class_idx = data.index.names.index('Class')
        classes = list(data.index.levels[class_idx])

        # Block signals so no trigger of update
        self.configpanels['Experiment'].cb_control.blockSignals(True)
        self.configpanels['Experiment'].cb_test.blockSignals(True)
        # Empty the toolbar controls
        self.configpanels['Experiment'].cb_control.clear()
        self.configpanels['Experiment'].cb_test.clear()
        # Data source change; update the experimental control with the data input source
        self.configpanels['Experiment'].cb_control.addItems(classes)
        self.configpanels['Experiment'].cb_test.addItem("*")
        self.configpanels['Experiment'].cb_test.addItems(classes)
        # Reset to previous values (-if possible)
        self.configpanels['Experiment'].cb_control.setCurrentIndex(self.configpanels['Experiment'].cb_control.findText(_control))  # PyQt4 compat
        self.configpanels['Experiment'].cb_test.setCurrentIndex(self.configpanels['Experiment'].cb_test.findText(_test))  # PyQt4 compat
        # Unblock
        self.configpanels['Experiment'].cb_control.blockSignals(False)
        self.configpanels['Experiment'].cb_test.blockSignals(False)
        # If previously nothing set; now set it to something
        _control = _control if _control in classes else classes[0]
        _test = _test if _test in classes else '*'

        is_updated = self.config.set_many({
            'experiment_control': _control,
            'experiment_test': _test,
        }, trigger_update=False)

        self.logger.debug('Update experiment toolbar for %s, %s' % (self.name, is_updated))

    def onDataChanged(self):
        self.repopulate_experiment_classes()

    def onDefineExperiment(self):
        pass
