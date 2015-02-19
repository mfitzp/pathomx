# -*- coding: utf-8 -*-
from pathomx.tools import BaseTool
from pathomx.ui import ConfigPanel
from pathomx.plugins import AnalysisPlugin

from pathomx.data import DataDefinition
from pathomx.qt import *


# Dialog box for Metabohunter search options
class PLSDAConfigPanel(ConfigPanel):

    def __init__(self, *args, **kwargs):
        super(PLSDAConfigPanel, self).__init__(*args, **kwargs)
        #row = QVBoxLayout()
        #cl = QLabel('Algorithm')
        #cb = QComboBox()
        #cb.addItems( ['NIPALS','SVD'] )
        #row.addWidget(cl)
        #row.addWidget(cb)
        #self.config.add_handler('algorithm', cb)
        #self.layout.addLayout(row)

        cb = QCheckBox('Autoscale input data')
        self.config.add_handler('autoscale', cb)
        self.layout.addWidget(cb)

        row = QVBoxLayout()
        cl = QLabel('Number of components')
        cb = QSpinBox()
        cb.setRange(0, 10)
        row.addWidget(cl)
        row.addWidget(cb)
        self.config.add_handler('number_of_components', cb)
        self.layout.addLayout(row)

        cb = QCheckBox('Plot sample numbers')
        self.config.add_handler('plot_sample_numbers', cb)
        self.layout.addWidget(cb)

        self.finalise()


class PLSDATool(BaseTool):

    name = "PLS-DA"
    notebook = 'pls_da.ipynb'
    shortname = 'pls_da'

    autoconfig_name = "{number_of_components} component(s)"

    legacy_launchers = ['PLSDAPlugin.PLSDAApp']
    legacy_inputs = {'input': 'input_data'}

    def __init__(self, *args, **kwargs):
        super(PLSDATool, self).__init__(*args, **kwargs)
        # Define automatic mapping (settings will determine the route; allow manual tweaks later)

        self.addExperimentConfigPanel()
        self.data.add_input('input_data')  # Add input slot

        self.config.set_defaults({
            'number_of_components': 2,
            'autoscale': False,
            'algorithm': 'NIPALS',

            'plot_sample_numbers': False,
        })

        self.addConfigPanel(PLSDAConfigPanel, 'PLSDA')

        # Setup data consumer options
        self.data.consumer_defs.append(
            DataDefinition('input_data', {})
        )


# Dialog box for Metabohunter search options
class PCAConfigPanel(ConfigPanel):

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

        cb = QCheckBox('Plot sample numbers')
        self.config.add_handler('plot_sample_numbers', cb)
        self.layout.addWidget(cb)

        cb = QCheckBox('Filter data by covariance (2sd)')
        self.config.add_handler('filter_data', cb)
        self.layout.addWidget(cb)

        self.finalise()


class PCATool(BaseTool):

    name = "PCA"
    notebook = 'pca.ipynb'
    shortname = 'pca'

    autoconfig_name = "{number_of_components} component(s)"

    legacy_launchers = ['PCAPlugin.PCAApp']
    legacy_inputs = {'input_data': 'input_data'}

    def __init__(self, *args, **kwargs):
        super(PCATool, self).__init__(*args, **kwargs)
        # Define automatic mapping (settings will determine the route; allow manual tweaks later)

        self.data.add_input('input_data')  # Add input slot

        self.data.add_output('scores')
        self.data.add_output('weights')
        self.data.add_output('filtered_data')

        # Setup data consumer options
        self.data.consumer_defs.append(
            DataDefinition('input_data', {
#            'labels_n':   (None,['Pathway']),
            })
        )

        self.config.set_defaults({
            'number_of_components': 2,

            'plot_sample_numbers': False,
        })

        self.addConfigPanel(PCAConfigPanel, 'PCA')


class Multivariate(AnalysisPlugin):

    def __init__(self, *args, **kwargs):
        super(Multivariate, self).__init__(*args, **kwargs)
        self.register_app_launcher(PLSDATool)
        self.register_app_launcher(PCATool)
