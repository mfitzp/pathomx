# -*- coding: utf-8 -*-


# Import PyQt5 classes
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWebKit import *
from PyQt5.QtNetwork import *
from PyQt5.QtWidgets import *
from PyQt5.QtPrintSupport import *
import os
import copy

from pathomx.plugins import ProcessingPlugin

import numpy as np
import nmrglue as ng

import pathomx.ui as ui
import pathomx.db as db

import pathomx.utils as utils

from pathomx.data import DataSet, DataDefinition
from pathomx.views import MplSpectraView, MplDifferenceView
from pathomx.qt import *


# Dialog box for Metabohunter search options
class SpectraNormConfigPanel(ui.ConfigPanel):

    def __init__(self, *args, **kwargs):
        super(SpectraNormConfigPanel, self).__init__(*args, **kwargs)

        self.algorithm_cb = QComboBox()
        self.algorithm_cb.addItems(self.v.algorithms)
        self.config.add_handler('algorithm', self.algorithm_cb)

        tl = QLabel('Scaling algorithm')
        tl.setIndent(5)
        self.layout.addWidget(tl)
        self.layout.addWidget(self.algorithm_cb)

        self.finalise()


class SpectraNormApp(ui.IPythonApp):

    name = "Spectra normalisation"
    notebook = 'spectra_norm.ipynb'
    
    algorithms = ['PQN','TSA']

    legacy_loaders = ['SpectraNorm.SpectraNormApp']
    legacy_inputs = {'input': 'input_data'}
    legacy_outputs = {'output': 'output_data'}

    def __init__(self, **kwargs):
        super(SpectraNormApp, self).__init__(**kwargs)

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
            'algorithm': 'PQN',
        })

        self.addConfigPanel(SpectraNormConfigPanel, 'Settings')

        self.finalise()



# Dialog box for Metabohunter search options
class PeakAdjConfigPanel(ui.ConfigPanel):
    
    def __init__(self, *args, **kwargs):
        super(PeakAdjConfigPanel, self).__init__(*args, **kwargs)        

        self.peak_targets = {
            'TMSP': (0.0, 0.25),
            'Creatinine @4.0': (4.045, 0.25),
            'Creatinine @3.0': (3.030, 0.25),
            'Custom': (None, None),
        }
        
        vw = QGridLayout()
        self.peak_target_cb = QComboBox()
        self.peak_target_cb.addItems( [k for k,v in list(self.peak_targets.items()) ] )
        self.peak_target_cb.currentIndexChanged.connect(self.onSetPredefinedTarget)
        self.config.add_handler('peak_target', self.peak_target_cb )
        vw.addWidget(self.peak_target_cb,0,0,1,2)        

        self.ppm_spin = QDoubleSpinBox()
        self.ppm_spin.setDecimals(2)
        self.ppm_spin.setRange(-1,15)
        self.ppm_spin.setSuffix('ppm')
        self.ppm_spin.setSingleStep(0.05)
        self.ppm_spin.valueChanged.connect(self.onSetCustomTarget) # Additional; to handle alternation
        self.config.add_handler('peak_target_ppm', self.ppm_spin )
        vw.addWidget(self.ppm_spin,1,1,1,1)

        self.ppm_tolerance_spin = QDoubleSpinBox()
        self.ppm_tolerance_spin.setDecimals(2)
        self.ppm_tolerance_spin.setRange(0,1)
        self.ppm_tolerance_spin.setSuffix('ppm')
        self.ppm_tolerance_spin.setSingleStep(0.05)
        self.ppm_tolerance_spin.valueChanged.connect(self.onSetCustomTarget) # Additional; to handle alternation
        self.config.add_handler('peak_target_ppm_tolerance', self.ppm_tolerance_spin )
        tl = QLabel('±')
        tl.setAlignment(Qt.AlignRight)
        vw.addWidget(tl,2,0,1,1)
        vw.addWidget(self.ppm_tolerance_spin,2,1,1,1)

        gb = QGroupBox('Peak target')
        gb.setLayout(vw)
        self.layout.addWidget(gb)

        vw = QVBoxLayout()
        self.toggle_shift = QPushButton( QIcon( os.path.join(  self.v.plugin.path, 'icon-16.png' ) ), 'Shift spectra', self.m)
        self.toggle_shift.setCheckable( True )
        self.config.add_handler('shifting_enabled', self.toggle_shift )
        vw.addWidget(self.toggle_shift)
        
        self.toggle_scale = QPushButton( QIcon( os.path.join(  self.v.plugin.path, 'icon-16.png' ) ), 'Scale spectra', self.m)
        self.toggle_scale.setCheckable( True )
        self.config.add_handler('scaling_enabled', self.toggle_scale )
        vw.addWidget(self.toggle_scale)    
         
        gb = QGroupBox('Toggle shift and scale')
        gb.setLayout(vw)
        self.layout.addWidget(gb)
        
        self.finalise()
        

    def onSetCustomTarget(self):
        if self._automated_update_config == False:
            self.peak_target_cb.setCurrentText('Custom')        
         
    def onSetPredefinedTarget(self):
        ppm, ppm_tol = self.peak_targets[ self.peak_target_cb.currentText() ]
        if ppm is not None:
            self._automated_update_config = True
            self.config.set('peak_target_ppm', ppm)
            self.config.set('peak_target_ppm_tolerance', ppm_tol)
            self._automated_update_config = False


