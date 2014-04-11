# -*- coding: utf-8 -*-
import os

import csv
import xml.etree.cElementTree as et
from collections import defaultdict

import numpy as np

import pathomx.ui as ui
import pathomx.db as db
import pathomx.threads as threads
import pathomx.utils as utils

from pathomx.data import DataSet
from pathomx.plugins import ImportPlugin
from pathomx.qt import *
from pathomx.utils import UnicodeReader


class GEOApp(ui.ImportDataApp):

    import_filename_filter = "All compatible files (*.soft);;Simple Omnibus Format in Text (*.soft);;All files (*.*)"
    import_description = "Open experimental data from downloaded data"

    # Data file import handlers (#FIXME probably shouldn't be here)
    def load_datafile(self, filename):

    # Determine if we've got a csv or peakml file (extension)
        fn, fe = os.path.splitext(filename)
        formats = {  # Run specific loading function for different source data types
                '.soft': self.load_soft_dataset,
            }

        if fe in list(formats.keys()):
            print("Loading... %s" % fe)

            dso = formats[fe](filename)

            dso.name = os.path.basename(filename)
            self.set_name(dso.name)
            dso.description = 'Imported %s file' % fe

            return {'output': dso}

        else:
            raise PathomxIncorrectFileFormatException("Unsupported file format.")
