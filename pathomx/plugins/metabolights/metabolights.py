# -*- coding: utf-8 -*-
import os

import csv
import xml.etree.cElementTree as et
from collections import defaultdict

import numpy as np

import pathomx.utils as utils
import pathomx.ui as ui
import pathomx.db as db

from pathomx.plugins import ImportPlugin
from pathomx.data import DataSet

class ImportMetabolightsApp( ui.ImportDataApp ):

    import_filename_filter = "All compatible files (*.csv);;Comma Separated Values (*.csv);;All files (*.*)"
    import_description =  "Open experimental data from Metabolights experimental datasets"

    # Data file import handlers (#FIXME probably shouldn't be here)
        
    def load_datafile(self, filename):
        dso=self.load_metabolights(filename)
        dso.name = os.path.basename( filename )
        self.set_name( dso.name )
        dso.description = 'Imported %s file' % filename  

        return {'output':dso}            
            
        
        
    def load_metabolights(self, filename, id_col=0, name_col=4, data_col=18): # Load from csv with experiments in COLUMNS, metabolites in ROWS
        print("Loading Metabolights...")
        
        #sample	1	2	3	4
        #class	ADG10003u_007	ADG10003u_008	ADG10003u_009	ADG10003u_010   ADG19007u_192
        #2-oxoisovalerate	0.3841	0.44603	0.45971	0.40812
        reader = csv.reader( open( filename, 'rU'), delimiter=',', dialect='excel')
    
        # Sample identities from top row ( sample labels )
        hrow = next(reader)
        sample_ids = hrow[1:]    

        # Sample classes from second row; crop off after u_
        hrow = next(reader)
        classes = hrow[1:]    
        classes = [ c.split('u_')[0] for c in classes]

        metabolites = []
        metabolite_data = []
        # Read in metabolite data n.b. can have >1 entry / metabolite so need to allow for this
        for row in reader:
            if row[0] != '': # Skip empty rows
                metabolites.append( row[0] )
                metabolite_data.append( row[1:] )
            
        ydim = len( classes )
        xdim = len( metabolites )
        
        dso = DataSet( size=(ydim, xdim) )

        dso.labels[0] = sample_ids
        dso.classes[0] = classes 

        dso.labels[1] = metabolites

        for n,md in enumerate(metabolite_data):
            dso.data[:,n] = np.array(md)
            
        return dso
        

class ImportMetabolights(ImportPlugin):

    def __init__(self, **kwargs):
        super(ImportMetabolights, self).__init__(**kwargs)
        self.register_app_launcher( ImportMetabolightsApp )

    

