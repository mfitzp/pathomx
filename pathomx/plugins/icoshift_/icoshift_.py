# -*- coding: utf-8 -*-

import os
import copy

import numpy as np
from icoshift import icoshift

import pathomx.ui as ui
import pathomx.db as db
import pathomx.utils as utils

from pathomx.plugins import ProcessingPlugin
from pathomx.data import DataSet, DataDefinition
from pathomx.views import MplSpectraView, MplDifferenceView
from pathomx.qt import *


# Dialog box for Metabohunter search options
class IcoshiftConfigPanel(ui.ConfigPanel):

    def __init__(self, *args, **kwargs):
        super(IcoshiftConfigPanel, self).__init__(*args, **kwargs)

        vw = QVBoxLayout()
        self.target_cb = QComboBox()
        self.target_cb.addItems(['average', 'median', 'max', 'average2'])
        self.config.add_handler('target', self.target_cb)
        vw.addWidget(self.target_cb)

        gb = QGroupBox('Algorithm')
        gb.setLayout(vw)
        self.layout.addWidget(gb)

        vw = QVBoxLayout()
        self.mode_cb = QComboBox()
        self.mode_cb.addItems(['whole', 'number_of_intervals', 'length_of_intervals', 'define', 'reference_signal'])
        self.config.add_handler('alignment_mode', self.mode_cb)
        vw.addWidget(self.mode_cb)

        gb = QGroupBox('Intervals')
        gb.setLayout(vw)
        self.layout.addWidget(gb)

        vw = QVBoxLayout()
        self.mode_cb = QComboBox()
        self.mode_cb.addItems(['n', 'b', 'f'])
        self.config.add_handler('maximum_shift', self.mode_cb)
        vw.addWidget(self.mode_cb)

        gb = QGroupBox('Maximum shift')
        gb.setLayout(vw)
        self.layout.addWidget(gb)

        vw = QVBoxLayout()

        self.coshift_btn = QCheckBox('Enable co-shift preprocessing', self.m)
        #self.coshift_btn.setCheckable( True )
        self.config.add_handler('coshift_proprocess', self.coshift_btn)
        vw.addWidget(self.coshift_btn)

        self.mode_cb = QComboBox()
        self.mode_cb.addItems(['n', 'b', 'f'])
        self.config.add_handler('mode', self.mode_cb)
        vw.addWidget(self.mode_cb)

        gb = QGroupBox('Co-shift preprocessing')
        gb.setLayout(vw)
        self.layout.addWidget(gb)

        self.finalise()
'''
ALL OPTIONS
[algorithm]
xT: 'average', 'median', 'max', 'average2'
n: maximum shift, best 'b', fast 'f'
[/]

[intervals]
inter: 'whole', number_of_intervals, 'ndata', [interval_list:(a b), (a b),], reference signal refs:refe, refs-refe
intervals_in_ppm
[/]

[co shift preprocessing]
enable_coshift_preprocessing
max shift
[/]

[misc]
filling: NaN, previous point
[/]
'''


class IcoshiftApp(ui.DataApp):

    def __init__(self, **kwargs):
        super(IcoshiftApp, self).__init__(**kwargs)

        self.addDataToolBar()
        self.addFigureToolBar()

        self.data.add_input('input')  # Add input slot
        self.data.add_output('output')
        self.table.setModel(self.data.o['output'].as_table)

        self.views.addView(MplSpectraView(self), 'Spectra')
        self.views.addView(MplDifferenceView(self), 'Shift')

        # Setup data consumer options
        self.data.consumer_defs.append(
            DataDefinition('input', {
            'labels_n': ('>1', None),
            'entities_t': (None, None),
            'scales_t': (None, ['float']),
            })
        )

        self.config.set_defaults({
            'target': 'average',
            'alignment_mode': 'whole',
            'maximum_shift': 'f',
        })

        self.addConfigPanel(IcoshiftConfigPanel, 'Settings')

        self.finalise()

    def generate(self, input=None):
        return {
            'output': self.icoshift(self.data.get('input')),
            'input': self.data.get('input')
            }

    def prerender(self, output=None, input=None):
        return {'Spectra': {'dso': output}, 'Shift': {'dso_a': input, 'dso_b': output}}

    def icoshift(self, dsi):
        # Generate bin values for range start_scale to end_scale
        # Calculate the number of bins at binsize across range
        spectra = dsi.data
        print(spectra)
        xCS, ints, ind, target = icoshift.icoshift(self.config.get('target'), spectra, inter=self.config.get('alignment_mode'), n=self.config.get('maximum_shift'))
        dsi.data = xCS
        return dsi


class Icoshift(ProcessingPlugin):

    def __init__(self, **kwargs):
        super(Icoshift, self).__init__(**kwargs)
        IcoshiftApp.plugin = self
        self.register_app_launcher(IcoshiftApp)
