# -*- coding: utf-8 -*-

from pathomx.tools import BaseTool
from pathomx.ui import SimpleFileOpenConfigPanel

from pathomx.plugins import ImportPlugin


class PeakMLConfigPanel(SimpleFileOpenConfigPanel):

    filename_filter = "PeakML (MzMatch) Data Files (*.peakml);;All files (*.*)"
    description = "Open experimental data from PeakML data files"


class ImportPeakMLApp(BaseTool):

    shortname = 'import_peakml'
    autoconfig_name = "{filename}"

    legacy_outputs = {'output': 'output_data'}

    category = "Import"
    subcategory = "Mass Spectrometry"

    def __init__(self, *args, **kwargs):
        super(ImportPeakMLApp, self).__init__(*args, **kwargs)

        self.config.set_defaults({
            'filename': None,
        })

        self.data.add_output('output_data')  # Add output slot

        self.addConfigPanel(PeakMLConfigPanel, 'Settings')


class ImportPeakML(ImportPlugin):

    def __init__(self, *args, **kwargs):
        super(ImportPeakML, self).__init__(*args, **kwargs)
        self.register_app_launcher(ImportPeakMLApp)
