#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
logging.debug('Loading ui.py')

# Import PyQt5 classes
from .qt import *

import os
import numpy as np
import pandas as pd
from collections import OrderedDict

from pyqtconfig import ConfigManager, RECALCULATE_VIEW, RECALCULATE_ALL
from . import utils
from . import data
from . import displayobjects
from .globals import styles, MATCH_EXACT, MATCH_CONTAINS, MATCH_START, MATCH_END, \
                    MATCH_REGEXP, MARKERS, LINESTYLES, FILLSTYLES, HATCHSTYLES, \
                    StyleDefinition, ClassMatchDefinition, notebook_queue, \
                    current_tools, current_tools_by_id, installed_plugin_names, current_datasets, \
                    mono_fontFamily, custom_pyqtconfig_hooks

import tempfile

from .views import HTMLView, StaticHTMLView, ViewManager, NotebookView, IPyMplView, DataFrameWidget, SVGView
# Translation (@default context)
from .translate import tr

import requests

from matplotlib.figure import Figure
from matplotlib import rcParams

import logging

css = os.path.join(utils.scriptdir, 'html', 'css', 'style.css')
from IPython.nbformat.current import read as read_notebook, NotebookNode
from IPython.nbconvert.filters.markdown import markdown2html_mistune
from IPython.core import display
from IPython.qt.console.ansi_code_processor import QtAnsiCodeProcessor

from .runqueue import STATUS_READY, STATUS_RUNNING, STATUS_COMPLETE, STATUS_ERROR, STATUS_BLOCKED
from .kernel_helpers import PathomxTool

try:
    from qutepart import Qutepart
except:
    Qutepart = None

PX_INIT_SHOT = 50
PX_RENDER_SHOT = 500

# Web views default HTML
BLANK_DEFAULT_HTML = '''
<html>
<style>
    * {
        width:100%;
        height:100%;
        margin:0;
        background-color: #f5f5f5;
    }
</style>
<body>&nbsp;</body></html>
'''


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
        self.ansi_processor = QtAnsiCodeProcessor()

    def emit(self, record):

        self.widget.textCursor().movePosition(QTextCursor.End)

        msg = self.format(record)
        if record.levelno < logging.INFO:
            return False

        for substring in self.ansi_processor.split_string(msg):
            format = self.ansi_processor.get_format()
            self.widget.textCursor().insertText(substring, format)

        self.widget.textCursor().insertText("\n")

    def write(self, m):
        pass


class KernelStatusWidget(QWidget):

    def __init__(self, *args, **kwargs):
        super(KernelStatusWidget, self).__init__(*args, **kwargs)

        # Kernel queue list interrogate
        self.layout = QHBoxLayout()
        self.setLayout(self.layout)

    def update(self, runmanager):
        runners = runmanager.runners

        # Ensure we've got enough items
        if len(runners) != self.layout.count():

            # Clear and re-paint; otherwise get artefacts
            while self.layout.count():
                self.layout.itemAt(0).widget().setParent(None)

            for i in range(len(runners)):
                w = QWidget()
                w.setMinimumSize(QSize(10, 10))
                w.setAutoFillBackground(True)
                self.layout.addWidget(w)


        for i, k in enumerate(runners):
            w = self.layout.itemAt(i).widget()
            p = w.palette()

            if k.status == STATUS_READY:
                p.setColor(w.backgroundRole(), QColor(0, 0, 0, 63))
            elif k.status == STATUS_RUNNING:
                p.setColor(w.backgroundRole(), QColor(0, 255, 0, 127))
            elif k.status == STATUS_COMPLETE:
                p.setColor(w.backgroundRole(), QColor(0, 0, 255, 127))
            elif k.status == STATUS_ERROR:
                p.setColor(w.backgroundRole(), QColor(255, 0, 0, 127))
            elif k.status == STATUS_BLOCKED:
                p.setColor(w.backgroundRole(), QColor(0, 255, 0, 63))

            w.setPalette(p)

    def sizeHint(self):
        return QSize(self.layout.count() * 10, 10)


class QColorButton(QPushButton):
    '''
    Custom Qt Widget to show a chosen color.
    
    Left-clicking the button shows the color-chooser, while
    right-clicking resets the color to None (no-color).    
    '''

    colorChanged = pyqtSignal()

    def __init__(self, is_reset_enabled=True, *args, **kwargs):
        super(QColorButton, self).__init__(*args, **kwargs)

        self._color = None
        self.setMaximumWidth(32)
        self.pressed.connect(self.onColorPicker)

        self.is_reset_enabled = is_reset_enabled

    def setColor(self, color):
        if color != self._color:
            self._color = color
            self.colorChanged.emit()

        if self._color:
            self.setStyleSheet("background-color: %s;" % self._color)
        else:
            self.setStyleSheet("")

    def color(self):
        return self._color

    def onColorPicker(self):
        '''
        Show color-picker dialog to select color.
        
        This should use the Qt-defined non-native dialog so custom colours
        can be auto-defined from the currently set palette - but it doesn't work due
        to a known bug - should auto-fix on Qt 5.2.2.
        '''
        dlg = QColorDialog(self)
        if self._color:
            dlg.setCurrentColor(QColor(self._color))

        dlg.setOption(QColorDialog.DontUseNativeDialog)
        # FIXME: Add colors from current default set to the custom color table
        # dlg.setCustomColor(0, QColor('red') )
        if dlg.exec_():
            self.setColor(dlg.currentColor().name())

    def mousePressEvent(self, e):
        if self.is_reset_enabled and e.button() == Qt.RightButton:
            self.setColor(None)
        else:
            return super(QColorButton, self).mousePressEvent(e)


class QNoneDoubleSpinBox(QDoubleSpinBox):
    '''
    Custom Qt widget to offer a DoubleSpinBox that can hold null values.
    
    The value can be set to null with right-click. When set to null the widget
    appears faded.
    '''

    def __init__(self, *args, **kwargs):
        super(QNoneDoubleSpinBox, self).__init__(*args, **kwargs)
        self.is_None = False

    def value(self):
        if self.is_None:
            return None
        else:
            return super(QNoneDoubleSpinBox, self).value()

    def setValue(self, v):
        if v is None:
            self.is_None = True
            self.setEnabled(False)
            self.valueChanged.emit(-65535)  # Dummy value
        else:
            self.is_None = False
            self.setEnabled(True)
            super(QNoneDoubleSpinBox, self).setValue(v)

    def event(self, e):
        if type(e) == QContextMenuEvent:  # int and event.button() == QtCore.Qt.RightButton:
            e.accept()
            if self.is_None:
                self.setValue(super(QNoneDoubleSpinBox, self).value())
            else:
                self.setValue(None)
            return True
        else:
            return super(QNoneDoubleSpinBox, self).event(e)


class QListWidgetAddRemove(QListWidget):
    itemAddedOrRemoved = pyqtSignal()

    def addItem(self, *args, **kwargs):
        r = super(QListWidgetAddRemove, self).addItem(*args, **kwargs)
        self.itemAddedOrRemoved.emit()
        return r

    def addItems(self, *args, **kwargs):
        r = super(QListWidgetAddRemove, self).addItems(*args, **kwargs)
        self.itemAddedOrRemoved.emit()
        return r

    def removeItemAt(self, row, *args, **kwargs):
        super(QListWidgetAddRemove, self).takeItem(row)
        self.itemAddedOrRemoved.emit()
        return r

    def clear(self, *args, **kwargs):
        r = super(QListWidgetAddRemove, self).clear(*args, **kwargs)
        self.itemAddedOrRemoved.emit()
        return r


class QFileOpenLineEdit(QWidget):

    textChanged = pyqtSignal(object)
    icon = 'disk--arrow.png'

    def __init__(self, parent=None, description=tr("Select file"), filename_filter=tr("All Files") + " (*.*);;", **kwargs):
        super(QFileOpenLineEdit, self).__init__(parent, **kwargs)

        self._text = None

        self.description = description
        self.filename_filter = filename_filter

        self.lineedit = QLineEdit()
        self.button = QToolButton()
        self.button.setIcon(QIcon(os.path.join(utils.scriptdir, 'icons', self.icon)))

        layout = QHBoxLayout(self)
        layout.addWidget(self.lineedit)
        layout.addWidget(self.button, stretch=1)
        self.setLayout(layout)

        self.button.pressed.connect(self.onSelectPath)

        # Reciprocal setting of values; keep in sync
        self.textChanged.connect(self.lineedit.setText)
        self.lineedit.textChanged.connect(self.setText)

    def onSelectPath(self):

        filename, _ = QFileDialog.getOpenFileName(self, self.description, '', self.filename_filter)
        if filename:
            self.setText(filename)

    def text(self):
        return self._text

    def setText(self, text):
        self._text = text
        self.textChanged.emit(self._text)


