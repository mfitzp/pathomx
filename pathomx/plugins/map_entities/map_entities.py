# -*- coding: utf-8 -*-
#from __future__ import unicode_literals

import os
import copy

import numpy as np

import pathomx.ui as ui
import pathomx.db as db
import pathomx.utils as utils

from pathomx.data import DataSet, DataDefinition, TableInterface
from pathomx.views import TableView
from pathomx.utils import UnicodeReader, UnicodeWriter
from pathomx.plugins import IdentificationPlugin
from pathomx.qt import *

TYPE_COLORS = {
    'compound': '#e2ebf5',
    'secondary': '#e2ebf5',
    'gene': '#e7f9d5',
    'protein': '#fefadb',
    }
#    729fcf, 8ae234, fce94f

MAP_ENTITY_ALL = 0
MAP_ENTITY_GENE = 1
MAP_ENTITY_PROTEIN = 2
MAP_ENTITY_COMPOUND = 3

MAP_TYPE_TABLE = {
    'Any entity': MAP_ENTITY_ALL,
    'Gene': MAP_ENTITY_GENE,
    'Protein': MAP_ENTITY_PROTEIN,
    'Compound (metabolite)': MAP_ENTITY_COMPOUND,
}


# Dialog box for Metabohunter search options
class MapEntityConfigPanel(ui.ConfigPanel):

    def __init__(self, *args, **kwargs):
        super(MapEntityConfigPanel, self).__init__(*args, **kwargs)

        self.cb_mapping_type = QComboBox()
        self.cb_mapping_type.addItems(list(MAP_TYPE_TABLE.keys()))
        self.config.add_handler('map_object_type', self.cb_mapping_type, MAP_TYPE_TABLE)

        self.layout.addWidget(self.cb_mapping_type)

        self.finalise()


