# -*- coding: utf-8 -*-
import os

from plugins import ImportPlugin

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

import ui, db, threads
from data import DataSet


class ImportTextView( ui.ImportDataView ):

    import_filename_filter = "All compatible files (*.csv *.txt *.tsv);;Comma Separated Values (*.csv);;Plain Text Files (*.txt);;Tab Separated Values (*.tsv);;All files (*.*)"
    import_description =  "Open experimental data from text file data file"

    def __init__(self, plugin, parent, auto_consume_data=True, **kwargs):
        super(ImportTextView, self).__init__(plugin, parent, **kwargs)

       
    # Data file import handlers (#FIXME probably shouldn't be here)
    def load_datafile(self, filename):
        self.worker = threads.Worker(self._load_datafile, filename)
        self.start_worker_thread(self.worker)
            
    def generated(self,dso):
        self.data.put('output',dso) 
        self.render({})
        
    def _load_datafile(self, filename):
    
        # Determine if we've got a csv or peakml file (extension)
        fn, fe = os.path.splitext(filename)
        formats = { # Run specific loading function for different source data types
                '.csv': self.load_csv,
            }
            
        if fe in formats.keys():
            print "Loading... %s" %fe

            dso=formats[fe](filename)


            dso.name = os.path.basename( filename )
            self.set_name( dso.name )
            dso.description = 'Imported %s file' % fe  

            return {'dso':dso}
            
        else:
            print "Unsupported file format."
            return {'dso':False}
        
###### LOAD WRAPPERS; ANALYSE FILE TO LOAD WITH OTHER HANDLER

    def load_csv(self, filename):

        # Wrapper function to allow loading from alternative format CSV files
        # Legacy is experiments in ROWS, limited number by Excel so also support experiments in COLUMNS
        reader = csv.reader( open( filename, 'rU'), delimiter=',', dialect='excel')
        hrow = reader.next() # Get top row
        
        if hrow[0].lower() == 'sample':
            if hrow[1].lower() == 'class':
                return self.load_csv_R(filename)
            else:
                return self.load_csv_C(filename)


###### LOAD HANDLERS

    def load_csv_C(self, filename): # Load from csv with experiments in COLUMNS, metabolites in ROWS
        # Read in data for the graphing metabolite, with associated value (generate mean)
        reader = csv.reader( open( filename, 'rU'), delimiter=',', dialect='excel')
        
        hrow = reader.next() # Discard top row (sample no's)
        samples = hrow[1:]

        hrow = reader.next() # Get 2nd row
        classesa = hrow[1:]
        classes = [c for c in classesa if c != '.' ]

        metabolites = []
        
        data = np.zeros( shape=(len(classes), 0) )
        
        for n,row in enumerate(reader):
            metabolite = row[0]
            metabolites.append( row[0] )
            quants = []
            for n, c in enumerate(row[1:]):
                if classesa[n] != '.':
                    try:
                        c = float(c)
                    except:
                        c = 0
                    quants.append(c)
            # Add the data to the data array; transposed
            data = np.hstack( [data, np.reshape( np.array(quants), newshape=(len(quants),1) ) ] )
        
        xdim = len( quants )
        ydim = len( classes )

        # Build dataset object        
        dso = DataSet( size=(xdim, ydim) ) #self.add_data('imported_data', DataSetself) )
        dso.empty(size=(ydim, xdim))
        dso.labels[1] = metabolites
        
        scales = []
        mlabels = []
        for m in metabolites:
            try:
                scales.append( float(m) )
                mlabels.append( None )
            except:
                scales.append( None )
                mlabels.append( m )
                
        dso.labels[0] = samples
        dso.classes[0] = classes
        dso.entities[0] = [None] * len(samples)

        dso.scales[1] = scales
        dso.labels[1] = mlabels
        dso.entities[1] = [None] * len(scales)

        dso.data = data
   
        return dso
                
    def load_csv_R(self, filename): # Load from csv with experiments in ROWS, metabolites in COLUMNS
        # Read in data for the graphing metabolite, with associated value (generate mean)
        reader = csv.reader( open( filename, 'rU'), delimiter=',', dialect='excel')
        
        hrow = reader.next() # Get top row
        metabolites = hrow[2:]
        ydim = 0
        xdim = len(metabolites)
        
        samples = []
        classes = []
        raw_data = []

        # Build quants table for metabolite classes
        #for metabolite in self.metabolites:
        #    quantities[ metabolite ] = defaultdict(list)
        
        for row in reader:
            ydim += 1
            if row[1] != '.': # Skip excluded classes # row[1] = Class
                samples.append( row[0] )
                classes.append( row[1] )  
                data_row = []
                for c in row[2:]: # in self.metabolites:
                    try:
                        c = float(c)
                    except:
                        c = 0
                    data_row.append( c )
                    
                raw_data.append( data_row ) 
                    #metabolite_column = hrow.index( metabolite )   
                    #if row[ metabolite_column ]:
                    #    data_row.append(
                    #    quantities[metabolite][ row[1] ].append( float(row[ metabolite_column ]) )
                        #self.statistics['ymin'] = min( self.statistics['ymin'], float(row[ metabolite_column ]) )
                        #self.statistics['ymax'] = max( self.statistics['ymax'], float(row[ metabolite_column ]) )
                    #else:
                    #    quantities[metabolite][ row[1] ].append( 0 )
            else:
                pass
                #self.statistics['excluded'] += 1

        # Build dataset object        
        dso = DataSet( size=(xdim, ydim) ) #self.add_data('imported_data', DataSetself) )
        dso.empty(size=(ydim, xdim))
        #dso.labels[1] = metabolites
        
        scales = []
        mlabels = []
        for m in metabolites:
            try:
                scales.append( float(m) )
                mlabels.append( None )
            except:
                scales.append( None )
                mlabels.append( m )
                
        dso.labels[0] = samples
        dso.classes[0] = classes
        dso.entities[0] = [None] * len(samples)

        dso.scales[1] = scales
        dso.labels[1] = mlabels
        dso.entities[1] = [None] * len(scales)

        dso.data = np.array( raw_data )
   
        return dso
        

class ImportText(ImportPlugin):

    def __init__(self, **kwargs):
        super(ImportText, self).__init__(**kwargs)
        self.register_app_launcher( self.app_launcher )

    def app_launcher(self, **kwargs):
        return ImportTextView( self, self.m, **kwargs )