class QFileSaveLineEdit(QFileOpenLineEdit):

    icon = 'disk--pencil.png'

    def __init__(self, parent=None, description=tr("Select save filename"), filename_filter=tr("All Files") + " (*.*);;", **kwargs):
        super(QFileSaveLineEdit, self).__init__(parent, description, filename_filter, **kwargs)

    def onSelectPath(self):
        filename, _ = QFileDialog.getSaveFileName(self.w, self.description, '', self.filename_filter)
        if filename:
            self.setText(filename)


class QFolderLineEdit(QFileOpenLineEdit):

    icon = 'folder-horizontal-open.png'

    def __init__(self, parent=None, description=tr("Select folder"), filename_filter="", **kwargs):
        super(QFolderLineEdit, self).__init__(parent, description, filename_filter, **kwargs)

    def onSelectPath(self):
        Qd = QFileDialog()
        Qd.setFileMode(QFileDialog.Directory)
        Qd.setOption(QFileDialog.ShowDirsOnly)

        folder = Qd.getExistingDirectory(self, self.description)
        if folder:
            self.setText(folder)


# GENERIC CONFIGURATION AND OPTION HANDLING

# Generic configuration dialog handling class
class GenericDialog(QDialog):
    '''
    A generic dialog wrapper that handles most common dialog setup/shutdown functions.
    
    Support for config, etc. to be added for auto-handling widgets and config load/save. 
    '''

    def __init__(self, parent, buttons=['ok', 'cancel'], **kwargs):
        super(GenericDialog, self).__init__(parent, **kwargs)

        self.sizer = QVBoxLayout()
        self.layout = QVBoxLayout()

        QButtons = {
            'ok': QDialogButtonBox.Ok,
            'cancel': QDialogButtonBox.Cancel,
        }
        Qbtn = 0
        for k in buttons:
            Qbtn = Qbtn | QButtons[k]

        # Setup default button configurations etc.
        self.buttonBox = QDialogButtonBox(Qbtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

    def dialogFinalise(self):
        self.sizer.addLayout(self.layout)
        self.sizer.addWidget(self.buttonBox)

        # Set dialog layout
        self.setLayout(self.sizer)

    def setListControl(self, control, list, checked):
        # Automatically set List control checked based on current options list
        items = control.GetItems()
        try:
            idxs = [items.index(e) for e in list]
            for idx in idxs:
                if checked:
                    control.Select(idx)
                else:
                    control.Deselect(idx)
        except:
            pass


class DialogAbout(QDialog):
    def __init__(self, parent, **kwargs):
        super(DialogAbout, self).__init__(parent, **kwargs)

        self.setWindowTitle('About Pathomx')
        self.help = QWebView(self)  # , parent.onBrowserNav)
        with open(os.path.join(utils.basedir, 'README.md'), 'rU') as f:
            md = f.read()

        html = '''<html>
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
        </html>'''.format(**{'baseurl': 'file:///' + os.path.join(utils.scriptdir), 'css': 'file:///' + css, 'html': markdown2html_mistune(md)})

        self.help.setHtml(html, QUrl('file:///' + os.path.join(utils.scriptdir)))
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.help)

        # Setup default button configurations etc.
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Close)
        self.buttonBox.rejected.connect(self.close)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)

    def sizeHint(self):
        return QSize(600, 600)


class DialogRegister(QDialog):
    def __init__(self, parent, **kwargs):
        super(DialogRegister, self).__init__(parent, **kwargs)

        self.setWindowTitle('Register Pathomx')

        self.layout = QVBoxLayout()
        self.layout.addWidget(QLabel('Please register Pathomx by entering your details below.\n\nThis is completely optional but helps it helps us find out\nhow Pathomx is being used.'))

        self.layout.addSpacerItem(QSpacerItem(0, 20))

        bx = QGridLayout()

        self.name = QLineEdit()
        bx.addWidget(QLabel('Name'), 0, 0)
        bx.addWidget(self.name, 0, 1)

        self.institution = QLineEdit()
        bx.addWidget(QLabel('Institution/Organisation'), 1, 0)
        bx.addWidget(self.institution, 1, 1)

        self.type = QComboBox()
        self.type.addItems(['Academic', 'Governmental', 'Commercial', 'Non-profit', 'Personal', 'Other'])
        bx.addWidget(QLabel('Type of organisation'), 2, 0)
        bx.addWidget(self.type, 2, 1)

        self.country = QLineEdit()
        bx.addWidget(QLabel('Country'), 3, 0)
        bx.addWidget(self.country, 3, 1)

        self.research = QLineEdit()
        bx.addWidget(QLabel('Research interest'), 4, 0)
        bx.addWidget(self.research, 4, 1)

        self.email = QLineEdit()
        bx.addWidget(QLabel('Email address'), 5, 0)
        bx.addWidget(self.email, 5, 1)

        bx.addItem(QSpacerItem(0, 20), 6, 0)

        self.releases = QComboBox()
        self.releases.addItems(['Check automatically (weekly)', 'Subscribe to mailing list', 'Don\'t check'])
        bx.addWidget(QLabel('Software updates'), 7, 0)
        bx.addWidget(self.releases, 7, 1)

        self.layout.addLayout(bx)

        # Setup default button configurations etc.
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        self.buttonBox.rejected.connect(self.close)
        self.buttonBox.accepted.connect(self.accept)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)

   
