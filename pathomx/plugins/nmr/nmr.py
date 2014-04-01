# -*- coding: utf-8 -*-


#import nmrglue as ng

import csv
import os
import pprint
import xml.etree.cElementTree as et
from collections import defaultdict

import numpy as np
import scipy as sp

import pathomx.ui as ui
import pathomx.db as db
import pathomx.utils as utils
import pathomx.threads as threads

from pathomx.data import DataSet
from pathomx.plugins import ImportPlugin
from pathomx.qt import *

import nmrglue as ng


class NMRApp(ui.ImportDataApp):

    def load_datafile_by_type(self, fn, type="bruker"):

        _callbacks = {
            'bruker': self.load_bruker,
        }

        self.worker = threads.Worker(_callbacks[type], fn)
        self.start_worker_thread(self.worker)

    def addImportDataToolbar(self):
        t = self.getCreatedToolbar('External Data', 'external-data')

        import_dataAction = QAction(QIcon(os.path.join(self.plugin.path, 'bruker.png')), 'Import spectra from Bruker spectra\u2026', self.m)
        import_dataAction.setStatusTip('Import spectra from Bruker format')
        import_dataAction.triggered.connect(self.onImportBruker)
        t.addAction(import_dataAction)
        #self.addExternalDataToolbar()

    def onImportBruker(self):
        """ Open a data file"""
        Qd = QFileDialog()
        Qd.setFileMode(QFileDialog.Directory)
        Qd.setOption(QFileDialog.ShowDirsOnly)

        folder = Qd.getExistingDirectory(self, 'Open parent folder for your Bruker NMR experiments')
        if folder:
            self.thread_load_datafile(folder, 'bruker')

            self.workspace_item.setText(0, os.path.basename(filename))

    def load_bruker(self, folder):
        # We should have a folder name; so find all files named fid underneath it (together with path)
        # Extract the path, and the parent folder name (for sample label)
        nmr_data = []
        sample_labels = []
        _ppm_real_scan_folder = False
        fids = []
        for r, d, files in os.walk(folder):
            if 'fid' in files:
                scan = os.path.basename(r)
                print('Read Bruker:', r, scan)
                if scan == '99999' or scan == '9999':  # Dummy Bruker thing
                    continue
                # The following is a hack; need some interface for choosing between processed/raw data
                # and for various formats of NMR data input- but simple
                fids.append(r)

        total_fids = len(fids)
        pc_init = None
        pc_history = []
        for n, fid in enumerate(fids):
            self.progress.emit(float(n) / total_fids)

            dic, data, pc = self.load_bruker_fid(fid, pc_init)
            # Store previous phase correction outputs to speed up subsequent runs
            pc_history.append(pc)
            pc_init = np.median(np.array(pc_history), axis=0)

            if data is not None:
                label = os.path.basename(fid)
                #if 'AUTOPOS' in dic['acqus']:
                #    label = label + " %s" % dic['acqus']['AUTOPOS']
                sample_labels.append(label)
                nmr_data.append(data)
                _ppm_real_scan_folder = fid

        # Generate the ppm for these spectra
        # read in the bruker formatted data// use latest
        dic, data_unp = ng.bruker.read(_ppm_real_scan_folder)
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
        offset = (float(dic['acqus']['SW']) / 2) - (float(dic['acqus']['O1']) / float(dic['acqus']['BF1']))
        start = float(dic['acqus']['SW']) - offset
        end = -offset
        step = float(dic['acqus']['SW']) / 32768

        nmr_ppms = np.arange(start, end, -step)[:32768]
        experiment_name = '%s (%s)' % (dic['acqus']['EXP'], folder)

        # We now have a list of ft'd Bruker fids; run them into a data object
        dso = self.process_data_to_dso(nmr_data, nmr_ppms, sample_labels, experiment_name)
        self.set_name(dso.name)

        return {'output': dso}

    def process_data_to_dso(self, nmr_data, nmr_ppms, sample_labels, experiment_name):

        print("Processing spectra to dso...")
        sample_n = len(sample_labels)
        ppm_n = len(nmr_ppms)

        dso = DataSet(size=(sample_n, ppm_n))

        for n, nd in enumerate(nmr_data):
            print("Spectra %s" % sample_labels[n])
            dso.data[n, :] = nd
            dso.labels[0][n] = sample_labels[n]

        dso.labels[1] = [str(ppm) for ppm in nmr_ppms]
        dso.scales[1] = [float(ppm) for ppm in nmr_ppms]
        dso.name = experiment_name

        return dso

    def load_bruker_fid(self, fn, pc_init=None):

        try:
            print("Reading %s" % fn)
            # read in the bruker formatted data
            dic, data = ng.bruker.read(fn)
        except:
            print("...fail")
            return None, None
        else:

            # remove the digital filter
            data = ng.bruker.remove_digital_filter(dic, data)

            # process the spectrum
            data = ng.proc_base.zf_size(data, 32768)    # zero fill to 32768 points
            data = ng.process.proc_bl.sol_boxcar(data, w=16, mode='same')  # Solvent removal

            data = ng.proc_base.fft(data)               # Fourier transform

            data, pc = self.autophase(data, pc_init)  # Automatic phase correction

            data = ng.proc_base.di(data)                # discard the imaginaries
            data = ng.proc_base.rev(data)               # reverse the data

            #data = data / 10000000.
            return dic, data, pc

    def autophase(self, nmr_data, pc_init=None, algorithm='Peak_minima'):
        if pc_init == None:
            pc_init = [0, 0]

        fn = {
            'ACME': self.autophase_ACME,
            'Peak_minima': self.autophase_PeakMinima,
        }[algorithm]

        opt = sp.optimize.fmin(fn, x0=pc_init, args=(nmr_data.reshape(1, -1)[:500], ))
        print("Phase correction optimised to: %s" % opt)
        return ng.process.proc_base.ps(nmr_data, p0=opt[0], p1=opt[1]), opt

    def autophase_ACME(self, x, s):
        # Based on the ACME algorithm by Chen Li et al. Journal of Magnetic Resonance 158 (2002) 164–168

        stepsize = 1

        n, l = s.shape
        phc0, phc1 = x

        s0 = ng.process.proc_base.ps(s, p0=phc0, p1=phc1)
        s = np.real(s0)
        maxs = np.max(s)

        # Calculation of first derivatives
        ds1 = np.abs((s[2:l] - s[0:l - 1]) / (stepsize * 2))
        p1 = ds1 / np.sum(ds1)

        # Calculation of entropy
        m, k = p1.shape

        for i in range(0, m):
            for j in range(0, k):
                if (p1[i, j] == 0):  # %in case of ln(0)
                    p1[i, j] = 1

        h1 = -p1 * np.log(p1)
        h1s = np.sum(h1)

        # Calculation of penalty
        pfun = 0.0
        as_ = s - np.abs(s)
        sumas = np.sum(as_)

        if (sumas < 0):
            pfun = pfun + np.sum((as_ / 2) ** 2)

        p = 1000 * pfun

        # The value of objective function
        return h1s + p

    def autophase_PeakMinima(self, x, s):
        # Based on the ACME algorithm by Chen Li et al. Journal of Magnetic Resonance 158 (2002) 164–168

        stepsize = 1

        phc0, phc1 = x

        s0 = ng.process.proc_base.ps(s, p0=phc0, p1=phc1)
        s = np.real(s0).flatten()

        i = np.argmax(s)
        peak = s[i]
        mina = np.min(s[i - 100:i])
        minb = np.min(s[i:i + 100])

        return np.abs(mina - minb)


class NMRGlue(ImportPlugin):

    def __init__(self, **kwargs):
        super(NMRGlue, self).__init__(**kwargs)
        self.register_app_launcher(NMRApp)
