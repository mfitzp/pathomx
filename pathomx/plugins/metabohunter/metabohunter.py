# -*- coding: utf-8 -*-


# Renderer for GPML as SVG
from gpml2svg import gpml2svg

import os
import sys
import re
import math
import logging

import pathomx.ui as ui
import pathomx.utils as utils
import pathomx.threads as threads

from pathomx.plugins import IdentificationPlugin
from pathomx.data import DataSet, DataDefinition
from pathomx.views import MplSpectraView
from pathomx.qt import *

from collections import OrderedDict

import csv
import poster
#import urllib, urllib2, cookielib
import requests


# Dialog box for Metabohunter search options
class MetaboHunterConfigPanel(ui.ConfigPanel):

    options = {
    'Metabotype': {
        'All': 'All',
        'Drug': 'Drug',
        'Food additive': 'Food additive',
        'Mammalian': 'Mammalian',
        'Microbial': 'Microbial',
        'Plant': 'Plant',
        'Synthetic/Industrial chemical': 'Synthetic/Industrial chemical',
        },
    'Database Source': {
        'Human Metabolome Database (HMDB)': 'HMDB',
        'Madison Metabolomics Consortium Database (MMCD)': 'MMCD',
        },
    'Sample pH': {
        '10.00 - 10.99': 'ph7',
        '7.00 - 9.99': 'ph7',
        '6.00 - 6.99': 'ph6',
        '5.00 - 5.99': 'ph5',
        '4.00 - 4.99': 'ph4',
        '3.00 - 3.99': 'ph3',
    },
    'Solvent': {
        'All': 'all',
        'Water': 'water',
        'CDCl3': 'cdcl3',
        'CD3OD': '5d3od',
        '5% DMSO': '5d30d',
    },
    'Frequency': {
        'All': 'all',
        '600 MHz': '600',
        '500 MHz': '500',
        '400 MHz': '400',
    },
    'Method': {
        'MH1: Highest number of matched peaks': 'HighestNumber',
        'MH2: Highest number of matched peaks with shift tolerance': 'HighestNumberNeighbourhood',
        'MH3: Greedy selection of metabolites with disjoint peaks': 'Greedy2',
        'MH4: Highest number of matched peaks with intensities': 'HighestNumberHeights',
        'MH5: Greedy selection of metabolites with disjoint peaks and heights': 'Greedy2Heights',
    },
    }

    def __init__(self, *args, **kwargs):
        super(MetaboHunterConfigPanel, self).__init__(*args, **kwargs)

        self.lw_combos = {}

        for o in ['Metabotype', 'Database Source', 'Sample pH', 'Solvent', 'Frequency', 'Method']:
            row = QVBoxLayout()
            cl = QLabel(o)
            cb = QComboBox()

            cb.addItems(list(self.options[o].keys()))
            row.addWidget(cl)
            row.addWidget(cb)
            self.config.add_handler(o, cb, self.options[o])

            self.layout.addLayout(row)

        row = QGridLayout()
        self.lw_spin = {}
        for n, o in enumerate(['Noise Threshold', 'Confidence Threshold', 'Tolerance']):
            cl = QLabel(o)
            cb = QDoubleSpinBox()
            cb.setDecimals(2)
            cb.setRange(0, 0.5)
            cb.setSingleStep(0.01)
            cb.setValue(float(self.config.get(o)))
            row.addWidget(cl, 0, n)
            row.addWidget(cb, 1, n)

            self.config.add_handler(o, cb)

        self.layout.addLayout(row)

        self.finalise()


