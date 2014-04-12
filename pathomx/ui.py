#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
logging.debug('Loading ui.py')

# Import PyQt5 classes
from .qt import *

from collections import defaultdict, OrderedDict
import os
import copy
import re
import json
import importlib
import sys
import numpy as np
from . import utils
from . import data
from . import config
from . import threads
from . import config
from .data import DataSet
from .styles import styles, MATCH_EXACT, MATCH_CONTAINS, MATCH_START, MATCH_END, \
                    MATCH_REGEXP, MARKERS, LINESTYLES, FILLSTYLES, HATCHSTYLES, \
                    StyleDefinition, ClassMatchDefinition

from .views import HTMLView, StaticHTMLView, ViewManager, MplSpectraView, TableView
from .editor.editor import WorkspaceEditor
# Translation (@default context)
from .translate import tr

try:
    from urllib.request import urlopen
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse
    from urllib import urlopen

from numpy import arange, sin, pi
from matplotlib.backend_bases import NavigationToolbar2
from .backend_qt5agg import NavigationToolbar2QTAgg

import logging

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


class QColorButton(QPushButton):
    '''
    Custom Qt Widget to show a chosen color.
    
    Left-clicking the button shows the color-chooser, while
    right-clicking resets the color to None (no-color).    
    '''

    colorChanged = pyqtSignal()

    def __init__(self, *args, **kwargs):
        super(QColorButton, self).__init__(*args, **kwargs)

        self._color = None
        self.setMaximumWidth(32)
        self.pressed.connect(self.onColorPicker)

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
        if e.button() == Qt.RightButton:
            self.setColor(None)

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
        if v == None:
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


class MATLABPathDialog(GenericDialog):
    '''
    Dialog for MATLAB exectuable path setting.
    '''
    def __init__(self, parent, path='matlab', **kwargs):
        super(MATLABPathDialog, self).__init__(parent, **kwargs)
        self.setWindowTitle('Set MATLAB Path')

        self.path = QLineEdit()
        self.path.setText( path )
        self.layout.addWidget( self.path )
        self.dialogFinalise()

    def sizeHint(self):
        return QSize(600, 100)

