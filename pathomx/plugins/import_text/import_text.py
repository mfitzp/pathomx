# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os

from pathomx.plugins import ImportPlugin

import csv
import xml.etree.cElementTree as et
from collections import defaultdict

import numpy as np

import pathomx.ui as ui
import pathomx.db as db
import pathomx.threads as threads
import pathomx.utils as utils

from pathomx.data import DataSet
from pathomx.custom_exceptions import *


class ImportTextApp(ui.ImportDataApp):

    import_filename_filter = "All compatible files (*.csv *.txt *.tsv);;Comma Separated Values (*.csv);;Plain Text Files (*.txt);;Tab Separated Values (*.tsv);;All files (*.*)"
    import_description = "Open experimental data from text file data file"

    def load_datafile(self, filename):

    # Determine if we've got a csv or peakml file (extension)
        fn, fe = os.path.splitext(filename)
        formats = {  # Run specific loading function for different source data types
                '.csv': self.load_csv,
            }

        if fe in list(formats.keys()):
            print("Loading... %s" % fe)
            dso = formats[fe](filename)
            if dso == None:
                raise PathomxIncorrectFileStructureException("Data not loaded, check file structure.")

            dso.name = os.path.basename(filename)

            self.set_name(dso.name)
            dso.description = 'Imported %s file' % fe

            return {'output': dso}

        else:
            raise PathomxIncorrectFileFormatException("Unsupported file format.")
###### LOAD WRAPPERS; ANALYSE FILE TO LOAD WITH OTHER HANDLER

    def load_csv(self, filename):

        # Wrapper function to allow loading from alternative format CSV files
        # Legacy is experiments in ROWS, limited number by Excel so also support experiments in COLUMNS
        reader = csv.reader(open(filename, 'rU'), delimiter=str(','), dialect='excel')
        hrow = next(reader)  # Get top row
        print(hrow)
        if 'sample' in hrow[0].lower():
            if 'class' in hrow[1].lower():
                return self.load_csv_R(filename)
            else:
                return self.load_csv_C(filename)

        raise PathomxIncorrectFileStructureException("Data not loaded, check file structure.")
###### LOAD HANDLERS

    def load_csv_C(self, filename):  # Load from csv with experiments in COLUMNS, metabolites in ROWS
        # Read in data for the graphing metabolite, with associated value (generate mean)
        f = open(filename, 'rU')
        fsize = os.path.getsize(filename)
        reader = csv.reader(f, delimiter=str(','), dialect='excel')

        hrow = next(reader)  # Discard top row (sample no's)
        samples = hrow[1:]

        hrow = next(reader)  # Get 2nd row
        classesa = hrow[1:]
        classes = [c for c in classesa if c != '.']

        metabolites = []

        data = []

        added_rows = 0
        for n, row in enumerate(reader):
            metabolite = row[0]
            metabolites.append(row[0])
            quants = []
            for cn, c in enumerate(row[1:]):
                if classesa[cn] != '.':
                    try:
                        data.append(float(c))
                    except:
                        data.append(0)

            if n % 100 == 0:
                try:
                    # FIXME: There should be a way around this
                    # This fails in Python 3 with
                    # 'telling position disabled by next() call'
                    self.progress.emit(float(f.tell()) / fsize)
                except:
                    pass

        data = np.asarray(data)
        data = np.reshape(data, (n + 1, len(classes))).T

        xdim = len(quants)
        ydim = len(classes)

        # Build dataset object
        dso = DataSet(size=(xdim, ydim))  # self.add_data('imported_data', DataSetself) )
        dso.empty(size=(ydim, xdim))
        dso.labels[1] = metabolites

        scales = []
        mlabels = []
        for m in metabolites:
            try:
                scales.append(float(m))
                mlabels.append(None)
            except:
                scales.append(None)
                mlabels.append(m)

        dso.scales[0] = [None] * len(samples)
        dso.labels[0] = samples
        dso.classes[0] = classes
        dso.entities[0] = [None] * len(samples)

        dso.scales[1] = scales
        dso.labels[1] = mlabels
        dso.classes[1] = [None] * len(scales)
        dso.entities[1] = [None] * len(scales)

        dso.data = data

        return dso

    def load_csv_R(self, filename):  # Load from csv with experiments in ROWS, metabolites in COLUMNS
        # Read in data for the graphing metabolite, with associated value (generate mean)
        f = open(filename, 'rU')
        fsize = os.path.getsize(filename)
        reader = csv.reader(f, delimiter=str(','), dialect='excel')
        print('R')
        hrow = next(reader)  # Get top row
        metabolites = hrow[2:]
        ydim = 0
        xdim = len(metabolites)

        samples = []
        classes = []
        raw_data = []

        # Build quants table for metabolite classes
        #for metabolite in self.metabolites:
        #    quantities[ metabolite ] = defaultdict(list)

        for n, row in enumerate(reader):
            ydim += 1
            if row[1] != '.':  # Skip excluded classes # row[1] = Class
                samples.append(row[0])
                classes.append(row[1])
                data_row = []
                for c in row[2:]:  # in self.metabolites:
                    try:
                        c = float(c)
                    except:
                        c = 0
                    data_row.append(c)

                raw_data.append(data_row)
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

            if n % 100 == 0:
                try:
                    # FIXME: There should be a way around this
                    # This fails in Python 3 with
                    # 'telling position disabled by next() call'
                    self.progress.emit(float(f.tell()) / fsize)
                except:
                    pass

                #self.statistics['excluded'] += 1

        # Build dataset object
        dso = DataSet(size=(xdim, ydim))  # self.add_data('imported_data', DataSetself) )
        dso.empty(size=(ydim, xdim))
        #dso.labels[1] = metabolites

        scales = []
        mlabels = []
        for m in metabolites:
            try:
                scales.append(float(m))
                mlabels.append(None)
            except:
                scales.append(None)
                mlabels.append(m)

        dso.scales[1] = [None] * len(samples)
        dso.labels[0] = samples
        dso.classes[0] = classes
        dso.entities[0] = [None] * len(samples)

        dso.scales[1] = scales
        dso.labels[1] = mlabels
        dso.entities[1] = [None] * len(scales)
        dso.classes[1] = [None] * len(scales)

        dso.data = np.array(raw_data)

        return dso


class ImportText(ImportPlugin):

    def __init__(self, **kwargs):
        super(ImportText, self).__init__(**kwargs)
        self.register_app_launcher(ImportTextApp)
        self.register_file_handler(ImportTextApp, 'csv')
