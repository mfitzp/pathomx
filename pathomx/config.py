# -*- coding: utf-8 -*-
# Experimental data manager
# Loads a csv data file and extracts key information into usable structures for analysis
from __future__ import unicode_literals
import logging
logging.debug('Loading config.py')

# Import PyQt5 classes
from .qt import *

import os
import sys
import re
import base64
import numpy as np
import types

from collections import defaultdict, OrderedDict
import operator
import json
import logging

from copy import copy, deepcopy

RECALCULATE_ALL = 1
RECALCULATE_VIEW = 2


def types_MethodType(fn, handler, handler_class):
    try:
        return types.MethodType(fn, handler, handler_class)
    except TypeError:
        return types.MethodType(fn, handler)

    
def build_dict_mapper(mdict):
    '''
    Build a map function pair for forward and reverse mapping from a specified dict
    
    Mapping requires both a forward and reverse (get, set) mapping function. This function
    is used to automatically convert a supplied dict to a forward and reverse paired lambda.
    
    :param mdict: A dictionary of display values (keys) and stored values (values)
    :type mdict: dict
    :rtype: 2-tuple of lambdas that perform forward and reverse map
                
    '''
    rdict = {v: k for k, v in mdict.items()}
    return (
        lambda x: mdict[x] if x in mdict else x,
        lambda x: rdict[x] if x in rdict else x,
        )


def build_tuple_mapper(mlist):
    '''
    Build a map function pair for forward and reverse mapping from a specified list of tuples
    
    :param mlist: A list of tuples of display values (keys) and stored values (values)
    :type mlist: list-of-tuples
    :rtype: 2-tuple of lambdas that perform forward and reverse map
                
    '''
    rdict = {v: k for k, v in mlist}
    return (
        lambda x: mdict[x] if x in mdict else x,
        lambda x: rdict[x] if x in rdict else x,
        )


# CUSTOM HANDLERS

# QComboBox
def _get_QComboBox(self):
    """
        Get value QCombobox via re-mapping filter
    """
    return self._get_map(self.currentText())


def _set_QComboBox(self, v):
    """
        Set value QCombobox via re-mapping filter
    """
    self.setCurrentText(self._set_map(v))


def _event_QComboBox(self):
    """
        Return QCombobox change event signal
    """
    return self.currentTextChanged


# QCheckBox
def _get_QCheckBox(self):
    """
        Get state of QCheckbox
    """
    return self.isChecked()


def _set_QCheckBox(self, v):
    """
        Set state of QCheckbox
    """
    self.setChecked(v)


def _event_QCheckBox(self):
    """
        Return state change signal for QCheckbox
    """
    return self.stateChanged


# QAction
def _get_QAction(self):
    """
        Get checked state of QAction
    """
    return self.isChecked()


def _set_QAction(self, v):
    """
        Set checked state of QAction
    """
    self.setChecked(v)


def _event_QAction(self):
    """
        Return state change signal for QAction
    """
    return self.toggled


# QAction
def _get_QPushButton(self):
    """
        Get checked state of QPushButton
    """
    return self.isChecked()


def _set_QPushButton(self, v):
    """
        Set checked state of QPushButton
    """
    self.setChecked(v)


def _event_QPushButton(self):
    """
        Return state change signal for QPushButton
    """
    return self.toggled


# QSpinBox
def _get_QSpinBox(self):
    """
        Get current value for QSpinBox
    """
    return self.value()


def _set_QSpinBox(self, v):
    """
        Set current value for QSpinBox
    """
    self.setValue(v)


def _event_QSpinBox(self):
    """
        Return value change signal for QSpinBox
    """
    return self.valueChanged


# QDoubleSpinBox
def _get_QDoubleSpinBox(self):
    """
        Get current value for QDoubleSpinBox
    """
    return self.value()


def _set_QDoubleSpinBox(self, v):
    """
        Set current value for QDoubleSpinBox
    """
    self.setValue(v)


def _event_QDoubleSpinBox(self):
    """
        Return value change signal for QDoubleSpinBox
    """
    return self.valueChanged


# QPlainTextEdit
def _get_QPlainTextEdit(self):
    """
        Get current document text for QPlainTextEdit
    """
    return self.document().toPlainText()


def _set_QPlainTextEdit(self, v):
    """
        Set current document text for QPlainTextEdit
    """
    self.setPlainText(v)


def _event_QPlainTextEdit(self):
    """
        Return current value changed signal for QPlainTextEdit box.
        
        Note that this is not a native Qt signal but a signal manually fired on 
        the user's pressing the "Apply changes" to the code button. Attaching to the 
        modified signal would trigger recalculation on every key-press.
    """
    return self.sourceChangesApplied


# QLineEdit
def _get_QLineEdit(self):
    """
        Get current text for QLineEdit
    """
    return self.text()


