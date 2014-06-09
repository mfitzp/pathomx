# -*- coding: utf-8 -*-
import os
import copy

import numpy as np

import pathomx.qt as qt
import pathomx.ui as ui
import pathomx.db as db
import pathomx.utils as utils
import pathomx.threads as threads

from pathomx.plugins import ProcessingPlugin
from pathomx.data import DataSet, DataDefinition
from pathomx.views import D3SpectraView, D3DifferenceView, MplSpectraView, MplDifferenceView
from pathomx.qt import *


# Dialog box for Metabohunter search options
class BinningConfigPanel(ui.ConfigPanel):

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

        self.binoffset_spin = QDoubleSpinBox()
        self.binoffset_spin.setDecimals(3)
        self.binoffset_spin.setRange(-0.5, 0.5)
        self.binoffset_spin.setSuffix('ppm')
        self.binoffset_spin.setSingleStep(0.001)
        tl = QLabel(self.tr('Bin offset (start)'))
        self.layout.addWidget(tl)
        self.layout.addWidget(self.binoffset_spin)
        self.config.add_handler('bin_offset', self.binoffset_spin)

        self.finalise()


class BinningApp(ui.IPythonApp):

    notebook = 'binning.ipynb'

    def __init__(self, **kwargs):
        super(BinningApp, self).__init__(**kwargs)

        self.addDataToolBar()
        self.addFigureToolBar()

        self.data.add_input('input')  # Add input slot
        self.data.add_output('output')

        #self.views.addTab(D3SpectraView(self), 'View')
        #self.views.addTab(D3DifferenceView(self), 'Difference')
        self.views.addTab(MplSpectraView(self), 'View')
        self.views.addTab(MplDifferenceView(self), 'Difference')

        # Setup data consumer options
        self.data.consumer_defs.append(
            DataDefinition('input', {
            'labels_n': ('>0', None),
            'entities_t': (None, None),
            'scales_t': (None, ['float']),
            })
        )

        self.config.set_defaults({
            'bin_size': 0.01,
            'bin_offset': 0,
        })

        self.addConfigPanel(BinningConfigPanel, 'Settings')

        self.finalise()


    def _prerender(self, output=None, input=None):
        return {
            'View': {'dso': output},
            'Difference': {'dso_a': input, 'dso_b': output}
            }


 
class Binning(ProcessingPlugin):

    def __init__(self, **kwargs):
        super(Binning, self).__init__(**kwargs)
        BinningApp.plugin = self
        self.register_app_launcher(BinningApp)