class MetaboHunterApp(ui.DataApp):

    def __init__(self, **kwargs):
        super(MetaboHunterApp, self).__init__(**kwargs)
        #Define automatic mapping (settings will determine the route; allow manual tweaks later)

        self.addDataToolBar(default_pause_analysis=True)
        self.addFigureToolBar()

        self.data.add_input('input')  # Add input slot
        self.data.add_output('output')
        self.table.setModel(self.data.o['output'].as_table)

        self.views.addView(MplSpectraView(self), 'View')

        self.config.set_defaults({
            'Metabotype': 'All',
            'Database Source': 'HMDB',
            'Sample pH': 'ph7',
            'Solvent': 'water',
            'Frequency': 'all',
            'Method': 'HighestNumberNeighbourhood',
            'Noise Threshold': 0.0,
            'Confidence Threshold': 0.4,
            'Tolerance': 0.1,
        })

        self.addConfigPanel(MetaboHunterConfigPanel, 'MetaboHunter')

        # Setup data consumer options
        self.data.consumer_defs.append(
            DataDefinition('input', {
            'scales_t': (None, ['float']),
            'entities_t': (None, None),
            })
        )

        self.finalise()
    #def onMetaboHunterSettings(self):
    #    dialog = DialogMetabohunter(parent=self, view=self)
    #    ok = dialog.exec_()
    #    if ok:
    #        # Extract the settings and from the dialog
    #        for n, o in self.options.items():
    #            self.config.set(n, dialog.lw_combos[n].currentText() )
    #
    #        for n in ['Noise Threshold','Hit Threshold','Tolerance']:
    #            self.config.set(n, dialog.lw_spin[n].value() )#
    #
    #           self.autogenerate()

    def generate(self, input=None):
        return {'output': self.metabohunter(dso=input)}

    def metabohunter(self, dso):

        ### GLOBAL VARIABLES ###
        samples = OrderedDict()
        ppm_master = list()  # ppm masterlist
        ppm_cleaned = list()  # ppm masterlist, no dups

        splits = dict()  # Peak sets [full, class-split, loading-split, class & loading split]
        annotate = dict()

        remote_data = dict()  # Container for references to metabolite data on remote server

        # Web service peak-list assignment (metabohunter)
        logging.info("Sending peaklist to MetaboHunter...")

        peaks_list = '\n'.join([' '.join([str(a), str(b)]) for a, b in zip(dso.scales[1], dso.data[0, :])])

        url = 'http://www.nrcbioinformatics.ca/metabohunter/post_handler.php'

        values = {  # 'file'          : open('metabid_peaklist.txt', 'rt'),
                  'posturl': 'upload_file.php',
                  'useall': 'yes',
                  'peaks_list': peaks_list,
                  'dbsource': self.config.get('Database Source'),
                  'metabotype': self.config.get('Metabotype'),
                  'sampleph': self.config.get('Sample pH'),
                  'solvent': self.config.get('Solvent'),
                  'freq': self.config.get('Frequency'),
                  'method': self.config.get('Method'),
                  'noise': self.config.get('Noise Threshold'),
                  'thres': self.config.get('Confidence Threshold'),
                  'neighbourhood': self.config.get('Tolerance'),  # tolerance, # Use same tolerance as for shift
                  'submit': 'Find matches',
                 }

        self.status.emit('waiting')

        try:
            r = requests.post(url, data=values)
        except e:
            print(e)
            return None

        html = r.content
        self.status.emit('active')

        m = re.search('name="hits" value="(.*?)\n(.*?)\n"', html, re.MULTILINE | re.DOTALL)
        remote_data['metabolite_table'] = m.group(2)

        m = re.search('name="sample_file" value="(.*?)"', html, re.MULTILINE | re.DOTALL)
        remote_data['sample_file'] = m.group(1)

        logging.info("Received analysis from MetaboHunter, interpreting...")

        # Regexp out the matched peaks table from the hidden form field in response (easiest to parse)
        metabolites = OrderedDict()

        # Iterate line by line (skip first, header) building a table of the returned metabolites
        for row in remote_data['metabolite_table'].split('\n'):

            fields = row.split('\t')  # split row on tabs
            m = re.match("(.*?) \((\d*?)/(\d*?)\)", fields[3])

            metabolites[fields[1]] = {
                'name': fields[2],
                'score': float(m.group(1)),
                'peaks': "%d/%d" % (int(m.group(2)), int(m.group(3))),
                'taxnomic': fields[4],
                'rank': fields[0],
                }

        logging.info("Retrieving matched peaks to metabolite relationships...")

        values = {'sample_file': remote_data['sample_file'],
                  'matched_peaks_file': remote_data['sample_file'] + "_matched_spectra.txt",
                  'noise': 0.0,
                  'hits': 'Rank\tID\tMetabolite name\tMatching peaks score\tTaxonomic origin\r\n' + remote_data['metabolite_table'] + '\r\n',
         }

        self.status.emit('waiting')

        # Create the Request object
        url = 'http://www.nrcbioinformatics.ca/metabohunter/download_matched_peaks.php'
        try:
            r = requests.post(url, data=values, files={'foo': 'bar'})
        except e:
            logging.error(e)
            return None

        matched_peaks_text = r.content
        self.status.emit('active')
        logging.info("Extracting data...")

        # Need to do this in two steps, so they are in the correct order for output
        metabolite_peaks = dict()
        matched_peak_metabolites = dict()

        for row in matched_peaks_text.split('\n'):
            fields = row.split()
            if fields:
                # fields[0] contains the HMDBid plus a colon :(
                fields[0] = fields[0].rstrip(':')
                metabolite_peaks[fields[0]] = fields[1:]

        for metabolite in metabolites:
            if metabolite in metabolite_peaks:
                # Save metabolite for each peak
                for peak in metabolite_peaks[metabolite]:
                    #if peak in matched_peak_metabolites:
                    #    matched_peak_metabolites[ peak ].append(metabolite)
                    #else:
                    matched_peak_metabolites[peak] = metabolite


        # Assign metabolite names to labels (for subsequent entity lookup)
        # dso.import_data( dsi )
        # Returned peaks are at 2dp so we need to check if we have a nearish match
        for n, p in enumerate(dso.scales[1]):
            sp2 = str(round(p, 2))
            if sp2 in matched_peak_metabolites:
                hmdbid = matched_peak_metabolites[sp2]
                dso.labels[1][n] = hmdbid
                # All in HMDBIDs; if we have it use the entity
                if hmdbid in self.m.db.unification['HMDB']:
                    dso.entities[1][n] = self.m.db.unification['HMDB'][hmdbid]
        # Now remove any data from the object that isn't assigned?
        #
        #

        return dso

            
class MetaboHunter(IdentificationPlugin):

    def __init__(self, **kwargs):
        super(MetaboHunter, self).__init__(**kwargs)
        MetaboHunterApp.plugin = self
        self.register_app_launcher(MetaboHunterApp)