class DialogAbout(QDialog):
    def __init__(self, parent, **kwargs):
        super(DialogAbout, self).__init__(parent, **kwargs)

        self.setWindowTitle('About Pathomx')
        self.help = QWebView(self)#, parent.onBrowserNav)
        template = parent.templateEngine.get_template('about.html')
        self.help.setHtml(template.render({
                    'htmlbase': os.path.join(utils.scriptdir, 'html'),
                    }), QUrl("~")
                    )
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

        countries = [
            ('AF', 'Afghanistan'),
            ('AL', 'Albania'),
            ('DZ', 'Algeria'),
            ('AS', 'American Samoa'),
            ('AD', 'Andorra'),
            ('AO', 'Angola'),
            ('AI', 'Anguilla'),
            ('AQ', 'Antarctica'),
            ('AG', 'Antigua And Barbuda'),
            ('AR', 'Argentina'),
            ('AM', 'Armenia'),
            ('AW', 'Aruba'),
            ('AU', 'Australia'),
            ('AT', 'Austria'),
            ('AZ', 'Azerbaijan'),
            ('BS', 'Bahamas'),
            ('BH', 'Bahrain'),
            ('BD', 'Bangladesh'),
            ('BB', 'Barbados'),
            ('BY', 'Belarus'),
            ('BE', 'Belgium'),
            ('BZ', 'Belize'),
            ('BJ', 'Benin'),
            ('BM', 'Bermuda'),
            ('BT', 'Bhutan'),
            ('BO', 'Bolivia'),
            ('BA', 'Bosnia And Herzegowina'),
            ('BW', 'Botswana'),
            ('BV', 'Bouvet Island'),
            ('BR', 'Brazil'),
            ('BN', 'Brunei Darussalam'),
            ('BG', 'Bulgaria'),
            ('BF', 'Burkina Faso'),
            ('BI', 'Burundi'),
            ('KH', 'Cambodia'),
            ('CM', 'Cameroon'),
            ('CA', 'Canada'),
            ('CV', 'Cape Verde'),
            ('KY', 'Cayman Islands'),
            ('CF', 'Central African Rep'),
            ('TD', 'Chad'),
            ('CL', 'Chile'),
            ('CN', 'China'),
            ('CX', 'Christmas Island'),
            ('CC', 'Cocos Islands'),
            ('CO', 'Colombia'),
            ('KM', 'Comoros'),
            ('CG', 'Congo'),
            ('CK', 'Cook Islands'),
            ('CR', 'Costa Rica'),
            ('CI', 'Cote D`ivoire'),
            ('HR', 'Croatia'),
            ('CU', 'Cuba'),
            ('CY', 'Cyprus'),
            ('CZ', 'Czech Republic'),
            ('DK', 'Denmark'),
            ('DJ', 'Djibouti'),
            ('DM', 'Dominica'),
            ('DO', 'Dominican Republic'),
            ('TP', 'East Timor'),
            ('EC', 'Ecuador'),
            ('EG', 'Egypt'),
            ('SV', 'El Salvador'),
            ('GQ', 'Equatorial Guinea'),
            ('ER', 'Eritrea'),
            ('EE', 'Estonia'),
            ('ET', 'Ethiopia'),
            ('FK', 'Falkland Islands (Malvinas)'),
            ('FO', 'Faroe Islands'),
            ('FJ', 'Fiji'),
            ('FI', 'Finland'),
            ('FR', 'France'),
            ('GF', 'French Guiana'),
            ('PF', 'French Polynesia'),
            ('TF', 'French S. Territories'),
            ('GA', 'Gabon'),
            ('GM', 'Gambia'),
            ('GE', 'Georgia'),
            ('DE', 'Germany'),
            ('GH', 'Ghana'),
            ('GI', 'Gibraltar'),
            ('GR', 'Greece'),
            ('GL', 'Greenland'),
            ('GD', 'Grenada'),
            ('GP', 'Guadeloupe'),
            ('GU', 'Guam'),
            ('GT', 'Guatemala'),
            ('GN', 'Guinea'),
            ('GW', 'Guinea-bissau'),
            ('GY', 'Guyana'),
            ('HT', 'Haiti'),
            ('HN', 'Honduras'),
            ('HK', 'Hong Kong'),
            ('HU', 'Hungary'),
            ('IS', 'Iceland'),
            ('IN', 'India'),
            ('ID', 'Indonesia'),
            ('IR', 'Iran'),
            ('IQ', 'Iraq'),
            ('IE', 'Ireland'),
            ('IL', 'Israel'),
            ('IT', 'Italy'),
            ('JM', 'Jamaica'),
            ('JP', 'Japan'),
            ('JO', 'Jordan'),
            ('KZ', 'Kazakhstan'),
            ('KE', 'Kenya'),
            ('KI', 'Kiribati'),
            ('KP', 'Korea (North)'),
            ('KR', 'Korea (South)'),
            ('KW', 'Kuwait'),
            ('KG', 'Kyrgyzstan'),
            ('LA', 'Laos'),
            ('LV', 'Latvia'),
            ('LB', 'Lebanon'),
            ('LS', 'Lesotho'),
            ('LR', 'Liberia'),
            ('LY', 'Libya'),
            ('LI', 'Liechtenstein'),
            ('LT', 'Lithuania'),
            ('LU', 'Luxembourg'),
            ('MO', 'Macau'),
            ('MK', 'Macedonia'),
            ('MG', 'Madagascar'),
            ('MW', 'Malawi'),
            ('MY', 'Malaysia'),
            ('MV', 'Maldives'),
            ('ML', 'Mali'),
            ('MT', 'Malta'),
            ('MH', 'Marshall Islands'),
            ('MQ', 'Martinique'),
            ('MR', 'Mauritania'),
            ('MU', 'Mauritius'),
            ('YT', 'Mayotte'),
            ('MX', 'Mexico'),
            ('FM', 'Micronesia'),
            ('MD', 'Moldova'),
            ('MC', 'Monaco'),
            ('MN', 'Mongolia'),
            ('MS', 'Montserrat'),
            ('MA', 'Morocco'),
            ('MZ', 'Mozambique'),
            ('MM', 'Myanmar'),
            ('NA', 'Namibia'),
            ('NR', 'Nauru'),
            ('NP', 'Nepal'),
            ('NL', 'Netherlands'),
            ('AN', 'Netherlands Antilles'),
            ('NC', 'New Caledonia'),
            ('NZ', 'New Zealand'),
            ('NI', 'Nicaragua'),
            ('NE', 'Niger'),
            ('NG', 'Nigeria'),
            ('NU', 'Niue'),
            ('NF', 'Norfolk Island'),
            ('MP', 'Northern Mariana Islands'),
            ('NO', 'Norway'),
            ('OM', 'Oman'),
            ('PK', 'Pakistan'),
            ('PW', 'Palau'),
            ('PA', 'Panama'),
            ('PG', 'Papua New Guinea'),
            ('PY', 'Paraguay'),
            ('PE', 'Peru'),
            ('PH', 'Philippines'),
            ('PN', 'Pitcairn'),
            ('PL', 'Poland'),
            ('PT', 'Portugal'),
            ('PR', 'Puerto Rico'),
            ('QA', 'Qatar'),
            ('RE', 'Reunion'),
            ('RO', 'Romania'),
            ('RU', 'Russian Federation'),
            ('RW', 'Rwanda'),
            ('KN', 'Saint Kitts And Nevis'),
            ('LC', 'Saint Lucia'),
            ('VC', 'St Vincent/Grenadines'),
            ('WS', 'Samoa'),
            ('SM', 'San Marino'),
            ('ST', 'Sao Tome'),
            ('SA', 'Saudi Arabia'),
            ('SN', 'Senegal'),
            ('SC', 'Seychelles'),
            ('SL', 'Sierra Leone'),
            ('SG', 'Singapore'),
            ('SK', 'Slovakia'),
            ('SI', 'Slovenia'),
            ('SB', 'Solomon Islands'),
            ('SO', 'Somalia'),
            ('ZA', 'South Africa'),
            ('ES', 'Spain'),
            ('LK', 'Sri Lanka'),
            ('SH', 'St. Helena'),
            ('PM', 'St.Pierre'),
            ('SD', 'Sudan'),
            ('SR', 'Suriname'),
            ('SZ', 'Swaziland'),
            ('SE', 'Sweden'),
            ('CH', 'Switzerland'),
            ('SY', 'Syrian Arab Republic'),
            ('TW', 'Taiwan'),
            ('TJ', 'Tajikistan'),
            ('TZ', 'Tanzania'),
            ('TH', 'Thailand'),
            ('TG', 'Togo'),
            ('TK', 'Tokelau'),
            ('TO', 'Tonga'),
            ('TT', 'Trinidad And Tobago'),
            ('TN', 'Tunisia'),
            ('TR', 'Turkey'),
            ('TM', 'Turkmenistan'),
            ('TV', 'Tuvalu'),
            ('UG', 'Uganda'),
            ('UA', 'Ukraine'),
            ('AE', 'United Arab Emirates'),
            ('UK', 'United Kingdom'),
            ('US', 'United States'),
            ('UY', 'Uruguay'),
            ('UZ', 'Uzbekistan'),
            ('VU', 'Vanuatu'),
            ('VA', 'Vatican City State'),
            ('VE', 'Venezuela'),
            ('VN', 'Viet Nam'),
            ('VG', 'Virgin Islands (British)'),
            ('VI', 'Virgin Islands (U.S.)'),
            ('EH', 'Western Sahara'),
            ('YE', 'Yemen'),
            ('YU', 'Yugoslavia'),
            ('ZR', 'Zaire'),
            ('ZM', 'Zambia'),
            ('ZW', 'Zimbabwe')
        ]

        self.country = QComboBox()
        self.country.addItems([v for k, v in countries])
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
        self.print_units.setCurrentText(self.default_print_units)

        w.addWidget(self.print_units, r, 2)
        r += 1

        self.resolution = QDoubleSpinBox()
        self.resolution.setRange(1, 1000000)
        self.resolution.setValue(300)
        self.resolution.setDecimals(2)

        self.resolution_units = QComboBox()
        self.resolution_units.addItems(list(self.resolution_u.keys()))
        self.resolution_units.setCurrentText(self.default_resolution_units)

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
            self.scaling.setCurrentText('Resample')
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

    LINESTYLES_dict = OrderedDict([('None', None)] + list( zip(LINESTYLES, LINESTYLES) ) )
    MARKERS_dict = OrderedDict([('None', None)] + list( zip(MARKERS, MARKERS) ) )
    FILLSTYLES_dict = OrderedDict([('None', None)] + list( zip(FILLSTYLES, FILLSTYLES) ) ) 
    HATCHSTYLES_dict = OrderedDict([('None', None)] + list( zip(HATCHSTYLES, HATCHSTYLES) ) )

    def __init__(self, parent, mdls=None, **kwargs):
        super(MatchStyleDialog, self).__init__(parent, **kwargs)

        self.setWindowTitle("Define class match and line-marker style")
        # '', 'RE', 'Marker', 'Fill', 'Line', 'Hatch', 'Color', 'Face', 'Edge'

        self.config = config.ConfigManager()
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

        self.m = parent

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
        item = QTreeWidgetItem()
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

                #self.m.onRefreshAllViews()
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

        #item.setSizeHint(0, QSize(50,30) )

        for c, s, v in [(3, '▬', ls.color), (7, '▩', ls.markerfacecolor), (8, '▩', ls.markeredgecolor)]:
            if v != None:
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
        self.setPage(QWebPageExtend(self.w))
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
        self.m = view.m

        self.setWindowTitle(tr("Select Data Source(s)"))

        # Build a list of dicts containing the widget
        # with target data in there
        self.lw_consumeri = list()
        for n, cd in enumerate(self.v.data.consumer_defs):

            self.lw_consumeri.append(QComboBox())
            cdw = self.lw_consumeri[n]  # Shorthand
            datasets = self.v.data.can_consume_which_of(self.m.datasets, [cd])

            cdw.addItem('No input')

            for nd, dataset in enumerate(datasets):

                e = set()
                for el in dataset.entities_t:
                    e |= set(el)  # Add entities to the set
                e = e - {'NoneType'}  # Remove if it's in there

                entities = ', '.join(e)
                dimensions = 'x'.join([str(s) for s in dataset.shape])

                cdw.addItem(QIcon(dataset.manager.v.plugin.workspace_icon), '%s %s %s (%s)' % (dataset.name, dataset.manager.v.name, entities, dimensions))

                # If this is the currently used data source for this interface, set it active
                if cd.target in self.v.data.i and dataset == self.v.data.i[cd.target]:
                    cdw.setCurrentIndex(nd + 1)  # nd+1 because of the None we've inserted at the front

            cdw.consumer_def = cd
            cdw.datasets = [None] + datasets

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
        self.m = view.m

        self.setWindowTitle("Data Output(s)")

        self.lw_sources = QTreeWidget()  # Use TreeWidget but flat; for multiple column view
        self.lw_sources.setColumnCount(5)
        self.lw_sources.setHeaderLabels(['', 'Source', 'Data', 'Entities', 'Size'])  # ,'#'])
        self.lw_sources.setUniformRowHeights(True)
        self.lw_sources.rootIsDecorated()
        self.lw_sources.hideColumn(0)

        datasets = self.m.datasets  # Get a list of dataset objects to test
        self.datasets = []

        for k, dataset in list(self.v.data.o.items()):

        #QListWidgetItem(dataset.name, self.lw_sources)
            tw = QTreeWidgetItem()

            tw.setText(0, str(len(self.datasets) - 1))  # Store index
            tw.setText(1, dataset.manager.v.name)
            if dataset.manager.v.plugin.workspace_icon:
                tw.setIcon(1, dataset.manager.v.plugin.workspace_icon)

            tw.setText(2, dataset.name)
            e = set()
            for el in dataset.entities_t:
                e |= set(el)  # Add entities to the set
            e = e - {'NoneType'}  # Remove if it's in there

            tw.setText(3, ', '.join(e))

            tw.setText(4, 'x'.join([str(s) for s in dataset.shape]))

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
class GenericApp(QMainWindow):
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

    nameChanged = pyqtSignal(str)

    def __init__(self, name=None, position=None, auto_focus=True, auto_consume_data=True, **kwargs):
        super(GenericApp, self).__init__()
        self.id = str(id(self))

        self._previous_size = None

        self.m = self.plugin.m
        self.m.apps.append(self)
        self.m.apps_dict[self.id] = self

        self._pause_analysis_flag = False
        self._latest_dock_widget = None
        self._latest_generator_result = None
        self._auto_consume_data = auto_consume_data

        self.logger = logging.getLogger(self.id)

        self.setDockOptions(QMainWindow.ForceTabbedDocks)

        if name == None:
            name = getattr(self, 'name', self.m.plugin_names[id(self.plugin)])
        self.set_name(name)

        logging.debug('Creating tool: %s' % name)

        logging.debug('Setting up data manager...')
        self.data = data.DataManager(self.m, self)

        logging.debug('Setting up view manager...')
        self.views = ViewManager(self)

        logging.debug('Setting up file watcher manager...')
        self.file_watcher = QFileSystemWatcher()
        self.file_watcher.fileChanged.connect(self.onFileChanged)

        if self.plugin.help_tab_html_filename:
            logging.debug('Loading help...')
            template = self.plugin.templateEngine.get_template(self.plugin.help_tab_html_filename)
            html = template.render({
                        'htmlbase': os.path.join(utils.scriptdir, 'html'),
                        'pluginbase': self.plugin.path,
                        'view': self,
                        })

            self.views.addView(StaticHTMLView(self, html), '?', unfocus_on_refresh=True)

        self.toolbars = {}

        logging.debug('Register internal url handler...')
        self.register_url_handler(self.default_url_handler)

        self.setCentralWidget(self.views)

        logging.debug('Connect event handlers...')
        self.status.connect(self.setWorkspaceStatus)
        self.progress.connect(self.updateProgress)
        self.complete.connect(self.views.onRefreshAll)

        logging.debug('Setup config manager...')
        self.config = config.ConfigManager()  # Configuration manager object; handle all get/setting, defaults etc.

        logging.debug('Create editor icon...')
        self.editorItem = self.m.editor.addApp(self, position=position)
        logging.debug('Create workspace list entry...')
        self.workspace_item = self.m.addWorkspaceItem(self, self.plugin.default_workspace_category, self.name, icon=self.plugin.workspace_icon)  # , icon = None)

        logging.debug('Add default toolbar...')
        self.addSelfToolBar()  # Everything has one

        logging.debug('Completed default tool (%s) setup.' % name)

    def finalise(self):

        self.data.source_updated.connect(self.autogenerate)  # Auto-regenerate if the source data is modified
        if self._auto_consume_data:
            self.data.consume_any_of(self.m.datasets[::-1])  # Try consume any dataset; work backwards
        self.config.updated.connect(self.autoconfig)  # Auto-regenerate if the configuration changes

    def register_url_handler(self, url_handler):
        self.m.register_url_handler(self.id, url_handler)

    def render(self, metadata):
        return

    def delete(self):
        # Tear down the config and data objects
        self.data.reset()
        self.config.reset()
        # Close the window obj
        self.m.removeWorkspaceItem(self)
        self.m.editor.removeApp(self)
        self.m.apps.remove(self)
        # Trigger notification for state change
        self.m.workspace_updated.emit()
        self.close()

    def autoconfig(self, signal):
        if signal == config.RECALCULATE_ALL or self._latest_generator_result == None:
            self.autogenerate()

        elif signal == config.RECALCULATE_VIEW:
            self.autoprerender(self._latest_generator_result)

    def autogenerate(self, *args, **kwargs):
        if self._pause_analysis_flag:
            self.setWorkspaceStatus('paused')
            return False

        self.views.autoSelect()  # Unfocus the help file if we've done something here
        self.thread_generate()

    def thread_generate(self):
        # Automatically trigger generator using inputs
        kwargs_dict = {}
        for i in list(self.data.i.keys()):
            kwargs_dict[i] = self.data.get(i)  # Will be 'None' if not available

        self.progress.emit(0.)
        self.worker = threads.Worker(self.generate, **kwargs_dict)
        self.wait_for_lock()
        self.start_worker_thread(self.worker, callback=self._generate_worker_result_callback)

    # Callback function for threaded generators; see _worker_result_callback and start_worker_thread
    def generated(self, **kwargs):
        # Automated pass on generated data if matching output port names
        for o in list(self.data.o.keys()):
            if o in kwargs:
                self.data.put(o, kwargs[o])

    def prerender(self, output=None, **kwargs):
        return {'View': dict(list({'dso': output}.items()) + list(kwargs.items()))}

    def _generate_worker_result_callback(self, kwargs_dict):
        self.release_lock()
        self.__latest_generator_result = kwargs_dict
        self.generated(**kwargs_dict)
        self.progress.emit(1.)
        self.autoprerender(kwargs_dict)

    def autoprerender(self, kwargs_dict):
        self.status.emit('render')
        self.prerender_worker = threads.Worker(self.prerender, **kwargs_dict)
        self.start_worker_thread(self.prerender_worker, callback=self._prerender_worker_result_callback)

    def _prerender_worker_result_callback(self, kwargs):
        self.views.data = kwargs
        self.views.source_data_updated.emit()
        #self.views.redraw()
        self.progress.emit(1.)
        self.status.emit('done')
        self.views.updated.emit()

    def _worker_error_callback(self, error=None):
        self.release_lock()
        self._latest_exception = error[1]
        self.progress.emit(1.)
        self.status.emit('error')
        self.logger.error(error[1])

    def _worker_status_callback(self, s):
        self.setWorkspaceStatus(s)

    def _thread_finished_callback(self):
        self.thread = None

    def start_worker_thread(self, worker, callback=None):
        if callback == None:
            callback = self._generate_worker_result_callback

        worker.signals.result.connect(callback)
        worker.signals.error.connect(self._worker_error_callback)

        self.status.emit('active')
        self.m.threadpool.start(worker)

    def store_views_data(self, kwargs_dict):
        self.views.source_data = kwargs_dict

    def set_name(self, name):
        self.name = name
        self.setWindowTitle(name)
        self.nameChanged.emit(name)

        try:
            self.workspace_item.setText(0, name)
        except:
            pass

    def updateProgress(self, progress):
        self.m.updateProgress(self.workspace_item, progress)

    def setWorkspaceStatus(self, status):
        self.m.setWorkspaceStatus(self.workspace_item, status)

    def clearWorkspaceStatus(self):
        self.m.clearWorkspaceStatus(self.workspace_item)

    def onDelete(self):
        self.delete()

    def addConfigPanel(self, Panel, name):
        dw = QDockWidget(name)
        dw.setWidget(Panel(self))
        dw.setMinimumWidth(300)
        dw.setMaximumWidth(300)

        self.addDockWidget(Qt.LeftDockWidgetArea, dw)
        if self._latest_dock_widget:
            self.tabifyDockWidget(dw, self._latest_dock_widget)

        self._latest_dock_widget = dw
        dw.raise_()

    def addSelfToolBar(self):
        t = self.addToolBar('App')
        t.setIconSize(QSize(16, 16))

        delete_selfAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'cross.png')), tr('Delete this app…'), self.m)
        delete_selfAction.setStatusTip('Delete this app')
        delete_selfAction.triggered.connect(self.onDelete)
        t.addAction(delete_selfAction)
        #popout_selfAction = QAction( QIcon( os.path.join(  utils.scriptdir, 'icons', 'applications-blue.png' ) ), tr('Move to new window'), self.m)
        #popout_selfAction.setStatusTip('Open this app in a separate window')
        #popout_selfAction.setCheckable(True)
        #popout_selfAction.setChecked(False)
        #popout_selfAction.toggled.connect(self.onPopOutToggle)
        #t.addAction(popout_selfAction)

        self.toolbars['self'] = t

    def addDataToolBar(self, default_pause_analysis=False):
        t = self.addToolBar('Data')
        t.setIconSize(QSize(16, 16))

        select_dataAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'data-source.png')), tr('Select a data source…'), self.m)
        select_dataAction.setStatusTip('Select a compatible data source')
        select_dataAction.triggered.connect(self.onSelectDataSource)
        t.addAction(select_dataAction)

        select_dataAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'play.png')), tr('Calculate'), self.m)
        select_dataAction.setStatusTip('Recalculate')
        select_dataAction.triggered.connect(self.onRecalculate)
        t.addAction(select_dataAction)

        pause_analysisAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'control-pause.png')), tr('Pause automatic analysis'), self.m)
        pause_analysisAction.setStatusTip('Do not automatically refresh analysis when source data updates')
        pause_analysisAction.setCheckable(True)
        pause_analysisAction.setChecked(default_pause_analysis)
        pause_analysisAction.toggled.connect(self.onAutoAnalysisToggle)
        t.addAction(pause_analysisAction)
        self._pause_analysis_flag = default_pause_analysis

        select_dataAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'data-output.png')), tr('View resulting data…'), self.m)
        select_dataAction.setStatusTip('View resulting data output from this plugin')
        select_dataAction.triggered.connect(self.onViewDataOutput)
        t.addAction(select_dataAction)

        self.toolbars['image'] = t

    def onSelectDataSource(self):
        # Basic add data source dialog. Extend later for multiple data sources etc.
        """ Open the mining setup dialog to define conditions, ranges, class-comparisons, etc. """
        dialog = DialogDataSource(parent=self, view=self)
        ok = dialog.exec_()
        if ok:
            for cb in dialog.lw_consumeri:  # Get list of comboboxes
                i = cb.currentIndex()  # Get selected item
                consumer_def = cb.consumer_def

                if i > 0:  # Something in the list (-1) and not 'No data'
                    dso = cb.datasets[i]
                    self.data.consume_with(dso, consumer_def)

                else:  # Stop consuming through this interface
                    self.data.unget(consumer_def.target)
            # Trigger notification for data source change; re-render inheritance map
            #self.m.onDataInheritanceChanged()

            #self.generate() automatic

    def onViewDataOutput(self):
        # Basic add data source dialog. Extend later for multiple data sources etc.
        """ Open the mining setup dialog to define conditions, ranges, class-comparisons, etc. """
        dialog = DialogDataOutput(parent=self, view=self)
        dialog.exec_()

    def closeEvent(self, e):
        self._previous_size = self.size()
        super(GenericApp, self).closeEvent(e)

    def getCreatedToolbar(self, name, id):
        if id not in self.toolbars:
            self.toolbars[id] = self.addToolBar(name)
            self.toolbars[id].setIconSize(QSize(16, 16))

        return self.toolbars[id]

    def addFigureToolBar(self):
        t = self.getCreatedToolbar(tr('Figures'), 'figure')

        export_imageAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'image-export.png')), tr('Export current figure as image…'), self.m)
        export_imageAction.setStatusTip(tr('Export figure to image'))
        export_imageAction.triggered.connect(self.onSaveImage)
        t.addAction(export_imageAction)
        #printAction = QAction(QIcon.fromTheme("document-print", QIcon( os.path.join( utils.scriptdir, 'icons', 'printer.png') )), tr('&Print…'), self)
        #printAction.setShortcut('Ctrl+P')
        #printAction.setStatusTip( tr('Print current figure') )
        #printAction.triggered.connect(self.onPrint)
        #t.addAction(printAction)

        self.addMplToolBarExtensions()

    def addExternalDataToolbar(self):
        t = self.getCreatedToolbar(tr('External Data'), 'external-data')

        watch_fileAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'eye--exclamation.png')), tr('Watch data file(s) for changes…'), self.m)
        watch_fileAction.setStatusTip(tr('Watch external data file(s) for changes and automatically refresh'))
        watch_fileAction.triggered.connect(self.onWatchSourceDataToggle)
        watch_fileAction.setCheckable(True)
        watch_fileAction.setChecked(False)
        t.addAction(watch_fileAction)
        self._autoload_source_files_on_change = False

    def addMplToolBarExtensions(self):
        if 'figure' in self.toolbars:  # Never more than one
            t = self.getCreatedToolbar(tr('Figure'), 'figure')

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

            self.views.currentChanged.connect(self.onMplToolBarCanvasChanged)
            #self.addToolBar( t )

    def dispatchMplEvent(self, e, callback):
        selected_view = self.views.widget(self.views.currentIndex())
        if selected_view.is_mpl_toolbar_enabled:
            getattr(selected_view.navigation, callback)(e)

    def onMplToolBarCanvasChanged(self, w):
        selected_view = self.views.widget(w)
        if selected_view.is_mpl_toolbar_enabled:
            # Reset buttons to current view state for the selected tabs' Canvas
            for c, m in [('zoom', 'ZOOM'), ('pan', 'PAN')]:
                self.toolbars['figure']._checkable_actions[c].setChecked(selected_view.navigation._active == m)

            for act in self.toolbars['figure']._mpl_specific_actions:
                act.setEnabled(True)
        else:
            for act in self.toolbars['figure']._mpl_specific_actions:
                act.setEnabled(False)

    def onWatchSourceDataToggle(self, checked):
        self._autoload_source_files_on_change = checked

    def onAutoAnalysisToggle(self, checked):
        self._pause_analysis_flag = checked

    def onFileChanged(self, file):
        if self._autoload_source_files_on_change:
            self.load_datafile(file)

    def onSaveImage(self):
        # Get currently selected webview
        cw = self.views.currentWidget()

        # Load dialog for image export dimensions and resolution
        # TODO: dialog!
        sizedialog = ExportImageDialog(self, size=cw.size(), show_rerender_options=cw._offers_rerender_on_save)
        ok = sizedialog.exec_()
        if ok:
            cw.saveAsImage(sizedialog)

    def onRecalculate(self):
        self.thread_generate()

    def onBrowserNav(self, url):
        self.m.onBrowserNav(url)

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
        
    def wait_for_lock(self):
        return True
        
    def release_lock(self):
        return True
    

