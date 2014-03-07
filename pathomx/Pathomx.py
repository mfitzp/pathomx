# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import sys
import re
import math
import codecs
import locale
import json
import importlib
import functools


if sys.version_info < (3, 0): # Python 2 only
    UTF8Writer = codecs.getwriter('utf8')
    sys.stdout = UTF8Writer(sys.stdout)
    reload(sys).setdefaultencoding('utf8')

from . import qt5
import textwrap

try:
    from urllib.request import urlopen
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse
    from urllib import urlopen

from optparse import Values
from collections import defaultdict

import numpy as np

from yapsy.PluginManager import PluginManager, PluginManagerSingleton

# wheezy templating engine
from wheezy.template.engine import Engine
from wheezy.template.ext.core import CoreExtension
from wheezy.template.ext.code import CodeExtension
from wheezy.template.loader import FileLoader

try:
    import xml.etree.cElementTree as et
except ImportError:
    import xml.etree.ElementTree as et

import matplotlib as mpl
from . import db
from . import data
from . import utils
from . import ui
from . import threads
from . import views
from . import custom_exceptions
from . import plugins  # plugin helper/manager
from .editor.editor import WorkspaceEditor

# Translation (@default context)
from .translate import tr

from distutils.version import StrictVersion

import logging
logging.basicConfig(level=logging.DEBUG)

VERSION_STRING = '2.2.0'

class Logger(logging.Handler):
    def __init__(self, widget, out=None, color=None):
        super(Logger, self).__init__()
        
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
        item = qt5.QListWidgetItem( msg )
        bg = {
            logging.CRITICAL:   qt5.QColor(164,27,27),
            logging.ERROR:      qt5.QColor(239,122,122),
            logging.WARNING:    qt5.QColor(252,238,126),
            logging.INFO:       None,
            logging.DEBUG:      qt5.QColor(186,196,207),
            logging.NOTSET:     None,
        }[record.levelno]
        if bg:
            item.setBackground( bg )
            
        self.widget.addItem( item )

    def write(self, m):
        pass

        #if self.color:
        #    tc = self.edit.textColor()
        #    self.edit.setTextColor(self.color)

        #self.edit.moveCursor(qt5.QTextCursor.End)
        #self.edit.insertPlainText( m )

        #if self.color:
        #    self.edit.setTextColor(tc)
        #

        #if self.out:
        #    self.out.write(m)
            


class DialogAbout(qt5.QDialog):
    def __init__(self, parent, **kwargs):
        super(DialogAbout, self).__init__(parent, **kwargs)

        self.setWindowTitle('About Pathomx')

        self.help = ui.QWebViewExtend(self, parent.onBrowserNav)
        template = parent.templateEngine.get_template('about.html')
        self.help.setHtml(template.render({
                    'htmlbase': os.path.join(utils.scriptdir, 'html'),
                    }), qt5.QUrl("~")
                    )

        self.layout = qt5.QVBoxLayout()
        self.layout.addWidget(self.help)

        # Setup default button configurations etc.
        self.buttonBox = qt5.QDialogButtonBox(qt5.QDialogButtonBox.Close)
        self.buttonBox.rejected.connect(self.close)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)

    def sizeHint(self):
        return qt5.QSize(600, 600)


class DialogRegister(qt5.QDialog):
    def __init__(self, parent, **kwargs):
        super(DialogRegister, self).__init__(parent, **kwargs)

        self.setWindowTitle('Register Pathomx')

        self.layout = qt5.QVBoxLayout()
        self.layout.addWidget(qt5.QLabel('Please register Pathomx by entering your details below.\n\nThis is completely optional but helps it helps us find out\nhow Pathomx is being used.'))

        self.layout.addSpacerItem(qt5.QSpacerItem(0, 20))

        bx = qt5.QGridLayout()

        self.name = qt5.QLineEdit()
        bx.addWidget(qt5.QLabel('Name'), 0, 0)
        bx.addWidget(self.name, 0, 1)

        self.institution = qt5.QLineEdit()
        bx.addWidget(qt5.QLabel('Institution/Organisation'), 1, 0)
        bx.addWidget(self.institution, 1, 1)

        self.type = qt5.QComboBox()
        self.type.addItems(['Academic', 'Governmental', 'Commercial', 'Non-profit', 'Personal', 'Other'])
        bx.addWidget(qt5.QLabel('Type of organisation'), 2, 0)
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
            ('qt5.QA', 'qt5.Qatar'),
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

        self.country = qt5.QComboBox()
        self.country.addItems([v for k, v in countries])
        bx.addWidget(qt5.QLabel('Country'), 3, 0)
        bx.addWidget(self.country, 3, 1)

        self.research = qt5.QLineEdit()
        bx.addWidget(qt5.QLabel('Research interest'), 4, 0)
        bx.addWidget(self.research, 4, 1)

        self.email = qt5.QLineEdit()
        bx.addWidget(qt5.QLabel('Email address'), 5, 0)
        bx.addWidget(self.email, 5, 1)

        bx.addItem(qt5.QSpacerItem(0, 20), 6, 0)

        self.releases = qt5.QComboBox()
        self.releases.addItems(['Check automatically (weekly)', 'Subscribe to mailing list', 'Don\'t check'])
        bx.addWidget(qt5.QLabel('Software updates'), 7, 0)
        bx.addWidget(self.releases, 7, 1)

        self.layout.addLayout(bx)

        # Setup default button configurations etc.
        self.buttonBox = qt5.QDialogButtonBox(qt5.QDialogButtonBox.Cancel | qt5.QDialogButtonBox.Ok)
        self.buttonBox.rejected.connect(self.close)
        self.buttonBox.accepted.connect(self.accept)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)

    #def sizeHint(self):
    #    return qt5.QSize(600,600)

