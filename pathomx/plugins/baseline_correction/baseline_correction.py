# -*- coding: utf-8 -*-

import os
import copy

import numpy as np
import nmrglue as ng

import pathomx.ui as ui
import pathomx.db as db
import pathomx.utils as utils

from pathomx.plugins import ProcessingPlugin
from pathomx.data import DataSet, DataDefinition
from pathomx.views import MplSpectraView
from pathomx.qt import *


# Dialog box for Metabohunter search options
class BaselineCorrectionConfigPanel(ui.ConfigPanel):

    def __init__(self, *args, **kwargs):
        super(BaselineCorrectionConfigPanel, self).__init__(*args, **kwargs)

        self.algorithm = {
            'Median': 'median',
            #'Selected datapoints': 'base',
            'Constant from % of spectra': 'cbf_pc',
            'Constant from start:end': 'cbf_explicit',
        }

        self.gbs = {}

        vw = QVBoxLayout()
        self.algorithm_cb = QComboBox()
        self.algorithm_cb.addItems([k for k, v in list(self.algorithm.items())])
        self.algorithm_cb.currentIndexChanged.connect(self.onSetAlgorithm)
        self.config.add_handler('algorithm', self.algorithm_cb, self.algorithm)
        vw.addWidget(self.algorithm_cb)  # ,0,0,1,2)        

        gb = QGroupBox('Algorithm')
        gb.setLayout(vw)
        self.layout.addWidget(gb)
        # Median  baseline settings
        #med_mw int
        #med_sf int
        #med_sigma float.0

        vw = QGridLayout()
        self.med_mw_spin = QSpinBox()
        self.med_mw_spin.setRange(1, 100)
        self.med_mw_spin.setSuffix('pts')
        self.config.add_handler('med_mw', self.med_mw_spin)
        tl = QLabel('Median window size')
        tl.setAlignment(Qt.AlignRight)
        vw.addWidget(tl, 0, 0)
        vw.addWidget(self.med_mw_spin, 0, 1)

        self.med_sf_spin = QSpinBox()
        self.med_sf_spin.setRange(1, 100)
        self.med_sf_spin.setSuffix('pts')
        self.config.add_handler('med_sf', self.med_sf_spin)
        tl = QLabel('Smooth window size')
        tl.setAlignment(Qt.AlignRight)
        vw.addWidget(tl, 1, 0)
        vw.addWidget(self.med_sf_spin, 1, 1)

        self.med_sigma_spin = QDoubleSpinBox()
        self.med_sigma_spin.setDecimals(1)
        self.med_sigma_spin.setRange(0.1, 10)
        self.med_sigma_spin.setSuffix('ppm')
        self.med_sigma_spin.setSingleStep(0.1)
        self.config.add_handler('med_sigma', self.med_sigma_spin)
        tl = QLabel('s.d. of Gaussian')
        tl.setAlignment(Qt.AlignRight)
        vw.addWidget(tl, 2, 0)
        vw.addWidget(self.med_sigma_spin, 2, 1)

        gb = QGroupBox('Median baseline correction')
        gb.setLayout(vw)
        self.layout.addWidget(gb)
        self.gbs['Median'] = gb
        # cbf settings
        #cbf_last_pc int

        vw = QGridLayout()
        self.cbf_last_pc_spin = QSpinBox()
        self.cbf_last_pc_spin.setRange(1, 100)
        self.cbf_last_pc_spin.setSuffix('%')
        self.config.add_handler('cbf_last_pc', self.cbf_last_pc_spin)
        tl = QLabel('Last n% of data')
        tl.setAlignment(Qt.AlignRight)
        vw.addWidget(tl, 0, 0)
        vw.addWidget(self.cbf_last_pc_spin, 0, 1)

        gb = QGroupBox('Constant from last % of spectra')
        gb.setLayout(vw)
        self.layout.addWidget(gb)
        self.gbs['Constant from % of spectra'] = gb
        # cbf_explicit settings
        #cbf_explicit_start int
        #cbf_explicit_end int

        vw = QGridLayout()
        self.cbf_explicit_start_spin = QSpinBox()
        self.cbf_explicit_start_spin.setRange(1, 32767)
        self.config.add_handler('cbf_explicit_start', self.cbf_explicit_start_spin)

        self.cbf_explicit_end_spin = QSpinBox()
        self.cbf_explicit_end_spin.setRange(2, 32768)
        self.config.add_handler('cbf_explicit_end', self.cbf_explicit_end_spin)

        tl = QLabel('Start:end')
        tl.setAlignment(Qt.AlignRight)
        vw.addWidget(tl, 0, 0)
        vw.addWidget(self.cbf_explicit_start_spin, 0, 1)
        vw.addWidget(self.cbf_explicit_end_spin, 0, 2)

        gb = QGroupBox('Constant from explicit region')
        gb.setLayout(vw)
        self.layout.addWidget(gb)
        self.gbs['Constant from start:end'] = gb
        # base settings
        #base_nl list of points
        #base_nw float.0

        self.onSetAlgorithm()
        self.finalise()

    def onSetAlgorithm(self):
        for k, v in list(self.gbs.items()):
            if self.algorithm_cb.currentText() == k:
                v.show()
            else:
                v.hide()


