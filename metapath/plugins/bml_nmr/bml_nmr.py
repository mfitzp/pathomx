# -*- coding: utf-8 -*-
from plugins import ImportPlugin

# Import PyQt5 classes
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWebKit import *
from PyQt5.QtNetwork import *
from PyQt5.QtWidgets import *
from PyQt5.QtWebKitWidgets import *
from PyQt5.QtPrintSupport import *

import os, csv
import xml.etree.cElementTree as et
from collections import defaultdict

import numpy as np
import zipfile
import tempfile 

import ui, db, utils
from data import DataSet


class BMLNMRView( ui.DataView ):
    def __init__(self, plugin, parent, **kwargs):
        super(BMLNMRView, self).__init__(plugin, parent, **kwargs)
    
        self.data.add_output('Raw') # Add output slot
        self.data.add_output('PQN') # Add output slot
        self.data.add_output('TSA') # Add output slot
        
        fn = self.onImportData()
        
        self.t = self.addToolBar('Data Import')
        self.t.setIconSize( QSize(16,16) )

        self.table.setModel(self.data.o['Raw'].as_table)
        

        import_dataAction = QAction( QIcon( os.path.join(  utils.scriptdir, 'icons', 'disk--arrow.png' ) ), 'Import .zip output of BML-NMR\u2026', self.m)
        import_dataAction.setStatusTip('Import from BML-NMR FIMA output (.zip)')
        import_dataAction.triggered.connect(self.onImportData)
        self.t.addAction(import_dataAction)

    def onImportData(self):
        """ Open a data file"""
        #Qd.setFileMode(QFileDialog.Directory)
        filename, _ = QFileDialog.getOpenFileName(self.m, 'Open BML-NMR FIMA .zip output', None, "Compressed Files (*.zip)")
        if filename:
                        
            self.load_bml_zipfile( filename )

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
    def load_bml_zipfile(self, filename):

        self.setWorkspaceStatus('active')

        # Unzip into temporary folder
        folder = tempfile.mkdtemp() #os.path.join( QDir.tempPath(), 
        zf = zipfile.ZipFile( filename )
        zf.extractall( folder )
        f = os.listdir( folder )
        bml_job = f[0]
        
        fns = [
            ('samples_vs_concs_matrix.txt','Raw'),
            ('samples_vs_concs_matrix_tsanorm.txt','TSA'),
            ('samples_vs_concs_matrix_pqnnorm.txt','PQN'),
        ]
    
        # We have the data folder; import each of the complete datasets in turn
        # non, PQN, TSA and label appropriately

        for fn,l in fns:
            # Load the data file
            data_path = os.path.join( folder, bml_job, 'overall_result_outputs', fn )    
            
            self.load_bml_datafile( data_path, l, "%s (%s)" % (bml_job, l) )

        self.set_name( bml_job )

        self.setWorkspaceStatus('done')
        self.clearWorkspaceStatus()
        

    def load_bml_datafile( self, data_path, target, name):
        
        dso = DataSet()

        # Read in data for the graphing metabolite, with associated value (generate mean)
        reader = csv.reader( utils.nonull( open( data_path, 'rb') ), delimiter='\t', dialect='excel') 

        for row in reader:
            if row and row[0] == 'metabolite': # Look for the top row
                break
        else:
            return
        
        samples = row[1:-2] # Sample identities
        samples = [ sample[8:-1] for sample in samples]

        xdim = 0
        ydim = len(samples)
        
        raw_data = []
        metabolites = []
        
        for row in reader:
            xdim += 1
            metabolites.append( row[0] )

            raw_data.append( [float(i) for i in row[1:-2]] )

        dso = DataSet( size=(ydim, xdim) )
        dso.labels[1] = metabolites
                
        dso.data = np.array( raw_data ).T

        dso.name = name
        dso.description = 'Imported from FIMA (%s)' % name  
        
        self.data.put( target, dso )
        
class BMLNMR(ImportPlugin):

    def __init__(self, **kwargs):
        super(BMLNMR, self).__init__(**kwargs)
        self.register_app_launcher( self.app_launcher )

    def app_launcher(self):
        #self.load_data_file()
        self.instances.append( BMLNMRView( self, self.m ) )
