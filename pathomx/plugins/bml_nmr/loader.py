# -*- coding: utf-8 -*-

from pathomx.tools import BaseTool
from pathomx.plugins import ImportPlugin
from pathomx.ui import SimpleFileOpenConfigPanel


class BMLNMRConfigPanel(SimpleFileOpenConfigPanel):
    filename_filter = "Compressed Files (*.zip);;All files (*.*)"
    description = "Open BML-NMR FIMA .zip output"


class BMLNMRApp(BaseTool):

    shortname = 'bml_nmr'
    autoconfig_name = "{filename}"

    category = "Import"
    subcategory = "Metabolomics"

    def __init__(self, *args, **kwargs):
        super(BMLNMRApp, self).__init__(*args, **kwargs)

        self.config.set_defaults({
            'filename': None,
        })

        self.data.add_output('raw')  # Add output slot
        self.data.add_output('pqn')  # Add output slot
        self.data.add_output('tsa')  # Add output slot

        self.addConfigPanel(BMLNMRConfigPanel, "Settings")


class BMLNMR(ImportPlugin):

    def __init__(self, *args, **kwargs):
        super(BMLNMR, self).__init__(*args, **kwargs)
        self.register_app_launcher(BMLNMRApp)
