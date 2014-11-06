# -*- coding: utf-8 -*-
# Experimental data manager
# Loads a csv data file and extracts key information into usable structures for analysis
from __future__ import unicode_literals
import logging
logging.debug('Loading data.py')

# Import PyQt5 classes
from .qt import *

from collections import defaultdict
from copy import deepcopy

import operator
import logging

import pandas as pd
import numpy as np


class DataTreeItem(object):
    '''
    a python object used to return row/column data, and keep note of
    it's parents and/or children
    '''

    def __init__(self, dso, header, parentItem):
        self.dso = dso
        self.parentItem = parentItem
        self.header = header
        self.childItems = []

    def appendChild(self, item):
        self.childItems.append(item)

    def child(self, row):
        return self.childItems[row]

    def childCount(self):
        return len(self.childItems)

    def columnCount(self):
        return 2

    def data(self, column):
        e = set()
        for el in self.dso.entities_t:
            e |= set(el)  # Add entities to the set

        map = {
        0: 0,
        1: self.dso.manager.v.name,
        2: self.dso.name,
        3: ', '.join(e - {'NoneType'}),
        4: 'x'.join([str(s) for s in self.dso.shape]),
        }

        if self.dso:
            return map[column]

        return QVariant()

    def icon(self):
        if self.dso.manager.v.plugin.workspace_icon:
            return self.dso.manager.v.plugin.workspace_icon

    def parent(self):
        return self.parentItem

    def row(self):
        if self.parentItem:
            return self.parentItem.childItems.index(self)
        return 0


class DataTreeModel(QAbstractItemModel):
    '''
    a model to display a few names, ordered by sex
    '''

    def __init__(self, dsos=[], parent=None):
        super(DataTreeModel, self).__init__(parent)
        self.dsos = dsos
        self.HORIZONTAL_HEADERS = ['', 'Source', 'Data', 'Entities', 'Size']
        self.rootItem = DataTreeItem(None, "ALL", None)
        self.parents = {0: self.rootItem}
        self.setupModelData()

    def columnCount(self, parent=None):
        if parent and parent.isValid():
            return parent.internalPointer().columnCount()
        else:
            return len(self.HORIZONTAL_HEADERS)

    def data(self, index, role):
        if not index.isValid():
            return QVariant()

        item = index.internalPointer()
        if role == Qt.DisplayRole:
            return item.data(index.column())
        if role == Qt.UserRole:
            if item:
                return item.dso
        if role == Qt.DecorationRole and index.column() == 1:
            return item.icon()

        return QVariant()

    def headerData(self, column, orientation, role):
        if (orientation == Qt.Horizontal and
        role == Qt.DisplayRole):
            try:
                return QVariant(self.HORIZONTAL_HEADERS[column])
            except IndexError:
                pass

        return QVariant()

    def index(self, row, column, parent):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        if not parent.isValid():
            parentItem = self.rootItem
        else:
            parentItem = parent.internalPointer()

        childItem = parentItem.child(row)
        if childItem:
            return self.createIndex(row, column, childItem)
        else:
            return QModelIndex()

    def parent(self, index):
        if not index.isValid():
            return QModelIndex()

        childItem = index.internalPointer()
        if not childItem:
            return QModelIndex()

        parentItem = childItem.parent()

        if parentItem == self.rootItem:
            return QModelIndex()

        return self.createIndex(parentItem.row(), 0, parentItem)

    def rowCount(self, parent=QModelIndex()):
        if parent.column() > 0:
            return 0
        if not parent.isValid():
            p_Item = self.rootItem
        else:
            p_Item = parent.internalPointer()
        return p_Item.childCount()

    def setupModelData(self):
        if self.dsos:
            for dso in self.dsos:
                newItem = DataTreeItem(dso, "", self.rootItem)
                self.rootItem.appendChild(newItem)

    def refresh(self):
        self.layoutAboutToBeChanged.emit([], QAbstractItemModel.NoLayoutChangeHint)

        ins = set()
        for n, item in enumerate(self.rootItem.childItems):  # self.parentItem.childItems.index(self)
            if item.dso not in self.dsos:
                self.removeRow(n)
            ins.add(item.dso)

        outs = set(self.dsos) - ins
        for dso in outs:
            newItem = DataTreeItem(dso, "", self.rootItem)
            self.rootItem.appendChild(newItem)

        self.layoutChanged.emit([], QAbstractItemModel.NoLayoutChangeHint)