def _set_QLineEdit(self, v):
    """
        Set current text for QLineEdit
    """
    self.setText(v)


def _event_QLineEdit(self):
    """
        Return current value changed signal for QLineEdit box.
    """
    return self.textChanged


# CodeEditor
def _get_CodeEditor(self):
    """
        Get current document text for CodeEditor. Wraps _get_QPlainTextEdit.
    """
    _get_QPlainTextEdit(self)


def _set_CodeEditor(self, v):
    """
        Set current document text for CodeEditor. Wraps _set_QPlainTextEdit.
    """
    _set_QPlainTextEdit(self, v)


def _event_CodeEditor(self):
    """
        Return current value changed signal for CodeEditor box. Wraps _event_QPlainTextEdit.
    """
    return _event_QPlainTextEdit(self)


# QListWidget
def _get_QListWidget(self):
    """
        Get currently selected values in QListWidget via re-mapping filter.
        
        Selected values are returned as a list.
    """
    return [self._get_map(s.text()) for s in self.selectedItems()]


def _set_QListWidget(self, v):
    """
        Set currently selected values in QListWidget via re-mapping filter.
        
        Supply values to be selected as a list.
    """
    if v:
        for s in v:
            self.findItems(self._set_map(s), Qt.MatchExactly)[0].setSelected(True)


def _event_QListWidget(self):
    """
        Return current selection changed signal for QListWidget.
    """
    return self.itemSelectionChanged


# QColorButton
def _get_QColorButton(self):
    """
        Get current value for QColorButton
    """
    return self.color()


def _set_QColorButton(self, v):
    """
        Set current value for QColorButton
    """
    self.setColor(v)


def _event_QColorButton(self):
    """
        Return value change signal for QColorButton
    """
    return self.colorChanged


# QNoneDoubleSpinBox
def _get_QNoneDoubleSpinBox(self):
    """
        Get current value for QDoubleSpinBox
    """
    return self.value()


def _set_QNoneDoubleSpinBox(self, v):
    """
        Set current value for QDoubleSpinBox
    """
    self.setValue(v)


def _event_QNoneDoubleSpinBox(self):
    """
        Return value change signal for QDoubleSpinBox
    """
    return self.valueChanged