class dialogDefineExperiment(ui.genericDialog):

    def filter_classes_by_timecourse_regexp(self, text):
        try:
            rx = re.compile('(?P<timecourse>%s)' % text)
        except:
            return

        filtered_classes = list(set([rx.sub('', c) for c in self.classes]))
        self.cb_control.clear()
        self.cb_control.addItems(filtered_classes)
        self.cb_test.clear()
        self.cb_test.addItems(filtered_classes)
        # Ensure something remains selected
        self.cb_control.setCurrentIndex(0)
        self.cb_test.setCurrentIndex(0)

    def __init__(self, parent=None, **kwargs):
        super(dialogDefineExperiment, self).__init__(parent, **kwargs)

        self.classes = sorted(parent.data.classes)
        self.setWindowTitle("Define Experiment")

        self.cb_control = qt5.QComboBox()
        self.cb_control.addItems(self.classes)

        self.cb_test = qt5.QComboBox()
        self.cb_test.addItems(self.classes)

        classes = qt5.QGridLayout()
        classes.addWidget(qt5.QLabel('Control:'), 1, 1)
        classes.addWidget(self.cb_control, 1, 2)

        classes.addWidget(qt5.QLabel('Test:'), 2, 1)
        classes.addWidget(self.cb_test, 2, 2)

        if 'control' in parent.experiment and 'test' in parent.experiment:
            self.cb_control.setCurrentIndex(self.cb_control.findText(parent.experiment['control']))
            self.cb_test.setCurrentIndex(self.cb_test.findText(parent.experiment['test']))
        else:
            self.cb_control.setCurrentIndex(0)
            self.cb_test.setCurrentIndex(0)

        self.le_timecourseRegExp = qt5.QLineEdit()
        self.le_timecourseRegExp.setText(parent.experiment['timecourse'] if 'timecourse' in parent.experiment else '')
        self.le_timecourseRegExp.textChanged.connect(self.filter_classes_by_timecourse_regexp)

        self.layout.addLayout(classes)
        self.layout.addWidget(qt5.QLabel('Timecourse filter (regexp:'))
        self.layout.addWidget(self.le_timecourseRegExp)

        if 'timecourse' in parent.experiment:
            self.filter_classes_by_timecourse_regexp(parent.experiment['timecourse'])

        # Build dialog layout
        self.dialogFinalise()


class toolBoxItemDelegate(qt5.QAbstractItemDelegate):

    def __init__(self, parent=None, **kwargs):
        super(toolBoxItemDelegate, self).__init__(parent, **kwargs)
        self._elidedwrappedtitle = {}  # Cache
        self._font = None

    def paint(self, painter, option, index):
        # GET TITLE, DESCRIPTION AND ICON
        icon = index.data(qt5.Qt.DecorationRole)
        title = index.data(qt5.Qt.DisplayRole)  # .toString()
        #description = index.data(qt5.Qt.UserRole) #.toString()
        #notice = index.data(qt5.Qt.UserRole+1) #.toString()

        if option.state & qt5.QStyle.State_Selected:
            painter.setPen(qt5.QPalette().highlightedText().color())
            painter.fillRect(option.rect, qt5.QBrush(qt5.QPalette().highlight().color()))
        else:
            painter.setPen(qt5.QPalette().text().color())

        icon.paint(painter, option.rect.adjusted(2, 2, -2, -34), qt5.Qt.AlignVCenter | qt5.Qt.AlignLeft)

        text_rect = option.rect.adjusted(0, 64, 0, 0)
        
        # Hacky adjustment of font, how to get the default font for this widget and shrink it?
        # avoids setting manually, so hopefully will look better on Windows/Linux
        if self._font == None:
            self._font = painter.font()
            self._font.setPointSize( self._font.pointSize()-2 )
        painter.setFont(self._font)

        if title not in self._elidedwrappedtitle:
            self._elidedwrappedtitle[title] = self.elideWrapText(painter, title, text_rect)

        painter.drawText(text_rect, qt5.Qt.AlignTop | qt5.Qt.AlignHCenter | qt5.Qt.TextWordWrap, self._elidedwrappedtitle[title])
        #painter.drawText(text_rect.x(), text_rect.y(), text_rect.width(), text_rect.height(),, 'Hello this is a long title', boundingRect=text_rect)

    def elideWrapText(self, painter, text, text_rect):
        text = textwrap.wrap(text, 10, break_long_words=False)
        wrapped_text = []
        for l in text[:2]:  # Max 2 lines
            l = painter.fontMetrics().elidedText(l, qt5.Qt.ElideRight, text_rect.width())
            wrapped_text.append(l)
        wrapped_text = '\n'.join(wrapped_text)
        return wrapped_text

    def sizeHint(self, option, index):
        return qt5.QSize(64, 96)


class ToolBoxItem(qt5.QListWidgetItem):
    def __init__(self, data=None, parent=None, **kwargs):
        super(ToolBoxItem, self).__init__(parent, **kwargs)
        self.data = data


