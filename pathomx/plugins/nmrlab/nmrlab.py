# -*- coding: utf-8 -*-

import os
import copy

import numpy as np
import logging

import pathomx.ui as ui
import pathomx.db as db
import pathomx.utils as utils

from pathomx.plugins import ProcessingPlugin
from pathomx.data import DataSet, DataDefinition
from pathomx.views import D3SpectraView, D3DifferenceView, MplSpectraView, MplDifferenceView
from pathomx.qt import *
from pathomx.custom_exceptions import PathomxExternalResourceTimeoutException


class NMRLabMetabolabTool(ui.IPythonApp):

    legacy_inputs = {'input': 'input_data'}
    legacy_outputs = {'output': 'output_data'}

    def __init__(self, *args, **kwargs):
        super(NMRLabMetabolabTool, self).__init__(*args, **kwargs)

        self.addDataToolBar()
        self.addFigureToolBar()

        self.data.add_input('input_data')  # Add input slot
        self.data.add_output('output_data')

        # Setup data consumer options
        self.data.consumer_defs.append(
            DataDefinition('input_data', {
            'labels_n': ('>0', None),
            'entities_t': (None, None),
            'scales_t': (None, ['float']),
            })
        )

        self.config.set_defaults({
            'bin_size': 0.01,
            'bin_offset': 0,
        })


# NMRLab BASELINE CORRECTION
class BaselineConfigPanel(ui.ConfigPanel):

    baseline_alg = {
#                 1: mean_bspts  & poly_bscorr (DEFAULT)
#                 2: flatt_bspts & poly_bscorr
#                 3: mean_bspts  & conv_bscorr
#                 4: flatt_bspts & conv_bscorr
#                 5: remove average of first or last n points
#                 6: mean_bspts  & spline_bscorr
#                 7: flatt_bspts & spline_bscorr
#                 8: remove using spline through predefined baseline points
#                    baselinenl(rspc,n,[],[],[],8,[],basepoints)
#                    n, number of points around picked points to calculate
#                    intensities to be used for spline

        'Mean base, poly baseline': 1,
        'FLATT base, poly baseline': 2,

        'Mean base, conv baseline': 3,
        'FLATT base, conv baseline': 4,

        'Remove average of first or last n points': 5,

        #'Mean base, spline baseline':6,
        #'FLATT base, spline baseline':7,

        #'Remove using spline through predefined baseline':8,
    }

    def __init__(self, *args, **kwargs):
        super(BaselineConfigPanel, self).__init__(*args, **kwargs)

        vw = QVBoxLayout()
        self.baseline_alg_cb = QComboBox()
        self.baseline_alg_cb.addItems(list(self.baseline_alg.keys()))
        #self.baseline_alg_cb.currentIndexChanged.connect(self.onBaselineMode)
        self.config.add_handler('baseline_alg', self.baseline_alg_cb, self.baseline_alg)
        vw.addWidget(self.baseline_alg_cb)  # ,0,0,1,2)        

        gb = QGroupBox('Baseline algorithm')
        gb.setLayout(vw)
        self.layout.addWidget(gb)

        vw = QGridLayout()
        self.base_par_spin = QSpinBox()
        self.base_par_spin.setRange(0, 32768)
        self.config.add_handler('baseline_par', self.base_par_spin)
        tl = QLabel(self.tr('Poly/conv order'))
        vw.addWidget(tl, 0, 0)
        vw.addWidget(self.base_par_spin, 0, 1)

        self.base_n_spin = QSpinBox()
        self.base_n_spin.setRange(0, 32768)
        self.config.add_handler('baseline_n', self.base_n_spin)
        tl = QLabel(self.tr('Number of points'))

        vw.addWidget(tl, 1, 0)
        vw.addWidget(self.base_n_spin, 1, 1)

        self.base_tau_spin = QSpinBox()
        self.base_tau_spin.setRange(0, 500)
        self.config.add_handler('baseline_tau', self.base_tau_spin)
        tl = QLabel(self.tr('Tau'))

        vw.addWidget(tl, 2, 0)
        vw.addWidget(self.base_tau_spin, 2, 1)

        self.base_bas_noise_spin = QSpinBox()
        self.base_bas_noise_spin.setRange(0, 10)
        self.config.add_handler('baseline_bas_noise', self.base_bas_noise_spin)
        tl = QLabel(self.tr('Baseline (fixed) noise'))

        vw.addWidget(tl, 3, 0)
        vw.addWidget(self.base_bas_noise_spin, 3, 1)

        self.spgb = QGroupBox('Parameters')
        self.spgb.setLayout(vw)
        self.layout.addWidget(self.spgb)

        self.finalise()

    #def onBaselineMode(self):
        #if self.config.get('baseline_alg') == 1:
        #    self.spgb.show()
        #else:
        #    self.spgb.hide()