# ConfigManager handles configuration for a given appview
# Supports default values, change signals, export/import from file (for workspace saving)
class ConfigManager(QObject):

    # Signals
    updated = pyqtSignal(int)  # Triggered anytime configuration is changed (refresh)

    def __init__(self, defaults={}, *args, **kwargs):
        super(ConfigManager, self).__init__(*args, **kwargs)

        self.reset()
        self.defaults = defaults  # Same mapping as above, used when config not set

    # Get config
    def get(self, key):
        """ 
            Get config value for a given key from the config manager.
            
            Returns the value that matches the supplied key. If the value is not set a
            default value will be returned as set by set_defaults.
            
            :param key: The configuration key to return a config value for
            :type key: str
            :rtype: Any supported (str, int, bool, list-of-supported-types)
        """
        if key in self.config:
            return self.config[key]
        elif key in self.defaults:
            return self.defaults[key]
        else:
            return None

    def set(self, key, value, trigger_update=True):
        """ 
            Set config value for a given key in the config manager.
            
            Set key to value. The optional trigger_update determines whether event hooks
            will fire for this key (and so re-calculation). It is useful to suppress these
            when updating multiple values for example.
            
            :param key: The configuration key to set
            :type key: str
            :param value: The value to set the configuration key to
            :type value: Any supported (str, int, bool, list-of-supported-types)
            :rtype: bool (success)              
        """
        if key in self.config and self.config[key] == value:
            return False  # Not updating

        # Set value
        self.config[key] = value

        if key in self.handlers:
            # Trigger handler to update the view
            getter = self.handlers[key].getter  # (self, '_get_%s' % self.handlers[key].__class__.__name__, False)
            setter = self.handlers[key].setter  # getattr(self, '_set_%s' % self.handlers[key].__class__.__name__, False)

            if setter and getter() != self.config[key]:
                setter(self.config[key])

        # Trigger update notification
        if trigger_update:
            self.updated.emit(self.eventhooks[key] if key in self.eventhooks else RECALCULATE_ALL)

        return True

    # Defaults are used in absence of a set value (use for base settings)
    def set_default(self, key, value, eventhook=RECALCULATE_ALL):
        """
        Set the default value for a given key.
        
        This will be returned if the value is 
        not set in the current config. It is important to include defaults for all 
        possible config values for backward compatibility with earlier versions of a plugin.
        
        :param key: The configuration key to set
        :type key: str
        :param value: The value to set the configuration key to
        :type value: Any supported (str, int, bool, list-of-supported-types)
        :param eventhook: Attach either a full recalculation trigger (default), or a view-only recalculation trigger to these values.
        :type eventhook: int RECALCULATE_ALL, RECALCULATE_VIEWS
        
        """

        self.defaults[key] = value
        self.eventhooks[key] = eventhook
        self.updated.emit(eventhook)

    def set_defaults(self, keyvalues, eventhook=RECALCULATE_ALL):
        """
        Set the default value for a set of keys.
        
        These will be returned if the value is 
        not set in the current config. It is important to include defaults for all 
        possible config values for backward compatibility with earlier versions of a plugin.
        
        :param keyvalues: A dictionary of keys and values to set as defaults
        :type key: dict
        :param eventhook: Attach either a full recalculation trigger (default), or a view-only recalculation trigger to these values.
        :type eventhook: int RECALCULATE_ALL, RECALCULATE_VIEWS
        
        """
        for key, value in list(keyvalues.items()):
            self.defaults[key] = value
            self.eventhooks[key] = eventhook

        # Updating the defaults may update the config (if anything without a config value
        # is set by it; should check)
        self.updated.emit(eventhook)
    # Completely replace current config (wipe all other settings)

    def replace(self, keyvalues, trigger_update=True):
        """
        Completely reset the config with a set of key values.
        
        Note that this does not wipe handlers or triggers (see reset), it simply replaces the values
        in the config entirely. It is the equivalent of unsetting all keys, followed by a
        set_many. Anything not in the supplied keyvalues will revert to default.
        
        :param keyvalues: A dictionary of keys and values to set as defaults
        :type keyvalues: dict
        :param trigger_update: Flag whether to trigger a config update (+recalculation) after all values are set. 
        :type trigger_update: bool
        
        """
        self.config = []
        self.set_many(keyvalues)

    def set_many(self, keyvalues, trigger_update=True):
        """
        Set the value of multiple config settings simultaneously.
        
        This postpones the 
        triggering of the update signal until all values are set to prevent excess signals.
        The trigger_update option can be set to False to prevent any update at all.
            
        :param keyvalues: A dictionary of keys and values to set.
        :type key: dict
        :param trigger_update: Flag whether to trigger a config update (+recalculation) after all values are set. 
        :type trigger_update: bool
        """
        has_updated = False
        for k, v in list(keyvalues.items()):
            u = self.set(k, v, trigger_update=False)
            logging.debug('Workflow config; setting %s to %s' % (k, v))
            has_updated = has_updated or u

        if has_updated and trigger_update:
            self.updated.emit(RECALCULATE_ALL)
    # HANDLERS

    # Handlers are UI elements (combo, select, checkboxes) that automatically update
    # and updated from the config manager. Allows instantaneous updating on config
    # changes and ensuring that elements remain in sync

    def add_handler(self, key, handler, mapper=(lambda x: x, lambda x: x)):
        """
        Add a handler (UI element) for a given config key.
        
        The supplied handler should be a QWidget or QAction through which the user
        can change the config setting. An automatic getter, setter and change-event
        handler is attached which will keep the widget and config in sync. The attached
        handler will default to the correct value from the current config.
        
        An optional mapper may also be provider to handler translation from the values
        shown in the UI and those saved/loaded from the config.

        """

    # Add map handler for converting displayed values to internal config data
        if type(mapper) == dict or type(mapper) == OrderedDict:  # By default allow dict types to be used
            mapper = build_dict_mapper(mapper)

        elif type(mapper) == list and type(mapper[0]) == tuple:
            mapper = build_tuple_mapper(mapper)

        handler._get_map, handler._set_map = mapper

        self.handlers[key] = handler

        handler.setter = types_MethodType(globals().get('_set_%s' % handler.__class__.__name__), handler, handler.__class__)
        handler.getter = types_MethodType(globals().get('_get_%s' % handler.__class__.__name__), handler, handler.__class__)
        handler.updater = types_MethodType(globals().get('_event_%s' % handler.__class__.__name__), handler, handler.__class__)

        print("Add handler %s for %s" % (handler.__class__.__name__, key))
        handler.updater().connect(lambda x = None: self.set(key, handler.getter()))

        # Keep handler and data consistent
        if key in self.config:
            handler.setter(self.config[key])

        # If the key is in defaults; set the handler to the default state (but don't add to config)
        elif key in self.defaults:
            handler.setter(self.defaults[key])

        # If the key is not in defaults, set the config to match the handler
        else:
            self.config[key] = handler.getter()

    def add_handlers(self, keyhandlers):
        for key, handler in list(keyhandlers.items()):
            self.add_handler(key, handler)

    # JSON
    def json_dumps(self):
        return json.dumps(self.config)

    def json_loads(self, json):
        self.config = json.loads(json)

    def reset(self):
        """ 
            Reset the config manager to it's initialised state.
            
            This clears all values, unsets all defaults and removes all handlers, maps, and hooks.
        """
        self.config = {}
        self.handlers = {}
        self.defaults = {}
        self.maps = {}
        self.eventhooks = {}