class ToolPanel(qt5.QListWidget):

    def __init__(self, parent, tools=[], **kwargs):
        super(ToolPanel, self).__init__(parent, **kwargs)

        self.setViewMode(qt5.QListView.IconMode)
        self.setGridSize(qt5.QSize(64, 96))
        #self._columns = 4
        self.setItemDelegate(toolBoxItemDelegate())

        self.tools = tools
        self.addTools()
        #self.setLayout(self.vlayout)
        #self.vlayout.addLayout( self.grid )
        #self.vlayout.addItem( qt5.QSpacerItem(10, 10, qt5.QSizePolicy.Maximum) )

    def addTools(self):

        
        for n, tool in enumerate(self.tools):
            #col = n % self._columns
            #row = n // self._columns

            #print tool
            t = ToolBoxItem(data=tool)
            #t.setToolButtonStyle(qt5.Qt.ToolButtonTextUnderIcon)
            t.setIcon(tool['plugin'].icon)
            #t.setIconSize( qt5.QSize(32, 32) )
            t.setText(getattr(tool['app'], 'name', tool['plugin'].name))
            self.addItem(t)
            #t = ToolItem(qt5.QIcon( tool['icon']), tool['name'], data=tool)
            #self.grid.addWidget( t, row, col )

    def colX(self, col):
        return col * self._tool_width

    def rowY(self, row):
        return row * self._tool_width

    def mouseMoveEvent(self, e):

        item = self.currentItem()

        mimeData = qt5.QMimeData()
        mimeData.setData('application/x-pathomx-app', item.data['id'])

        drag = qt5.QDrag(self)
        drag.setMimeData(mimeData)
        drag.setPixmap(item.data['plugin'].pixmap.scaled(qt5.QSize(64, 64), transformMode=qt5.Qt.SmoothTransformation))
        drag.setHotSpot(e.pos() - self.visualItemRect(item).topLeft())

        dropAction = drag.exec_(qt5.Qt.MoveAction)



def _convert_list_type_from_XML(vs):
    '''
    Lists are a complex type with possibility for mixed sub-types. Therefore each
    sub-entity must be wrapped with a type specifier.
    '''
    vlist = vs.findall('ConfigListItem')
    l = []
    for xconfig in vlist:
        v = xconfig.text
        if xconfig.get('type') in CONVERT_TYPE_FROM_XML:
            # Recursive; woo!
            v = CONVERT_TYPE_FROM_XML[xconfig.get('type')](xconfig)
        l.append( v )
    return l

def _convert_list_type_to_XML(co,vs):
    '''
    Lists are a complex type with possibility for mixed sub-types. Therefore each
    sub-entity must be wrapped with a type specifier.
    '''
    for cv in vs:
        c = et.SubElement(co, "ConfigListItem")
        t = type(cv).__name__
        c.set("type", t)
        c = CONVERT_TYPE_TO_XML[t](c, cv)    
    return co
    

def _apply_text_str(co, s):
    co.text = str(s)
    return co

CONVERT_TYPE_TO_XML = {
    'str': _apply_text_str,
    'unicode': _apply_text_str,
    'int': _apply_text_str,
    'float': _apply_text_str,
    'bool': _apply_text_str,
    'list': _convert_list_type_to_XML
}


