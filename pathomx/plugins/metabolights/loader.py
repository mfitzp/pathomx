# -*- coding: utf-8 -*-

from pathomx.tools import BaseTool
from pathomx.ui import SimpleFileOpenConfigPanel

from pathomx.plugins import ImportPlugin


class MetabolightsConfigPanel(SimpleFileOpenConfigPanel):

    filename_filter = "All compatible files (*.csv);;Comma Separated Values (*.csv);;All files (*.*)"
    description = "Open experimental data from Metabolights experimental datasets"


class ImportMetabolightsApp(BaseTool):

    shortname = 'metabolights'
    autoconfig_name = "{filename}"

    category = "Import"
    subcategory = "Metabolomics"

    def __init__(self, *args, **kwargs):
        super(ImportMetabolightsApp, self).__init__(*args, **kwargs)

        self.config.set_defaults({
            'filename': None,
        })

        self.data.add_output('output_data')  # Add output slot        

        self.addConfigPanel(MetabolightsConfigPanel, 'Settings')


class ImportMetabolights(ImportPlugin):

    def __init__(self, *args, **kwargs):
        super(ImportMetabolights, self).__init__(*args, **kwargs)
        self.register_app_launcher(ImportMetabolightsApp)
