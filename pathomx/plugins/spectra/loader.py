# -*- coding: utf-8 -*-
from pathomx.plugins import ProcessingPlugin
import pathomx.ui as ui

from pathomx.data import DataDefinition, PandasDataDefinition
from pathomx.qt import *


# Dialog box for Metabohunter search options
class SpectraNormConfigPanel(ui.ConfigPanel):

    algorithms = ['PQN', 'TSA']

    def __init__(self, *args, **kwargs):
        super(SpectraNormConfigPanel, self).__init__(*args, **kwargs)

        self.algorithm_cb = QComboBox()
        self.algorithm_cb.addItems(self.algorithms)
        self.config.add_handler('algorithm', self.algorithm_cb)

        tl = QLabel('Scaling algorithm')
        tl.setIndent(5)
        self.layout.addWidget(tl)
        self.layout.addWidget(self.algorithm_cb)

        self.finalise()


class SpectraNormApp(ui.IPythonApp):

    name = "Spectra normalisation"
    notebook = 'spectra_norm.ipynb'
    shortname = 'spectra_norm'

    legacy_launchers = ['SpectraNorm.SpectraNormApp']
    legacy_inputs = {'input': 'input_data'}
    legacy_outputs = {'output': 'output_data'}

    autoconfig_name = "{algorithm}"

    def __init__(self, *args, **kwargs):
        super(SpectraNormApp, self).__init__(*args, **kwargs)

        self.data.add_input('input_data')  # Add input slot
        self.data.add_output('output_data')

        # Setup data consumer options
        self.data.consumer_defs.append(
            PandasDataDefinition('input_data', {
                'shape': ['>0', '>0']
            })
        )

        self.config.set_defaults({
            'algorithm': 'PQN',
        })

        self.addConfigPanel(SpectraNormConfigPanel, 'Settings')


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
        self.peak_target_cb.addItems([k for k, v in list(self.peak_targets.items())])
        self.peak_target_cb.currentIndexChanged.connect(self.onSetPredefinedTarget)
        self.config.add_handler('peak_target', self.peak_target_cb)
        vw.addWidget(self.peak_target_cb, 0, 0, 1, 2)

        self.ppm_spin = QDoubleSpinBox()
        self.ppm_spin.setDecimals(2)
        self.ppm_spin.setRange(-1, 15)
        self.ppm_spin.setSuffix('ppm')
        self.ppm_spin.setSingleStep(0.05)
        self.ppm_spin.valueChanged.connect(self.onSetCustomTarget)  # Additional; to handle alternation
        self.config.add_handler('peak_target_ppm', self.ppm_spin)
        vw.addWidget(self.ppm_spin, 1, 1, 1, 1)

        self.ppm_tolerance_spin = QDoubleSpinBox()
        self.ppm_tolerance_spin.setDecimals(2)
        self.ppm_tolerance_spin.setRange(0, 1)
        self.ppm_tolerance_spin.setSuffix('ppm')
        self.ppm_tolerance_spin.setSingleStep(0.05)
        self.ppm_tolerance_spin.valueChanged.connect(self.onSetCustomTarget)  # Additional; to handle alternation
        self.config.add_handler('peak_target_ppm_tolerance', self.ppm_tolerance_spin)
        tl = QLabel('±')
        tl.setAlignment(Qt.AlignRight)
        vw.addWidget(tl, 2, 0, 1, 1)
        vw.addWidget(self.ppm_tolerance_spin, 2, 1, 1, 1)

        gb = QGroupBox('Peak target')
        gb.setLayout(vw)
        self.layout.addWidget(gb)

        vw = QVBoxLayout()
        self.toggle_shift = QPushButton(QIcon(os.path.join(self.parent().t.plugin.path, 'icon.png')), 'Shift spectra', self.parent())
        self.toggle_shift.setCheckable(True)
        self.config.add_handler('shifting_enabled', self.toggle_shift)
        vw.addWidget(self.toggle_shift)

        self.toggle_scale = QPushButton(QIcon(os.path.join(self.parent().t.plugin.path, 'icon.png')), 'Scale spectra', self.parent())
        self.toggle_scale.setCheckable(True)
        self.config.add_handler('scaling_enabled', self.toggle_scale)
        vw.addWidget(self.toggle_scale)

        gb = QGroupBox('Toggle shift and scale')
        gb.setLayout(vw)
        self.layout.addWidget(gb)

        self.finalise()

    def onSetCustomTarget(self):
        if self._automated_update_config is False:
            self.peak_target_cb.setCurrentText('Custom')

    def onSetPredefinedTarget(self):
        ppm, ppm_tol = self.peak_targets[self.peak_target_cb.currentText()]
        if ppm is not None:
            self._automated_update_config = True
            self.config.set('peak_target_ppm', ppm)
            self.config.set('peak_target_ppm_tolerance', ppm_tol)
            self._automated_update_config = False