# Data view prototypes

class DataApp(GenericApp):
    def __init__(self, **kwargs):
        super(DataApp, self).__init__(**kwargs)

        self.table = TableView()
        self.views.addView(self.table, tr('Table'), unfocus_on_refresh=True)

# Import Data viewer

class ImportDataApp(DataApp):

    import_type = tr('Data')
    import_filename_filter = tr("All Files") + " (*.*);;"
    import_description = tr("Open experimental data from file")

    def __init__(self, filename=None, **kwargs):
        super(ImportDataApp, self).__init__(**kwargs)

        self.data.add_output('output')  # Add output slot
        self.table.setModel(self.data.o['output'].as_table)
        self.views.addTab(MplSpectraView(self), 'View')

        self.addImportDataToolbar()
        self.addFigureToolBar()

        if filename:
            self.thread_load_datafile(filename)

    # Data file import handlers (#FIXME probably shouldn't be here)
    def thread_load_datafile(self, filename, type=None):
        if type:
            self.worker = threads.Worker(self.load_datafile_by_type, filename, type)
        else:
            self.worker = threads.Worker(self.load_datafile, filename)
        self.start_worker_thread(self.worker)

    def prerender(self, output=None):
        return {'View': {'dso': output}}

    def onImportData(self):
        """ Open a data file"""
        filename, _ = QFileDialog.getOpenFileName(self, self.import_description, '', self.import_filename_filter)
        if filename:
            self.thread_load_datafile(filename)

            self.file_watcher = QFileSystemWatcher()
            self.file_watcher.fileChanged.connect(self.onFileChanged)
            self.file_watcher.addPath(filename)

            self.set_name(os.path.basename(filename))

        return False

    def onFileChanged(self, file):
        self.load_datafile(file)
        pass

    def addImportDataToolbar(self):
        t = self.getCreatedToolbar(tr('External Data'), 'external-data')

        import_dataAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'disk--arrow.png')), 'Import %s file…' % self.import_type, self.m)
        import_dataAction.setStatusTip(self.import_description)
        import_dataAction.triggered.connect(self.onImportData)
        t.addAction(import_dataAction)

        self.addExternalDataToolbar()


