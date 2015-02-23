# -*- coding: utf-8 -*-

from pathomx.tools import BaseTool
from pathomx.ui import ConfigPanel, RegionConfigPanel, QNoneDoubleSpinBox
from pathomx.plugins import ProcessingPlugin
from pathomx.data import DataDefinition
from pathomx.qt import *

from collections import defaultdict

'''
def icoshift(xt,  xp,  inter='whole',  n='f', scale=None, coshift_preprocessing=False,
             coshift_preprocessing_max_shift=None, fill_with_previous=True, average2_multiplier=3):

'''


# Dialog box for Metabohunter search options
class IcoshiftConfigPanel(ConfigPanel):

    def __init__(self, *args, **kwargs):
        super(IcoshiftConfigPanel, self).__init__(*args, **kwargs)

        self.display_options = defaultdict(dict)
        self.config.updated.connect(self.change_display)

        gb = QGroupBox('Target')
        gd = QGridLayout()
        gb.setLayout(gd)
        self.target_cb = QComboBox()
        self.target_cb.addItems(['average', 'median', 'max', 'average2', 'input_target', 'spectra_number'])
        self.config.add_handler('target', self.target_cb)
        gd.addWidget(self.target_cb, 0, 0)

        average2_l = QLabel('Average2 multiplier')
        average2_sb = QSpinBox()
        gd.addWidget(average2_l, 1, 0)
        gd.addWidget(average2_sb, 1, 1)
        self.config.add_handler('average2_multiplier', average2_sb)
        self.display_options['target']['average2'] = (average2_l, average2_sb)

        spectran_l = QLabel('Spectra number')
        spectran_sb = QSpinBox()
        spectran_sb.setMinimum(0)
        gd.addWidget(spectran_l, 2, 0)
        gd.addWidget(spectran_sb, 2, 1)
        self.config.add_handler('spectra_number', spectran_sb)
        self.display_options['target']['spectra_number'] = (spectran_l, spectran_sb)

        self.layout.addWidget(gb)

        gb = QGroupBox('Intervals')
        gd = QGridLayout()
        gb.setLayout(gd)
        self.mode_cb = QComboBox()

        self.mode_cb.addItems(['whole', 'number_of_intervals', 'length_of_intervals', 'selected_intervals'])  # , 'define', 'reference_signal'])
        self.config.add_handler('intervals', self.mode_cb)
        gd.addWidget(self.mode_cb, 0, 0)

        number_int_l = QLabel('Number of intervals')
        number_int_sb = QSpinBox()

        self.config.add_handler('number_of_intervals', number_int_sb)
        gd.addWidget(number_int_l, 1, 0)
        gd.addWidget(number_int_sb, 1, 1)
        self.display_options['intervals']['number_of_intervals'] = (number_int_l, number_int_sb)

        length_intervals_l = QLabel('Length of intervals')
        length_intervals_sb = QSpinBox()
        self.config.add_handler('length_of_intervals', length_intervals_sb)
        gd.addWidget(length_intervals_l, 2, 0)
        gd.addWidget(length_intervals_sb, 2, 1)
        self.layout.addWidget(gb)
        self.display_options['intervals']['length_of_intervals'] = (length_intervals_l, length_intervals_sb)

        gb = QGroupBox('Maximum shift')
        gd = QGridLayout()
        gb.setLayout(gd)
        self.mode_cb = QComboBox()
        self.mode_cb.addItems(['n', 'b', 'f'])
        self.config.add_handler('maximum_shift', self.mode_cb)
        gd.addWidget(self.mode_cb, 0, 0)

        maxshift_l = QLabel('Max shift (n)')
        maxshift_sb = QSpinBox()
        self.config.add_handler('maximum_shift_n', maxshift_sb)
        gd.addWidget(maxshift_l, 1, 0)
        gd.addWidget(maxshift_sb, 1, 1)
        self.layout.addWidget(gb)
        self.display_options['maximum_shift']['n'] = (maxshift_l, maxshift_sb)

        gb = QGroupBox('Co-shift preprocessing')
        gd = QGridLayout()
        gb.setLayout(gd)

        self.coshift_btn = QCheckBox('Enable co-shift preprocessing')
        #self.coshift_btn.setCheckable( True )
        self.config.add_handler('coshift_preprocessing', self.coshift_btn)
        gd.addWidget(self.coshift_btn, 0, 0)

        self.coshift_max_cb = QNoneDoubleSpinBox()
        self.config.add_handler('coshift_preprocessing_max_shift', self.coshift_max_cb)
        gd.addWidget(QLabel('Maximum shift'), 1, 0)
        gd.addWidget(self.coshift_max_cb, 1, 1)

        self.layout.addWidget(gb)

        gb = QGroupBox('Miscellaneous')
        gd = QGridLayout()
        gb.setLayout(gd)

        self.fill_previous = QCheckBox('Fill shifted regions with previous value')
        #self.coshift_btn.setCheckable( True )
        self.config.add_handler('fill_with_previous', self.fill_previous)
        gd.addWidget(self.fill_previous, 0, 0)
        self.layout.addWidget(gb)

        self.change_display()  # Set starting state
        self.finalise()

    def change_display(self, *args):
        for k, v in self.display_options.items():
            ic = self.config.get(k)
            for i, o in v.items():
                for oo in o:
                    if i == ic:
                        oo.show()
                    else:
                        oo.hide()

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


class IcoshiftApp(BaseTool):

    notebook = 'icoshift_.ipynb'
    shortname = 'icoshift_'

    legacy_inputs = {'input': 'input_data'}
    legacy_outputs = {'output': 'output_data'}

    subcategory = "Spectra"

    def __init__(self, *args, **kwargs):
        super(IcoshiftApp, self).__init__(*args, **kwargs)

        self.data.add_input('input_data')  # Add input slot
        self.data.add_input('input_target')

        self.data.add_output('output_data')

        # Setup data consumer options
        # Setup data consumer options
        self.data.consumer_defs.append(
            DataDefinition('input_data', {
            'labels_n': (None, '>0'),
            'entities_t': (None, None),
            })
        )

        self.config.set_defaults({
            'target': 'average',
            'intervals': 'whole',
            'maximum_shift': 'f',
            'maximum_shift_n': 50,
            'coshift_preprocessing': False,
            'coshift_preprocessing_max_shift': None,
            'average2_multiplier': 3,
            'number_of_intervals': 50,
            'fill_with_previous': True,
            'spectra_number': 0,

            'selected_data_regions': [],
        })

        self.addConfigPanel(IcoshiftConfigPanel, 'Settings')
        self.addConfigPanel(RegionConfigPanel, 'Regions')


class Icoshift(ProcessingPlugin):

    def __init__(self, *args, **kwargs):
        super(Icoshift, self).__init__(*args, **kwargs)
        IcoshiftApp.plugin = self
        self.register_app_launcher(IcoshiftApp)
