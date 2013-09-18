# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from plugins import DataPlugin
#import nmrglue as ng

# Import PyQt5 classes
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWebKit import *
from PyQt5.QtNetwork import *
from PyQt5.QtWidgets import *
from PyQt5.QtWebKitWidgets import *
from PyQt5.QtPrintSupport import *

import utils
import csv
import xml.etree.cElementTree as et
from collections import defaultdict

import numpy as np

import data, ui, db

class NMRGlueView( ui.DataView ):
    def __init__(self, plugin, parent, **kwargs):
        super(NMRGlueView, self).__init__(plugin, parent, **kwargs)
    
        self.data.addo('output') # Add output slot
        
        fn = self.onImportData()
        self.table.setModel(self.data.o['output'].as_table)
        
        self.t = self.w.addToolBar('Data Import')
        self.t.setIconSize( QSize(16,16) )

        import_dataAction = QAction( QIcon( os.path.join(  utils.scriptdir, 'icons', 'disk--arrow.png' ) ), 'Import directory of NMR data\u2026', self.m)
        import_dataAction.setStatusTip('Import from a number of NMR formats')
        import_dataAction.triggered.connect(self.onImportData)
        self.t.addAction(import_dataAction)

    def onImportData(self):
        """ Open a data file"""
        Qd = QFileDialog
        Qd.setFileMode(QFileDialog.Directory)
        filename, _ = Qd.getOpenFileName(self.m, 'Open experimental metabolite data file', '')
        if filename:

            self.load_datafile( filename )

            self.file_watcher = QFileSystemWatcher()            
            self.file_watcher.fileChanged.connect( self.onFileChanged )
            self.file_watcher.addPath( filename )

            self.render({})

            #self.data.o['imported_data'].as_filtered(classes=['H'])
            
            #self.m.data.translate(self.m.db)
            self.workspace_item.setText(0, os.path.basename(filename))
            
        return False
        
    def onFileChanged(self, file):
        self.load_datafile( file )




       
    # Data file import handlers (#FIXME probably shouldn't be here)
        
    def load_datafile(self, filename):
    
        # Determine if we've got a csv or peakml file (extension)
        fn, fe = os.path.splitext(filename)
        formats = { # Run specific loading function for different source data types
                '.csv': self.load_csv,
                '.peakml': self.load_peakml,
                '': self.load_txt,
            }
            
        if fe in formats.keys():
            print "Loading... %s" %fe
            self.setWorkspaceStatus('active')

        
            self.data.o['output'].empty()

            formats[fe](filename)
            
            self.data.o['output'].name = os.path.basename( filename )
            self.data.o['output'].description = 'Imported %s file' % fe  

            self.set_name( self.data.o['output'].name )
            
            self.setWorkspaceStatus('done')
            self.data.o['output'].refresh_consumers()
            self.clearWorkspaceStatus()
            
        else:
            print "Unsupported file format."
        




class NMRGlue(DataPlugin):

    def __init__(self, **kwargs):
        super(NMRGlue, self).__init__(**kwargs)
        self.register_app_launcher( self.app_launcher )

    def app_launcher(self):
        #self.load_data_file()
        self.instances.append( NMRGlueView( self, self.m ) )