# DataManager allows a view/analysis class to handle control of consumable data sources
class DataManager(QObject):

    # Signals
    source_updated = pyqtSignal(object)
    output_updated = pyqtSignal(object)

    consumed = pyqtSignal(tuple, tuple)
    unconsumed = pyqtSignal(tuple, tuple)

    interfaces_changed = pyqtSignal()

    def __init__(self, parent, view, *args, **kwargs):
        super(DataManager, self).__init__(*args, **kwargs)

        self.m = parent
        self.v = view

        self.id = self.v.id  # Data manager id == that of parent (simplicity; one manager per view)

        self.consumer_defs = []  # Holds data-consumer definitions
        self.consumes = []  # Holds list of data objects that are consumed

        self.i = {}  # Inputs: dict of 'interface' tuples: (origin,interface)
        self.o = {}  # Outputs

        self.watchers = defaultdict(set)  # List of watchers on each output interface

    # Get a dataset through input interface id;
    # This provides indirect access to a copy of the object (local link in self.i = {})
    def get(self, interface):
        if interface in self.i and self.i[interface] is not None:
            # Add ourselves to the watcher for this interface
            source_manager, source_interface = self.i[interface]
            data = source_manager.o[source_interface]
            #dso.manager.watchers[ dso.manager_interface ].add( self )
            return deepcopy(data)

        return None

    def unget(self, interface):
        if interface in self.i:
            self._unconsume(interface)
            self.i[interface] = None

    # Output a dataset through output interface id
    # Advertise object for consumption; needs to handle notification of all consumers
    # independent of the object itself (so can overwrite instead of warping)
    def put(self, interface, dso, update_consumers=True):
        if interface in self.o:

            self.o[interface] = dso
            # Update consumers / refresh views
            #self.o[interface].refresh_interfaces()
            #self.o[interface].previously_managed_by.append(self)
            self.notify_watchers(interface)
            self.output_updated.emit(interface)

            return True

        return False

    def unput(self, interface):
        logging.debug('Unputting data on interface %s' % interface)
        # Trigger _unconsume on all watchers
        for w in list(self.watchers[interface]):
            for i in w.i.keys():
                if w.i[i] is not None:
                    w.unget(i)

        self.watchers[interface] = set()
        self.o[interface] = None  # DataSet(manager=self) # Empty dso (temp; replace with None later?)

    # Get a dataset through output interface id;
    def geto(self, interface):
        if interface in self.o:
            dso = self.o[interface]
            return dso
        return False

    def add_output(self, interface, dso=None, is_public=True):
        self.o[interface] = None
        self.interfaces_changed.emit()

    def remove_output(self, interface):
        if interface in self.o:
            #self.watchers[interface]
            del self.o[interface]
            self.notify_watchers(interface)
            del self.watchers[interface]
            self.interfaces_changed.emit()
            return True
        return False

    def add_input(self, interface):
        if interface not in self.i:
            self.i[interface] = None
            self.interfaces_changed.emit()
            return True
        else:
            return False

    def remove_input(self, interface):
        if interface in self.i:
            self._unconsume(interface)
            del self.i[interface]
            self.interfaces_changed.emit()
            return True
        return False

    def notify_watchers(self, interface):
        for manager in self.watchers[interface]:
            for dest_interface, mi in manager.i.items():
                if mi:
                    m, i = mi
                    if m == self:
                        manager.source_updated.emit(dest_interface)

    # Handle consuming of a data object; assignment to internal tables and processing triggers (plus child-triggers if appropriate)
    # Build import/hooks for this consumable object (need interface logic here; standardise where things will end up)
    def can_consume(self, source_manager, source_interface, consumer_defs=None, interface=None):

        if consumer_defs is None:
            consumer_defs = self.consumer_defs

        if interface:
            consumer_defs = [d for d in consumer_defs if d.target == interface]

        # Don't add data from self manager (infinite loop trigger)
        if source_manager == self:
            return False

        for consumer_def in consumer_defs:
            if consumer_def.can_consume(source_manager.o[source_interface]):
                return True
        return False

    def can_consume_which_of(self, molist, consumer_defs=None):
        which = []
        for source_manager, source_interface in molist:
            if self.can_consume(source_manager, source_interface, consumer_defs):
                which.append((source_manager, source_interface))
        return which

    # Check if a manager has a consumable data object
    def has_consumable(self, manager):
        for data in manager.provides:
            if self.can_consume(data):
                return True
        return False

    def _unconsume(self, interface):
        if self.i[interface] is not None:
            source_manager, source_interface = self.i[interface]

            if self in source_manager.watchers[source_interface]:
                source_manager.watchers[source_interface].remove(self)

            del self.i[interface]
            self.unconsumed.emit((source_manager, source_interface), (self, interface))

    # This is an unchecked consume action; for loading mainly
    def _consume_action(self, source_manager, source_interface, interface):

        # Remove consumed data to update the source watchers
        if interface in self.i:
            self._unconsume(interface)

        self.i[interface] = (source_manager, source_interface)  # Store source as a tuple; we re-do the get rather than storing the actual data
        source_manager.watchers[source_interface].add(self)

        self.consumed.emit((source_manager, source_interface), (self, interface))
        return interface

    # Check if we can consume some data, then do it
    def _consume(self, source_manager, source_interface, consumer_defs=None):
        if consumer_defs is None:
            consumer_defs = self.consumer_defs

        # Check whether this is allowed (checks manager, checks hierarchy (infinite loopage) )
        if not self.can_consume(source_manager, source_interface, consumer_defs):
            return False

        for consumer_def in consumer_defs:
            if consumer_def.can_consume(source_manager.o[source_interface]):
                # Remove existing data object link (stop watching)
                return self._consume_action(source_manager, source_interface, consumer_def.target)

            return False

    def consume(self, source_manager, source_interface):
        interface = self._consume(source_manager, source_interface)
        if interface:
            self.source_updated.emit(interface)
            return True
        return False

    def consume_any_app(self, app_l):
        for a in app_l:
            # Iterate all outputs for this app's data manager
            for o in a.data.o.keys():
                interface = self._consume(a.data, o)
                if interface:
                    self.source_updated.emit(interface)
                    return a.data.o[o]
        return False

    def consume_with(self, data, consumer_def):
        if self._consume(data, [consumer_def]):
            self.source_updated.emit(consumer_def.target)
            return True

    def provide(self, target):
        self.provides.append(self.o[target])

    def stop_consuming(self, target):
        if target in self.i:
            del self.i[target]

    def refresh_consumed_data(self):
        self.source_updated.emit(None)  # Trigger recalculation

    def reset(self):
        for i in list(self.i.keys()):
            self.unget(i)

        for i in list(self.o.keys()):
            self.unput(i)

