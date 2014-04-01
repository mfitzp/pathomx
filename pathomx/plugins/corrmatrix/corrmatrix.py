# -*- coding: utf-8 -*-

import numpy as np

# Renderer for GPML as SVG
from gpml2svg import gpml2svg

import os

import pathomx.ui as ui
import pathomx.utils as utils

from pathomx.data import DataSet, DataDefinition
from pathomx.views import D3PrerenderedView
from pathomx.plugins import VisualisationPlugin


# Class for data visualisations using GPML formatted pathways
# Supports loading from local file and WikiPathways
class CorrMatrixApp(ui.AnalysisApp):
    def __init__(self, **kwargs):
        super(CorrMatrixApp, self).__init__(**kwargs)

        self.addDataToolBar()
        self.addFigureToolBar()

        self.views.addView(D3PrerenderedView(self), 'View')

        self.data.add_input('input')  # Add input slot            
        # Setup data consumer options
        self.data.consumer_defs.append(
            DataDefinition('input', {
            'entities_t': (None, ['Compound']),
            })
        )

        t = self.addToolBar('Bar')
        self.toolbars['bar'] = t

        self.finalise()

    def generate(self, input=None):
        #State,Under 5 Years,5 to 13 Years,14 to 17 Years,18 to 24 Years,25 to 44 Years,45 to 64 Years,65 Years and Over
        #CA,2704659,4499890,2159981,3853788,10604510,8819342,4114496
        #TX,2027307,3277946,1420518,2454721,7017731,5656528,2472223
        #NY,1208495,2141490,1058031,1999120,5355235,5120254,2607672
        #FL,1140516,1938695,925060,1607297,4782119,4746856,3187797
        #IL,894368,1558919,725973,1311479,3596343,3239173,1575308
        #PA,737462,1345341,679201,1203944,3157759,3414001,1910571

        dso = input

        fd = np.mean(dso.data, axis=0)
        fdm = list(zip(dso.labels[1], fd))
        sms = sorted(fdm, key=lambda x: abs(x[1]), reverse=True)
        metabolites = [m for m, s in sms]

        data = []
        for n, c in enumerate(dso.classes[0]):

            data.append(
                (c, {m: dso.data[n, dso.labels[1].index(m)] for m in metabolites[:4]})
            )

        metadata = {
            'figure': {
                            'type': 'bar',
                            'data': data,
                        },
                    }

        return {'metadata': metadata}

    def prerender(self, metadata=None):
        return {'View': {'metadata': metadata, 'template': 'd3/corrmatrix.svg'}}


class CorrMatrix(VisualisationPlugin):

    def __init__(self, **kwargs):
        super(CorrMatrix, self).__init__(**kwargs)
        CorrMatrixApp.plugin = self
        self.register_app_launcher(CorrMatrixApp)