class BaselineMetabolabTool(NMRLabMetabolabTool):
    name = "Baseline correction"
    notebook = "nmrlab_baseline_correction.ipynb"
    # function mat_out = spcbaseline(mat_in,bs_mode,nopts)
    # spcbaseline - baseline correctino on matric
    #
    #               bs_mode: 0: none
    #                        1: a simple baseline correction using the
    #                           edges of the spectrum will be applied.
    #                        2: nmrlab baseline function with reasonable
    #                           default parameters [y=baseline(y,20,20,3,1,1)]
    #
    #               nopts: length of ends for mode 1, can be a number of a
    #               range [start:stop]

    def __init__(self, *args, **kwargs):
        super(BaselineMetabolabTool, self).__init__(*args, **kwargs)

        self.config.set_defaults({
            'baseline_alg': 1,

            'baseline_n': 20,
            'baseline_tau': 20,
            'baseline_par': 6,
            'baseline_bas_noise': 0,
        })

        self.addConfigPanel(BaselineConfigPanel, 'Settings')

    def generate(self, input):
        self.status.emit('active')

        bc_mat, baseline, is_baseline = self.matlab.baselinenl(input.data.T,
                        self.config.get('baseline_n'),
                        self.config.get('baseline_tau'),
                        self.config.get('baseline_par'),
                        1,  # tfact; obsolete
                        self.config.get('baseline_alg'),
                        self.config.get('baseline_bas_noise'),
                        nout=3)

        input.data = bc_mat.reshape(input.shape)

        return {'output': input}


# NMRLab TMSP ALIGNMENT Tool
class TMSPAlignConfigPanel(ui.ConfigPanel):

    def __init__(self, *args, **kwargs):
        super(TMSPAlignConfigPanel, self).__init__(*args, **kwargs)

        vw = QGridLayout()
        self.spectra_n_spin = QSpinBox()
        self.spectra_n_spin.setRange(1, 32768)
        self.config.add_handler('reference_spectra_n', self.spectra_n_spin)
        tl = QLabel(self.tr('Reference spectra'))
        vw.addWidget(tl, 0, 0)
        vw.addWidget(self.spectra_n_spin, 0, 1)

        self.shift_max_spin = QSpinBox()
        self.spectra_n_spin.setRange(1, 32768)
        self.config.add_handler('maximum_shift', self.shift_max_spin)
        tl = QLabel(self.tr('Maximum shift (ppm)'))

        vw.addWidget(tl, 1, 0)
        vw.addWidget(self.shift_max_spin, 1, 1)

        self.spgb = QGroupBox('Parameters')
        self.spgb.setLayout(vw)
        self.layout.addWidget(self.spgb)

        self.finalise()

 
class TMSPAlignMetabolabTool(NMRLabMetabolabTool):
    name = "Align NMR spectra (TMSP)"
    notebook = "nmrlab_tmsp_align.ipynb"
    # function [mat_out,shift] = spcalign_tmsp(mat_in, refspc, maxshift, ref, SILENT)
    # spcalign_tmsp - Align spectra using TMSP signal, data must be in columns of mat_in
    #            refspc:   no of reference spectrum in matrix
    #            maxshift: the largest possible shift in either direction

    def __init__(self, *args, **kwargs):
        super(TMSPAlignMetabolabTool, self).__init__(*args, **kwargs)

        self.config.set_defaults({
            'reference_spectra_n': 1,
            'maximum_shift': 22,
        })

        self.addConfigPanel(TMSPAlignConfigPanel, 'Settings')

    def generate(self, input):

        self.status.emit('active')

        mat_out, shift = self.matlab.spcalign_tmsp(input.data.T,
                        self.config.get('reference_spectra_n'),
                        self.config.get('maximum_shift'),
                        input.data[self.config.get('reference_spectra_n'), :],
                        True,
                        nout=2)

        input.data = mat_out.reshape(input.shape)

        return {'output': input}