class CodeEditorTool(GenericApp):

    def addCodeEditorToolbar(self):
        t = self.getCreatedToolbar(tr('Code Editor'), 'code-editor')

        codeedit_applyAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'script-apply.png')), 'Apply changes', self.m)
        codeedit_applyAction.triggered.connect(self.onCodeEditApply)
        t.addAction(codeedit_applyAction)

    def onCodeEditApply(self):
        self.editor.sourceChangesApplied.emit(self.editor.document().toPlainText())


class ExportDataApp(GenericApp):
    def __init__(self, filename=None, **kwargs):
        super(ExportDataApp, self).__init__(**kwargs)

        self.data.add_input('input')  # Add output slot

        self.addExportDataToolbar()
        #if filename:
        #    self.thread_load_datafile( filename )

    def addExportDataToolbar(self):
        t = self.getCreatedToolbar(tr('Export Data'), 'export-data')

        export_dataAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'disk--pencil.png')), 'Export %s file…' % self.export_type, self.m)
        export_dataAction.setStatusTip(self.export_description)
        export_dataAction.triggered.connect(self.onExportData)
        t.addAction(export_dataAction)

    def thread_generate(self, *args, **kwargs):
        return False

    # Data file import handlers (#FIXME probably shouldn't be here)
    def thread_save_datafile(self, filename, dso, type=None):
        if type:
            self.worker = threads.Worker(self.save_datafile_by_type, filename, dso, type)
        else:
            self.worker = threads.Worker(self.save_datafile, filename, dso)
        self.start_worker_thread(self.worker)

    def onExportData(self):
        """ Open a data file"""
        filename, _ = QFileDialog.getSaveFileName(self, self.export_description, '', self.export_filename_filter)
        if filename:
            self.thread_save_datafile(filename, self.data.get('input'))
            self.set_name(os.path.basename(filename))

        return False


