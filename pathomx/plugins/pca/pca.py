# -*- coding: utf-8 -*-

from pathomx.plugins import AnalysisPlugin

from collections import defaultdict
import os
import time
from copy import copy

import numpy as np
from sklearn.decomposition import PCA

import pathomx.ui as ui
import pathomx.db as db
import pathomx.utils as utils


from pathomx.data import DataSet, DataDefinition
from pathomx.views import MplScatterView, MplSpectraView
from pathomx.qt import *


# Dialog box for Metabohunter search options
class PCAConfigPanel(ui.ConfigPanel):

    def __init__(self, *args, **kwargs):
        super(PCAConfigPanel, self).__init__(*args, **kwargs)

        row = QVBoxLayout()
        cl = QLabel('Number of components')
        cb = QSpinBox()
        cb.setRange(0, 10)
        row.addWidget(cl)
        row.addWidget(cb)
        self.config.add_handler('number_of_components', cb)
        self.layout.addLayout(row)

        self.finalise()


class PCAApp(ui.AnalysisApp):
    def __init__(self, **kwargs):
        super(PCAApp, self).__init__(**kwargs)
        # Define automatic mapping (settings will determine the route; allow manual tweaks later)

        self.views.addView(MplScatterView(self), 'Scores')
        self.views.addView(MplSpectraView(self), 'PC1')
        self.views.addView(MplSpectraView(self), 'PC2')
        self.views.addView(MplSpectraView(self), 'PC3')
        self.views.addView(MplSpectraView(self), 'PC4')
        self.views.addView(MplSpectraView(self), 'PC5')

        self.addDataToolBar()
        self.addFigureToolBar()

        self.data.add_input('input')  # Add input slot

        self.data.add_output('scores')
        self.data.add_output('weights')

        # Setup data consumer options
        self.data.consumer_defs.append(
            DataDefinition('input', {
#            'labels_n':   (None,['Pathway']),
            })
        )

        self.config.set_defaults({
            'number_of_components': 2,
        })

        self.addConfigPanel(PCAConfigPanel, 'PCA')

        self.finalise()

    def generate(self, input=None):
        data = input.data

        pca = PCA(n_components=self.config.get('number_of_components'))
        pca.fit(data)
        scores = pca.transform(data)

        # Build scores into a dso no_of_samples x no_of_principal_components
        scored = DataSet(size=(scores.shape))
        scored.labels[0] = input.labels[0]
        scored.classes[0] = input.classes[0]
        scored.data = scores

        for n in range(0, scored.shape[1]):
            scored.labels[1][n] = 'Principal Component %d (%0.2f%%)' % (n + 1, pca.explained_variance_ratio_[0] * 100.)

        weightsd = DataSet(size=pca.components_.shape)
        weightsd.data = pca.components_

        weightsd.scales[1] = input.scales[1]

        dso_pc = {}
        for n in range(0, pca.components_.shape[0]):
            pcd = DataSet(size=(1, input.shape[1]))
            pcd.entities[1] = input.entities[1]
            pcd.labels[1] = input.labels[1]
            pcd.scales[1] = input.scales[1]
            pcd.data = weightsd.data[n:n + 1, :]
            dso_pc['pc%s' % (n + 1)] = pcd
            weightsd.labels[0][n] = "PC %s" % (n + 1)
            #weightsd.classes[0][n] = "PC %s" % (n+1)

        return dict(list({
            'dso': input,
            'pca': pca,
            'scores': scored,
            'weights': weightsd,
        }.items()) + list(dso_pc.items()))

    def prerender(self, dso=None, pca=None, scores=None, pc1=None, pc2=None, pc3=None, pc4=None, pc5=None, **kwargs):
        scores.crop((scores.shape[0], 2))
        print scores.data
        return {
            'Scores': {'dso': scores},
            'PC1': {'dso': pc1},
            'PC2': {'dso': pc2},
            'PC3': {'dso': pc3},
            'PC4': {'dso': pc4},
            'PC5': {'dso': pc5},
            }

        
class PCAPlugin(AnalysisPlugin):

    def __init__(self, **kwargs):
        super(PCAPlugin, self).__init__(**kwargs)
        PCAApp.plugin = self
        self.register_app_launcher(PCAApp)
