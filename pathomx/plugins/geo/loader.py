# -*- coding: utf-8 -*-
from pathomx.ui import SimpleFileOpenConfigPanel
from pathomx.tools import BaseTool
from pathomx.plugins import ImportPlugin


class GEOConfigPanel(SimpleFileOpenConfigPanel):

    filename_filter = "All compatible files (*.soft);;Simple Omnibus Format in Text (*.soft);;All files (*.*)"
    description = "Open experimental data from downloaded data"


class GEOApp(BaseTool):

    shortname = 'geo'
    autoconfig_name = "{filename}"

    legacy_outputs = {'output': 'output_data'}

    category = "Import"
    subcategory = "Transcriptomics"

    def __init__(self, *args, **kwargs):
        super(GEOApp, self).__init__(*args, **kwargs)

        self.config.set_defaults({
            'filename': None,
        })

        self.data.add_output('output_data')  # Add output slot
        self.addConfigPanel(GEOConfigPanel, 'Settings')


class GEO(ImportPlugin):

    def __init__(self, *args, **kwargs):
        super(GEO, self).__init__(*args, **kwargs)
        self.register_app_launcher(GEOApp)
        self.register_file_handler(GEOApp, 'soft')