# Analysis/Visualisation view prototypes
# Class for analysis views, using graph-based visualisations of defined datasets
# associated layout and/or analysis
class AnalysisApp(GenericApp):
    def __init__(self, **kwargs):
        super(AnalysisApp, self).__init__(**kwargs)

    # Build change table
    def build_change_table_of_classes(self, dso, objs, classes):
        print(dso.shape)

        # Reduce dimensionality; combine all class/entity objects via np.mean()
        dso = dso.as_summary()

        #FIXME: Need to allow entities to be passed in and use entity / labels
        #entities = []
        #for o in objs:
        #    entities.extend( [ self.m.db.index[id] for id in o if id in self.m.db.index] )


        # Filter for the things we're displaying
        dso = dso.as_filtered(labels=objs)

        #data = data.as_class_grouped(classes=classes)
        data = np.zeros((len(classes), len(objs)))

        for x, l in enumerate(objs):  # [u'PYRUVATE', u'PHOSPHO-ENOL-PYRUVATE']
            for y, c in enumerate(classes):
                #e = self.m.db.index[o] # Get entity for lookup
                data[y, x] = dso.data[dso.classes[0].index(c), dso.labels[1].index(l)]

        return data.T

    def build_change_table_of_entitytypes(self, dso, objs, entityt):

    # Reduce dimensionality; combine all class/entity objects via np.mean()
        dso = dso.as_summary()
        entities = []
        for o in objs:
            entities.extend([self.m.db.index[id] for id in o if id in self.m.db.index])

        # Filter for the things we're displaying
        dso = dso.as_filtered(entities=entities)
        #data = data.as_class_grouped(classes=classes)
        data = np.zeros((len(objs), len(entityt)))

        for y, obj in enumerate(objs):  # [u'PYRUVATE', u'PHOSPHO-ENOL-PYRUVATE']
            for x, o in enumerate(obj):
                try:
                    e = self.m.db.index[o]  # Get entity for lookup
                    data[y, x] = dso.data[0, dso.entities[1].index(e)]
                except:  # Can't find it
                    pass

        return data

    def build_log2_change_control_vs_multi(self, objs, classes):
        data = np.zeros((len(objs), len(classes)))
        for x, xl in enumerate(classes):
            for y, yl in enumerate(objs):
                data[y, x] = self.parent.data.get_log2(yl, xl) - self.parent.data.get_log2(yl, self.parent.experiment['control'])

        return data

    def build_raw_change_control_vs_multi(self, objs, classes):
        data = np.zeros((len(objs), len(classes)))
        for x, xl in enumerate(classes):
            for y, yl in enumerate(objs):
                data[y, x] = np.mean(self.parent.data.quantities[yl][xl]) - np.mean(self.parent.data.quantities[yl][self.parent.experiment['control']])

        return data

    def build_heatmap_dso(self, labelsX, labelsY, data, remove_empty_rows=False, remove_incomplete_rows=False, sort_data=False):

        dso = DataSet(size=(len(labelsY), len(labelsX)))
        dso.data = data
        dso.labels[0] = labelsY
        dso.labels[1] = labelsX
        return dso

    #self.build_heatmap_buckets( labelsX, labelsY, self.build_log2_change_table_of_classtypes( self.phosphate, labelsX ), remove_empty_rows=True, sort_data=True  )
    def build_heatmap_buckets(self, labelsX, labelsY, data, remove_empty_rows=False, remove_incomplete_rows=False, sort_data=False):
        buckets = []

        if remove_empty_rows:
            mask = ~np.isnan(data).all(axis=1)
            data = data[mask]
            labelsY = [l for l, m in zip(labelsY, mask) if m]

        elif remove_incomplete_rows:
            mask = ~np.isnan(data).any(axis=1)
            data = data[mask]
            labelsY = [l for l, m in zip(labelsY, mask) if m]


        # Broken, fix if needed
        #if remove_empty_cols:
        #    mask = ~np.isnan(data).all(axis=0)
        #    data = data.T[mask.T]
        #    labelsX = [l for l,m in zip(labelsX,mask) if m]

        if sort_data:
            # Preferable would be to sort by the total for each row
            # can then use that to sort the labels list also
            totals = np.ma.masked_invalid(data).sum(1).data  # Get sum for rows, ignoring NaNs
            si = totals.argsort()[::-1]
            data = data[si]  # Sort
            labelsY = list(np.array(labelsY)[si])  # Sort Ylabels via numpy array.

        for x, xL in enumerate(labelsX):
            for y, yL in enumerate(labelsY):

                if data[y][x] != np.nan:
                    buckets.append([xL, yL, data[y][x]])

        return buckets

    def build_matrix(self, targets, target_links):

        data = []
        for mx in targets:
            row = []
            for my in targets:
                n = len(list(target_links[my] & target_links[mx]))
                row.append(n)

            data.append(row)
        return data, targets

    def get_fig_tempfile(self, fig):
        tf = QTemporaryFile()
        tf.open()
        fig.savefig(tf.fileName(), format='png', bbox_inches='tight')
        return tf

    def addExperimentToolBar(self):

        t = self.addToolBar(tr('Experiment'))
        t.setIconSize(QSize(16, 16))

        # DATA MENU
        define_experimentAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'layout-design.png')), tr('Define experiment…'), self)
        define_experimentAction.setShortcut('Ctrl+Q')
        define_experimentAction.setStatusTip(tr('Define experiment control, test and timecourse settings'))
        define_experimentAction.triggered.connect(self.onDefineExperiment)

        t.addAction(define_experimentAction)

        t.cb_control = QComboBox()
        t.cb_control.addItems(['Control'])
        self.config.add_handler('experiment_control', t.cb_control)

        t.cb_test = QComboBox()
        t.cb_test.addItems(['Test'])
        self.config.add_handler('experiment_test', t.cb_test)

        t.addWidget(t.cb_control)
        t.addWidget(t.cb_test)

        self.toolbars['experiment'] = t

        self.data.source_updated.connect(self.repopulate_experiment_classes)  # Update the classes if data source changes        

    def repopulate_experiment_classes(self):
        _control = self.config.get('experiment_control')
        _test = self.config.get('experiment_test')

        classes = self.data.i['input'].classes_l[0]

        if _control not in classes or _test not in classes:
            # Block signals so no trigger of update
            self.toolbars['experiment'].cb_control.blockSignals(True)
            self.toolbars['experiment'].cb_test.blockSignals(True)
            # Empty the toolbar controls
            self.toolbars['experiment'].cb_control.clear()
            self.toolbars['experiment'].cb_test.clear()
            # Data source change; update the experimental control with the data input source
            self.toolbars['experiment'].cb_control.addItems([i for i in self.data.i['input'].classes_l[0]])
            self.toolbars['experiment'].cb_test.addItem("*")
            self.toolbars['experiment'].cb_test.addItems([i for i in self.data.i['input'].classes_l[0]])
            # Reset to previous values (-if possible)
            self.toolbars['experiment'].cb_control.setCurrentText(_control)
            self.toolbars['experiment'].cb_test.setCurrentText(_test)
            # Unblock
            self.toolbars['experiment'].cb_control.blockSignals(False)
            self.toolbars['experiment'].cb_test.blockSignals(False)
            # If previously nothing set; now set it to something
            _control = _control if _control in self.data.i['input'].classes_l[0] else self.data.i['input'].classes_l[0][0]
            _test = _test if _test in self.data.i['input'].classes_l[0] else '*'

            self.config.set_many({
                'experiment_control': _control,
                'experiment_test': _test,
            })

    def onDataChanged(self):
        self.repopulate_experiment_classes()

    def onDefineExperiment(self):
        pass

    def onModifyExperiment(self):
        """ Update the experimental settings for analysis then regenerate """
        self._experiment_control = self.toolbars['experiment'].cb_control.currentText()
        self._experiment_test = self.toolbars['experiment'].cb_test.currentText()
        self.generate()


