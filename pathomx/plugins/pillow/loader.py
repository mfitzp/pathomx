# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os

from pathomx.plugins import ProcessingPlugin

from PIL import Image

from pathomx.qt import *

import pathomx.ui as ui
import pathomx.utils as utils


class EnhanceConfigPanel(ui.ConfigPanel):

    def __init__(self, parent, filename=None, *args, **kwargs):
        super(EnhanceConfigPanel, self).__init__(parent, *args, **kwargs)

        self.v = parent
        self.config = parent.config
        gb = QGroupBox('Enhance')
        grid = QGridLayout()

        self.bright = QSlider(Qt.Horizontal)
        self.bright.setRange(0, 200)
        self.bright.setSingleStep(10)
        self.bright.setPageStep(50)
        grid.addWidget(QLabel('Brightness'), 0, 0)
        grid.addWidget(self.bright, 0, 1)
        self.config.add_handler('brightness', self.bright)

        self.contrast = QSlider(Qt.Horizontal)
        self.contrast.setRange(0, 200)
        self.contrast.setSingleStep(10)
        self.contrast.setPageStep(50)
        grid.addWidget(QLabel('Contrast'), 1, 0)
        grid.addWidget(self.contrast, 1, 1)
        self.config.add_handler('contrast', self.contrast)

        self.color = QSlider(Qt.Horizontal)
        self.color.setRange(0, 200)
        self.color.setSingleStep(10)
        self.color.setPageStep(50)
        grid.addWidget(QLabel('Color'), 2, 0)
        grid.addWidget(self.color, 2, 1)
        self.config.add_handler('color', self.color)
        
        self.sharp = QSlider(Qt.Horizontal)
        self.sharp.setRange(0, 200)
        self.sharp.setSingleStep(10)
        self.sharp.setPageStep(50)
        grid.addWidget(QLabel('Sharp'), 3, 0)
        grid.addWidget(self.sharp, 3, 1)
        self.config.add_handler('sharpness', self.sharp)
        
        gb.setLayout(grid)

        self.layout.addWidget(gb)

        self.finalise()


class AdjustApp(ui.GenericTool):

    name = "Image Adjust"
    shortname = 'adjust'

    def __init__(self, *args, **kwargs):
        super(AdjustApp, self).__init__(*args, **kwargs)

        self.config.set_defaults({
            'brightness': 100,
            'contrast': 100,
            'color': 100,
            'sharpness': 100,
        })

        self.addConfigPanel(EnhanceConfigPanel, 'Settings')

        self.data.add_input('input_image')  # Add output slot
        self.data.add_output('output_image')  # Add output slot





class ChopsConfigPanel(ui.ConfigPanel):
    operation_types = {
        'Add (Modulo)': 'add_modulo',
        'Darker': 'darker',
        'Difference': 'difference',
        'Lighter': 'lighter',
        'Logical AND': 'logical_and',
        'Logical OR': 'logical_or',
        'Multiply': 'multiply',
        'Screen': 'screen',
        'Subtract (Modulo)': 'subtract_modulo',
    }

    def __init__(self, parent, *args, **kwargs):
        super(ChopsConfigPanel, self).__init__(parent, *args, **kwargs)

        self.v = parent
        self.config = parent.config
        gb = QGroupBox('Channel Operations')
        grid = QGridLayout()

        self.cb_op = QComboBox()
        self.cb_op.addItems(list(self.operation_types.keys()))
        grid.addWidget(QLabel('Operation'), 1, 0)
        grid.addWidget(self.cb_op, 1, 1)
        self.config.add_handler('operation', self.cb_op, self.operation_types)
        gb.setLayout(grid)

        self.layout.addWidget(gb)

        self.finalise()


class ChopsApp(ui.GenericTool):

    name = "Channel Operations"
    shortname = 'chops'

    def __init__(self, *args, **kwargs):
        super(ChopsApp, self).__init__(*args, **kwargs)

        self.config.set_defaults({
            'operation': 'add'
        })

        self.addConfigPanel(ChopsConfigPanel, 'Settings')

        self.data.add_input('image1')
        self.data.add_input('image2')
        self.data.add_output('output_image')



class FilterConfigPanel(ui.ConfigPanel):
    filter_types = {
        'Contour': 'contour',
        'Detail': 'detail',
        'Edge Enhance': 'edge_enhance',
        'Edge Enhance (More)': 'edge_enhance_more',
        'Emboss': 'emboss',
        'Find Edges': 'find_edges',
        'Smooth': 'smooth',
        'Smooth (More)': 'smooth_more',
        'Sharpen': 'sharpen',
    }

    def __init__(self, parent, *args, **kwargs):
        super(FilterConfigPanel, self).__init__(parent, *args, **kwargs)

        self.v = parent
        self.config = parent.config
        gb = QGroupBox('Apply Filter')
        grid = QGridLayout()

        self.cb_op = QComboBox()
        self.cb_op.addItems(list(self.filter_types.keys()))
        grid.addWidget(QLabel('Filter'), 1, 0)
        grid.addWidget(self.cb_op, 1, 1)
        self.config.add_handler('filter', self.cb_op, self.filter_types)
        gb.setLayout(grid)

        self.layout.addWidget(gb)

        self.finalise()


class FilterApp(ui.GenericTool):

    name = "Image Filter"
    shortname = 'filter'

    def __init__(self, *args, **kwargs):
        super(FilterApp, self).__init__(*args, **kwargs)

        self.config.set_defaults({
            'filter': 'smooth'
        })

        self.addConfigPanel(FilterConfigPanel, 'Settings')

        self.data.add_input('input_image')
        self.data.add_output('output_image')




class Pillow(ProcessingPlugin):

    def __init__(self, *args, **kwargs):
        super(Pillow, self).__init__(*args, **kwargs)
        self.register_app_launcher(AdjustApp)
        self.register_app_launcher(ChopsApp)
        self.register_app_launcher(FilterApp)