class ExportImageDialog(GenericDialog):
    """
    Standard dialog to handle image export fromm any view.
    
    Dialog box presenting a set of options for image export, including dimensions and
    resolution. Resolution is handled as dpm (dots per metre) in keeping with 
    internal Qt usage, but convertor functions are available.
    
    :param parent: Parent window to attach dialog to
    :type QObject: object inherited from QObject
    :param size: Default dimensions for export
    :type size: QSize
    :param dpm: Default dots per metre
    :type dpm: int
    :param show_rerender_options: Show options to re-render/scale output
    :type show_rerender_options: bool
    
    """
    print_u = {  # Qt uses pixels/meter as it's default resolution so measure relative to meters
        'in': 39.3701,
        'mm': 1000,
        'cm': 100,
        'm': 1,
        }

    print_p = {  # Spinbox parameters dp, increment
        'in': (3, 1, 0.01, 1000),
        'mm': (2, 1, 0.1, 100000),
        'cm': (3, 1, 0.01, 10000),
        'm': (5, 1, 0.0001, 100),
    }

    resolution_u = {  # Qt uses pixels/meter as it's default resolution so scale to that
                    'dpi': 39.3701,
                    'px/mm': 1000,
                    'px/cm': 100,
                    'px/m': 1,
                    }

    convert_res_to_unit = {'dpi': 'in', 'px/mm': 'mm', 'px/cm': 'cm', 'px/m': 'm'}

    def __init__(self, parent, size=QSize(800, 600), dpm=11811, show_rerender_options=False, **kwargs):
        super(ExportImageDialog, self).__init__(parent, **kwargs)

        self.setWindowTitle(tr("Export Image"))

        # Handle measurements internally as pixels, convert to/from
        self._w = size.width()
        self._h = size.height()
        self.default_print_units = 'cm'
        self.default_resolution_units = 'dpi'

        self._updating = False

        r = 0
        w = QGridLayout()

        w.addWidget(QLabel('<b>Image Size</b>'), r, 0)
        r += 1

        self.width = QSpinBox()
        self.width.setRange(1, 100000)
        w.addWidget(QLabel('Width'), r, 0)
        w.addWidget(self.width, r, 1)
        r += 1

        self.height = QSpinBox()
        self.height.setRange(1, 100000)
        w.addWidget(QLabel('Height'), r, 0)
        w.addWidget(self.height, r, 1)
        r += 1
        w.addItem(QSpacerItem(1, 10), r, 0)
        r += 1

        w.addWidget(QLabel('<b>Print Size</b>'), r, 0)
        r += 1

        self.width_p = QDoubleSpinBox()
        self.width_p.setRange(0.0001, 10000)
        w.addWidget(QLabel('Width'), r, 0)
        w.addWidget(self.width_p, r, 1)
        r += 1

        self.height_p = QDoubleSpinBox()
        self.height_p.setRange(0.0001, 10000)
        w.addWidget(QLabel('Height'), r, 0)
        w.addWidget(self.height_p, r, 1)

        self.print_units = QComboBox()
        self.print_units.addItems(list(self.print_u.keys()))
        self.print_units.setCurrentIndex(self.print_units.findText(self.default_print_units))

        w.addWidget(self.print_units, r, 2)
        r += 1

        self.resolution = QDoubleSpinBox()
        self.resolution.setRange(1, 1000000)
        self.resolution.setValue(300)
        self.resolution.setDecimals(2)

        self.resolution_units = QComboBox()
        self.resolution_units.addItems(list(self.resolution_u.keys()))
        self.resolution_units.setCurrentIndex(self.resolution_units.findText(self.default_resolution_units))

        w.addWidget(QLabel('Resolution'), r, 0)
        w.addWidget(self.resolution, r, 1)
        w.addWidget(self.resolution_units, r, 2)
        r += 1
        w.addItem(QSpacerItem(1, 10), r, 0)
        r += 1

        if show_rerender_options:
            w.addWidget(QLabel('<b>Scaling</b>'), r, 0)
            r += 1
            self.scaling = QComboBox()
            self.scaling.addItems(['Resample', 'Resize'])
            self.scaling.setCurrentIndex(self.scaling.findText('Resample'))
            w.addWidget(QLabel('Scaling method'), r, 0)
            w.addWidget(self.scaling, r, 1)
            r += 1
            w.addItem(QSpacerItem(1, 20), r, 0)
        else:
            self.scaling = False

        # Set values
        self.width.setValue(self._w)
        self.height.setValue(self._h)
        self.update_print_dimensions()

        # Set event handlers (here so not triggered while setting up)
        self.width.valueChanged.connect(self.changed_image_dimensions)
        self.height.valueChanged.connect(self.changed_image_dimensions)
        self.width_p.valueChanged.connect(self.changed_print_dimensions)
        self.height_p.valueChanged.connect(self.changed_print_dimensions)
        self.resolution_units.currentIndexChanged.connect(self.changed_resolution_units)
        self.resolution.valueChanged.connect(self.changed_print_resolution)
        self.print_units.currentIndexChanged.connect(self.changed_print_units)

        self.layout.addLayout(w)

        self.setMinimumSize(QSize(300, 150))
        self.layout.setSizeConstraint(QLayout.SetMinimumSize)

        self._current_dimension = self.print_units.currentText()
        self._current_resolution = self.resolution.value()
        self._current_resolution_units = self.resolution_units.currentText()

        # Build dialog layout
        self.dialogFinalise()

    def changed_image_dimensions(self):
        if not self._updating:
            self._updating = True
            self.update_print_dimensions()
        self._updating = False

        # Keep internal data synced
        self._w = self.width.value()
        self._h = self.height.value()

    def changed_print_dimensions(self):
        if not self._updating:
            self._updating = True
            self.update_image_dimensions()
        self._updating = False

    def changed_print_resolution(self):
        w_p = self.width_p.value()
        h_p = self.height_p.value()

        new_resolution = self.resolution.value()
        self.width_p.setValue((w_p / self._current_resolution) * new_resolution)
        self.height_p.setValue((h_p / self._current_resolution) * new_resolution)
        self._current_resolution = self.resolution.value()

    def changed_print_units(self):
        dimension_t = self.print_units.currentText()
        for o in [self.height_p, self.width_p]:
            o.setDecimals(self.print_p[dimension_t][0])
            o.setSingleStep(self.print_p[dimension_t][1])
            o.setRange(self.print_p[dimension_t][2], self.print_p[dimension_t][3])

        if dimension_t != self._current_dimension:
            # We've had a change, so convert
            self.width_p.setValue(self.get_converted_measurement(self.width_p.value(), self._current_dimension, dimension_t))
            self.height_p.setValue(self.get_converted_measurement(self.height_p.value(), self._current_dimension, dimension_t))

        self._current_dimension = dimension_t

    def changed_resolution_units(self):
        ru = self.resolution_units.currentText()
        self.resolution.setValue(self.resolution.value() * self.resolution_u[self._current_resolution_units] / float(self.resolution_u[ru]))
        self._current_resolution_units = ru

    # Update print dimensions using the image dimensions and resolutions
    def update_print_dimensions(self):
        self._w = self.width.value()
        self._h = self.height.value()

        print_units = self.print_units.currentText()
        w_p = self.get_as_print_size(self._w, print_units)
        h_p = self.get_as_print_size(self._h, print_units)

        self.width_p.setValue(w_p)
        self.height_p.setValue(h_p)

    def get_as_print_size(self, s, u):
        ps = self.resolution.value()
        ps_u = self.resolution_units.currentText()
        s = s / (ps * self.resolution_u[ps_u])  # Get size in metres
        return self.get_converted_measurement(s, 'm', u)  # Return converted value    

    def get_print_size(self, u):
        return (
            self.get_as_print_size(self._w, u),
            self.get_as_print_size(self._h, u)
            )

    # Update image dimensions using the print dimensions and resolutions
    def update_image_dimensions(self):
        w_p = self.width_p.value()
        h_p = self.height_p.value()

        print_units = self.print_units.currentText()
        resolution = self.resolution.value()
        resolution_units = self.resolution_units.currentText()

        self._w = self.get_pixel_size(w_p, print_units, resolution, resolution_units)
        self._h = self.get_pixel_size(h_p, print_units, resolution, resolution_units)

        self.width.setValue(self._w)
        self.height.setValue(self._h)

    def get_pixel_size(self, s, pu, r, ru):
        s = s / self.print_u[pu]  # Convert to metres
        rm = r * self.resolution_u[ru]  # Dots per metre
        return s * rm

    def get_converted_measurement(self, x, f, t):
        # Convert measurement from f to t
        f = self.print_u[f]
        t = self.print_u[t]
        return (float(x) / float(f)) * t

    def get_pixel_dimensions(self):
        return QSize(self._w, self._h)

    def get_dots_per_meter(self):
        return self.resolution.value() * self.resolution_u[self.resolution_units.currentText()]

    def get_dots_per_inch(self):
        if self.resolution_units.currentText() == 'in':
            return self.resolution.value()
        else:
            return self.get_converted_measurement(self.resolution.value(), self.convert_res_to_unit[self.resolution_units.currentText()], 'in')

    def get_resample(self):
        if self.scaling:
            return self.scaling.currentText() == 'Resample'
        else:
            return False