class remoteQueryDialog(GenericDialog):

    def parse(self, data):
        # Parse incoming data and return a dict mapping the displayed values to the internal value
        l = data.split('\n')
        return dict(list(zip(l, l)))

    def do_query(self):
        f = urllib.request.urlopen(self.query_target % urllib.parse.quote(self.textbox.text()))
        query_result = f.read()
        f.close()

        self.data = self.parse(query_result)
        self.select.clear()
        self.select.addItems(list(self.data.keys()))

    def __init__(self, parent, query_target=None, **kwargs):
        super(remoteQueryDialog, self).__init__(parent, **kwargs)

        self.textbox = QLineEdit()
        querybutton = QPushButton('↺')
        querybutton.clicked.connect(self.do_query)

        queryboxh = QHBoxLayout()
        queryboxh.addWidget(self.textbox)
        queryboxh.addWidget(querybutton)

        self.data = None  # Deprecated

        self.select = QListWidget()
        self.query_target = query_target

        self.layout.addLayout(queryboxh)
        self.layout.addWidget(self.select)

        self.dialogFinalise()


class ConfigPanel(QWidget):

    def __init__(self, parent, *args, **kwargs):
        super(ConfigPanel, self).__init__(parent, *args, **kwargs)

        self.v = parent
        self.m = parent.m
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


