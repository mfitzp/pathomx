# -*- coding: utf-8 -*-

import os

import pathomx.ui as ui
from pathomx.plugins import AnalysisPlugin
from pathomx.data import DataDefinition
from pathomx.qt import *

class TwoSampleConfigPanel(ui.ConfigPanel):

    def __init__(self, parent, *args, **kwargs):
        super(TwoSampleConfigPanel, self).__init__(parent, *args, **kwargs)

        self.v = parent
        self.config = parent.config
        gb = QGroupBox('Sample groups')
        grid = QGridLayout()


        self.cb_independent = QComboBox()
        self.cb_independent.addItems(['Independent', 'Related'])
        self.config.add_handler('related_or_independent', self.cb_independent)

        grid.addWidget(QLabel('Sample relationship'), 0, 0)
        grid.addWidget(self.cb_independent, 0, 1)

        self.cb_equalvar = QCheckBox()
        self.config.add_handler('assume_equal_variances', self.cb_equalvar)
        grid.addWidget(QLabel('Assume equal variances?'), 1, 0)
        grid.addWidget(self.cb_equalvar, 1, 1)

        self.cb_histogram = QCheckBox()
        self.config.add_handler('plot_distribution', self.cb_histogram)
        grid.addWidget(QLabel('Plot distribution?'), 2, 0)
        grid.addWidget(self.cb_histogram, 2, 1)



        gb.setLayout(grid)
        self.layout.addWidget(gb)

        self.finalise()


class TwoSampleT(ui.AnalysisApp):

    name = "Two-sample t-test"
    shortname = 'two_sample_t'

    def __init__(self, *args, **kwargs):
        super(TwoSampleT, self).__init__(*args, **kwargs)

        self.config.set_defaults({
            'experiment_control': None,
            'experiment_test': None,
            'related_or_independent': 'Related',
            'assume_equal_variances': True,
            'plot_distribution': True,
        })

        self.data.add_input('input_data')  # Add input slot

        # We need an input filter for this type; accepting *anything*
        self.data.consumer_defs.append(
            DataDefinition('input_data', {
            })
        )

        self.addExperimentConfigPanel()
        self.addConfigPanel(TwoSampleConfigPanel, 'Extra')


class Parametric(AnalysisPlugin):

    def __init__(self, *args, **kwargs):
        super(Parametric, self).__init__(*args, **kwargs)
        self.register_app_launcher(TwoSampleT)