###### LOAD HANDLERS

    def preprocess_soft(self, reader, f=None, fsize=None):
        # Preprocess into the chunks (then can manageable process them in turn)
        soft_data = defaultdict(list)
        for n, row in enumerate(reader):
            if row[0].startswith('^'):  # Control row
                section = row[0]
                continue
            soft_data[section].append(row)

            if f and fsize and n % 100 == 0:
                self.progress.emit(float(f.tell()) / fsize)

        return soft_data

    def get_soft_metadata(self, rows, while_starts_with='!'):

        metadata = {}

        for row in rows:
            if not row[0].startswith('!'):
                break

            key, value = row[0][1:].split(' = ')  # Remove the ! and then split, removing the ' = '
            metadata[key] = value

        return metadata

    def get_float(self, x):
        try:
            x = float(x)
        except:
            if x == 'null':
                x = None
        return x

    def get_soft_data(self, rows, starts, ends):
        headers = False
        data = {}
        headers_at = False
        for n, row in enumerate(rows):
            if row[0] == starts:
                headers_at = n + 1
                start_at = n + 2
                break

        if not headers_at:
            return False

        headers = rows[headers_at]

        for row in rows[start_at:]:
            if row[0] == ends:
                break

            # Rewrite to account for null values; skip header (left column)
            row_data = row
            row_data[1:] = [self.get_float(x) for x in row[1:]]
            data[row[0]] = dict(list(zip(headers, row_data)))

        return data

    def load_soft_dataset(self, filename):  # Load from soft data file for genes
        # SOFT files are a /sort of/ bastardized csv with data in tab-separated columns
        # So, we use the csv reader to get that, accounting for most stuff being single field with
        # slightly strange identifiers
        f = open(filename, 'rb')
        fsize = os.path.getsize(filename)
        reader = UnicodeReader(f, delimiter='\t', dialect='excel')

        soft_data = self.preprocess_soft(reader, f=f, fsize=fsize)
        # soft_data now contains lists of sections with ^ markers

        database = {}
        dataset = {}
        dataset_data = {}
        subsets = {}

        for section, rows in list(soft_data.items()):

            if section.startswith('^DATABASE'):
                database = self.get_soft_metadata(rows)

            elif section.startswith('^DATASET'):
                dataset.update(self.get_soft_metadata(rows))  # update because seems can be >1 entry to dataset
                data = self.get_soft_data(rows, '!dataset_table_begin', '!dataset_table_end')
                dataset_data = data

            elif section.startswith('^SUBSET'):
                key, subset_id = section.split(' = ')
                subsets[subset_id] = self.get_soft_metadata(rows)
                subsets[subset_id]['subset_sample_id'] = subsets[subset_id]['subset_sample_id'].split(',')  # Turn to list of ids

        # We now have the entire dataset loaded; but in a bit of a messed up format
        # Build a dataset object to fit and map the data in
        sample_ids = []
        for k, subset in list(subsets.items()):
            sample_ids.extend(subset['subset_sample_id'])
        sample_ids = sorted(sample_ids)  # Get the samples sorted so we keep everything lined up

        class_lookup = {}
        for class_id, s in list(subsets.items()):
            for s_id in s['subset_sample_id']:
                class_lookup[s_id] = "%s (%s)" % (s['subset_description'] if 'subset_description' in s else '', class_id)

        xdim = len(dataset_data)  # Use first sample to access the gene list
        ydim = len(sample_ids)

        # Build dataset object
        dso = DataSet(size=(xdim, ydim))  # self.add_data('imported_data', DataSetself) )
        dso.empty(size=(ydim, xdim))

        gene_ids = sorted(dataset_data.keys())  # Get the keys sorted so we keep everything lined up

        dso.labels[0] = sample_ids
        dso.classes[0] = [class_lookup[s_id] for s_id in sample_ids]
        dso.labels[1] = [dataset_data[gene_id]['IDENTIFIER'] for gene_id in gene_ids]
        dso.entities[1] = [self.m.db.get_via_synonym(gene_id) for gene_id in dso.labels[1]]

        for xn, gene_id in enumerate(gene_ids):
            for yn, sample_id in enumerate(sample_ids):

                dso.data[yn, xn] = dataset_data[gene_id][sample_id]

        return dso

    def load_soft_series_family(self, filename):  # Load from soft data file for genes
        # SOFT files are a /sort of/ basterdized csv with data in tab-separated columns
        # So, we use the csv reader to get that, accounting for most stuff being single field with
        # slightly strange identifiers

        reader = csv.reader(open(filename, 'rU'), delimiter='\t', dialect='excel')
        soft_data = self.preprocess_soft(reader)

        database = {}
        platform = {}
        samples = {}
        sample_data = {}

        for section, rows in list(soft_data.items()):

            if section.startswith('^DATABASE'):
                database = self.get_soft_metadata(rows)

            elif section.startswith('^PLATFORM'):
                platform = self.get_soft_metadata(rows)
                platform_data = self.get_soft_data(rows, '!platform_table_begin', '!platform_table_end')

            elif section.startswith('^SAMPLE'):
                key, sample_id = row[0].split(' = ')
                samples[sample_id] = self.get_soft_metadata(rows)
                sample_data[sample_id] = self.get_soft_data(rows, '!sample_table_begin', '!sample_table_end')
        # We now have the entire dataseries loaded; but in a bit of a messed up format
        # Build a dataset object to fit and map the data in

        xdim = len(platform_data)  # Use first sample to access the gene list
        ydim = len(sample_data)

        # Build dataset object
        dso = DataSet(size=(xdim, ydim))  # self.add_data('imported_data', DataSetself) )
        dso.empty(size=(ydim, xdim))

        sample_ids = sorted(samples.keys())  # Get the samples sorted so we keep everything lined up
        gene_ids = sorted(platform_data.keys())  # Get the keys sorted so we keep everything lined up

        dso.labels[0] = sample_ids
        dso.labels[1] = [platform_data[gene_id]['UNIGENE'] for gene_id in gene_ids]
        dso.entities[1] = [self.m.db.get_via_unification('UNIGENE', gene_id) for gene_id in dso.labels[1]]

        for xn, gene_id in enumerate(gene_ids):
            for yn, sample_id in enumerate(sample_ids):

                dso.data[yn, xn] = sample_data[sample_id][gene_id]['VALUE']

        return dso


class GEO(ImportPlugin):

    def __init__(self, **kwargs):
        super(GEO, self).__init__(**kwargs)
        self.register_app_launcher(GEOApp)
        self.register_file_handler(GEOApp, 'soft')