class CodeEditor(QPlainTextEdit):

    sourceChangesApplied = pyqtSignal(str)

    def __init__(self, parent=None):
        super(CodeEditor, self).__init__(parent)

        font = QFont("Courier", 12)
        font.setStyleHint(QFont.TypeWriter)

        self.setFont(font)

        tabStop = 4  # 4 characters
        self.setTabStopWidth(tabStop * QFontMetrics(font).width('_'))

        self.lineNumberArea = LineNumberArea(self)

        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)
        #self.cursorPositionChanged.connect( self.highlightCurrentLine )

        self.updateLineNumberAreaWidth(0)
        #self.highlightCurrentLine()

    def lineNumberAreaWidth(self):

        digits = len(str(max(1, self.blockCount())))
        space = QApplication.fontMetrics().width('_') * (digits + 2)
        return space

    def updateLineNumberAreaWidth(self, newBlockCount):
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)
        self.lineNumberArea.update()

    def updateLineNumberArea(self, rect, dy):
        if (dy):
            self.lineNumberArea.scroll(0, dy)
        else:
            self.lineNumberArea.update(0, rect.y(), self.lineNumberArea.width(), rect.height())

        if (rect.contains(self.viewport().rect())):
            self.updateLineNumberAreaWidth(0)

    def resizeEvent(self, e):
        super(CodeEditor, self).resizeEvent(e)
        cr = self.contentsRect()
        self.lineNumberArea.setGeometry(QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height()))

    def highlightCurrentLine(self):
        selection = QTextEdit.ExtraSelection()

        selection.format = QTextCharFormat()
        selection.format.setBackground(QColor(Qt.yellow))
        selection.format.setForeground(QColor(Qt.red))
        selection.format.setProperty(QTextFormat.FullWidthSelection, True)

        selection.cursor = QTextCursor()
        selection.cursor.clearSelection()

        self.setExtraSelections([selection])

    def lineNumberAreaPaintEvent(self, event):
        painter = QPainter(self.lineNumberArea)
        painter.fillRect(event.rect(), Qt.lightGray)

        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = " %s " % str(blockNumber + 1)
                painter.setPen(Qt.black)
                painter.drawText(0, top, self.lineNumberArea.width(), QApplication.fontMetrics().height(),
                                 Qt.AlignRight, number)

            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            blockNumber += 1

            
class DbApp(QMainWindow):
    def __init__(self, parent, **kwargs):
        super(DbApp, self).__init__(parent)

        self.id = str(id(self))

        self._previous_size = None
        self.m = parent
        self.views = ViewManager(self)

        self.setDockOptions(QMainWindow.ForceTabbedDocks)
        self.toolbars = {}
        #self.register_url_handler(self.default_url_handler)

        self.setCentralWidget(self.views)

        self.dbBrowser = HTMLView(self)
        self.views.addView(self.dbBrowser, tr('Database'), unfocus_on_refresh=False)
