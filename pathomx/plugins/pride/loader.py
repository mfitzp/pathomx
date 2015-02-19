# -*- coding: utf-8 -*-

from pathomx.ui import SimpleFileOpenConfigPanel
from pathomx.tools import BaseTool

from pathomx.plugins import ImportPlugin


class PRIDEConfigPanel(SimpleFileOpenConfigPanel):

    filename_filter = "All compatible files (*.zip);;Zipped PRIDE data files (*.*);;All files (*.*)"
    description = "Import experimental data from PRIDE experimental datasets"


class ImportPRIDETool(BaseTool):

    shortname = 'pride'
    autoconfig_name = "{filename}"

    legacy_outputs = {'output': 'output_data'}

    category = "Import"
    subcategory = "Proteomics"

    def __init__(self, *args, **kwargs):
        super(ImportPRIDETool, self).__init__(*args, **kwargs)

        self.config.set_defaults({
            'filename': None,
        })

        self.data.add_output('output_data')  # Add output slot

        self.addConfigPanel(PRIDEConfigPanel, "Settings")


class ImportPRIDE(ImportPlugin):

    def __init__(self, *args, **kwargs):
        super(ImportPRIDE, self).__init__(*args, **kwargs)
        self.register_app_launcher(ImportPRIDETool)