class PeakAdjApp(ui.IPythonApp):

    name = "Peak Scale & Shift"
    notebook = 'spectra_peakadj.ipynb'
    shortname = 'spectra_peakadj'

    legacy_launchers = ['NMRPeakAdj.NMRPeakAdjApp']
    legacy_inputs = {'input': 'input_data'}
    legacy_outputs = {'output': 'output_data'}

    def __init__(self, *args, **kwargs):
        super(PeakAdjApp, self).__init__(*args, **kwargs)

        self.data.add_input('input_data')  # Add input slot
        self.data.add_output('output_data')
        self.data.add_output('region')

        # Setup data consumer options
        self.data.consumer_defs.append(
            PandasDataDefinition('input_data', {
                'shape': ['>0', '>0']
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

        self.addConfigPanel(PeakAdjConfigPanel, 'Settings')


# Dialog box for Metabohunter search options
class PeakPickConfigPanel(ui.ConfigPanel):

    def __init__(self, *args, **kwargs):
        super(PeakPickConfigPanel, self).__init__(*args, **kwargs)

        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setDecimals(5)
        self.threshold_spin.setRange(0.00001, 1)
        self.threshold_spin.setSuffix('rel')
        self.threshold_spin.setSingleStep(0.00001)
        tl = QLabel('Threshold')
        self.layout.addWidget(tl)
        self.layout.addWidget(self.threshold_spin)
        self.config.add_handler('peak_threshold', self.threshold_spin)

        self.separation_spin = QDoubleSpinBox()
        self.separation_spin.setDecimals(1)
        self.separation_spin.setRange(0, 5)
        self.separation_spin.setSingleStep(0.5)
        tl = QLabel('Peak separation')
        self.layout.addWidget(tl)
        self.layout.addWidget(self.separation_spin)
        self.config.add_handler('peak_separation', self.separation_spin)

        self.algorithms = {
            'Connected': 'connected',
            'Threshold': 'thres',
            'Threshold (fast)': 'thres-fast',
            'Downward': 'downward',
        }

        self.algorithm_cb = QComboBox()
        self.algorithm_cb.addItems([k for k, v in list(self.algorithms.items())])
        tl = QLabel('Algorithm')
        self.layout.addWidget(tl)
        self.layout.addWidget(self.algorithm_cb)
        self.config.add_handler('algorithm', self.algorithm_cb)

        self.finalise()


class PeakPickingApp(ui.IPythonApp):

    name = "Peak picking"
    notebook = 'spectra_peak_pick.ipynb'
    shortname = 'spectra_peak_pick'

    legacy_launchers = ['NMRPeakPicking.NMRPeakPickingApp']
    legacy_inputs = {'input': 'input_data'}
    legacy_outputs = {'output': 'output_data'}

    autoconfig_name = "{peak_algorithm} ≥{peak_threshold} ·{peak_separation}"

    def __init__(self, *args, **kwargs):
        super(PeakPickingApp, self).__init__(*args, **kwargs)

        self.data.add_input('input_data')  # Add input slot
        self.data.add_output('output_data')

        # Setup data consumer options
        self.data.consumer_defs.append(
            PandasDataDefinition('input_data', {
                'shape': ['>0', '>0']
            })
        )

        self.config.set_defaults({
            'peak_threshold': 0.05,
            'peak_separation': 0.5,
            'peak_algorithm': 'Threshold',
        })

        self.addConfigPanel(PeakPickConfigPanel, 'Settings')


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
    shortname = 'spectra_binning'

    legacy_launchers = ['Binning.BinningApp']
    legacy_inputs = {'input': 'input_data'}
    legacy_outputs = {'output': 'output_data'}

    autoconfig_name = "{bin_size}ppm {bin_offset}ppm"

    def __init__(self, *args, **kwargs):
        super(BinningApp, self).__init__(*args, **kwargs)

        self.data.add_input('input_data')  # Add input slot
        self.data.add_output('output_data')

        # Setup data consumer options
        self.data.consumer_defs.append(
            PandasDataDefinition('input_data', {
                'shape': ['>0', '>0']
            })
        )

        self.config.set_defaults({
            'bin_size': 0.01,
            'bin_offset': 0,
        })

        self.addConfigPanel(BinningConfigPanel, 'Settings')


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


class BaselineCorrectionTool(ui.IPythonApp):

    name = "Baseline correction"
    description = "Baseline correct NMR spectra"
    notebook = 'spectra_baseline.ipynb'
    shortname = 'spectra_baseline'

    legacy_launchers = ['BaselineCorrection.BaselineCorrectionTool']
    legacy_inputs = {'input': 'input_data'}
    legacy_outputs = {'output': 'output_data'}

    autoconfig_name = "{algorithm}"

    def __init__(self, *args, **kwargs):
        super(BaselineCorrectionTool, self).__init__(*args, **kwargs)

        self.data.add_input('input_data')  # Add input slot
        self.data.add_output('output_data')

        # Setup data consumer options
        self.data.consumer_defs.append(
            PandasDataDefinition('input_data', {
                'shape': ['>0', '>0']
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


class SpectraExclusionTool(ui.IPythonApp):

    name = "Spectra Exclusion"
    description = "Exclude regions of an NMR spectra"
    notebook = 'spectra_exclude.ipynb'
    shortname = 'spectra_exclude'

    def __init__(self, *args, **kwargs):
        super(SpectraExclusionTool, self).__init__(*args, **kwargs)

        self.data.add_input('input_data')  # Add input slot
        self.data.add_output('output_data')

        # Setup data consumer options
        self.data.consumer_defs.append(
            PandasDataDefinition('input_data', {
                'shape': ['>0', '>0']
            })
        )

        # Define default settings for pathway rendering
        self.config.set_defaults({

            'selected_data_regions': [
                ('TMSP', -2, 0, 0.2, 0),
                ('Water', 4.5, 0, 5, 0),
                ('Far', 10, 0, 12, 0),
            ],
        })

        self.addConfigPanel(ui.RegionConfigPanel, 'Regions')


class Spectra(ProcessingPlugin):

    def __init__(self, *args, **kwargs):
        super(Spectra, self).__init__(*args, **kwargs)
        self.register_app_launcher(SpectraNormApp)
        self.register_app_launcher(PeakAdjApp)
        self.register_app_launcher(PeakPickingApp)
        self.register_app_launcher(BinningApp)
        self.register_app_launcher(BaselineCorrectionTool)
        self.register_app_launcher(SpectraExclusionTool)
