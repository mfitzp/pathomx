# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from pathomx.tools import BaseTool
from pathomx.ui import ConfigPanel
from pathomx.plugins import ProcessingPlugin
from pathomx.qt import *

STAIN_TYPES = {
    'Hematoxylin + Eosin + DAB': 'hed_from_rgb',
    'Hematoxylin + DAB': 'hdx_from_rgb',
    'Feulgen + Light Green': 'fgx_from_rgb',
    'Giemsa stain (Methyl Blue + Eosin)': 'bex_from_rgb',
    'FastRed + FastBlue + DAB': 'rbd_from_rgb',
    'Methyl Green + DAB': 'gdx_from_rgb',
    'Hematoxylin + AEC': 'hax_from_rgb',
    'Blue matrix Anilline Blue + Red matrix Azocarmine + Orange matrix Orange-G': 'bro_from_rgb',
    'Methyl Blue + Ponceau Fuchsin': 'bpx_from_rgb',
    'Alcian Blue + Hematoxylin': 'ahx_from_rgb',
    'Hematoxylin + PAS': 'hpx_from_rgb',
}


class SeparateStainsConfigPanel(ConfigPanel):

    def __init__(self, parent, filename=None, *args, **kwargs):
        super(SeparateStainsConfigPanel, self).__init__(parent, *args, **kwargs)

        self.v = parent
        self.config = parent.config
        gb = QGroupBox('Stain')
        grid = QGridLayout()

        self.cb_stain = QComboBox()
        self.cb_stain.addItems(list(STAIN_TYPES.keys()))
        grid.addWidget(QLabel('Stain'), 2, 0)
        grid.addWidget(self.cb_stain, 2, 1)
        self.config.add_handler('stain', self.cb_stain, STAIN_TYPES)

        gb.setLayout(grid)

        self.layout.addWidget(gb)

        self.finalise()


class SeperateStainsApp(BaseTool):

    name = "Separate Stains"

    shortname = 'separate_stains'
    autoconfig_name = "{filename}"

    category = "Processing"
    subcategory = "Immunohistochemistry"

    def __init__(self, *args, **kwargs):
        super(SeperateStainsApp, self).__init__(*args, **kwargs)

        self.config.set_defaults({
            'stain': 'hdx_from_rgb',
        })

        self.addConfigPanel(SeparateStainsConfigPanel, 'Settings')

        self.data.add_input('input_image')
        for o in ('Hematoxylin', 'Eosin', 'DAB', 'Feulgen', 'LightGreen', 'MethylBlue',
                    'FastRed', 'FastBlue', 'MethylGreen', 'Hematoxylin', 'AEC',
                    'AnillineBlue', 'Azocarmine', 'OrangeG', 'MethylBlue',
                    'PonceauFuchsin', 'AlcianBlue', 'Hematoxylin', 'PAS'):
            self.data.add_output(o)  # FIXME: Auto-hide some outputs (auto-delete; only if unconnected; etc. ? needs modifications in the editor)


class Immunohistochemistry(ProcessingPlugin):

    def __init__(self, *args, **kwargs):
        super(Immunohistochemistry, self).__init__(*args, **kwargs)
        self.register_app_launcher(SeperateStainsApp)
