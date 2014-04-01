# -*- coding: utf-8 -*-

import os
import copy

import numpy as np
import mlabwrap

import pathomx.ui as ui
import pathomx.db as db
import pathomx.utils as utils
import pathomx.threads as threads

from pathomx.data import DataSet, DataDefinition
from pathomx.views import D3SpectraView, D3DifferenceView, MplSpectraView, MplDifferenceView
from pathomx.plugins import AnalysisPlugin
from pathomx.qt import *


class PLSToolboxApp(ui.DataApp):
    def __init__(self, **kwargs):
        super(PLSToolboxApp, self).__init__(**kwargs)

        self.addDataToolBar()
        self.addFigureToolBar()

        self.data.add_input('input')  # Add input slot
        self.data.add_output('output')
        self.table.setModel(self.data.o['output'].as_table)

        self.views.addTab(MplSpectraView(self), 'View')

        # Start matlab interface
        self.matlab = mlabwrap.init()
        #code = "addpath('%s')" % os.path.abspath( self.plugin.path )
        #r = self.matlab.run_code(code)
        #print r,"!!!!"

        # Setup data consumer options
        self.data.consumer_defs.append(
            DataDefinition('input', {
            'labels_n': ('>1', None),
            'entities_t': (None, None),
            'scales_t': (None, ['float']),
            })
        )

        self.config.set_defaults({
            'bin_size': 0.01,
            'bin_offset': 0,
        })

    def __exit__(self, ext_type, exc_value, traceback):
        self.matlab.stop()


# Dialog box for Metabohunter search options
class BaselineConfigPanel(ui.ConfigPanel):

    def __init__(self, *args, **kwargs):
        super(BaselineConfigPanel, self).__init__(*args, **kwargs)

        self.baseline_alg = {
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

class BaselineMetabolabApp(PLSToolboxApp):
    name = "Baseline correction"
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

    def __init__(self, **kwargs):
        super(BaselineMetabolabApp, self).__init__(**kwargs)

        self.config.set_defaults({
            'baseline_alg': 1,

            'baseline_n': 20,
            'baseline_tau': 20,
            'baseline_par': 6,
            'baseline_bas_noise': 0,
        })

        self.addConfigPanel(BaselineConfigPanel, 'Settings')
        self.finalise()

    def generate(self, input):
        self.status.emit('waiting')
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


class PLSToolbox(AnalysisPlugin):

    def __init__(self, **kwargs):
        super(PLSToolbox, self).__init__(**kwargs)
        self.register_app_launcher(PLSToolboxApp)