class MatchStyleDialog(GenericDialog):
    '''
    Edit individual match rules and styles
    '''

    match_types = {
        'Exact': MATCH_EXACT,
        'Contains': MATCH_CONTAINS,
        'Starts with': MATCH_START,
        'Ends with': MATCH_END,
        'Regular expression': MATCH_REGEXP,
    }

    LINESTYLES_dict = OrderedDict([('None', None)] + list(zip(LINESTYLES, LINESTYLES)))
    MARKERS_dict = OrderedDict([('None', None)] + list(zip(MARKERS, MARKERS)))
    FILLSTYLES_dict = OrderedDict([('None', None)] + list(zip(FILLSTYLES, FILLSTYLES)))
    HATCHSTYLES_dict = OrderedDict([('None', None)] + list(zip(HATCHSTYLES, HATCHSTYLES)))

    def __init__(self, parent, mdls=None, **kwargs):
        super(MatchStyleDialog, self).__init__(parent, **kwargs)

        self.setWindowTitle("Define class match and line-marker style")
        # '', 'RE', 'Marker', 'Fill', 'Line', 'Hatch', 'Color', 'Face', 'Edge'

        self.config = ConfigManager()
        self.config.set_defaults({
            'match_str': '',
            'match_type': MATCH_EXACT,
            'style': '-',
            'linewidth': 0.75,
            'color': '#000000',
            'marker': 's',
            'markersize': 8.0,
            'markerfacecolor': '#000000',
            'markeredgecolor': None,
            'fillstyle': None,
            'hatch': None,
        })

        if mdls:
            md, ls = mdls
            self.config.set_many({
                'match_str': md.match_str,
                'match_type': md.match_type,
                'linestyle': ls.linestyle,
                'linewidth': ls.linewidth,
                'color': ls.color,
                'marker': ls.marker,
                'markersize': ls.markersize,
                'markerfacecolor': ls.markerfacecolor,
                'markeredgecolor': ls.markeredgecolor,
                'fillstyle': ls.fillstyle,
                'hatch': ls.hatch,
            })

        # Match definition
        vw = QGridLayout()
        self.match_str_le = QLineEdit()
        self.config.add_handler('match_str', self.match_str_le)
        vw.addWidget(self.match_str_le, 0, 0)

        self.match_type_cb = QComboBox()
        self.match_type_cb.addItems(self.match_types.keys())
        self.config.add_handler('match_type', self.match_type_cb, self.match_types)
        vw.addWidget(self.match_type_cb, 0, 1)

        gb = QGroupBox('Rule matching')
        gb.setLayout(vw)
        self.layout.addWidget(gb)
        # Style definition
        # '', '?', 'Line', 'Color', 'Marker',  'Face', 'Edge', 'Fill', 'Hatch' ]

        vw = QGridLayout()
        vw.addWidget(QLabel('Line'), 0, 0)

        self.line_cb = QComboBox()
        self.line_cb.addItems(self.LINESTYLES_dict.keys())
        self.config.add_handler('style', self.line_cb, self.LINESTYLES_dict)
        vw.addWidget(self.line_cb, 0, 1)

        self.linewidth_sb = QNoneDoubleSpinBox()
        self.linewidth_sb.setRange(0, 10)
        self.linewidth_sb.setDecimals(2)
        self.config.add_handler('linewidth', self.linewidth_sb)
        vw.addWidget(self.linewidth_sb, 0, 2)

        self.color_btn = QColorButton()
        self.config.add_handler('color', self.color_btn)
        vw.addWidget(self.color_btn, 0, 3)

        vw.addWidget(QLabel('Marker'), 1, 0)

        self.marker_cb = QComboBox()
        self.marker_cb.addItems(self.MARKERS_dict.keys())
        self.config.add_handler('marker', self.marker_cb, self.MARKERS_dict)
        vw.addWidget(self.marker_cb, 1, 1)

        self.markersize_sb = QNoneDoubleSpinBox()
        self.markersize_sb.setRange(1, 24)
        self.markersize_sb.setDecimals(2)
        self.config.add_handler('markersize', self.markersize_sb)
        vw.addWidget(self.markersize_sb, 1, 2)

        self.face_btn = QColorButton()
        #self.face_btn.setColor( ls.markerfacecolor )
        self.config.add_handler('markerfacecolor', self.face_btn)
        vw.addWidget(self.face_btn, 1, 3)

        self.edge_btn = QColorButton()
        #self.edge_btn.setColor( ls.markeredgecolor )
        self.config.add_handler('markeredgecolor', self.edge_btn)
        vw.addWidget(self.edge_btn, 1, 4)

        vw.addWidget(QLabel('Fill type'), 2, 0)

        self.fill_fb = QComboBox()
        self.fill_fb.addItems(self.FILLSTYLES_dict.keys())
        self.config.add_handler('fillstyle', self.fill_fb, self.FILLSTYLES_dict)
        vw.addWidget(self.fill_fb, 2, 1)

        self.hatch_cb = QComboBox()
        self.hatch_cb.addItems(self.HATCHSTYLES_dict.keys())
        self.config.add_handler('hatch', self.hatch_cb, self.HATCHSTYLES_dict)
        vw.addWidget(QLabel('Hatching'), 3, 0)
        vw.addWidget(self.hatch_cb, 3, 1)

        gb = QGroupBox('Line and Marker Style')
        gb.setLayout(vw)
        self.layout.addWidget(gb)

        # Build dialog layout
        self.dialogFinalise()

    def onColorPicker(self):
        dlg = QColorDialog(self)
        dlg.setOption(QColorDialog.DontUseNativeDialog)
        # FIXME: Add colors from current default set to the custom color table
        # dlg.setCustomColor(0, QColor('red') )
        if dlg.exec_():
            pass

    def sizeHint(self):
        return QSize(600, 300)


class MatchStyleManagerDialog(GenericDialog):
    '''
    An editor for the line style configuration
    Present two tabs one for custom, one for auto
    
    On the custom tab allow addition/editing/removal of style definitions
        - and editing of the custom match options (string, type, etc.)
        
    On the auto tab allow editing/removal of the existing style definitions only
    
    Save and apply back to the main manager.
    '''

    match_styles_abbrev = {
        MATCH_EXACT: '=',
        MATCH_CONTAINS: 'I',
        MATCH_START: 'S',
        MATCH_END: 'E',
        MATCH_REGEXP: 'R',
    }

    def __init__(self, parent=None, **kwargs):
        super(MatchStyleManagerDialog, self).__init__(parent, **kwargs)

        self.setWindowTitle("Line styles and markers")

        self.styles_tw = QTreeWidget()
        self.styles_tw.setColumnCount(11)
        self.styles_tw.setColumnWidth(0, 200)

        headerItem = QTreeWidgetItem()
        headers = ['', '?', 'Line', 'Color', ' W ', 'Marker', 'S', 'Face', 'Edge', 'Fill', 'Hatch']

        for n, str in enumerate(headers):
            headerItem.setText(n, str)
            if n > 0:
                headerItem.setTextAlignment(n, Qt.AlignHCenter)
                self.styles_tw.setColumnWidth(n, 16 + len(headers[n]) * 6)

        self.styles_tw.setHeaderItem(headerItem)

        vw = QGridLayout()
        self.styles_tw.setMinimumSize(self.sizeHint())
        vw.addWidget(self.styles_tw, 0, 0, 6, 1)
        self.populate_style_list()

        self.new_btn = QPushButton('New')
        self.new_btn.clicked.connect(self.onNew)
        vw.addWidget(self.new_btn, 0, 1)

        self.edit_btn = QPushButton('Edit')
        self.edit_btn.clicked.connect(self.onEdit)
        vw.addWidget(self.edit_btn, 1, 1)

        self.delete_btn = QPushButton('Delete')
        self.delete_btn.clicked.connect(self.onDelete)
        vw.addWidget(self.delete_btn, 2, 1)

        self.up_btn = QPushButton('↑')
        self.up_btn.clicked.connect(self.onMoveUp)
        vw.addWidget(self.up_btn, 3, 1)

        self.down_btn = QPushButton('↓')
        self.down_btn.clicked.connect(self.onMoveDown)
        vw.addWidget(self.down_btn, 4, 1)

        self.layout.addLayout(vw)

        # Build dialog layout
        self.dialogFinalise()

    def onNew(self):
        dlg = MatchStyleDialog(self)
        if dlg.exec_():
            md = ClassMatchDefinition()
            ls = StyleDefinition()
            for k in ['match_str', 'match_type']:
                md.__dict__[k] = dlg.config.get(k)

            for k in ['linestyle', 'color', 'marker', 'markersize', 'markerfacecolor', 'markeredgecolor', 'fillstyle', 'hatch', 'linewidth']:
                ls.__dict__[k] = dlg.config.get(k)

            styles.matchdefs.append((md, ls))
            self.styles_tw.clear()
            self.populate_style_list()

    def onEdit(self, checked=None):
        items = self.styles_tw.selectedItems()
        if items:
            item = items[0]  # Only one
            dlg = MatchStyleDialog(self, (item.md, item.ls))
            if dlg.exec_():
                # Get data from from the dialog and update the md,ls to match
                md, ls = item.md, item.ls

                if md.is_auto:
                    # Shift auto items to non-auto
                    styles.automatchdefs.remove((md, ls))
                    styles.matchdefs.append((md, ls))

                for k in ['match_str', 'match_type']:
                    md.__dict__[k] = dlg.config.get(k)

                for k in ['linestyle', 'color', 'marker', 'markersize', 'markerfacecolor', 'markeredgecolor', 'fillstyle', 'hatch', 'linewidth']:
                    ls.__dict__[k] = dlg.config.get(k)

                if md.is_auto:
                    md.is_auto = False  # No longer auto, has been edited
                    self.refresh()
                else:
                    self.update_item(item, md, ls)

    def onMoveUp(self):
        item = self.styles_tw.currentItem()
        try:
            idx = styles.matchdefs.index((item.md, item.ls))
        except ValueError:
            return
        else:
            if idx > 0:
                t = styles.matchdefs[idx - 1]
                styles.matchdefs[idx - 1] = styles.matchdefs[idx]
                styles.matchdefs[idx] = t
                self.refresh()
                self.styles_tw.setCurrentItem(self.styles_tw.topLevelItem(idx - 1))

    def onMoveDown(self):
        item = self.styles_tw.currentItem()
        try:
            idx = styles.matchdefs.index((item.md, item.ls))
        except ValueError:
            return
        else:
            if idx < len(styles.matchdefs):
                t = styles.matchdefs[idx + 1]
                styles.matchdefs[idx + 1] = styles.matchdefs[idx]
                styles.matchdefs[idx] = t
                self.refresh()
                self.styles_tw.setCurrentItem(self.styles_tw.topLevelItem(idx + 1))

    def onDelete(self):
        item = self.styles_tw.currentItem()
        self.styles_tw.takeTopLevelItem(self.styles_tw.indexOfTopLevelItem(item))
        if item.md.is_auto:
            styles.automatchdefs.remove((item.md, item.ls))
        else:
            styles.matchdefs.remove((item.md, item.ls))

    def sizeHint(self):
        return QSize(600, 300)

    def refresh(self):
        self.styles_tw.clear()
        self.populate_style_list()

    def update_item(self, item, md, ls):
        item.md = md
        item.ls = ls

        if md.is_auto:
            item.setIcon(0, QIcon(os.path.join(utils.scriptdir, 'icons', 'lightning.png')))
        else:
            item.setIcon(0, QIcon(None))

        item.setText(0, md.match_str)
        item.setText(1, self.match_styles_abbrev[md.match_type])
        item.setText(2, ls.linestyle)
        item.setText(4, str(ls.linewidth) if ls.linewidth is not None else '')
        item.setText(5, ls.marker)
        item.setText(6, str(ls.markersize) if ls.markersize is not None else '')
        item.setText(9, ls.fillstyle)
        item.setText(10, ls.hatch)

        for c, s, v in [(3, '▬', ls.color), (7, '▩', ls.markerfacecolor), (8, '▩', ls.markeredgecolor)]:
            if v is not None:
                item.setText(c, s)
                item.setForeground(c, QColor(v))

        return item

    def populate_style_list(self):

        for n, (md, ls) in enumerate(styles.matchdefs + styles.automatchdefs):
            item = QTreeWidgetItem()

            if not md.is_auto:
                item.order = n
            else:
                item.order = 65536

            for c in range(1, 9):
                item.setTextAlignment(c, Qt.AlignHCenter | Qt.AlignVCenter)

            self.update_item(item, md, ls)
            self.styles_tw.addTopLevelItem(item)


