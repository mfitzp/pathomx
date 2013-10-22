# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from plugins import ImportPlugin
#import nmrglue as ng

# Import PyQt5 classes
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWebKit import *
from PyQt5.QtNetwork import *
from PyQt5.QtWidgets import *
from PyQt5.QtWebKitWidgets import *
from PyQt5.QtPrintSupport import *

import csv, os, pprint
import xml.etree.cElementTree as et
from collections import defaultdict

import numpy as np

import ui, db, utils
from data import DataSet

import nmrglue as ng

class NMRGlueView( ui.DataView ):
    def __init__(self, plugin, parent, **kwargs):
        super(NMRGlueView, self).__init__(plugin, parent, **kwargs)
    
        self.data.add_output('output') # Add output slot
        self.table.setModel(self.data.o['output'].as_table)
        
        t = self.getCreatedToolbar('NMR Import','nmr-import')

        import_dataAction = QAction( QIcon( os.path.join(  self.plugin.path, 'bruker.png' ) ), 'Import spectra from Bruker spectra\u2026', self.m)
        import_dataAction.setStatusTip('Import spectra from Bruker format')
        import_dataAction.triggered.connect(self.onImportBruker)
        t.addAction(import_dataAction)

        fn = self.onImportBruker()


    def onImportBruker(self):
        """ Open a data file"""
        Qd = QFileDialog()
        Qd.setFileMode(QFileDialog.Directory)
        Qd.setOption(QFileDialog.ShowDirsOnly)
        
        folder = Qd.getExistingDirectory(self, 'Open parent folder for your Bruker NMR experiments')
        if folder:
            # We should have a folder name; so find all files named fid underneath it (together with path)
            # Extract the path, and the parent folder name (for sample label)
            nmr_data = []
            sample_labels = []
            _ppm_real_scan_folder = False
            for r,d,files in os.walk( folder ):
                if 'fid' in files:
                    scan = os.path.basename(r)
                    print 'Read Bruker:',r
                    if scan == '99999' or scan == '9999': # Dummy Bruker thing
                        continue
                    # The following is a hack; need some interface for choosing between processed/raw data
                    # and for various formats of NMR data input- but simple
                    dic, data = self.load_bruker( r )
                    
                    if data is not None:
                        label = scan
                        #if 'AUTOPOS' in dic['acqus']:
                        #    label = label + " %s" % dic['acqus']['AUTOPOS']
                            
                        sample_labels.append( label )
                        nmr_data.append( data  )
                        _ppm_real_scan_folder = r
                        
            # Generate the ppm for these spectra
            # read in the bruker formatted data// use latest
            dic, data_unp = ng.bruker.read( _ppm_real_scan_folder )
            # Calculate ppms
            # SW total ppm 11.9877
            # SW_h total Hz 7194.244
            # SF01 Hz of 0ppm 600
            # TD number of data points 32768
            
            # Offset (not provided but we have:
            # O1 Hz offset (shift) of spectra 2822.5 centre!
            # BF ? 600Mhz
            # O1/BF = centre of the spectra
            # OFFSET = (SW/2) - (O1/BF)
            
            # What we need to calculate is start, end, increment
            offset = ( float(dic['acqus']['SW'])/2 ) - ( float(dic['acqus']['O1'])/float(dic['acqus']['BF1']) )
            start = float(dic['acqus']['SW'])-offset
            end = -offset
            step = float(dic['acqus']['SW'])/32768
            
            nmr_ppms = np.arange(start, end, -step)[:32768]
            experiment_name = '%s (%s)' % ( dic['acqus']['EXP'], folder) 
        
            # We now have a list of ft'd Bruker fids; run them into a data object                
            dso = self.process_data_to_dso(nmr_data, nmr_ppms, sample_labels, experiment_name )
            self.set_name( dso.name )
            self.data.put('output',dso)
            
            self.render({})
            
        return False
        

    def process_data_to_dso(self, nmr_data, nmr_ppms, sample_labels, experiment_name):
        
        print "Processing spectra to dso..."
        sample_n = len(sample_labels)
        ppm_n = len(nmr_ppms)

        dso = DataSet( size=(sample_n, ppm_n) )

        for n, nd in enumerate(nmr_data):
            print "Spectra %s" % sample_labels[n]
            dso.data[n, :] = nd
            dso.labels[0][n] = sample_labels[n]

        dso.labels[1] = [str(ppm) for ppm in nmr_ppms]
        dso.scales[1] = [float(ppm) for ppm in nmr_ppms]
        dso.name = experiment_name
        
        return dso
        

    def load_bruker(self, fn):

        try:
            print "Reading %s" % fn
            # read in the bruker formatted data
            dic, data = ng.bruker.read(fn)
        except:
            print "...fail"
            return None, None
        else:
            # remove the digital filter
            data = ng.bruker.remove_digital_filter(dic, data)

            # process the spectrum
            data = ng.proc_base.zf_size(data, 32768)    # zero fill to 32768 points
            data = ng.process.proc_bl.sol_boxcar(data, w=16, mode='same') # Solvent removal
            data = ng.proc_base.fft(data)               # Fourier transform
            data = ng.proc_base.ps(data, p0=75, p1=-10)      # phase correction
            data = ng.proc_base.di(data)                # discard the imaginaries
            data = ng.proc_base.rev(data)               # reverse the data
            
            # This should be in a processing plugin?
            data = ng.process.proc_bl.med(data, mw=24, sf=16, sigma=5.0) # Baseline correction
            data = data / 10000000.
            return dic, data
        
class NMRGlue(ImportPlugin):

    def __init__(self, **kwargs):
        super(NMRGlue, self).__init__(**kwargs)
        self.register_app_launcher( self.app_launcher )

    def app_launcher(self):
        #self.load_data_file()
        self.instances.append( NMRGlueView( self, self.m ) )
