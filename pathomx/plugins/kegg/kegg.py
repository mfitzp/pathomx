# -*- coding: utf-8 -*-

# Renderer for GPML as SVG
from gpml2svg import gpml2svg

import os
import re

import pathomx.ui as ui
import pathomx.utils as utils

from pathomx.data import DataSet, DataDefinition
from pathomx.views import HTMLView
from pathomx.plugins import VisualisationPlugin
from pathomx.qt import *

import numpy as np

try:
    import xml.etree.cElementTree as et
except ImportError:
    import xml.etree.ElementTree as et


# Class for data visualisations using KEGG formatted pathways
# Supports loading from KEGG site
class KEGGPathwayApp(ui.AnalysisApp):

    notebook = 'kegg_pathway.ipynb'
    legacy_outputs = {'output': 'output_data'}

    def __init__(self, *args, **kwargs):
        super(KEGGPathwayApp, self).__init__(*args, **kwargs)

        self.svg = None  # Rendered GPML file as SVG
        self.metadata = {}
        #self.browser = ui.QWebViewExtend(self)
        #self.views.addTab(self.browser,'App')

        self.data.add_input('input_data')  # Add input slot
        # Setup data consumer options
        self.data.consumer_defs.append(
            DataDefinition('input_data', {
            'entities_t': (None, ['Compound', 'Gene']),
            }, 'Relative concentration data'),
        )

        self.config.set_defaults({
            'kegg_pathway_id': 'hsa00010',
        })

        self.addDataToolBar(default_pause_analysis=True)
        self.addFigureToolBar()

        self.kegg_pathway_t = QLineEdit()
        t = self.addToolBar('KEGG')
        t.setIconSize(QSize(16, 16))
        t.addWidget(self.kegg_pathway_t)

        self.config.add_handler('kegg_pathway_id', self.kegg_pathway_t)


class dialogWikiPathways(ui.remoteQueryDialog):
    def __init__(self, parent=None, query_target=None, **kwargs):
        super(dialogWikiPathways, self).__init__(parent, query_target, **kwargs)

        self.setWindowTitle("Load GPML pathway from WikiPathways")

    def parse(self, data):
        result = {}
        tree = et.fromstring(data.encode('utf-8'))
        pathways = tree.iterfind('{http://www.wso2.org/php/xsd}result')

        for p in pathways:
            result['%s (%s)' % (p.find('{http://www.wikipathways.org/webservice}name').text, p.find('{http://www.wikipathways.org/webservice}species').text)] = p.find('{http://www.wikipathways.org/webservice}id').text

        return result


class KEGG(VisualisationPlugin):

    def __init__(self, *args, **kwargs):
        super(KEGG, self).__init__(*args, **kwargs)
        KEGGPathwayApp.plugin = self
        self.register_app_launcher(KEGGPathwayApp)