# NMRLab Spectra ALIGNMENT Tool
class SpectraAlignConfigPanel(ui.ConfigPanel):

    algorithm = {
        'Min of differences ': 1,
        'Max correlation functions ': 2,
    }

    def __init__(self, *args, **kwargs):
        super(SpectraAlignConfigPanel, self).__init__(*args, **kwargs)

        vw = QGridLayout()
        self.spectra_n_spin = QSpinBox()
        self.spectra_n_spin.setRange(1, 32768)
        self.config.add_handler('reference_spectra_n', self.spectra_n_spin)
        tl = QLabel(self.tr('Reference spectra'))
        vw.addWidget(tl, 0, 0)
        vw.addWidget(self.spectra_n_spin, 0, 1)

        self.shift_max_spin = QSpinBox()
        self.spectra_n_spin.setRange(1, 32768)
        self.config.add_handler('maximum_shift', self.shift_max_spin)
        tl = QLabel(self.tr('Maximum shift (ppm)'))

        vw.addWidget(tl, 1, 0)
        vw.addWidget(self.shift_max_spin, 1, 1)
        #FIXME: Bug in algorithm correlation shifting hangs system
        #self.algorithm_cb = QComboBox()
        #self.algorithm_cb.addItems(list(self.algorithm.keys()))
        #self.baseline_alg_cb.currentIndexChanged.connect(self.onBaselineMode)
        #self.config.add_handler('algorithm', self.algorithm_cb, self.algorithm)

        #tl = QLabel(self.tr('Algorithm'))
        #vw.addWidget(tl, 2, 0)
        #vw.addWidget(self.algorithm_cb, 2, 1)

        self.spgb = QGroupBox('Parameters')
        self.spgb.setLayout(vw)
        self.layout.addWidget(self.spgb)

        self.finalise()

 
class SpectraAlignMetabolabTool(NMRLabMetabolabTool):
    name = "Align NMR spectra (whole)"
    notebook = "nmrlab_spectra_align.ipynb"
    # function [mat_out,shift] = spcalign(mat_in, refspc, maxshift, alg, SILENT)
    # spcalign - Align spectra, data must be in columns of mat_in
    #            refspc:   no of reference spectrum in matrix
    #            maxshift: the largest possible shift in either direction
    #            alg: 1:   min of differences
    #                 2:   max correlation functions

    def __init__(self, *args, **kwargs):
        super(SpectraAlignMetabolabTool, self).__init__(*args, **kwargs)

        self.config.set_defaults({
            'reference_spectra_n': 1,
            'maximum_shift': 22,
            'algorithm': 1,
        })

        self.addConfigPanel(SpectraAlignConfigPanel, 'Settings')

    def generate(self, input):

        self.status.emit('active')

        mat_out, shift = self.matlab.spcalign(input.data.T,
                        self.config.get('reference_spectra_n'),
                        self.config.get('maximum_shift'),
                        self.config.get('algorithm'),
                        True,
                        nout=2)

        input.data = mat_out.T.reshape(input.shape)

        return {'output': input}


