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

    def set(self, key, value, trigger_update=True):
            if key in self.config and self.config[key] == value:
                return False # Not updating

            # Set value    
            self.config[key] = value

            if key in self.handlers:
                # Trigger handler to update the view
                getter = getattr(self, '_get_%s' % self.handlers[key].__class__.__name__, False)
                setter = getattr(self, '_set_%s' % self.handlers[key].__class__.__name__, False)
            
                if setter and getter( self.handlers[key] ) != self.config[key]:
                    setter( self.handlers[key], self.config[key] )
    
            # Trigger update notification
            if trigger_update:
                self.updated.emit()

            return True
        
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
        self.config = []
        self.set_many( keyvalues )

    def set_many(self, keyvalues, trigger_update=True):
        has_updated = False
        for k,v in keyvalues.items():
            u = self.set(k, v, trigger_update=False)
            print 'Workflow config; setting %s to %s' % (k,v)
            has_updated = has_updated or u
        
        if has_updated and trigger_update:
            self.updated.emit()             


    # HANDLERS

    # Handlers are UI elements (combo, select, checkboxes) that automatically update
    # and updated from the config manager. Allows instantaneous updating on config
    # changes and ensuring that elements remain in sync
        
    def add_handler(self, key, handler):
        self.handlers[key] = handler
        print "Add handler %s for %s" % ( handler.__class__.__name__, key )
        fn = getattr(self, '_event_%s' % handler.__class__.__name__, False)
        fn( handler ).connect( lambda x: self.set(key, x) )
        
        # Keep handler and data consistent
        if key not in self.config:
            # If the key is in defaults; set the handler to the default state (but don't add to config)
            if key in self.defaults:
                fn = getattr(self, '_set_%s' % handler.__class__.__name__, False)
                fn( handler, self.defaults[key] )
            
            # If the key is not in defaults, set the config to match the handler
            else:
                fn = getattr(self, '_get_%s' % handler.__class__.__name__, False)
                self.config[key] = fn( handler )
            
    def add_handlers(self, keyhandlers):
        for key, handler in keyhandlers.items():
            self.add_handler( key, handler )
    
    # QComboBox
    
    def _get_QComboBox(self, o):
        return o.currentText()

    def _set_QComboBox(self, o, v):
        print 'setting via combo %s %s' %(o,v)
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
        
    # QAction
    
    def _get_QAction(self, o):
        print 'o', o.isChecked()
        return o.isChecked()

    def _set_QAction(self, o, v):
        print 'o', o.isChecked()
        o.setChecked(v)

    def _event_QAction(self, o):
        return o.toggled
        
    # QSpinBox
    
    def _get_QSpinBox(self, o):
        return o.value()

    def _set_QSpinBox(self, o, v):
        o.setValue(v)

    def _event_QSpinBox(self, o):
        return o.valueChanged        
        
    # QDoubleSpinBox
    
    def _get_QDoubleSpinBox(self, o):
        return o.value()

    def _set_QDoubleSpinBox(self, o, v):
        o.setValue(v)

    def _event_QDoubleSpinBox(self, o):
        return o.valueChanged                
        
    # JSON
    
    def json_dumps(self):
        return json.dumps( self.config ) 
    
    def json_loads(self, json):
        self.config = json.loads( json )
        
    def reset(self):
        self.config = {}
        self.handlers = {}
        self.defaults = {}
    