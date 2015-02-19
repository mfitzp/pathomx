# -*- coding: utf-8 -*-
from pathomx.ui import SimpleFileOpenConfigPanel
from pathomx.tools import BaseTool

from pathomx.plugins import ImportPlugin


class MaxQuantConfigPanel(SimpleFileOpenConfigPanel):

    filename_filter = "All compatible files (*.csv *.txt *.tsv);;All files (*.*)"
    description = "Open a MaxQuant output file"


class MaxQuantApp(BaseTool):

    shortname = 'maxquant'
    autoconfig_name = "{filename}"

    category = "Import"
    subcategory = "Proteomics"

    def __init__(self, *args, **kwargs):
        super(MaxQuantApp, self).__init__(*args, **kwargs)

        self.config.set_defaults({
            'filename': None,
        })

        self.data.add_output('output_data')  # Add output slot

        self.addConfigPanel(MaxQuantConfigPanel, 'Settings')


class MaxQuant(ImportPlugin):

    def __init__(self, *args, **kwargs):
        super(MaxQuant, self).__init__(*args, **kwargs)
        self.register_app_launcher(MaxQuantApp)
