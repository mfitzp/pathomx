# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os

from pathomx.plugins import ImportPlugin

from PIL import Image

from pathomx.qt import *

import pathomx.ui as ui
import pathomx.utils as utils

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


class ImportImageConfigPanel(ui.ConfigPanel):

    def __init__(self, parent, filename=None, *args, **kwargs):
        super(ImportImageConfigPanel, self).__init__(parent, *args, **kwargs)

        self.v = parent
        self.config = parent.config
        gb = QGroupBox('Open file')
        grid = QGridLayout()
        self.filename = ui.QFileOpenLineEdit(filename_filter="""All compatible files 
(*.bmp *.dib *.eps *.gif *.im *.jpg *.jpe *.jpeg *.pcx *.pcd *.psd *.png *.pbm *.pgm *.ppm *.spi *.sgi *.tif *.tiff *.xbm *.xpm);;
Bitmap Image File (*.bmp *.dib);;Encapsulated PostScript (*.eps);;
Graphics Interchange Format (*.gif);;IM (LabEye) Format (*.im);;
Joint Photographic Experts Group (*.jpg *.jpe *.jpeg);;
Personal Computer Exchange (*.pcx);;PhotoCD Format (*.pcd);;Photoshop Document (*.psd);;
Portable Network Graphics (*.png);;Portable Bitmap/NetPBM (*.pbm *.pgm *.ppm);;
Truevision TGA (*.tga);;
Tagged Image File Format (*.tif *.tiff);;
Silicon Graphics Image (*.sgi);;
SPIDER Format (*.spi);;
WebP Format (*.webp);;
X Bitmap (*.xbm);;X Pixmap (*.xpm);;All files (*.*)""",description="Open image file")
        grid.addWidget(QLabel('Path'), 0, 0)
        grid.addWidget(self.filename, 0, 1)
        self.config.add_handler('filename', self.filename)
        
        self.cb_color = QComboBox()
        self.cb_color.addItems(list(COLORSPACES.keys()))
        grid.addWidget(QLabel('Mode'), 2, 0)
        grid.addWidget(self.cb_color, 2, 1)
        self.config.add_handler('colorspace', self.cb_color, COLORSPACES)
        
        gb.setLayout(grid)

        self.layout.addWidget(gb)

        self.finalise()


class ImportImageApp(ui.GenericTool):

    shortname = 'import_image'
    autoconfig_name = "{filename}"

    def __init__(self, *args, **kwargs):
        super(ImportImageApp, self).__init__(*args, **kwargs)

        self.config.set_defaults({
            'filename': None,
            'colorspace': None,
        })

        self.addConfigPanel(ImportImageConfigPanel, 'Settings')

        self.data.add_output('output_image')  # Add output slot




class ImportImage(ImportPlugin):

    def __init__(self, *args, **kwargs):
        super(ImportImage, self).__init__(*args, **kwargs)
        self.register_app_launcher(ImportImageApp)
        
        self.register_file_handler(ImportImageApp, 'png')
        self.register_file_handler(ImportImageApp, 'tif')
        self.register_file_handler(ImportImageApp, 'tiff')
        self.register_file_handler(ImportImageApp, 'jpeg')
        self.register_file_handler(ImportImageApp, 'jpg')