class QWebPageExtend(QWebPage):
    def shouldInterruptJavascript():
        return False


class QWebViewExtend(QWebView):

    def __init__(self, parent, onNavEvent=None, **kwargs):
        super(QWebViewExtend, self).__init__(parent, **kwargs)

        self.w = parent
        #self.setPage(QWebPageExtend(self.w))
        self.setHtml(BLANK_DEFAULT_HTML, QUrl("~"))

        self.page().setContentEditable(False)
        self.page().setLinkDelegationPolicy(QWebPage.DelegateExternalLinks)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Override links for internal link cleverness
        if onNavEvent:
            self.onNavEvent = onNavEvent
            self.linkClicked.connect(self.delegateUrlWrapper)

        self.setContextMenuPolicy(Qt.CustomContextMenu)  # Disable right-click

    def delegateUrlWrapper(self, url):
        if url.isRelative() and url.hasFragment():
            self.page().currentFrame().evaluateJavaScript("$('html,body').scrollTop( $(\"a[name='%s']\").offset().top );" % url.fragment())
        else:
            self.onNavEvent(url)

    def sizeHint(self):
        if self.w:
            return self.w.size()
        else:
            return super(QWebViewExtend, self).sizeHint()

    @pyqtSlot(str)
    def delegateLink(self, url):
        self.onNavEvent(QUrl(url))
        return True


# View Dialogs

# Source data selection dialog
# Present a list of widgets (drop-downs) for each of the interfaces available on this plugin
# in each list show the data sources that can potentially file that slot.
# Select the currently used
class DialogDataSource(GenericDialog):
    def __init__(self, parent=None, view=None, **kwargs):
        super(DialogDataSource, self).__init__(parent, **kwargs)

        self.v = view

        self.setWindowTitle(tr("Select Data Source(s)"))

        # Build a list of dicts containing the widget
        # with target data in there
        self.lw_consumeri = list()
        for n, cd in enumerate(self.v.data.consumer_defs):

            self.lw_consumeri.append(QComboBox())
            cdw = self.lw_consumeri[n]  # Shorthand
            #datasets = self.v.data.can_consume_which_of(current_datasets, [cd])

            cdw.addItem('No input')
            interfaces = []
            nd = 0
            # Iterate all available outputs on all tools
            for t in current_tools:
                if t is not self.v:
                    for k, dataset in t.data.o.items():
                        interfaces.append((t.data, k))

                        if type(dataset) == pd.DataFrame:
                            ts = 'pandas.DataFrame(%s)' % dataset.values.dtype
                            shape = 'x'.join([str(s) for s in dataset.shape])
                        elif type(dataset) == np.ndarray:
                            ts = 'numpy.ndarray(%s)' % dataset.values.dtype
                            shape = 'x'.join([str(s) for s in dataset.shape])
                        else:
                            ts = type(dataset)
                            shape = 'None'

                        cdw.addItem(QIcon(t.icon), '%s %s %s (%s)' % (t.name, k, ts, shape))

                        nd += 1
                        # If this is the currently used data source for this interface, set it active
                        if self.v.data.i[cd.target] is not None and t.data == self.v.data.i[cd.target][0] and k == self.v.data.i[cd.target][1]:
                            cdw.setCurrentIndex(nd)  # nd+1 because of the None we've inserted at the front

            cdw.consumer_def = cd
            cdw.interfaces = [None] + interfaces

            self.layout.addWidget(QLabel("%s:" % cd.title))
            self.layout.addWidget(cdw)

        self.setMinimumSize(QSize(600, 100))
        self.layout.setSizeConstraint(QLayout.SetMinimumSize)

        # Build dialog layout
        self.dialogFinalise()

        
class DialogDataOutput(GenericDialog):
    def __init__(self, parent=None, view=None, **kwargs):
        super(DialogDataOutput, self).__init__(parent, buttons=['ok'], **kwargs)

        self.v = view

        self.setWindowTitle("Data Output(s)")

        self.lw_sources = QTreeWidget()  # Use TreeWidget but flat; for multiple column view
        self.lw_sources.setColumnCount(4)
        self.lw_sources.setHeaderLabels(['', 'Output', 'Type', 'Size'])  # ,'#'])
        self.lw_sources.setUniformRowHeights(True)
        self.lw_sources.rootIsDecorated()
        self.lw_sources.hideColumn(0)

        datasets = current_datasets  # Get a list of dataset objects to test
        self.datasets = []

        for k, dataset in list(self.v.data.o.items()):

        #QListWidgetItem(dataset.name, self.lw_sources)
            tw = QTreeWidgetItem()

            tw.setText(0, str(len(self.datasets) - 1))  # Store index
            tw.setText(1, k)

            if type(dataset) == pd.DataFrame:
                ts = 'pandas.DataFrame(%s)' % dataset.values.dtype
            elif type(dataset) == np.ndarray:
                ts = 'numpy.ndarray(%s)' % dataset.values.dtype
            else:
                ts = type(dataset)

            tw.setText(2, ts)
            tw.setText(3, 'x'.join([str(s) for s in dataset.shape]))

            self.lw_sources.addTopLevelItem(tw)

        for c in range(5):
            self.lw_sources.resizeColumnToContents(c)

        self.layout.addWidget(self.lw_sources)
        self.setMinimumSize(QSize(600, 100))
        self.layout.setSizeConstraint(QLayout.SetMinimumSize)

        # Build dialog layout
        self.dialogFinalise()


# Overload this to provide some better size hinting to the inside tabs
class QTabWidgetExtend(QTabWidget):

    auto_unfocus_tabs = ['?']

    def __init__(self, parent, **kwargs):
        super(QTabWidgetExtend, self).__init__(parent, **kwargs)
        self.w = parent
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self._unfocus_tabs_enabled = True

    def sizeHint(self):
        return self.w.size()

    # A few wrappers to
    def addView(self, widget, name, focused=True, unfocus_on_refresh=False, **kwargs):
        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # Automagically unfocus the help (+any other equivalent) tabs if were' refreshing a more interesting one
        widget._unfocus_on_refresh = unfocus_on_refresh
        t = super(QTabWidgetExtend, self).addView(widget, name, **kwargs)

        return t

    def autoSelect(self):
        if self._unfocus_tabs_enabled:
            cw = self.currentWidget()
            if cw._unfocus_on_refresh:
                for w in range(0, self.count()):
                    uf = self.widget(w)._unfocus_on_refresh
                    if not uf and self.widget(w).isEnabled():
                        self.setCurrentIndex(w)
                        self._unfocus_tabs_enabled = False  # Don't do this again (so user can select whatever they want)
                        break


