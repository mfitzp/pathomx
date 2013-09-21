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

class ImportTextView( ui.ImportDataView ):

    import_filename_filter = "All compatible files (*.csv *.txt *.tsv);;Comma Separated Values (*.csv);;Plain Text Files (*.txt);;Tab Separated Values (*.tsv);;All files (*.*)"
    import_description =  "Open experimental data from text file data file"

    def __init__(self, plugin, parent, **kwargs):
        super(ImportTextView, self).__init__(plugin, parent, **kwargs)

       
    # Data file import handlers (#FIXME probably shouldn't be here)
        
    def load_datafile(self, filename):
    
        # Determine if we've got a csv or peakml file (extension)
        fn, fe = os.path.splitext(filename)
        formats = { # Run specific loading function for different source data types
                '.csv': self.load_csv,
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
            self.render({})
            
            self.setWorkspaceStatus('done')
            
            
            self.data.o['output'].refresh_consumers()
            self.clearWorkspaceStatus()
            
        else:
            print "Unsupported file format."
        
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


    def load_txt(self, filename):
        # Wrapper function to allow loading from alternative format txt files
        # Currently only supports Metabolights format files
        reader = csv.reader( open( filename, 'rU'), delimiter='\t', dialect='excel')
        hrow = reader.next() # Get top row
        
        if hrow[0].lower() == 'database_identifier': # M format metabolights
            return self.load_metabolights(filename)

        if hrow[0].lower() == 'identifier': # A format metabolights
            return self.load_metabolights(filename, id_col=0, name_col=2, data_col=19)


###### LOAD HANDLERS

    def load_csv_C(self, filename): # Load from csv with experiments in COLUMNS, metabolites in ROWS
        
        # Read in data for the graphing metabolite, with associated value (generate mean)
        reader = csv.reader( open( filename, 'rU'), delimiter=',', dialect='excel')
        
        hrow = reader.next() # Discard top row (sample no's)
        hrow = reader.next() # Get 2nd row
        classes = hrow[1:]
        metabolites = []
        
        
        for row in reader:
            metabolite = row[0]
            metabolites.append( row[0] )
            quantities[ metabolite ] = defaultdict(list)

            for n, c in enumerate(row[1:]):
                if self.classes[n] != '.':
                    try:
                        c = float(c)
                    except:
                        c = 0
                    
                    quantities[metabolite][ self.classes[n] ].append( c )
                    #self.statistics['ymin'] = min( self.statistics['ymin'], c )
                    #self.statistics['ymax'] = max( self.statistics['ymax'], c )

        #self.statistics['excluded'] = self.classes.count('.')
        classes = set( [c for c in self.classes if c != '.' ] )
        
                
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
                for i in row[2:]: # in self.metabolites:
                    data_row.append( float(i) )
                    
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
        #dso = data.DataSet(size=(xdim, ydim) ) #self.add_data('imported_data', data.DataSet(self) )
        self.data.o['output'].empty(size=(ydim, xdim))
        self.data.o['output'].labels[1] = metabolites
        
        scales = []
        for m in metabolites:
            try:
                scales.append( float(m) )
            except:
                scales.append( None )
                
        self.data.o['output'].scales[1] = scales
        self.data.o['output'].labels[0] = samples
        self.data.o['output'].classes[0] = classes
        self.data.o['output'].data = np.array( raw_data )
   
        

class ImportText(DataPlugin):

    def __init__(self, **kwargs):
        super(ImportText, self).__init__(**kwargs)
        self.register_app_launcher( self.app_launcher )

    def app_launcher(self):
        #self.load_data_file()
        self.instances.append( ImportTextView( self, self.m ) )