class EntityItemDelegate(QStyledItemDelegate):

    def paint(self, painter, option, index):

        if index.data(Qt.UserRole):
            painter.setPen(QColor(TYPE_COLORS[index.data(Qt.UserRole)]))
            painter.setBrush(QColor(TYPE_COLORS[index.data(Qt.UserRole)]))
            painter.drawRect(option.rect)

        if isinstance(index.data(Qt.DisplayRole), QPixmap):
            pix = index.data(Qt.DisplayRole).scaled(QSize(option.rect.width(), option.rect.height()), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            # Calculate how to paint into the space without distortion
            x = (option.rect.width() - pix.width()) / 2
            y = (option.rect.height() - pix.height()) / 2

            painter.drawPixmap(QPoint(option.rect.x() + x, option.rect.y() + y), pix)

        else:
            super(EntityItemDelegate, self).paint(painter, option, index)

    def sizeHint(self, option, index):
        return QSize(100, 50)


# Table interface to a entity table. This is a simple multiple column/row view of the data
# with information on mappings, targets and (later) the option to change these mappings
class EntityTableInterface(TableInterface):
    def __init__(self, dso, *args, **kwargs):
        super(EntityTableInterface, self).__init__(dso, *args, **kwargs)
        self.dso = dso

    def rowCount(self, parent):
        return self.dso.shape[1]

    def columnCount(self, parent):
        return 5

    def data(self, index, role):
        if not index.isValid():
            return None

        r, c = index.row(), index.column()

        if role == Qt.UserRole:
            if self.dso.entities[1][r] != None:
                return self.dso.entities[1][r].type

        if role == Qt.DisplayRole:

        # Return different data depending on the index column
            r, c = index.row(), index.column()

            if c == 0:
                return self.dso.labels[1][r]

        
            if self.dso.entities[1][r] != None:
                if c == 1:
                    return self.dso.entities[1][r].id

                elif c == 2:
                    return self.dso.entities[1][r].name

                elif c == 3:
                    return self.dso.entities[1][r].type

                elif c == 4:
                    return QPixmap(self.dso.entities[1][r].image)

        return None

    def headerData(self, col, orientation, role):

        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return ["Source identifier", "Mapped entity", "Common name", "Type", "Structure"][col]

        elif orientation == Qt.Vertical and role == Qt.DisplayRole:
            return col + 1

        return None


class MapEntityApp(ui.GenericApp):

    def __init__(self, **kwargs):
        super(MapEntityApp, self).__init__(**kwargs)
        # Define automatic mapping (settings will determine the route; allow manual tweaks later)

        self.addDataToolBar()
        self.addFigureToolBar()
        self.data.add_input('input')  # Add input slot
        self.data.add_output('output')

        self.table = TableView()
        self.table.setItemDelegate(EntityItemDelegate())
        self.data.o['output'].register_interface('as_entity_table', EntityTableInterface)
        self.views.addView(self.table, 'Table', unfocus_on_refresh=True)
        self.table.setModel(self.data.o['output'].as_entity_table)
        # Deprecate as too slow for large mappings
        #self.views.addTab(WheezyView(self), 'Entities')

        t = self.getCreatedToolbar('Entity mapping', 'external-data')

        import_dataAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'disk--arrow.png')), 'Load annotations from file\\u2026', self.m)
        import_dataAction.setStatusTip('Load annotations from .csv. file')
        import_dataAction.triggered.connect(self.onImportEntities)
        t.addAction(import_dataAction)

        self.addExternalDataToolbar()  # Add standard source data options

        self.config.set_defaults({
            'map_object_type': MAP_ENTITY_ALL,
        })

        self._entity_mapping_table = {}

        # Setup data consumer options
        self.data.consumer_defs.append(
            DataDefinition('input', {
            'labels_n': (None, '>0'),
            'entities_t': (None, None),
            })
        )

        self.addConfigPanel(MapEntityConfigPanel, 'Mapping')

        self.finalise()

    def onImportEntities(self):
        """ Open a data file"""
        filename, _ = QFileDialog.getOpenFileName(self.m, 'Load entity mapping from file', 'Load CSV mapping for name <> identity', "All compatible files (*.csv);;Comma Separated Values (*.csv);;All files (*.*)")
        if filename:
            self.load_datafile(filename)

    def load_datafile(self, filename):

        self._entity_mapping_table = {}
        # Load metabolite entities mapping from file (csv)
        reader = UnicodeReader(open(filename, 'rU'), delimiter=',', dialect='excel')

        # Read each row in turn, build link between items on a row (multiway map)
        # If either can find an entity (via synonyms; make the link)
        for row in reader:
            for s in row:
                if s in self.m.db.index:
                    e = self.m.db.index[s]
                    break
            else:
                continue  # next row if we find nothing

            # break to here if we do
            for s in row:
                self._entity_mapping_table[s] = e

            self.generate()

    def generate(self, input=None):
        dso = self.translate(input, self.m.db)
        return {'output': dso}
    ###### TRANSLATION to METACYC IDENTIFIERS

    def translate(self, data, db):
        lku = {
            MAP_ENTITY_ALL: db.synrev,
            MAP_ENTITY_GENE: db.synrev_by_type['gene'],
            MAP_ENTITY_PROTEIN: db.synrev_by_type['protein'],
            MAP_ENTITY_COMPOUND: db.synrev_by_type['compound'],
                }[self.config.get('map_object_type')]

        # Translate loaded data names to metabolite IDs using provided database for lookup
        for n, m in enumerate(data.labels[1]):

        # Match first using entity mapping table if set (allows override of defaults)
            if m in self._entity_mapping_table:
                data.entities[1][n] = self._entity_mapping_table[m]

            # Use the internal database identities
            elif m and m.lower() in lku:
                data.entities[1][n] = lku[m.lower()]

                #self.quantities[ transid ] = self.quantities.pop( m )
        #print self.metabolites
        return data


class MapEntity(IdentificationPlugin):

    def __init__(self, **kwargs):
        super(MapEntity, self).__init__(**kwargs)
        #MapEntityApp.plugin = self
        self.register_app_launcher(MapEntityApp)