# Provider/Consumer classes define data availability and requirements for a given dataManager object.
# Object can accept input from any Provider that offers it's Consumer requirements; process it; and then provide it downstream
# view it's own Provider class definition.

def at_least_one_element_in_common(l1, l2):
    return len(set(l1) & set(l2)) > 0


class DataDefinition(object):

    cmp_map = {
         '<': operator.lt,
        '<=': operator.le,
         '=': operator.eq,
        '!=': operator.ne,
         '>': operator.gt,
        '>=': operator.ge,
        'aloeic': at_least_one_element_in_common,
    }

    def __init__(self, target, definition={}, title=None, *args, **kwargs):
        super(DataDefinition, self).__init__(*args, **kwargs)

        # Store consumer/provider description as entity entries from dict
        self.target = target  # Target interface for imported data - stored under this in dataManager
        self.definition = definition

        self.title = title if title else target

    def can_consume(self, data):
        logging.debug("Checking can consume object on %s" % self.target)
        return self.check(data)

    def check(self, o):
        return o is not None

    def get_cmp_fn(self, s):
        if type(s) == list:
            return self.cmp_map['aloeic'], s

        s = str(s)  # Treat all input as strings
        for k, v in list(self.cmp_map.items()):
            if k in s:
                return v, s.replace(k, '')

        return self.cmp_map['='], s


class NumpyArrayDataDefinition(DataDefinition):
    ''' Custom matching definition for numpy arrays '''

    def check(self, o):
        return self._check_instance(o) and \
               self._check_dimensionality(o)

    def _check_instance(self, o):
        return isinstance(o, np.ndarray)

    def _check_dimensionality(self, o):
        if 'shape' not in self.definition:
            logging.debug("  not checking shape")
            return True

        shape = o.shape
        d = self.definition['shape']

        if len(shape) != len(d):
            logging.debug("  dimensionality failure %s %s" % (len(shape), len(d)))
            return False

        for n, cr in enumerate(d):
            if cr is None:  # No restriction on this definition
                logging.debug('  pass')
                continue

            cmp_fn, crr = self.get_cmp_fn(cr)
            if not cmp_fn(shape[n], int(crr)):
                logging.debug("  comparison failure %s %s %s" % (shape[n], cmp_fn, crr))
                return False

        return True


class PandasDataDefinition(NumpyArrayDataDefinition):
    ''' Custom matching definition for pandas dataframes '''

    def check(self, o):
        return self._check_instance(o) and \
            self._check_dimensionality(o) and \
            self._check_columns(o) and \
            self._check_index(o)

    def _check_columns(self, o):
        if 'columns' not in self.definition:
            logging.debug("  not checking columns")
            return True

        vl = []
        for m in self.definition['columns']:
            if not isinstance(m, tuple):
                m = (m, )
            for i in m:
                vl.append(i in o.columns.names)

        return all(vl)

    def _check_index(self, o):
        if 'index' not in self.definition:
            logging.debug("  not checking index")
            return True

        vl = []
        for m in self.definition['index']:
            if not isinstance(m, tuple):
                m = (m, )
            for i in m:
                vl.append(m in o.columns.names)

        return all(vl)

    def _check_instance(self, o):
        logging.debug("  check instance")
        return isinstance(o, pd.DataFrame)
