# -*- coding: utf-8 -*-
# Experimental data manager
# Loads a csv data file and extracts key information into usable structures for analysis

# Import PyQt5 classes
from PyQt5.QtGui import *
from PyQt5.QtCore import *
#from PyQt5.QtWebKit import *
from PyQt5.QtNetwork import *
from PyQt5.QtWidgets import *
#from PyQt5.QtWebKitWidgets import *
from PyQt5.QtPrintSupport import *

import os, sys, re, base64
import numpy as np

from collections import defaultdict
import operator, json

from copy import copy, deepcopy

# ConfigManager handles configuration for a given appview
# Supports default values, change signals, export/import from file (for workspace saving)
class ConfigManager( QObject ):

    # Signals
    updated = pyqtSignal() #Triggered anytime configuration is changed (refresh)


    def __init__(self, defaults={}, *args, **kwargs):
        super(ConfigManager, self).__init__( *args, **kwargs)

        self.reset()
        self.defaults = defaults # Same mapping as above, used when config not set

    # Get config
    def get(self, key):
        if key in self.config:
            return self.config[key]
        elif key in self.defaults:
            return self.defaults[key]
        else:
            return None

    def set(self, key, value):
        # Set value    
        self.config[key] = value
        
        if key in self.handlers:
            # Trigger handler to update the view
            fn = getattr(self, '_set_%s' % self.config[key].__class__.__name__, False)
            if fn: # We have setter
                fn( self.config[key], value )
        
        # Trigger update notification
        self.updated.emit()
        
    # Defaults are used in absence of a set value (use for base settings)    
    def set_default(self, key, value):
        self.defaults[key] = value
        self.updated.emit()
        
    def set_defaults(self, keyvalues):
        for key, value in keyvalues.items():
            self.defaults[key] = value
            
        # Updating the defaults may update the config (if anything without a config value
        # is set by it; should check)
        self.updated.emit()
            
    # Completely replace current config (wipe all other settings)
            
    def replace(self, keyvalues):
        self.config = keyvalues

    # HANDLERS

    # Handlers are UI elements (combo, select, checkboxes) that automatically update
    # and updated from the config manager. Allows instantaneous updating on config
    # changes and ensuring that elements remain in sync
        
    def add_handler(self, key, handler):
        self.handlers[key] = handler
        fn = getattr(self, '_event_%s' % handler.__class__.__name__, False)
        fn( handler ).connect( lambda x: self.set(key, x) )
        
        if key not in self.config:
            fn = getattr(self, '_get_%s' % handler.__class__.__name__, False)
            self.config[key] = fn( handler )

    def add_handlers(self, keyhandlers):
        for key, handler in keyhandlers.items():
            self.add_handler( key, handler )
    
    # QComboBox
    
    def _get_QComboBox(self, o):
        return o.currentText()

    def _set_QComboBox(self, o, v):
        o.setCurrentText(v)

    def _event_QComboBox(self, o):
        return o.currentTextChanged

    # QCheckBox
    
    def _get_QCheckBox(self, o):
        return o.isChecked()

    def _set_QCheckBox(self, o, v):
        o.setChecked(v)

    def _event_QCheckBox(self, o):
        return o.stateChanged
        
    # JSON
    
    def json_dumps(self):
        return json.dumps( self.config ) 
    
    def json_loads(self, json):
        self.config = json.loads( json )
        
    def reset(self):
        self.config = {}
        self.handlers = {}
        self.defaults = {}
    