CONVERT_TYPE_FROM_XML = {
    'str': lambda x: str(x.text),
    'unicode': lambda x: str(x.text),
    'int': lambda x: int(x.text),
    'float': lambda x: float(x.text),
    'bool': lambda x: bool(x.text),
    'list': _convert_list_type_from_XML
}





     
class MainWindow(qt5.QMainWindow):

    workspace_updated = qt5.pyqtSignal()

    def __init__(self, app):
        super(MainWindow, self).__init__()

        self.app = app
        
        # Initiate logging
        self.logView = qt5.QListWidget()

        logHandler = Logger(self.logView)
        logging.getLogger().addHandler(logHandler)        
        #sys.stdout = Logger( self.logView, sys.__stdout__)
        #sys.stderr = Logger( self.logView, sys.__stderr__, qt5.QColor(255,0,0) )
        logging.info('Welcome to Pathomx v%s' % (VERSION_STRING))

        # Central variable for storing application configuration (load/save from file?
        self.config = qt5.QSettings()
        if self.config.value('/Pathomx/Is_setup', False) != True:
            logging.info("Setting up initial configuration...")
            self.onResetConfig()
            logging.info('Done')

        # Do version upgrade availability check
        # FIXME: Do check here; if not done > 2 weeks
        if StrictVersion(self.config.value('/Pathomx/Latest_version','0.0.0')) > StrictVersion(VERSION_STRING):
            # We've got an upgrade
            logging.warning('A new version (v%s) is available' % self.config.value('/Pathomx/Update/Latest_version','0.0.0'))


        # Create database accessor
        self.db = db.databaseManager()
        self.data = None  # deprecated
        self.datasets = []  # List of instances of data.datasets() // No data loaded by default

        self.experiment = dict()
        self.layout = None  # No map by default

        # The following holds tabs & pathway objects for gpml imported pathways
        self.gpmlpathways = []
        self.tab_handlers = []
        self.url_handlers = defaultdict(list)
        self.app_launchers = {}
        self.app_launcher_categories = defaultdict(list)
        self.file_handlers = {}

        # Create templating engine
        self.templateEngine = Engine(
            loader=FileLoader([os.path.join(utils.scriptdir, 'html')]),
            extensions=[CoreExtension(), CodeExtension()]
        )
        self.templateEngine.global_vars.update({'tr': tr})

        self.update_view_callback_enabled = True

        self.printer = qt5.QPrinter()

        qt5.QNetworkProxyFactory.setUseSystemConfiguration(True)

        #  UI setup etc
        self.menuBars = {
            'file': self.menuBar().addMenu(tr('&File')),
            'plugins': self.menuBar().addMenu(tr('&Plugins')),
            'database': self.menuBar().addMenu(tr('&Database')),
            'help': self.menuBar().addMenu(tr('&Help')),
        }

        # FILE MENU
        aboutAction = qt5.QAction(qt5.QIcon.fromTheme("help-about"), 'About', self)
        aboutAction.setStatusTip(tr('About Pathomx'))
        aboutAction.triggered.connect(self.onAbout)
        self.menuBars['file'].addAction(aboutAction)

        newAction = qt5.QAction(qt5.QIcon(os.path.join(utils.scriptdir, 'icons', 'document.png')), tr('&New Blank Workspace'), self)
        newAction.setShortcut('Ctrl+N')
        newAction.setStatusTip(tr('Create new blank workspace'))
        newAction.triggered.connect(self.onClearWorkspace)
        self.menuBars['file'].addAction(newAction)

        openAction = qt5.QAction(qt5.QIcon(os.path.join(utils.scriptdir, 'icons', 'folder-open-document.png')), tr('&Open…'), self)
        openAction.setShortcut('Ctrl+O')
        openAction.setStatusTip(tr('Open previous analysis workspace'))
        openAction.triggered.connect(self.onOpenWorkspace)
        #self.menuBars['file'].addAction(openAction)

        openAction = qt5.QAction(qt5.QIcon(os.path.join(utils.scriptdir, 'icons', 'folder-open-document.png')), tr('&Open Workflow…'), self)
        openAction.setStatusTip(tr('Open an analysis workflow'))
        openAction.triggered.connect(self.onOpenWorkflow)
        self.menuBars['file'].addAction(openAction)

        self.menuBars['file'].addSeparator()

        saveAction = qt5.QAction(qt5.QIcon(os.path.join(utils.scriptdir, 'icons', 'disk.png')), tr('&Save'), self)
        saveAction.setShortcut('Ctrl+S')
        saveAction.setStatusTip(tr('Save current workspace for future use'))
        saveAction.triggered.connect(self.onSaveWorkspace)
        #self.menuBars['file'].addAction(saveAction)

        saveAsAction = qt5.QAction(qt5.QIcon(os.path.join(utils.scriptdir, 'icons', 'disk--pencil.png')), tr('Save &As…'), self)
        saveAsAction.setShortcut('Ctrl+A')
        saveAsAction.setStatusTip(tr('Save current workspace for future use'))
        saveAsAction.triggered.connect(self.onSaveWorkspaceAs)
        #self.menuBars['file'].addAction(saveAsAction)

        saveAsAction = qt5.QAction(qt5.QIcon(os.path.join(utils.scriptdir, 'icons', 'disk--pencil.png')), tr('Save Workflow As…'), self)
        saveAsAction.setStatusTip(tr('Save current workflow for future use'))
        saveAsAction.triggered.connect(self.onSaveWorkflowAs)
        self.menuBars['file'].addAction(saveAsAction)

        self.menuBars['file'].addSeparator()

        printAction = qt5.QAction(qt5.QIcon(os.path.join(utils.scriptdir, 'icons', 'printer.png')), tr('&Print…'), self)
        printAction.setShortcut('Ctrl+P')
        printAction.setStatusTip(tr('Print current figure'))
        printAction.triggered.connect(self.onPrint)
        self.menuBars['file'].addAction(printAction)

        self.menuBars['file'].addSeparator()

        # DATABASE MENU
        explore_dbAction = qt5.QAction(qt5.QIcon(os.path.join(utils.scriptdir, 'icons', 'database-explore.png')), tr('&Explore database…'), self)
        explore_dbAction.setStatusTip('Explore database')
        explore_dbAction.triggered.connect(self.onDBExplore)
        self.menuBars['database'].addAction(explore_dbAction)

        load_identitiesAction = qt5.QAction(qt5.QIcon(os.path.join(utils.scriptdir, 'icons', 'database-import.png')), tr('&Load database unification…'), self)
        load_identitiesAction.setStatusTip('Load additional unification mappings into database')
        load_identitiesAction.triggered.connect(self.onLoadIdentities)
        self.menuBars['database'].addAction(load_identitiesAction)

        self.menuBars['database'].addSeparator()

        reload_databaseAction = qt5.QAction(qt5.QIcon(os.path.join(utils.scriptdir, 'icons', 'exclamation-red.png')), tr('&Reload database'), self)
        reload_databaseAction.setStatusTip('Reload pathway & metabolite database')
        reload_databaseAction.triggered.connect(self.onReloadDB)
        self.menuBars['database'].addAction(reload_databaseAction)
        # PLUGINS MENU

        change_pluginsAction = qt5.QAction(tr('&Manage plugins…'), self)
        change_pluginsAction.setStatusTip('Find, activate, deactivate and remove plugins')
        change_pluginsAction.triggered.connect(self.onChangePlugins)
        self.menuBars['plugins'].addAction(change_pluginsAction)

        check_pluginupdatesAction = qt5.QAction(tr('&Check for updated plugins'), self)
        check_pluginupdatesAction.setStatusTip('Check for updates to installed plugins')
        check_pluginupdatesAction.triggered.connect(self.onCheckPluginUpdates)
        #self.menuBars['plugins'].addAction(check_pluginupdatesAction)  FIXME: Add a plugin-update check

        aboutAction = qt5.QAction(qt5.QIcon.fromTheme("help-about"), 'Introduction', self)
        aboutAction.setStatusTip(tr('About Pathomx'))
        aboutAction.triggered.connect(self.onAbout)
        self.menuBars['help'].addAction(aboutAction)

        self.menuBars['help'].addSeparator()

        goto_pathomx_websiteAction = qt5.QAction(tr('&Pathomx homepage'), self)
        goto_pathomx_websiteAction.setStatusTip('Go to the Pathomx website')
        goto_pathomx_websiteAction.triggered.connect(self.onGoToPathomxWeb)
        self.menuBars['help'].addAction(goto_pathomx_websiteAction)

        goto_pathomx_docsAction = qt5.QAction(tr('&Pathomx documentation'), self)
        goto_pathomx_docsAction.setStatusTip('Read latest Pathomx documentation')
        goto_pathomx_docsAction.triggered.connect(self.onGoToPathomxDocs)
        self.menuBars['help'].addAction(goto_pathomx_docsAction)

        goto_pathomx_demosAction = qt5.QAction(tr('&Pathomx demos'), self)
        goto_pathomx_demosAction.setStatusTip('Watch Pathomx demo videos')
        goto_pathomx_demosAction.triggered.connect(self.onGoToPathomxDemos)
        self.menuBars['help'].addAction(goto_pathomx_demosAction)

        self.menuBars['help'].addSeparator()

        do_registerAction = qt5.QAction(tr('&Register Pathomx'), self)
        do_registerAction.setStatusTip('Register Pathomx for release updates')
        do_registerAction.triggered.connect(self.onDoRegister)
        self.menuBars['help'].addAction(do_registerAction)

        # GLOBAL WEB SETTINGS
        qt5.QNetworkProxyFactory.setUseSystemConfiguration(True)

        qt5.QWebSettings.setMaximumPagesInCache(0)
        qt5.QWebSettings.setObjectCacheCapacities(0, 0, 0)
        qt5.QWebSettings.clearMemoryCaches()

        # Display a introductory helpfile
        self.mainBrowser = ui.QWebViewExtend(None, onNavEvent=self.onBrowserNav)

        self.plugins = {}  # Dict of plugin shortnames to data
        self.plugins_obj = {}  # Dict of plugin name references to objs (for load/save)
        self.pluginManager = PluginManagerSingleton.get()
        self.pluginManager.m = self

        self.plugin_places = []
        self.core_plugin_path = os.path.join(utils.scriptdir, 'plugins')
        self.plugin_places.append(self.core_plugin_path)

        user_application_data_paths = qt5.QStandardPaths.standardLocations(qt5.QStandardPaths.DataLocation)
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
               "Identification": plugins.IdentificationPlugin,
               "Analysis": plugins.AnalysisPlugin,
               "Visualisation": plugins.VisualisationPlugin,
               "Export": plugins.ExportPlugin,
               "Scripting": plugins.ScriptingPlugin,
               }
        self.pluginManager.setCategoriesFilter(categories_filter)
        self.pluginManager.collectPlugins()

        plugin_categories = ["Import", "Processing", "Identification", "Analysis", "Visualisation", "Export", "Scripting"]  # categories_filter.keys()
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

                metadata = {
                    'id': plugin.plugin_object.__class__.__name__,  # __module__,
                    'image': plugin_image,
                    'image_forward_slashes': plugin_image.replace('\\', '/'),  # Slashes fix for CSS in windows
                    'name': plugin.name,
                    'version': plugin.version,
                    'description': plugin.description,
                    'author': plugin.author,
                    'info': plugin,
                    'path': os.path.dirname(plugin.path),
                    'module': os.path.basename(plugin.path),
                    'shortname': os.path.basename(plugin.path),
                    'is_core_plugin': plugin.path.startswith(self.core_plugin_path)
                }

                self.plugins[metadata['shortname']] = metadata
                self.plugin_names[id(plugin.plugin_object)] = plugin.name

                plugin.plugin_object.post_setup(path=os.path.dirname(plugin.path), name=plugin.name)

                apps[category].append(metadata)

        self.stack = qt5.QStackedWidget()
        self.apps = []

        self.threadpool = qt5.QThreadPool()
        logging.info( "Multithreading with maximum %d threads" % self.threadpool.maxThreadCount() )
    
        self.setCentralWidget(self.stack)
        self.stack.setCurrentIndex(0)

        self.workspace_count = 0  # Auto-increment
        self.workspace_parents = {}
        self.workspace_index = {}  # id -> obj

        self.workspace = qt5.QTreeWidget()
        self.workspace.setColumnCount(4)
        self.workspace.expandAll()

        self.workspace.setHeaderLabels(['', 'ID', ' ◎', ' ⚑'])  # ,'#'])
        self.workspace.setUniformRowHeights(True)
        self.workspace.hideColumn(1)

        self.editor = WorkspaceEditor(self)
        self.setCentralWidget(self.editor)

        app_category_icons = {
               "Import": qt5.QIcon(os.path.join(utils.scriptdir, 'icons', 'disk--arrow.png')),
               "Processing": qt5.QIcon(os.path.join(utils.scriptdir, 'icons', 'ruler-triangle.png')),
               "Identification": qt5.QIcon(os.path.join(utils.scriptdir, 'icons', 'target.png')),
               "Analysis": qt5.QIcon(os.path.join(utils.scriptdir, 'icons', 'calculator.png')),
               "Visualisation": qt5.QIcon(os.path.join(utils.scriptdir, 'icons', 'star.png')),
               "Export": qt5.QIcon(os.path.join(utils.scriptdir, 'icons', 'disk--pencil.png')),
               "Scripting": qt5.QIcon(os.path.join(utils.scriptdir, 'icons', 'script-text.png')),
               }

        template = self.templateEngine.get_template('apps.html')
        for category in plugin_categories:
            self.addWorkspaceItem(None, None, category, app_category_icons[category])

        self.workspace.setSelectionMode(qt5.QAbstractItemView.SingleSelection)
        self.workspace.currentItemChanged.connect(self.onWorkspaceStackChange)

        self.toolbox = qt5.QToolBox(self)
        for category in plugin_categories:
            panel = ToolPanel(self, tools=self.tools[category])
            self.toolbox.addItem(panel, app_category_icons[category], category)

        self.toolDock = qt5.QDockWidget(tr('Toolkit'))
        self.toolDock.setWidget(self.toolbox)

        self.workspaceDock = qt5.QDockWidget(tr('Workspace'))
        self.workspaceDock.setWidget(self.workspace)
        self.workspace.setHorizontalScrollBarPolicy(qt5.Qt.ScrollBarAlwaysOff)
        self.workspace.setColumnWidth(0, 298 - 25 * 2)
        self.workspace.setColumnWidth(2, 24)
        self.workspace.setColumnWidth(3, 24)
        self.workspaceDock.setMinimumWidth(300)
        self.workspaceDock.setMaximumWidth(300)

        self.dataView = qt5.QTreeView(self)
        self.dataModel = data.DataTreeModel(self.datasets)
        self.dataView.setModel(self.dataModel)

        self.dataView.hideColumn(0)

        self.dataDock = qt5.QDockWidget(tr('Data'))
        self.dataDock.setWidget(self.dataView)
        self.dataDock.setMinimumWidth(300)
        self.dataDock.setMaximumWidth(300)

        self.logDock = qt5.QDockWidget(tr('Log'))
        self.logDock.setWidget(self.logView)

        self.addDockWidget(qt5.Qt.LeftDockWidgetArea, self.logDock)
        self.addDockWidget(qt5.Qt.LeftDockWidgetArea, self.dataDock)
        self.addDockWidget(qt5.Qt.LeftDockWidgetArea, self.workspaceDock)
        self.addDockWidget(qt5.Qt.LeftDockWidgetArea, self.toolDock)

        self.tabifyDockWidget(self.toolDock, self.workspaceDock)
        self.tabifyDockWidget(self.workspaceDock, self.dataDock)
        self.tabifyDockWidget(self.dataDock, self.logDock)
        self.toolDock.raise_()

        self.dbtool = ui.DbApp(self)
        self.dbBrowser = self.dbtool.dbBrowser

        self.setWindowTitle(tr('Pathomx'))

        self.progressBar = qt5.QProgressBar(self.statusBar())
        self.progressBar.setMaximumSize(qt5.QSize(170, 19))
        self.progressBar.setRange(0, 100)
        self.statusBar().addPermanentWidget(self.progressBar)
        self.progressTracker = {}  # Dict storing values for each view/object

        logging.info('Ready.')
        self.statusBar().showMessage(tr('Ready'))
        self.showMaximized()

        # Do version upgrade check
        if StrictVersion(self.config.value('/Pathomx/Current_version','0.0.0')) < StrictVersion(VERSION_STRING):
            # We've got an upgrade
            self.onAbout()
            self.config.setValue('/Pathomx/Current_version', VERSION_STRING)

        if self.config.value('/Pathomx/Offered_registration', False) != True:
            self.onDoRegister()
            self.config.setValue('/Pathomx/Offered_registration', True)

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
        # Defaults not set, apply now and save complete config file
        self.config.setValue('Pathomx/Is_setup', True)
        self.config.setValue('Pathomx/Current_version', '0.0.0')
        self.config.setValue('Pathomx/Update/Latest_version', '0.0.0')
        self.config.setValue('Pathomx/Update/Last_checked', None)
        self.config.setValue('Pathomx/Offered_registration', False)

        self.config.setValue('Plugins/Active', [])
        self.config.setValue('Plugins/Disabled', [])
        self.config.setValue('Plugins/Available', [])
        self.config.setValue('Plugins/Paths', [])
    # UI Events

    def onGoToPathomxWeb(self):
        qt5.QDesktopServices.openUrl(qt5.QUrl('http://pathomx.org'))

    def onGoToPathomxDemos(self):
        qt5.QDesktopServices.openUrl(qt5.QUrl('http://pathomx.org/demos'))

    def onGoToPathomxDocs(self):
        qt5.QDesktopServices.openUrl(qt5.QUrl('http://docs.pathomx.org/'))

    def onDoRegister(self):
        # Pop-up a registration window; take an email address and submit to
        # register for update-announce.
        dlg = DialogRegister(self)
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

    def onPrint(self):
        dialog = qt5.QPrintDialog(self.printer, self)
        if dialog.exec_():
            self.mainBrowser.print_(self.printer)

    def onZoomOut(self):
        zf = self.mainBrowser.zoomFactor()
        zf = max(0.5, zf - 0.1)
        self.mainBrowser.setZoomFactor(zf)

    def onZoomIn(self):
        zf = self.mainBrowser.zoomFactor()
        zf = min(1.5, zf + 0.1)
        self.mainBrowser.setZoomFactor(zf)

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
                    a = self.app_launchers[app]()

                # Update workspace viewer
                self.workspace_updated.emit()  # Notify change to workspace layout        


            elif app == 'db':
                kind, id, action = url.path().strip('/').split('/')
                            # View an object
                if action == 'view':
                    if kind == 'pathway' and id in self.db.pathways:
                        pathway = self.db.pathways[id]
                        self.generatedbBrowserView(template='db/pathway.html', data={
                            'title': pathway.name,
                            'object': pathway,
                            })
                    elif kind == 'reaction' and id in self.db.reactions:
                        reaction = self.db.reactions[id]
                        self.generatedbBrowserView(template='db/reaction.html', data={
                            'title': reaction.name,
                            'object': reaction,
                            })
                    elif kind == 'compound' and id in self.db.compounds:
                        compound = self.db.compounds[id]
                        self.generatedbBrowserView(template='db/compound.html', data={
                            'title': compound.name,
                            'object': compound,
                            })
                    elif kind == 'protein' and id in self.db.proteins:
                        protein = self.db.proteins[id]
                        self.generatedbBrowserView(template='db/protein.html', data={
                            'title': protein.name,
                            'object': protein,
                            })
                    elif kind == 'gene' and id in self.db.genes:
                        gene = self.db.genes[id]
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
            qt5.QDesktopServices.openUrl(url)

    def onLoadIdentities(self):
        """ Open a data file"""
        filename, _ = qt5.QFileDialog.getOpenFileName(self, 'Load compound identities file', '')
        if filename:
            self.db.load_synonyms(filename)
            # Re-translate the datafile if there is one and refresh
            if self.data:
                self.data.translate(self.db)
                self.generateGraphView(regenerate_analysis=True)

    def onSaveAs(self):
        """ Save a copy of the graph as one of the supported formats"""
        # Note this will regenerate the graph with the current settings, with output type specified appropriately
        filename, _ = qt5.QFileDialog.getSaveFileName(self, 'Save current metabolic pathway map', '')
        if filename:
            fn, ext = os.path.splitext(filename)
            format = ext.replace('.', '')
            # Check format is supported
            if format in ['bmp', 'canon', 'dot', 'xdot', 'cmap', 'eps', 'fig', 'gd', 'gd2', 'gif', 'gtk', 'ico', 'imap', 'cmapx', 'imap_np', 'cmapx_np', 'ismap', 'jpg', 'jpeg', 'jpe', 'pdf', 'plain', 'plain-ext', 'png', 'ps', 'ps2', 'svg', 'svgz', 'tif', 'tiff', 'vml', 'vmlz', 'vrml', 'wbmp', 'webp', 'xlib']:
                self.generateGraph(filename, format)
            else:
                # Unsupported format error
                pass

    def onAbout(self):
        dlg = DialogAbout(self)
        dlg.exec_()

    def onExit(self):
        self.Close(True)  # Close the frame.

    def onReloadDB(self):
        self.db = db.databaseManager()

    def onRefresh(self):
        self.generateGraphView()

    def generatedbBrowserView(self, template='base.html', data={'title': '', 'object': {}, 'data': {}}):
        metadata = {
            'htmlbase': os.path.join(utils.scriptdir, 'html'),
            # Current state data
            'current_pathways': [],  # self.config.value('/Pathways/Show').split(','),
            'data': self.data,
            # Color schemes
            # 'rdbu9':['b2182b', 'd6604d', 'f4a582', '33a02c', 'fddbc7', 'f7f7f7', 'd1e5f0', '92c5de', '4393c3', '2166ac']
        }

        template = self.templateEngine.get_template(template)
        self.dbBrowser.setHtml(template.render(dict(list(data.items()) + list(metadata.items()))), qt5.QUrl("~"))

    def onWorkspaceStackChange(self, item, previous):
        widget = self.workspace_index[item.text(1)]
        if widget:
            widget.show()
            widget.raise_()

    def addWorkspaceItem(self, widget, section, title, icon=None):

        tw = qt5.QTreeWidgetItem()
        wid = str(id(tw))
        tw.setText(0, tr(title))
        tw.setText(1, wid)

        if widget:
            widget._workspace_index = wid

        self.workspace_index[wid] = widget

        if icon:
            tw.setIcon(0, icon)

        if section:
            self.workspace_parents[section].addChild(tw)
            widget._workspace_section = self.workspace_parents[section]
            widget._workspace_tree_widget = tw
        else:
            self.workspace.addTopLevelItem(tw)
            self.workspace_parents[title] = tw
            tw.setExpanded(True)

        return tw

    def removeWorkspaceItem(self, widget):
        del self.workspace_index[widget._workspace_index]
        widget._workspace_section.removeChild(widget._workspace_tree_widget)

    def setWorkspaceStatus(self, workspace_item, status):
        status_icons = {
            'active': qt5.QIcon(os.path.join(utils.scriptdir, 'icons', 'flag-green.png')),
            'render': qt5.QIcon(os.path.join(utils.scriptdir, 'icons', 'flag-purple.png')),
            'waiting': qt5.QIcon(os.path.join(utils.scriptdir, 'icons', 'flag-yellow.png')),
            'error': qt5.QIcon(os.path.join(utils.scriptdir, 'icons', 'flag-red.png')),
            'paused': qt5.QIcon(os.path.join(utils.scriptdir, 'icons', 'flag-white.png')),
            'done': qt5.QIcon(os.path.join(utils.scriptdir, 'icons', 'flag-checker.png')),
            'clear': qt5.QIcon(None)
        }

        if status not in list(status_icons.keys()):
            status = 'clear'

        workspace_item.setIcon(3, status_icons[status])
        self.workspace.update(self.workspace.indexFromItem(workspace_item))

        # Keep things ticking
        qt5.QCoreApplication.processEvents()

        if status == 'active':  # Starting
            self.updateProgress(workspace_item, 0)

        elif status == 'clear' or status == 'error':
            self.updateProgress(workspace_item, None)

        elif status == 'done':  # Flash done then clear in a bit
            self.updateProgress(workspace_item, 1)
            statusclearCallback = functools.partial(self.setWorkspaceStatus, workspace_item, 'clear')
            workspace_item.status_timeout = qt5.QTimer.singleShot(1000, statusclearCallback)

    def clearWorkspaceStatus(self, workspace_item):
        self.setWorkspaceStatus(workspace_item, 'clear')

    def updateProgress(self, workspace_item, progress):

        if progress == None:
            if workspace_item in self.progressTracker:
                del(self.progressTracker[workspace_item])
            if len(self.progressTracker) == 0:
                self.progressBar.reset()
                return
        else:
            self.progressTracker[workspace_item] = progress

        m = 100.0 / len(self.progressTracker)
        pt = sum([n * m for n in list(self.progressTracker.values())])

        if self.progressBar.value() < pt:  # Don't go backwards it's annoying FIXME: once hierarchical prediction; stack all things that 'will' start
            self.progressBar.setValue(pt)
        # Keep things ticking
        #qt5.QCoreApplication.processEvents()

    def register_url_handler(self, identifier, url_handler):
        self.url_handlers[identifier].append(url_handler)
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
        reply = qt5.QMessageBox.question(self, "Clear Workspace", "Are you sure you want to clear the workspace? Everything will be deleted.",
                            qt5.QMessageBox.Yes | qt5.QMessageBox.No)
        if reply == qt5.QMessageBox.Yes:
            self.clearWorkspace()

    def clearWorkspace(self):
        for v in self.apps[:]:  # Copy as v.delete modifies the self.apps list
            v.delete()

        # Remove all workspace datasets
        del self.datasets[:]

        self.workspace_updated.emit()
    ### OPEN/SAVE WORKFLOWS

    def onSaveWorkflowAs(self):
        filename, _ = qt5.QFileDialog.getSaveFileName(self, 'Save current workflow', '', "Pathomx Workflow Format (*.mpf)")
        if filename:
            self.saveWorkflow(filename)

    def saveWorkflow(self, fn):

        root = et.Element("Workflow")
        root.set('xmlns:mpwfml', "http://pathomx.org/schema/Workflow/2013a")

        # Build a JSONable object representing the entire current workspace and write it to file
        for v in self.apps:
            app = et.SubElement(root, "App")
            app.set("id", v.id)

            name = et.SubElement(app, "Name")
            name.text = v.name

            plugin = et.SubElement(app, "Plugin")
            plugin.set("version", '1.0')
            plugin.text = v.plugin.__class__.__name__

            plugin_class = et.SubElement(app, "Launcher")
            plugin_class.text = v.__class__.__name__

            position = et.SubElement(app, "EditorXY")
            position.set("x", str(v.editorItem.x()))
            position.set("y", str(v.editorItem.y()))

            config = et.SubElement(app, "Config")
            for ck, cv in list(v.config.config.items()):
                co = et.SubElement(config, "ConfigSetting")
                co.set("id", ck)
                t = type(cv).__name__
                co.set("type", type(cv).__name__)
                co = CONVERT_TYPE_TO_XML[t](co, cv)

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
        filename, _ = qt5.QFileDialog.getOpenFileName(self, 'Open new workflow', '', "Pathomx Workflow Format (*.mpf)")
        if filename:
            self.openWorkflow(filename)
    
    

            
    def openWorkflow(self, fn):
        logging.info("Loading workflow... %s" % fn)
        # Wipe existing workspace
        self.clearWorkspace()
        # Load from file
        tree = et.parse(fn)
        workflow = tree.getroot()

        appref = {}
        logging.info("...Loading apps.")
        for xapp in workflow.findall('App'):
            # FIXME: This does not work with multiple launchers/plugin - define as plugin.class?
            # Check plugins loaded etc.
            logging.info(('- %s' % xapp.find('Name').text))
            app = self.app_launchers["%s.%s" % (xapp.find("Plugin").text, xapp.find("Launcher").text)](auto_consume_data=False, name=xapp.find('Name').text)
            editorxy = xapp.find('EditorXY')
            app.editorItem.setPos(qt5.QPointF(float(editorxy.get('x')), float(editorxy.get('y'))))
            #app = self.app_launchers[ item.find("launcher").text ]()
            #app.set_name(  )
            appref[xapp.get('id')] = app

            config = {}
            for xconfig in xapp.findall('Config/ConfigSetting'):
                #id="experiment_control" type="unicode" value="monocyte at intermediate differentiation stage (GDS2430_2)"/>
                if xconfig.get('type') in CONVERT_TYPE_FROM_XML:
                    v = CONVERT_TYPE_FROM_XML[xconfig.get('type')](xconfig)
                config[xconfig.get('id')] = v

            app.config.set_many(config, trigger_update=False)

        logging.info("...Linking objects.")
        # Now build the links between objects; we need to force these as data is not present
        for xapp in workflow.findall('App'):
            app = appref[xapp.get('id')]

            for idef in xapp.findall('DataInputs/Input'):
                app.data._consume_action(idef.get('id'), appref[idef.get('manager')].data.o[idef.get('interface')])

        logging.info("Load complete.")
        # Focus the home tab & refresh the view
        self.workspace_updated.emit()