# NMRLab VARIANCE STABILISATION
class VarianceStabilisationConfigPanel(ui.ConfigPanel):

    algorithm = {
        'Auto scaling': 'autoscale',
        'Pareto': 'pareto',
        'Generalised log transform': 'glog',
    }

    def __init__(self, *args, **kwargs):
        super(VarianceStabilisationConfigPanel, self).__init__(*args, **kwargs)

        vw = QGridLayout()

        self.alg_cb = QComboBox()
        self.alg_cb.addItems(list(self.algorithm.keys()))
        #self.baseline_alg_cb.currentIndexChanged.connect(self.onBaselineMode)
        self.config.add_handler('algorithm', self.alg_cb, self.algorithm)
        vw.addWidget(self.alg_cb)  # ,0,0,1,2)        

        self.alggb = QGroupBox('Algorithm')
        self.alggb.setLayout(vw)

        self.layout.addWidget(self.alggb)

        vw = QGridLayout()
        self.lambda_spin = QSpinBox()
        self.lambda_spin.setRange(-20, 20)
        self.config.add_handler('lambda', self.lambda_spin)
        tl = QLabel(self.tr('Lambda (1e__)'))
        vw.addWidget(tl, 0, 0)
        vw.addWidget(self.lambda_spin, 0, 1)

        self.y0_spin = QSpinBox()
        self.y0_spin.setRange(0, 10)
        self.config.add_handler('y0', self.y0_spin)
        tl = QLabel(self.tr('y0'))

        vw.addWidget(tl, 1, 0)
        vw.addWidget(self.y0_spin, 1, 1)

        self.spgb = QGroupBox('Generalised log transform')
        self.spgb.setLayout(vw)

        self.layout.addWidget(self.spgb)

        self.finalise()

 
class VarianceStabilisationMetabolabTool(NMRLabMetabolabTool):
    name = "Variance stabilisation"
    notebook = "nmrlab_variance_stabilisation.ipynb"
    # function mat_out = glogtrans(mat_in,lambda,y0)
    # glogtrans - Modified log-transform with lambda scaling for high values
    #             and a y0 shift to reduce scaling in the noise region of signals.

    def __init__(self, *args, **kwargs):
        super(VarianceStabilisationMetabolabTool, self).__init__(*args, **kwargs)

        self.config.set_defaults({
            'algorithm': 'glog',
            'lambda': -8,
            'y0': 0,
        })

        self.addConfigPanel(VarianceStabilisationConfigPanel, 'Settings')

    def generate(self, input):

        self.status.emit('active')

        if self.config.get('algorithm') == 'glog':

            mat_out = self.matlab.glogtrans(input.data,
                            10 ** self.config.get('lambda'),
                            self.config.get('y0'),
                            nout=1)
            input.data = mat_out.reshape(input.shape)

        elif self.config.get('algorithm') == 'pareto':

            mat_out = self.matlab.paretoscale2d(input.data,
                            nout=1)
            input.data = mat_out.reshape(input.shape)

        elif self.config.get('algorithm') == 'auto':

            mat_out = self.matlab.autoscale2d(input.data,
                            nout=1)
            input.data = mat_out.reshape(input.shape)

        return {'output': input}


# NMRLab BINNING
class BinningConfigPanel(ui.ConfigPanel):

    algorithm = {
        'Auto scaling': 'autoscale',
        'Pareto': 'pareto',
        'Generalised log transform': 'glog',
    }

    def __init__(self, *args, **kwargs):
        super(BinningConfigPanel, self).__init__(*args, **kwargs)

        self.binsize_spin = QDoubleSpinBox()
        self.binsize_spin.setDecimals(3)
        self.binsize_spin.setRange(0.001, 0.5)
        self.binsize_spin.setSuffix('ppm')
        self.binsize_spin.setSingleStep(0.005)
        tl = QLabel(self.tr('Bin width'))
        self.layout.addWidget(tl)
        self.layout.addWidget(self.binsize_spin)
        self.config.add_handler('bin_size', self.binsize_spin)

        self.finalise()

 
class BinningMetabolabTool(NMRLabMetabolabTool):
    name = "Bucket spectra"
    notebook = "nmrlab_bucket_spectra.ipynb"
    # function mat_out=spcbucket(mat_in,bucketsize)
    # spcbucket - spectra binning for NMRLab

    def __init__(self, *args, **kwargs):
        super(BinningMetabolabTool, self).__init__(*args, **kwargs)

        self.config.set_defaults({
            'bin_size': 0.006,
        })

        self.addConfigPanel(BinningConfigPanel, 'Settings')


class NMRLab(ProcessingPlugin):

    def __init__(self, *args, **kwargs):
        super(NMRLab, self).__init__(*args, **kwargs)
        self.register_app_launcher(BaselineMetabolabTool)
        self.register_app_launcher(TMSPAlignMetabolabTool)
        self.register_app_launcher(SpectraAlignMetabolabTool)
        self.register_app_launcher(VarianceStabilisationMetabolabTool)
        self.register_app_launcher(BinningMetabolabTool)