class PeakAdjApp( ui.IPythonApp ):

    name = "Peak Scale & Shift"
    notebook = 'spectra_peakadj.ipynb'

    legacy_loaders = ['NMRPeakAdj.NMRPeakAdjApp']
    legacy_inputs = {'input': 'input_data'}
    legacy_outputs = {'output': 'output_data'}
    
    def __init__(self, **kwargs):
        super(PeakAdjApp, self).__init__(**kwargs)
        
        self.addDataToolBar()
        self.addFigureToolBar()
        
        self.data.add_input('input_data') # Add input slot        
        self.data.add_output('output_data')
        self.data.add_output('region')
    
        
        # Setup data consumer options
        self.data.consumer_defs.append( 
            DataDefinition('input_data', {
            'labels_n':     ('>0', None),
            'entities_t':   (None, None), 
            'scales_t': (None, ['float']),
            })
        )
        
        # Define default settings for pathway rendering
        self.config.set_defaults({
            # Peak target
            'peak_target': 'TMSP',
            'peak_target_ppm': 0.0,
            'peak_target_ppm_tolerance': 0.5,
            # Shifting
            'shifting_enabled': True,
            
            # Scaling
            'scaling_enabled': True,
        })        

        self.addConfigPanel( PeakAdjConfigPanel, 'Settings')

        self.finalise()



# Dialog box for Metabohunter search options
class PeakPickConfigPanel(ui.ConfigPanel):
    
    def __init__(self, *args, **kwargs):
        super(PeakPickConfigPanel, self).__init__(*args, **kwargs)        


        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setDecimals(5)
        self.threshold_spin.setRange(0.00001,1)
        self.threshold_spin.setSuffix('rel')
        self.threshold_spin.setSingleStep(0.00001)
        tl = QLabel('Threshold')
        self.layout.addWidget(tl)
        self.layout.addWidget(self.threshold_spin)
        self.config.add_handler('peak_threshold', self.threshold_spin)

        self.separation_spin = QDoubleSpinBox()
        self.separation_spin.setDecimals(1)
        self.separation_spin.setRange(0,5)
        self.separation_spin.setSingleStep(0.5)
        tl = QLabel('Peak separation')
        self.layout.addWidget(tl)
        self.layout.addWidget(self.separation_spin)
        self.config.add_handler('peak_separation', self.separation_spin)

        self.algorithms = {
            'Connected':'connected',
            'Threshold':'thres',
            'Threshold (fast)':'thres-fast',
            'Downward':'downward',
        }

        self.algorithm_cb = QComboBox()
        self.algorithm_cb.addItems( [k for k,v in list(self.algorithms.items()) ] )
        tl = QLabel('Algorithm')
        self.layout.addWidget(tl)
        self.layout.addWidget(self.algorithm_cb)  
        self.config.add_handler('algorithm', self.algorithm_cb)

        self.finalise()
        

class PeakPickingApp( ui.IPythonApp ):

    name = "Peak picking"
    notebook = 'spectra_peak_pick.ipynb'
    
    legacy_loaders = ['NMRPeakPicking.NMRPeakPickingApp']
    legacy_inputs = {'input': 'input_data'}
    legacy_outputs = {'output': 'output_data'}


    def __init__(self, **kwargs):
        super(PeakPickingApp, self).__init__(**kwargs)
        
        self.addDataToolBar()
        self.addFigureToolBar()
        
        self.data.add_input('input_data') # Add input slot        
        self.data.add_output('output_data')
        
        # Setup data consumer options
        self.data.consumer_defs.append( 
            DataDefinition('input_data', {
            'labels_n':     ('>0', None),
            'entities_t':   (None, None), 
            'scales_t': (None, ['float']),
            })
        )
        
        
        self.config.set_defaults({
            'peak_threshold': 0.05,
            'peak_separation': 0.5,
            'peak_algorithm': 'Threshold',
        })

        self.addConfigPanel( PeakPickConfigPanel, 'Settings')


        self.finalise()



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

    name = "Spectra Binning (1D)"
    notebook = 'spectra_binning.ipynb'
    
    legacy_loaders = ['Binning.BinningApp']
    legacy_inputs = {'input': 'input_data'}
    legacy_outputs = {'output': 'output_data'}


    def __init__(self, **kwargs):
        super(BinningApp, self).__init__(**kwargs)

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

        self.addConfigPanel(BinningConfigPanel, 'Settings')

        self.finalise()


 
class Spectra(ProcessingPlugin):

    def __init__(self, **kwargs):
        super(Spectra, self).__init__(**kwargs)
        self.register_app_launcher(SpectraNormApp)
        self.register_app_launcher(PeakAdjApp)
        self.register_app_launcher(PeakPickingApp)
        self.register_app_launcher(BinningApp)
