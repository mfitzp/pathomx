# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from pathomx.plugins import ProcessingPlugin

from pathomx.qt import *
from pathomx.ui import ConfigPanel, QColorButton
from pathomx.tools import BaseTool

from pathomx.data import ImageDataDefinition

COLORSPACES = {
    'None (use image default)': None,
    'I (1-bit pixels, black and white, stored with one pixel per byte)': 'I',
    'L (8-bit pixels, black and white)': 'L',
    'P (8-bit pixels, mapped to any other mode using a color palette)': 'P',
    'RGB (3x8-bit pixels, true color)': 'RGB',
    'RGBA (4x8-bit pixels, true color with transparency mask)': 'RGBA',
    'CMYK (4x8-bit pixels, color separation)': 'CMYK',
    'YCbCr (3x8-bit pixels, color video format)': 'YCbCr',
    'LAB (3x8-bit pixels, the L*a*b color space)': 'LAB',
    'HSV (3x8-bit pixels, Hue, Saturation, Value color space)': 'HSV',
    'I (32-bit signed integer pixels)': 'I',
    'F (32-bit floating point pixels)': 'F',
}


class EnhanceConfigPanel(ConfigPanel):

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


class AdjustApp(BaseTool):

    name = "Image Adjust"
    shortname = 'adjust'

    subcategory = "Image"

    autoconfig_name = "Br{brightness} Ct{contrast} Co{color} Sh{sharpness}"

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

        self.data.consumer_defs.append(
            ImageDataDefinition('input_image', {
            })
        )


class ChopsConfigPanel(ConfigPanel):
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


class ChopsApp(BaseTool):

    name = "Channel Operations"
    shortname = 'chops'

    subcategory = "Image"

    autoconfig_name = "{operation}"

    def __init__(self, *args, **kwargs):
        super(ChopsApp, self).__init__(*args, **kwargs)

        self.config.set_defaults({
            'operation': 'add_modulo'
        })

        self.addConfigPanel(ChopsConfigPanel, 'Settings')

        self.data.add_input('image1')
        self.data.add_input('image2')
        self.data.add_output('output_image')


class InvertApp(BaseTool):

    name = "Invert Image"
    shortname = 'invert'

    subcategory = "Image"

    def __init__(self, *args, **kwargs):
        super(InvertApp, self).__init__(*args, **kwargs)

        self.config.set_defaults({
        })

        self.data.add_input('input_image')
        self.data.add_output('output_image')

        self.data.consumer_defs.append(
            ImageDataDefinition('input_image', {
            })
        )


class FilterConfigPanel(ConfigPanel):
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


class FilterApp(BaseTool):

    name = "Basic Filter"
    shortname = 'filter'

    subcategory = "Image"

    autoconfig_name = "{filter}"

    def __init__(self, *args, **kwargs):
        super(FilterApp, self).__init__(*args, **kwargs)

        self.config.set_defaults({
            'filter': 'smooth'
        })

        self.addConfigPanel(FilterConfigPanel, 'Settings')

        self.data.add_input('input_image')
        self.data.add_output('output_image')

        self.data.consumer_defs.append(
            ImageDataDefinition('input_image', {
            })
        )


# Dialog box for Metabohunter search options
class ColorspaceConfigPanel(ConfigPanel):

    def __init__(self, parent, filename=None, *args, **kwargs):
        super(ColorspaceConfigPanel, self).__init__(parent, *args, **kwargs)

        self.v = parent
        self.config = parent.config
        gb = QGroupBox('Modify Colorspace')
        grid = QGridLayout()

        self.cb_color = QComboBox()
        self.cb_color.addItems(list(COLORSPACES.keys()))
        grid.addWidget(QLabel('Colorspace'), 1, 0)
        grid.addWidget(self.cb_color, 1, 1)
        self.config.add_handler('colorspace', self.cb_color, COLORSPACES)

        gb.setLayout(grid)

        self.layout.addWidget(gb)

        self.finalise()


class ColorspaceApp(BaseTool):

    name = "Convert Colorspace"
    shortname = 'colorspace'
    icon = 'colorspace.png'

    subcategory = "Image"

    autoconfig_name = "{colorspace}"

    def __init__(self, *args, **kwargs):
        super(ColorspaceApp, self).__init__(*args, **kwargs)

        self.config.set_defaults({
            'colorspace': None,
        })

        self.addConfigPanel(ColorspaceConfigPanel, 'Settings')

        self.data.add_input('input_image')
        self.data.add_output('output_image')  # Add output slot

        self.data.consumer_defs.append(
            ImageDataDefinition('input_image', {
            })
        )


class HistogramApp(BaseTool):

    name = "Image Histogram"
    shortname = 'histogram'

    category = "Analysis"
    subcategory = "Image"

    def __init__(self, *args, **kwargs):
        super(HistogramApp, self).__init__(*args, **kwargs)

        self.config.set_defaults({
        })

        self.data.add_input('input_image')
        self.data.add_output('output_image')  # Add output slot

        self.data.consumer_defs.append(
            ImageDataDefinition('input_image', {
            })
        )


class ColorizeConfigPanel(ConfigPanel):

    def __init__(self, parent, filename=None, *args, **kwargs):
        super(ColorizeConfigPanel, self).__init__(parent, *args, **kwargs)

        self.v = parent
        self.config = parent.config
        gb = QGroupBox('Colorize')
        grid = QGridLayout()

        self.cb_black = QColorButton()
        grid.addWidget(QLabel('Black'), 0, 0)
        grid.addWidget(self.cb_black, 0, 1)
        self.config.add_handler('black', self.cb_black)

        self.cb_white = QColorButton()
        grid.addWidget(QLabel('White'), 1, 0)
        grid.addWidget(self.cb_white, 1, 1)
        self.config.add_handler('white', self.cb_white)

        gb.setLayout(grid)

        self.layout.addWidget(gb)

        self.finalise()


class ColorizeApp(BaseTool):

    name = "Colorize"
    shortname = 'colorize'
    icon = 'colorize.png'

    subcategory = "Image"

    autoconfig_name = "{black}…{white}"

    def __init__(self, *args, **kwargs):
        super(ColorizeApp, self).__init__(*args, **kwargs)

        self.config.set_defaults({
            'black': '#000000',
            'white': '#ffffff',
        })

        self.addConfigPanel(ColorizeConfigPanel, 'Settings')

        self.data.add_input('input_image')
        self.data.add_output('output_image')

        self.data.consumer_defs.append(
            ImageDataDefinition('input_image', {
            })
        )


class Pillow(ProcessingPlugin):

    def __init__(self, *args, **kwargs):
        super(Pillow, self).__init__(*args, **kwargs)
        self.register_app_launcher(AdjustApp)
        self.register_app_launcher(ChopsApp)
        self.register_app_launcher(InvertApp)
        self.register_app_launcher(FilterApp)
        self.register_app_launcher(ColorspaceApp)
        self.register_app_launcher(HistogramApp)
        self.register_app_launcher(ColorizeApp)