#### View Object Prototypes (Data, Assignment, Processing, Analysis, Visualisation) e.g. used by plugins
class GenericApp(QObject):
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
        super(GenericApp, self).__init__(parent)
        self.id = str(id(self))

        self.w = QMainWindow()
        self.w.t = self  # Pass through reference to self

        self._lock = False
        self._previous_size = None

        current_tools.append(self)
        current_tools_by_id[self.id] = self

        self._pause_analysis_flag = False
        self._latest_dock_widget = None
        self._latest_generator_result = None
        self._auto_consume_data = auto_consume_data

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

        self.logger.debug('Creating tool: %s' % name)

        self.logger.debug('Setting up data manager...')
        self.data = data.DataManager(self.parent(), self)

        self.logger.debug('Setting up view manager...')
        self.views = ViewManager(self)

        self.logger.debug('Setting up file watcher manager...')
        self.file_watcher = QFileSystemWatcher()
        self.file_watcher.fileChanged.connect(self.onFileChanged)

        self.toolbars = {}
        self.configPanels = QTabWidget()
        self.configpanels = {}

        self.logger.debug('Register internal url handler...')
        self.register_url_handler(self.default_url_handler)

        self.w.setCentralWidget(self.views)

        self.logger.debug('Setup config manager...')
        self.config = ConfigManager()  # Configuration manager object; handle all get/setting, defaults etc.
        # Add hooks for custom widgets
        self.config.hooks = dict(self.config.hooks.items() + custom_pyqtconfig_hooks.items())

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
        self._init_timer = QTimer.singleShot(PX_INIT_SHOT, self.init_auto_consume_data)

    def init_auto_consume_data(self):
        self.logger.debug('Post-init: init_auto_consume_data')

        self._is_autoconsume_success = False
        if self._auto_consume_data:
            self._is_autoconsume_success = self.data.consume_any_app(current_tools[::-1])  # Try consume from any app; work backwards

        self.data.source_updated.connect(self.autogenerate)  # Auto-regenerate if the source data is modified
        self.config.updated.connect(self.autoconfig)  # Auto-regenerate if the configuration changes

        if self.autoconfig_name:
            self.config.updated.connect(self.autoconfig_rename)  # Auto-rename if it is set

        self._init_timer = QTimer.singleShot(PX_INIT_SHOT, self.init_notebook)

    def init_notebook(self):
        self.logger.debug('Post-init: init_notebook')


        # Initial display of the notebook
        if self.code_editor.is_enhanced_editor:
            self.code_editor.detectSyntax(language='Python')

        self.addDataToolBar()
        self.addEditorToolBar()
        self.addFigureToolBar()

        self.load_notes()
        self.load_source()

        html = '''<html>
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

        self.notes_viewer.setHtml(unicode(html))

        self.views.addView(self.notes_viewer, '&?', unfocus_on_refresh=True)
        self.views.addView(self.code_editor, '&#', unfocus_on_refresh=True)
        self.views.addView(self.log_viewer, '&=', unfocus_on_refresh=True)
        #self.views.addView( self.logView, 'Log')

        if self._is_autoconsume_success is not False:
            # This will fire after the notebook has completed above
            self._init_timer = QTimer.singleShot(PX_INIT_SHOT, self.autogenerate)

    def reload(self):
        self.load_notes()
        self.load_source()

    def load_notes(self):
        with open(os.path.join(self.plugin.path, "%s.md" % self.shortname), 'rU') as f:
            self.notes = f.read().decode('utf-8')

    def load_source(self):
        with open(os.path.join(self.plugin.path, "%s.py" % self.shortname), 'rU') as f:
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

    def autogenerate(self, *args, **kwargs):
        self.logger.debug("autogenerate %s" % self.name)
        if self._pause_analysis_flag:
            self.status.emit('paused')
            return False
        self.generate()

    def generate(self):
        self.logger.info("Running tool %s" % self.name)

        strip_rcParams = ['tk.pythoninspect', 'savefig.extension']
        varsi = {
            'config': self.config.as_dict(),
            'rcParams': {k: v for k, v in rcParams.items() if k not in strip_rcParams},
            'styles': styles,
            '_pathomx_tool_path': self.plugin.path,
            '_pathomx_database_path': os.path.join(utils.scriptdir, 'database'),
        }

        self.status.emit('active')
        self.progress.emit(0.)

        notebook_queue.add_job(self, varsi, progress_callback=self.progress.emit, result_callback=self._worker_result_callback)  # , error_callback=self._worker_error_callback)

    def _worker_result_callback(self, result):
        self.progress.emit(1.)

        if 'stdout' in result:
            self.logger.error(result['stdout'])

        if result['status'] == 0:
            self.logger.debug("Notebook complete %s" % self.name)
            self.status.emit('done')
            varso = result['varso']

            if 'styles' in varso:
                global styles
                styles = varso['styles']

        elif result['status'] == -1:
            self.logger.debug("Notebook error %s" % self.name)
            self.status.emit('error')
            self.logger.error(result['traceback'])
            varso = {}
        #varso['_pathomx_result_notebook'] = result['notebook']
        #self.nb = result['notebook']

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
        notebook_queue.in_process_runner.kernel_manager.kernel.shell.push({'t%s' % self.id: PathomxTool(self.name, **kwargs)})

    def autoprerender(self, kwargs_dict):
        self.logger.debug("autoprerender %s" % self.name)
        self.views.data = self.prerender(**kwargs_dict)
        # Delay this 1/2 second so next processing gets underway
        # FIXME: when we've got a better runner system
        QTimer.singleShot(PX_RENDER_SHOT, self.views.source_data_updated.emit)
        #self.views.source_data_updated.emit()

    def prerender(self, *args, **kwargs):

        FIGURE_COLOR = QColor(0, 127, 0)
        DATA_COLOR = QColor(0, 0, 127)

        result_dict = {
        #    'Notebook': {'notebook': kwargs['_pathomx_result_notebook']}
            }

        for k, v in kwargs.items():
            if type(v) == Figure:
                if self.views.get_type(k) != IPyMplView:
                    self.views.addView(IPyMplView(self), k, color=FIGURE_COLOR)
                result_dict[k] = {'fig': v}

            elif type(v) == displayobjects.Svg or type(v) == display.SVG:
                if self.views.get_type(k) != SVGView:
                    self.views.addView(SVGView(self), k, color=FIGURE_COLOR)

                result_dict[k] = {'svg': v}

            elif type(v) == displayobjects.Html or type(v) == displayobjects.Markdown:
                if self.views.get_type(k) != HTMLView:
                    self.views.addView(HTMLView(self), k, color=FIGURE_COLOR)

                result_dict[k] = {'html': v}

            elif type(v) == pd.DataFrame:
                if self.views.get_type(k) != DataFrameWidget:
                    self.views.addView(DataFrameWidget(pd.DataFrame({}), parent=self), k, color=DATA_COLOR)

                result_dict[k] = {'data': v}

            elif hasattr(v, '_repr_html_'):
                # on IPython notebook aware objects to generate Html views
                if self.views.get_type(k) != HTMLView:
                    self.views.addView(HTMLView(self), k, color=FIGURE_COLOR)

                result_dict[k] = {'html': v._repr_html_()}

        return result_dict

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

    def autoconfig_rename(self, signal):
        self.set_name(self.autoconfig_name.format(**self.config.as_dict()))

    def store_views_data(self, kwargs_dict):
        self.views.source_data = kwargs_dict

    def set_name(self, name):
        self.name = name
        self.w.setWindowTitle(name)
        self.nameChanged.emit(name)

    def show(self):
        self.parent().activetoolDock.setWidget(self.w)
        self.parent().activetoolDock.setWindowTitle(self.name)
        self.parent().activetoolDock.show()

        self.parent().toolDock.setWidget(self.configPanels)

    def raise_(self):
        self.parent().activetoolDock.setWidget(self.w)
        self.parent().activetoolDock.setWindowTitle(self.name)
        self.parent().activetoolDock.raise_()

    def hide(self):
        self.parent().toolDock.setWidget(self.parent().toolbox)
        self.parent().activetoolDock.setWidget(QWidget())  # Empty

    def addToolBar(self, *args, **kwargs):
        return self.w.addToolBar(*args, **kwargs)

    def onDelete(self):
        self.delete()

    def addConfigPanel(self, Panel, name):
        panel = Panel(self)
        self.configPanels.addTab(panel, name)
        self.configpanels[name] = panel

    def addSelfToolBar(self):

        pass

    def addDataToolBar(self):
        if 'data' in self.toolbars:
            return False

        t = self.w.addToolBar('Data')
        t.setIconSize(QSize(16, 16))

        select_dataAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'data-source.png')), tr('Select a data source…'), self.w)
        select_dataAction.setStatusTip('Select a compatible data source')
        select_dataAction.triggered.connect(self.onSelectDataSource)
        t.addAction(select_dataAction)

        select_dataAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'play.png')), tr('Calculate'), self.w)
        select_dataAction.setStatusTip('Recalculate')
        select_dataAction.triggered.connect(self.onRecalculate)
        t.addAction(select_dataAction)

        self.pause_analysisAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'control-pause.png')), tr('Pause automatic analysis'), self.w)
        self.pause_analysisAction.setStatusTip('Do not automatically refresh analysis when source data updates')
        self.pause_analysisAction.setCheckable(True)
        self.pause_analysisAction.setChecked(self.default_pause_analysis)
        self.pause_analysisAction.toggled.connect(self.onAutoAnalysisToggle)
        t.addAction(self.pause_analysisAction)
        self._pause_analysis_flag = self.default_pause_analysis

        select_dataAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'data-output.png')), tr('View resulting data…'), self.w)
        select_dataAction.setStatusTip('View resulting data output from this plugin')
        select_dataAction.triggered.connect(self.onViewDataOutput)
        t.addAction(select_dataAction)

        self.toolbars['data'] = t

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

    def addFigureToolBar(self):
        if 'figure' in self.toolbars:
            return False

        t = self.w.addToolBar('Figure')
        t.tool = self
        t.setIconSize(QSize(16, 16))

        export_imageAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'image-export.png')), tr('Export current figure as image…'), self.w)
        export_imageAction.setStatusTip(tr('Export figure to image'))
        export_imageAction.triggered.connect(self.onSaveImage)
        t.addAction(export_imageAction)

        t.addSeparator()
        toolitems = (
            ('Home', 'Reset original view', 'home.png', 'home'),
            ('Back', 'Back to  previous view', 'back.png', 'back'),
            ('Forward', 'Forward to next view', 'forward.png', 'forward'),
            ('Pan', 'Pan axes with left mouse, zoom with right', 'move.png', 'pan'),
            ('Zoom', 'Zoom to rectangle', 'zoom_to_rect.png', 'zoom'),
        )

        t._mpl_specific_actions = []
        t._checkable_actions = {}
        t.modeActionGroup = QActionGroup(t)

        for text, tooltip_text, image_file, callback in toolitems:
            act = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', image_file)), text, self)

            def make_callback(callback):
                return lambda e: self.dispatchMplEvent(e, callback)
            act.triggered.connect(make_callback(callback))

            t._mpl_specific_actions.append(act)

            if callback in ['zoom', 'pan']:
                act.setCheckable(True)
                t._checkable_actions[callback] = act
                act.setActionGroup(t.modeActionGroup)

            if tooltip_text is not None:
                act.setToolTip(tooltip_text)

            act.setEnabled(False)  # Disable by default; nonstandard
            t.addAction(act)

        # Add custom toolbar option for selecting regions of matplotlib plots
        select_regionAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'zone-select.png')), tr('Select regions from plot…'), self)
        select_regionAction.setCheckable(True)
        select_regionAction.setStatusTip(tr('Select regions in current plot'))
        select_regionAction.triggered.connect(make_callback('select_region'))
        t.addAction(select_regionAction)
        t._checkable_actions['select_region'] = select_regionAction
        select_regionAction.setActionGroup(t.modeActionGroup)
        select_regionAction.setEnabled(False)

        t._mpl_selection_region_action = select_regionAction

        self.views.currentChanged.connect(self.onMplToolBarCanvasChanged)

        self.toolbars['figure'] = t

    def dispatchMplEvent(self, e, callback):
        selected_view = self.views.widget(self.views.currentIndex())
        if selected_view.is_mpl_toolbar_enabled:
            getattr(selected_view.navigation, callback)(e)

    def onMplToolBarCanvasChanged(self, w):
        selected_view = self.views.widget(w)
        if selected_view and hasattr(selected_view, 'is_mpl_toolbar_enabled') and selected_view.is_mpl_toolbar_enabled:
            # Reset buttons to current view state for the selected tabs' Canvas
            for c, m in [('zoom', 'ZOOM'), ('pan', 'PAN')]:
                self.toolbars['figure']._checkable_actions[c].setChecked(selected_view.navigation._active == m)

            for act in self.toolbars['figure']._mpl_specific_actions:
                act.setEnabled(True)

            if self.config.get('selected_data_regions') is not None:
                self.toolbars['figure']._mpl_selection_region_action.setEnabled(True)

            selected_view.navigation.add_region_callback = self.onAddRegion
            # Pass these values for the region selection
        else:
            for act in self.toolbars['figure']._mpl_specific_actions:
                act.setEnabled(False)
            self.toolbars['figure']._mpl_selection_region_action.setEnabled(False)

    def onAddRegion(self, *args):
        selected_view = self.views.widget(self.views.currentIndex())
        if selected_view and self.config.get('selected_data_regions') is not None:
            # FIXME: Copy; list mutable will fudge config - fix in pyqtconfig
            current_regions = self.config.get('selected_data_regions')[:]
            current_regions.append(tuple([selected_view.name] + list(args)))
            self.config.set('selected_data_regions', current_regions)

    def onWatchSourceDataToggle(self, checked):
        self._autoload_source_files_on_change = checked

    def onAutoAnalysisToggle(self, checked):
        self._pause_analysis_flag = checked
        self.pause_status_changed.emit(checked)

    def onFileChanged(self, file):
        if self._autoload_source_files_on_change:
            self.load_datafile(file)

    def onSaveImage(self):
        # Get currently selected webview
        cw = self.views.currentWidget()

        # Load dialog for image export dimensions and resolution
        # TODO: dialog!
        sizedialog = ExportImageDialog(self.w, size=cw.size(), show_rerender_options=cw._offers_rerender_on_save)
        ok = sizedialog.exec_()
        if ok:
            cw.saveAsImage(sizedialog)

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


class IPythonApp(GenericApp):
    pass


# Renaming for sense
class GenericTool(GenericApp):
    pass


class ExportDataApp(IPythonApp):
    def __init__(self, *args, **kwargs):
        super(ExportDataApp, self).__init__(*args, **kwargs)

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


# Analysis/Visualisation view prototypes
# Class for analysis views, using graph-based visualisations of defined datasets
# associated layout and/or analysis
class AnalysisApp(IPythonApp):
    def __init__(self, *args, **kwargs):
        super(AnalysisApp, self).__init__(*args, **kwargs)
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


class remoteQueryDialog(GenericDialog):

    request_key = 'v'

    def parse(self, data):
        # Parse incoming data and return a dict mapping the displayed values to the internal value
        l = data.split('\n')
        return dict(list(zip(l, l)))

    def do_query(self):
        self.select.clear()
        r = requests.get(self.request_url, params={self.request_key: self.textbox.text()})
        if r.status_code == 200:
            self.data = self.parse(r.text)
            self.select.addItems(list(self.data.keys()))

    def __init__(self, parent, request_url=None, request_key=None, **kwargs):
        super(remoteQueryDialog, self).__init__(parent, **kwargs)
        self.textbox = QLineEdit()
        querybutton = QPushButton('↺')
        querybutton.clicked.connect(self.do_query)

        queryboxh = QHBoxLayout()
        queryboxh.addWidget(self.textbox)
        queryboxh.addWidget(querybutton)

        self.data = None  # Deprecated

        self.select = QListWidget()
        self.request_url = request_url
        self.request_key = request_key

        self.layout.addLayout(queryboxh)
        self.layout.addWidget(self.select)

        self.dialogFinalise()


class ConfigPanel(QWidget):

    def __init__(self, parent, *args, **kwargs):
        super(ConfigPanel, self).__init__(parent.w, *args, **kwargs)

        self.tool = parent
        self.config = parent.config
        self.layout = QVBoxLayout()

    def finalise(self):

        self.layout.addStretch()
        self.setLayout(self.layout)

    def setListControl(self, control, list, checked):
        # Automatically set List control checked based on current options list
        items = control.GetItems()
        try:
            idxs = [items.index(e) for e in list]
            for idx in idxs:
                if checked:
                    control.Select(idx)
                else:
                    control.Deselect(idx)
        except:
            pass


class SimpleFileOpenConfigPanel(ConfigPanel):
    ''' Simple file open configuration panel for standard use
        
        This simple configuration panel shows just a file path widget and button
        and can be used for most standard import tools that have no complex options.
    '''

    description = tr("Open experimental data from file")
    filename_filter = tr("All Files") + " (*.*);;"

    def __init__(self, parent, *args, **kwargs):
        super(SimpleFileOpenConfigPanel, self).__init__(parent, *args, **kwargs)

        self.v = parent
        self.config = parent.config
        gb = QGroupBox('Open file')
        grid = QGridLayout()
        self.filename = QFileOpenLineEdit(description=self.description, filename_filter=self.filename_filter)
        grid.addWidget(QLabel('Path'), 0, 0)
        grid.addWidget(self.filename, 0, 1)
        self.config.add_handler('filename', self.filename)
        gb.setLayout(grid)

        self.layout.addWidget(gb)

        self.finalise()


class RegionConfigPanel(ConfigPanel):
    ''' Automatic config panel for selecting regions in data, e.g. for icoshift

        This simple config panel lists currently defined data regions, currently defineable
        via drag-drop in output views. Manual definition should also be possible.
    '''

    def __init__(self, *args, **kwargs):
        super(RegionConfigPanel, self).__init__(*args, **kwargs)

        self.fwd_map_cache = {}

        # Correlation variables
        gb = QGroupBox('Regions')
        vbox = QVBoxLayout()
        # Populate the list boxes
        self.lw_variables = QListWidgetAddRemove()
        self.lw_variables.setSelectionMode(QAbstractItemView.ExtendedSelection)
        vbox.addWidget(self.lw_variables)

        vboxh = QHBoxLayout()
        remfr = QPushButton('Remove')
        remfr.clicked.connect(self.onRegionRemove)

        #remfr = QPushButton('Add')
        #remfr.clicked.connect(self.onRegressionAdd)

        #vboxh.addWidget(addfr)
        vboxh.addWidget(remfr)
        vbox.addLayout(vboxh)

        gb.setLayout(vbox)
        self.layout.addWidget(gb)

        self.config.add_handler('selected_data_regions', self.lw_variables, (self.map_list_fwd, self.map_list_rev))

        self.finalise()

    def onRegionRemove(self):
        self.lw_variables.removeItemAt(self.lw_variables.currentRow())

    def map_list_fwd(self, s):
        " Receive text name, return the indexes "
        return self.fwd_map_cache[s]

    def map_list_rev(self, x):
        " Receive the indexes, return the label"
        s = "\t".join([str(e) for e in x])
        self.fwd_map_cache[s] = x
        return s


class ConfigTablePanel(QTableWidget):

    def __init__(self, parent, *args, **kwargs):
        super(ConfigTablePanel, self).__init__(parent.w, *args, **kwargs)
        self.config = parent.config


class ExperimentConfigPanel(ConfigPanel):
    ''' Standard experiment definition config panel
    
        Offers a reusable standardised experimental control panel to define
        experimental classes. Will be extended to support timecourse analysis etc.
        + auto cross-configuration between multiple instance (config-passing)
    '''

    def __init__(self, parent, *args, **kwargs):
        super(ExperimentConfigPanel, self).__init__(parent, *args, **kwargs)

        self.v = parent
        self.config = parent.config
        gb = QGroupBox('Classes')
        grid = QGridLayout()

        self.cb_control = QComboBox()
        self.cb_control.addItems(['Control'])
        self.config.add_handler('experiment_control', self.cb_control)

        self.cb_test = QComboBox()
        self.cb_test.addItems(['Test'])
        self.config.add_handler('experiment_test', self.cb_test)

        grid.addWidget(QLabel('Control'), 0, 0)
        grid.addWidget(self.cb_control, 0, 1)

        grid.addWidget(QLabel('Test'), 1, 0)
        grid.addWidget(self.cb_test, 1, 1)
        gb.setLayout(grid)
        self.layout.addWidget(gb)

        self.finalise()


class WebPanel(QWebView):

    def __init__(self, parent, *args, **kwargs):
        super(WebPanel, self).__init__(parent, *args, **kwargs)


class LineNumberArea(QWidget):

    def __init__(self, editor):
        super(LineNumberArea, self).__init__(editor)
        self.codeEditor = editor

    def sizeHint(self):
        return QSize(self.codeEditor.lineNumberAreaWidth(), 0)

    def paintEvent(self, event):
        self.codeEditor.lineNumberAreaPaintEvent(event)

            
class DbApp(QMainWindow):
    def __init__(self, parent, **kwargs):
        super(DbApp, self).__init__(parent)

        self.id = str(id(self))

        self._previous_size = None

        self.setDockOptions(QMainWindow.ForceTabbedDocks)
        self.toolbars = {}
        #self.register_url_handler(self.default_url_handler)

        #self.setCentralWidget(self.views)

        #self.dbBrowser = HTMLView(self)
        #self.views.addView(self.dbBrowser, tr('Database'), unfocus_on_refresh=False)


class QCheckTreeWidget(QTreeWidget):

    itemCheckedChanged = pyqtSignal()

    def __init__(self, *args, **kwargs):
        super(QCheckTreeWidget, self).__init__(*args, **kwargs)
        self.itemChanged.connect(self.updateChecks)
        self._checked_item_cache = set()

    def updateCheckCache(self, item, checkstate):
        # Only count items without children (leaf nodes)
        if item.childCount() != 0:
            return

        if checkstate == Qt.Checked:
            self._checked_item_cache.add(item.text(0))
        else:
            self._checked_item_cache.discard(item.text(0))

    def updateChecks(self, item, column, recursing=False):
        self.blockSignals(True)
        diff = False
        if column != 0 and column != -1:
            return

        checkState = item.checkState(0)
        self.updateCheckCache(item, checkState)

        if item.childCount() != 0 and item.checkState(0) != Qt.PartiallyChecked and column != -1:
            for i in range(item.childCount()):
                if item.child(i).checkState != checkState:
                    item.child(i).setCheckState(0, checkState)
                    self.updateCheckCache(item.child(i), checkState)
                    self.updateChecks(item.child(i), column, recursing=True)

        elif item.childCount() == 0 or column == -1:
            if item.parent() is None:
                return

            for j in range(item.parent().childCount()):
                if j != item.parent().indexOfChild(item) and item.checkState(0) != item.parent().child(j).checkState(0):
                    diff = True

            if diff:
                item.parent().setCheckState(0, Qt.PartiallyChecked)
                self.updateCheckCache(item.parent(), Qt.PartiallyChecked)
            else:
                item.parent().setCheckState(0, checkState)
                self.updateCheckCache(item.parent(), checkState)

            if item.parent() is not None:
                self.updateChecks(item.parent(), -1, recursing=True)

        if not recursing:
            self.blockSignals(False)
            self.itemCheckedChanged.emit()

            
class QBioCycPathwayTreeWidget(QCheckTreeWidget):

    def __init__(self, pathways, *args, **kwargs):
        super(QBioCycPathwayTreeWidget, self).__init__(*args, **kwargs)
        from biocyc import biocyc

        top_level_items = []
        for p in pathways:
            o = biocyc.get(p)
            i = QTreeWidgetItem()
            i.setCheckState(0, Qt.Unchecked)
            i.setText(0, str(o))
            i.biocyc = o
            top_level_items.append(i)

        self.addTopLevelItems(top_level_items)
        self.setHeaderLabels(['Pathway'])

        current_queue = top_level_items
        items_added_this_loop = None
        while len(current_queue) > 0:

            items_added_this_loop = 0
            next_queue = []
            for i in current_queue[:]:
                o = i.biocyc
                p = o.instances + o.subclasses
                cl = []
                for pw in p:
                    c = QTreeWidgetItem()
                    c.setCheckState(0, Qt.Unchecked)
                    c.setText(0, str(pw))
                    c.biocyc = pw
                    cl.append(c)

                i.addChildren(cl)
                next_queue.extend(cl)
            current_queue = next_queue

        self.sortItems(0, Qt.AscendingOrder)
