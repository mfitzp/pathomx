# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# Import PyQt5 classes
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWebKit import *
from PyQt5.QtNetwork import *
from PyQt5.QtWidgets import *
from PyQt5.QtWebKitWidgets import *
from PyQt5.QtPrintSupport import *


# Renderer for GPML as SVG
from gpml2svg import gpml2svg


from plugins import IdentificationPlugin

import os, sys, re, math

import ui, utils
from data import DataSet, DataDefinition




import csv


from collections import OrderedDict
from optparse import OptionParser
from poster.encode import multipart_encode

from poster.streaminghttp import register_openers
import urllib, urllib2, cookielib



# Dialog box for Metabohunter search options
class DialogMetabohunter(ui.genericDialog):

    
    #noise
    #thres
    #neighbourhood
    
    def __init__(self, parent=None, view=None, **kwargs):
        super(DialogMetabohunter, self).__init__(parent, **kwargs)        
        
        self.v = view
        self.m = view.m
        
        self.setWindowTitle("Set MetaboHunter parameters")

        self.lw_combos = {}
        for n, o in self.v.options.items():
            row = QVBoxLayout()
            cl = QLabel(n)
            cb = QComboBox()
            
            cb.addItems( o.keys() )
            row.addWidget(cl)
            row.addWidget(cb)
            self.lw_combos[ n ] = cb # For read out on exit

            current = self.v.config.get(n)
            cb.setCurrentText(current)

            self.layout.addLayout(row)
            
        #self.layout.addWidget(ctw)
            
        self.setMinimumSize( QSize(600,100) )
        self.layout.setSizeConstraint(QLayout.SetMinimumSize)
        
        # Build dialog layout
        self.dialogFinalise()
        
        
        

