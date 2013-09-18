# -*- coding: utf-8 -*-
import os

from plugins import DataPlugin

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

class ImportDataView( ui.DataView ):
    def __init__(self, plugin, parent, **kwargs):
        super(ImportDataView, self).__init__(plugin, parent, **kwargs)
    
        self.data.addo('output') # Add output slot
        
        fn = self.onImportData()
        print self.data.o['output'].shape
        print len(self.data.o['output'].entities[1])
        print len(self.data.o['output'].labels[1])
        self.table.setModel(self.data.o['output'].as_table)
        
        self.t = self.addToolBar('Data Import')
        self.t.setIconSize( QSize(16,16) )

        import_dataAction = QAction( QIcon( os.path.join(  utils.scriptdir, 'icons', 'disk--arrow.png' ) ), 'Import from file\u2026', self.m)
        import_dataAction.setStatusTip('Import from a compatible file source')
        import_dataAction.triggered.connect(self.onImportData)
        self.t.addAction(import_dataAction)

    def onImportData(self):
        """ Open a data file"""
        filename, _ = QFileDialog.getOpenFileName(self.m, 'Open experimental metabolite data file', '')
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
        
    def load_peakml(self, filename):
    
        # Determine if we've got a csv or peakml file (extension)
        fn, fe = os.path.splitext(filename)
            '.peakml': self.load_peakml,
            
        if fe in formats.keys():
            print "Loading... %s" %fe
            self.setWorkspaceStatus('active')

        
            self.data.o['output'].empty()

            load_peakml(filename)
            
            self.data.o['output'].name = os.path.basename( filename )
            self.data.o['output'].description = 'Imported %s file' % fe  

            self.set_name( self.data.o['output'].name )
            
            self.setWorkspaceStatus('done')
            self.data.o['output'].refresh_consumers()
            self.clearWorkspaceStatus()
            
        else:
            print "Unsupported file format."
        
###### LOAD WRAPPERS; ANALYSE FILE TO LOAD WITH OTHER HANDLER


        def decode(s):
            s = base64.decodestring(s)
            # Each number stored as a 4-chr representation (ascii value, not character)
            l = []
            for i in xrange(0, len(s), 4):
                c = s[i:i+4]
                val = 0
                for n,v in enumerate(c):
                    val += ord(v) * 10**(3-n)
                l.append( str(val) )
            return l
        
        # Read data in from peakml format file
        xml = et.parse( filename )

        # Get sample ids, names and class groupings
        sets = xml.iterfind('header/sets/set')
        midclass = {}
        for set in sets:
            id = set.find('id').text
            mids = set.find('measurementids').text
            for mid in decode(mids):
                midclass[mid] = id
            self.classes.add(id)

        #meaurements = xml.iterfind('peakml/header/measurements/measurement')
        #samples = {}
        #for measurement in measurements:
        #    id = measurement.find('id').text
        #    label = measurement.find('label').text
        #    sampleid = measurement.find('sampleid').text
        #    samples[id] = {'label':label, 'sampleid':sampleid}
        
        # We have all the sample data now, parse the intensity and identity info
        peaksets = xml.iterfind('peaks/peak')
        metabolites = {}
        quantities = {}
        for peakset in peaksets:
            
            # Find metabolite identities
            annotations = peakset.iterfind('annotations/annotation')
            identities = False
            for annotation in annotations:
                if annotation.find('label').text == 'identification':
                    identities = annotation.find('value').text.split(', ')
                    break

            if identities:
                # PeakML supports multiple alternative metabolite identities,currently we don't so duplicate
                for identity in identities:
                    if not identity in self.quantities:
                        self.quantities[ identity ] = defaultdict(list)
                    self.metabolites.append(identity)
            
                # We have identities, now get intensities for the different samples            
                chromatograms = peakset.iterfind('peaks/peak') # Next level down
                quants = defaultdict(list)
                for chromatogram in chromatograms:
                    mid = chromatogram.find('measurementid').text
                    intensity = float( chromatogram.find('intensity').text )
                    
                    classid = midclass[mid]
                    quants[classid].append(intensity)

                for classid, q in quants.items():
                    for identity in identities:
                        self.quantities[ identity ][ classid ].extend( q )

        

class ImportText(DataPlugin):

    def __init__(self, **kwargs):
        super(ImportText, self).__init__(**kwargs)
        self.register_app_launcher( self.app_launcher )

    def app_launcher(self):
        #self.load_data_file()
        self.instances.append( ImportDataView( self, self.m ) )
