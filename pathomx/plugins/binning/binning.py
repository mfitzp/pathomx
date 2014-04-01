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


class BinningApp(ui.DataApp):
    def __init__(self, **kwargs):
        super(BinningApp, self).__init__(**kwargs)

        self.addDataToolBar()
        self.addFigureToolBar()

        self.data.add_input('input')  # Add input slot
        self.data.add_output('output')
        self.table.setModel(self.data.o['output'].as_table)

        #self.views.addTab(D3SpectraView(self), 'View')
        #self.views.addTab(D3DifferenceView(self), 'Difference')
        self.views.addTab(MplSpectraView(self), 'View')
        self.views.addTab(MplDifferenceView(self), 'Difference')

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

        self.addConfigPanel(BinningConfigPanel, 'Settings')

        self.finalise()

    def generate(self, input=None, **kwargs):
        return {'output': self.binning(dsi=input), 'input': input}

    def prerender(self, output=None, input=None):
        return {
            'View': {'dso': output},
            'Difference': {'dso_a': input, 'dso_b': output}
            }

    def generate(self, input=None):
        dsi = input
        ###### BINNING USING CONFI
        # Generate bin values for range start_scale to end_scale
        # Calculate the number of bins at binsize across range
        dso = DataSet()
        dso.import_data(dsi)

        r = dsi.scales_r[1]
        self._bin_size, self._bin_offset = self.config.get('bin_size'), self.config.get('bin_offset')

        bins = np.arange(r[0] + self._bin_offset, r[1] + self._bin_offset, self._bin_size)
        number_of_bins = len(bins) - 1

        # Can't increase the size of data, if bins > current size return the original
        if number_of_bins >= len(dso.scales[1]):
            return {'dso': dso}

        # Resize (lossy) to the new shape
        old_shape, new_shape = list(dsi.data.shape), list(dso.data.shape)
        new_shape[1] = number_of_bins
        dso.crop(new_shape)  # Lossy crop, but we'll be within the boundary below


        for n, d in enumerate(dsi.data):
            binned_data = np.histogram(dsi.scales[1], bins=bins, weights=d)
            binned_num = np.histogram(dsi.scales[1], bins=bins)  # Number of data points that ended up contributing to each bin
            dso.data[n, :] = binned_data[0] / binned_num[0]  # Mean

        dso.scales[1] = [float(x) for x in binned_data[1][:-1]]
        #dso.labels[1] = [str(x) for x in binned_data[1][:-1]]

        # Remove any NaNs that have crept in (due to the histogram)
        dso.remove_invalid_data()

        return {'output': dso, 'input': input}  # Pass back input for difference plot

 
class Binning(ProcessingPlugin):

    def __init__(self, **kwargs):
        super(Binning, self).__init__(**kwargs)
        BinningApp.plugin = self
        self.register_app_launcher(BinningApp)
