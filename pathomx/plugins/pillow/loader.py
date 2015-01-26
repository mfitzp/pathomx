# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os

from pathomx.plugins import ProcessingPlugin

from PIL import Image

from pathomx.qt import *

import pathomx.ui as ui
import pathomx.utils as utils


# Dialog box for Metabohunter search options
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

    name = "Adjust Image"
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


class Pillow(ProcessingPlugin):

    def __init__(self, *args, **kwargs):
        super(Pillow, self).__init__(*args, **kwargs)
        self.register_app_launcher(AdjustApp)