class QApplicationExtend(qt5.QApplication):
    def event(self, e):
        if e.type() == qt5.QEvent.FileOpen:
            fn, fe = os.path.splitext(e.file())
            formats = {  # Run specific loading function for different source data types
                    '.mpf': self.openWorkflow,
                }
            if fe in list(formats.keys()):
                formats[fe](e.file())

            return True

        else:
            return super(QApplicationExtend, self).event(e)


def main():
    # Create a qt5.Qt application
    app = QApplicationExtend(sys.argv)
    app.setStyle('fusion')
    app.setOrganizationName("Pathomx")
    app.setOrganizationDomain("pathomx.org")
    app.setApplicationName("Pathomx")

    locale = qt5.QLocale.system().name()
    #locale = 'nl'

    #sys.path.append(utils.scriptdir)

    # Load base qt5.QT translations from the normal place (does not include _nl, or _it)
    translator_qt = qt5.QTranslator()
    if translator_qt.load("qt_%s" % locale, qt5.QLibraryInfo.location(qt5.QLibraryInfo.TranslationsPath)):
        logging.debug(("Loaded qt5.Qt translations for locale: %s" % locale))
        app.installTranslator(translator_qt)

    # See if we've got a default copy for _nl, _it or others
    elif translator_qt.load("qt_%s" % locale, os.path.join(utils.scriptdir, 'translations')):
        logging.debug(("Loaded qt5.Qt (self) translations for locale: %s" % locale))
        app.installTranslator(translator_qt)

    # Load Pathomx specific translations
    translator_mp = qt5.QTranslator()
    if translator_mp.load("pathomx_%s" % locale, os.path.join(utils.scriptdir, 'translations')):
        logging.debug(("Loaded Pathomx translations for locale: %s" % locale))
    app.installTranslator(translator_mp)

    # Set Matplotlib defaults for nice looking charts
    mpl.rcParams['figure.facecolor'] = 'white'
    mpl.rcParams['figure.autolayout'] = True
    mpl.rcParams['lines.linewidth'] = 0.25
    mpl.rcParams['lines.color'] = 'black'
    mpl.rcParams['lines.markersize'] = 10
    mpl.rcParams['axes.linewidth'] = 0.5
    mpl.rcParams['axes.color_cycle'] = utils.category10
    mpl.rcParams['font.size'] = 8
    mpl.rcParams['font.sans-serif'] = ['Helvetica', 'Arial', 'Bitstream Vera Sans', 'Lucida Grande', 'Verdana', 'Geneva', 'Lucid', 'Arial']
    mpl.rcParams['patch.linewidth'] = 0

    MainWindow(app)
    app.exec_()
    # Enter qt5.Qt application main loop
    sys.exit()

if __name__ == "__main__":
    main()
