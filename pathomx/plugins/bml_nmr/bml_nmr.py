# -*- coding: utf-8 -*-

import os
import csv
import xml.etree.cElementTree as et
from collections import defaultdict

import numpy as np
import zipfile
import tempfile

import pathomx.ui as ui
import pathomx.db as db
import pathomx.utils as utils

from pathomx.data import DataSet
from pathomx.plugins import ImportPlugin
from pathomx.qt import *


class BMLNMRApp(ui.ImportDataApp):

    import_filename_filter = "Compressed Files (*.zip);;All files (*.*)"
    import_description = "Open BML-NMR FIMA .zip output"

    def __init__(self, **kwargs):
        super(BMLNMRApp, self).__init__(**kwargs)

        self.data.add_output('Raw')  # Add output slot
        self.data.add_output('PQN')  # Add output slot
        self.data.add_output('TSA')  # Add output slot

        self.t = self.addToolBar('Data Import')
        self.t.setIconSize(QSize(16, 16))

        self.table.setModel(self.data.o['Raw'].as_table)

        self.finalise()

    def onFileChanged(self, file):
        self.load_datafile(file)

    def prerender(self, Raw=None, PQN=None, TSA=None):
        return {'View': {'dso': Raw}}

    def load_datafile(self, filename):

        # Unzip into temporary folder
        folder = tempfile.mkdtemp()  # os.path.join( QDir.tempPath(),
        zf = zipfile.ZipFile(filename)
        zf.extractall(folder)
        f = os.listdir(folder)
        bml_job = f[0]

        fns = [
            ('samples_vs_concs_matrix.txt', 'Raw'),
            ('samples_vs_concs_matrix_tsanorm.txt', 'TSA'),
            ('samples_vs_concs_matrix_pqnnorm.txt', 'PQN'),
        ]

        # We have the data folder; import each of the complete datasets in turn
        # non, PQN, TSA and label appropriately
        dsos = {}

        for fn, l in fns:
            # Load the data file
            data_path = os.path.join(folder, bml_job, 'overall_result_outputs', fn)

            dsos[l] = self.load_bml_datafile(data_path, l, "%s (%s)" % (bml_job, l))

        self.set_name(bml_job)
        print(dsos)
        return dsos

    def load_bml_datafile(self, data_path, target, name):

        dso = DataSet()

        # Read in data for the graphing metabolite, with associated value (generate mean)
        reader = csv.reader(utils.nonull(open(data_path, 'rb')), delimiter='\t', dialect='excel')

        for row in reader:
            if row and row[0] == 'metabolite':  # Look for the top row
                break
        else:
            return

        samples = row[1:-2]  # Sample identities
        samples = [sample[8:-1] for sample in samples]

        xdim = 0
        ydim = len(samples)

        raw_data = []
        metabolites = []

        for row in reader:
            xdim += 1
            metabolites.append(row[0])

            raw_data.append([float(i) for i in row[1:-2]])

        dso = DataSet(size=(ydim, xdim))
        dso.labels[1] = metabolites

        dso.data = np.array(raw_data).T

        dso.name = name
        dso.description = 'Imported from FIMA (%s)' % name

        return dso


class BMLNMR(ImportPlugin):

    def __init__(self, **kwargs):
        super(BMLNMR, self).__init__(**kwargs)
        self.register_app_launcher(BMLNMRApp)