class MetaboHunterView( ui.DataView ):


    options = {
    'Metabotype': {
        'All':'All',
        'Drug':'Drug',
        'Food additive':'Food additive',
        'Mammalian':'Mammalian',
        'Microbial':'Microbial',
        'Plant':'Plant',
        'Synthetic/Industrial chemical':'Synthetic/Industrial chemical',
        },
    'Database Source': {
        'Human Metabolome Database (HMDB)':'HMDB',
        'Madison Metabolomics Consortium Database (MMCD)':'MMCD',
        },
    'Sample pH': {
        '10.00 - 10.99':'ph7',
        '9.00 - 9.99':'ph7',
        '8.00 - 8.99':'ph7',
        '7.00 - 7.99':'ph7',
        '6.00 - 6.99':'ph6',
        '5.00 - 5.99':'ph5',
        '4.00 - 4.99':'ph4',
        '3.00 - 3.99':'ph3',
    },
    'Solvent': {
        'All':'all',
        'Water':'water',
        'CDCl3':'cdcl3',
        'CD3OD':'5d3od',
        '5% DMSO':'5d30d',
    },
    'Frequency': {
        'All':'all',
        '600 MHz':'600',
        '500 MHz':'500',
        '400 MHz':'400',
    },
    'Method': {
        'MH1: Highest number of matched peaks':'HighestNumber',
        'MH2: Highest number of matched peaks with shift tolerance':'HighestNumberNeighbourhood',
        'MH3: Greedy selection of metabolites with disjoint peaks':'Greedy2',
        'MH4: Highest number of matched peaks with intensities':'HighestNumberHeights',
        'MH5: Greedy selection of metabolites with disjoint peaks and heights':'Greedy2Heights',
    },
    }

    def __init__(self, plugin, parent, **kwargs):
        super(MetaboHunterView, self).__init__(plugin, parent, **kwargs)

        #Define automatic mapping (settings will determine the route; allow manual tweaks later)
        
        self.addDataToolBar(default_pause_analysis=True)
        self.addFigureToolBar()
        
        self.data.add_input('input') # Add input slot        
        self.data.add_output('output')
        self.table.setModel(self.data.o['output'].as_table)
        
        t = self.getCreatedToolbar('MetaboHunter', 'metabohunter')
        metabohunterSetup = QAction( QIcon( os.path.join(  self.plugin.path, 'icon-16.png' ) ), 'Set up MetaboHunter \u2026', self.m)
        metabohunterSetup.setStatusTip('Set parameters for MetaboHunter matching')
        metabohunterSetup.triggered.connect(self.onMetaboHunterSettings)
        t.addAction(metabohunterSetup)
        
        self.config.set_defaults({
            'Metabotype': 'All',
            'Database Source': 'Human Metabolome Database (HMDB)',
            'Sample pH':'7.00 - 7.99',
            'Solvent': 'Water',
            'Frequency': 'All',
            'Method': 'MH2: Highest number of matched peaks with shift tolerance',
        })
        
        # Setup data consumer options
        self.data.consumer_defs.append( 
            DataDefinition('input', {
            'scales_t':     (None, ['float']),
            'entities_t':   (None, None), 
            })
        )
        
        self.data.source_updated.connect( self.autogenerate ) # Auto-regenerate if the source data is modified
        self.data.consume_any_of( self.m.datasets[::-1] ) # Try consume any dataset; work backwards

    def onMetaboHunterSettings(self):
        dialog = DialogMetabohunter(parent=self, view=self)
        ok = dialog.exec_()
        if ok:
            # Extract the settings and from the dialog
            for n, o in self.options.items():
                self.config.set(n, dialog.lw_combos[n].currentText() )

            self.autogenerate()            
      
        
    def generate(self):

        self.setWorkspaceStatus('active')
    
        dso = self.data.get('input')
        #dso = DataSet()

        parser = OptionParser()

        parser.add_option("--tolerance", dest="tolerance", default=0.1,
                          help="ppm +/- range for 'equivalent' peak")

        parser.add_option("--peak_threshold", dest="peak_threshold", default=0.01,
                          help="cutoff below which 'peaks' are ignored")

        parser.add_option("--hit_threshold", dest="hit_threshold", default=0.4,
                          help="minimum score for metabolite to count as hit ")

        (options, args) = parser.parse_args()

        ### GLOBAL VARIABLES ###
        samples = OrderedDict()
        ppm_master = list() # ppm masterlist
        ppm_cleaned = list() # ppm masterlist, no dups


        splits = dict() # Peak sets [full, class-split, loading-split, class & loading split]
        annotate = dict()

        remote_data = dict() # Container for references to metabolite data on remote server

        # Web service peak-list assignment (metabohunter)
        print("Sending peaklist to MetaboHunter...")

        opener = register_openers()
        opener.add_handler(urllib2.HTTPCookieProcessor(cookielib.CookieJar()))

        ### WAS BUILDING GENERIC PEAKLIST BY GETTING ALL SAMPLES WITH IT SET
        ### INTEGRATE THIS WITH LOADINGS SPLIT? CAN BUILD *AFTER* SPLITS FOR BETTER RESULTS
        ### OR USE CLASSIFICATION GROUPINGS TO SPLIT (MORE SENSIBLE?) - SEPARATE STEPS
    
        peaks_list = '\n'.join( [ ' '.join( [str(a), str(b)] ) for a,b in zip( dso.scales[1], dso.data[0,:] ) ]  )
        
        url = 'http://www.nrcbioinformatics.ca/metabohunter/post_handler.php'

        values = {#'file'          : open('metabid_peaklist.txt', 'rt'),
                  'posturl'       : 'upload_file.php',
                  'useall'        : 'yes',
                  'peaks_list'    : peaks_list,
                  'dbsource'      : self.options['Database Source'][ self.config.get('Database Source') ],
                  'metabotype'    : self.options['Metabotype'][ self.config.get('Metabotype') ],
                  'sampleph'      : self.options['Sample pH'][ self.config.get('Sample pH') ],
                  'solvent'       : self.options['Solvent'][ self.config.get('Solvent') ],
                  'freq'          : self.options['Frequency'][ self.config.get('Frequency') ],
                  'method'        : self.options['Method'][ self.config.get('Method') ],
                  'noise'         : '0',
                  'thres'         : options.hit_threshold,
                  'neighbourhood' : options.tolerance, #tolerance, # Use same tolerance as for shift
                  'submit'        : 'Find matches',
                 }

        self.setWorkspaceStatus('waiting')

        data = urllib.urlencode(values)
        request = urllib2.Request(url, data)

        try:
            response = urllib2.urlopen(request)
        except urllib2.HTTPError, e:
            print e
            return


        html = response.read()

        self.setWorkspaceStatus('active')

        m = re.search('name="hits" value="(.*?)\n(.*?)\n"', html, re.MULTILINE | re.DOTALL)
        remote_data['metabolite_table'] = m.group(2)

        m = re.search('name="sample_file" value="(.*?)"', html, re.MULTILINE | re.DOTALL)
        remote_data['sample_file'] = m.group(1)
        
        print("Received analysis from MetaboHunter, interpreting...")

        # Regexp out the matched peaks table from the hidden form field in response (easiest to parse)
        metabolites = OrderedDict()
        #hits = re.search('name="hits" value="(.*?)\n(.*?)\n"', html, re.MULTILINE | re.DOTALL)

        # Iterate line by line (skip first, header) building a table of the returned metabolites
        for row in remote_data['metabolite_table'].split('\n'):

            fields = row.split('\t') #split row on tabs
            m = re.match("(.*?) \((\d*?)/(\d*?)\)",fields[3])

            metabolites[ fields[1] ] = {
                'name': fields[2],
                'score': float( m.group(1) ),
                'peaks': "%d/%d" %( int(m.group(2)), int(m.group(3)) ),
                'taxnomic': fields[4],
                'rank': fields[0],
                }

        #writer.writerow( ['HMDBid','%','Score','Name','Rank','Taxonomic'] )

        print("Retrieving matched peaks to metabolite relationships...")

        values = {'hits'          : remote_data['metabolite_table'],
                  'sample_file'   : remote_data['sample_file'],
                  'matched_peaks_file'   : remote_data['sample_file'] + "_matched_spectra.txt",
                  'noise'         : '0',
         }

        self.setWorkspaceStatus('waiting')

        data = urllib.urlencode(values)

        url = 'http://www.nrcbioinformatics.ca/metabohunter/download_matched_peaks.php'
        request = urllib2.Request(url, data)

        try:
            response = urllib2.urlopen(request)
        except urllib2.HTTPError, e:
            print e
            return

        matched_peaks_text = response.read()
        self.setWorkspaceStatus('active')
        
        print("Extracting data...")

        # Need to do this in two steps, so they are in the correct order for output
        metabolite_peaks = dict()
        matched_peak_metabolites = dict()

        for row in matched_peaks_text.split('\n'):
            fields = row.split()
            if fields:
                # fields[0] contains the HMDBid plus a colon :(
                fields[0] = fields[0].rstrip(':')
                metabolite_peaks[ fields[0] ] = fields[1:]

        for metabolite in metabolites:
            if metabolite in metabolite_peaks:
                # Save metabolite for each peak
                for peak in metabolite_peaks[ metabolite ]:
                    #if peak in matched_peak_metabolites:
                    #    matched_peak_metabolites[ peak ].append(metabolite)
                    #else:
                    matched_peak_metabolites[ peak ] = metabolite
    
    
    
        # Assign metabolite names to labels (for subsequent entity lookup)
        # dso.import_data( dsi )
        # Returned peaks are at 2dp so we need to check if we have a nearish match
        for n,p in enumerate(dso.scales[1]):
            sp2 = str( round(p,2) )
            if sp2 in matched_peak_metabolites:
                hmdbid = matched_peak_metabolites[ sp2 ]
                dso.labels[1][n] = hmdbid
                # All in HMDBIDs; if we have it use the entity
                if hmdbid in self.m.db.unification['HMDB']:
                    dso.entities[1][n] = self.m.db.unification['HMDB'][ hmdbid ]

        # Now remove any data from the object that isn't assigned?
        #
        #

        self.setWorkspaceStatus('done')
        self.data.put('output', dso)
        self.render({})
        self.clearWorkspaceStatus()

        print("Done.")



class MetaboHunter(IdentificationPlugin):

    def __init__(self, **kwargs):
        super(MetaboHunter, self).__init__(**kwargs)
        #self.register_url_handler( self.id, self.url_handler )
        #self.register_menus( 'pathways', [
        #    {'title': u'&Load GPML pathway\u2026', 'action': self.onLoadGPMLPathway, 'status': 'Load a GPML pathway file'},
        #    {'title': u'&Load GPML pathway via WikiPathways\u2026', 'action': self.onLoadGPMLPathway, 'status': 'Load a GPML pathway from WikiPathways service'},        
        #] )
        self.register_app_launcher( self.app_launcher )
    
    # Create a new instance of the plugin viewer object to handle all behaviours
    def app_launcher(self):
        return MetaboHunterView( self, self.m )

