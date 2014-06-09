# -*- coding: utf-8 -*-
import os

import csv
import xml.etree.cElementTree as et
from collections import defaultdict

import numpy as np

import zipfile
import tempfile

import pathomx.utils as utils
import pathomx.ui as ui
import pathomx.db as db

from pathomx.plugins import ImportPlugin
from pathomx.data import DataSet

class ImportPRIDETool( ui.ImportDataApp ):

    import_filename_filter = "All compatible files (*.zip);;Zipped PRIDE data files (*.*);;All files (*.*)"
    import_description =  "Import experimental data from PRIDE experimental datasets"

    def __init__(self, **kwargs):
        super(ImportPRIDETool, self).__init__(**kwargs)

        self.data.add_output('output')  # Add output slot

        self.table.setModel(self.data.o['output'].as_table)

        self.finalise()

    def onFileChanged(self, file):
        self.load_datafile(file)

    def prerender(self, output=None):
        return {'View': {'dso': output}}
        
    def load_datafile(self, filename):

        # Unzip into temporary folder
        folder = tempfile.mkdtemp()
        zf = zipfile.ZipFile(filename)
        try:
            zf.extract('peptides.txt', folder)  
        except:
            return None

        datafile = os.path.join(folder, 'peptides.txt')

        dso = DataSet()

        fsize = os.path.getsize(datafile)
        # Read in data for the graphing metabolite, with associated value (generate mean)
        reader = csv.reader(open(datafile, 'r'), delimiter='\t', dialect='excel')
        
        # Get top row
        row = reader.next()

        # Get columns for protein identities; leading is the top-ranked use preferentially
        # else use the proteins col (should use all identities?)
        proteins_col = row.index('Proteins') if 'Proteins' in row else None
        lead_protein_col = row.index('Leading razor protein') if 'Leading razor protein' in row else None
    
        # Row labels for quants is give as Intensity followed by the class name
        # so find all cols with Intensity\s<something> headers and extract the labels + data
        labels = []
        labelsc = []
        for n, c in enumerate(row):
            if 'Intensity ' in c:
                # Quantification column
                labelsn = c.replace('Intensity ', '')
                labels.append( labelsn )
                labelsc.append( n )
    
        raw_data = []
        entities = []
        n = 0
        # Now get data    
        for row in reader:
        
            datar = [float(row[x]) for x in labelsc]
            raw_data.append( datar )
        
            entity = None
        
            # Identify protein
            if lead_protein_col:
                entity = db.dbm.get_via_synonym( row[ lead_protein_col ] )
        
            if entity == None and proteins_col:
                entity = db.dbm.get_via_synonym( row[ proteins_col ].split(';')[0] )
        
            entities.append( entity )
        
            n += 1
        
            if n % 100 == 0:
                try:
                    # FIXME: There should be a way around this
                    # This fails in Python 3 with
                    # 'telling position disabled by next() call'
                    self.progress.emit(float(f.tell()) / fsize)
                except:
                    pass            

        xdim = n
        ydim = len(labels)

        dso = DataSet(size=(ydim, xdim))
        dso.labels[0] = labels
        dso.entities[1] = entities

        dso.data = np.array(raw_data).T

        dso.name = filename
        dso.description = 'Imported from PRIDE (%s)' % filename

        self.change_name.emit(filename)

        return {'output':dso}
            

        

class ImportPRIDE(ImportPlugin):

    def __init__(self, **kwargs):
        super(ImportPRIDE, self).__init__(**kwargs)
        self.register_app_launcher( ImportPRIDETool )

    