class BaselineCorrectionTool(ui.DataApp):

    def __init__(self, **kwargs):
        super(BaselineCorrectionTool, self).__init__(**kwargs)

        self.addDataToolBar()
        self.addFigureToolBar()

        self.data.add_input('input')  # Add input slot
        self.data.add_output('output')
        self.table.setModel(self.data.o['output'].as_table)

        self.views.addView(MplSpectraView(self), 'View')

        # Setup data consumer options
        self.data.consumer_defs.append(
            DataDefinition('input', {
            'labels_n': ('>1', None),
            'entities_t': (None, None),
            'scales_t': (None, ['float']),
            })
        )

        # Define default settings for pathway rendering
        self.config.set_defaults({
            # Peak target
            'algorithm': 'median',
            # Baseline settings
            'med_mw': 24,
            'med_sf': 16,
            'med_sigma': 5.0,
            # cbf settings
            'cbf_last_pc': 10,
            # cbf_explicit settings
            'cbf_explicit_start': 0,
            'cbf_explicit_end': 100,
            # base settings
            'base_nl': [],
            'base_nw': 0,
        })

        self.addConfigPanel(BaselineCorrectionConfigPanel, 'Settings')
        self.finalise()

    def generate(self, input=None):
        dso = self.baseline_correct(input)  # , self._bin_size, self._bin_offset)
        return {'output': dso}

    def prerender(self, output):
        return {
            'View': {'dso': output},
            }

    # Shift and scale NMR spectra to target peak
    def baseline_correct(self, dsi):
        # Get the target region from the spectra (will be using this for all calculations;
        # then applying the result to the original data)
        scale = dsi.scales[1]

        algorithm = self.config.get('algorithm')

        # Medium algorithm vars
        med_mw = self.config.get('med_mw')
        med_sf = self.config.get('med_sf')
        med_sigma = self.config.get('med_sigma')

        # Cbf pc algorithm vars
        cbf_last_pc = self.config.get('cbf_last_pc')

        # Cbf explicit algorithm vars
        cbf_explicit_start = self.config.get('cbf_explicit_start')
        cbf_explicit_end = self.config.get('cbf_explicit_start')

        for n, dr in enumerate(dsi.data):

            if algorithm == 'median':
                dr = ng.process.proc_bl.med(dr, mw=med_mw, sf=med_sf, sigma=med_sigma)

            elif algorithm == 'cbf_pc':
                dr = ng.process.proc_bl.cbf(dr, last=cbf_last_pc)

            elif algorithm == 'cbf_explicit':
                dr = ng.process.proc_bl.cbf_explicit(dr, calc=slice(cbf_explicit_start, cbf_explicit_end))

            dsi.data[n, :] = dr
        # Baseline settings
        #baseline_med_mw
        #baseline_med_sf
        #baseline_med_sigma

        # cbf settings
        #cbf_last_pc

        # cbf_explicit settings
        #cbf_explicit_start
        #cbf_explicit_end

        # base settings
        #base_nl
        #base_nw

        return dsi

 
class BaselineCorrection(ProcessingPlugin):

    def __init__(self, **kwargs):
        super(BaselineCorrection, self).__init__(**kwargs)
        BaselineCorrection.plugin = self
        self.register_app_launcher(BaselineCorrectionTool)
