# -*- coding: utf-8 -*-

# Renderer for GPML as SVG
from gpml2svg import gpml2svg

import os

import pathomx.ui as ui
import pathomx.db as db

import pathomx.utils as utils

from pathomx.plugins import VisualisationPlugin
from pathomx.data import DataSet, DataDefinition
from pathomx.views import HTMLView
from pathomx.qt import *

import numpy as np

try:
    import xml.etree.cElementTree as et
except ImportError:
    import xml.etree.ElementTree as et

import logging


class GPMLView(HTMLView):

    def generate(self, gpml=None, node_colors=None):

        # Add our urls to the defaults
        xref_urls = {
            'MetaCyc compound': 'pathomx://db/compound/%s/view',
            'MetaCyc gene': 'pathomx://db/gene/%s/view',
            'MetaCyc protein': 'pathomx://db/protein/%s/view',
            'WikiPathways': 'pathomx://wikipathway/%s/import',
        }
        if gpml:
            svg, metadata = gpml2svg.gpml2svg(gpml, xref_urls=xref_urls, xref_synonyms_fn=self.w.get_extended_xref_via_unification_list, node_colors=node_colors)  # Add Pathomx required customisations here
            self.setHtml(svg, QUrl("~"))


            #self.v.change_name.emit( metadata['Name'] )


# Class for data visualisations using GPML formatted pathways
# Supports loading from local file and WikiPathways
class GPMLPathwayApp(ui.AnalysisApp):

    notebook = 'gpml.ipynb'
    legacy_inputs = {'input': 'compound_data'}

    def __init__(self, *args, **kwargs):
        super(GPMLPathwayApp, self).__init__(*args, **kwargs)

        self.gpml = None  # Source GPML file
        self.svg = None  # Rendered GPML file as SVG
        self.metadata = {}

        self.config.set_defaults({
            'gpml_file': None,
            'gpml_wikipathways_id': None,
        
        })

        self.data.add_input('compound_data')  # Add input slot
        self.data.add_input('gene_data')  # Add input slot
        self.data.add_input('protein_data')  # Add input slot
        # Setup data consumer options
        self.data.consumer_defs.extend([
            DataDefinition('compound_data', {
            'entities_t': (None, ['Compound', ])
            }, 'Relative compound (metabolite) concentration data'),
            DataDefinition('gene_data', {
            'entities_t': (None, ['Gene', 'Protein'])
            }, 'Relative gene expression data'),
            DataDefinition('protein_data', {
            'entities_t': (None, ['Protein']),
            }, 'Relative protein concentration data'),
        ])

        load_gpmlAction = QAction(QIcon(os.path.join(self.plugin.path, 'document-open-gpml.png')), 'Load a GPML pathway file\u2026', self.w)
        load_gpmlAction.setShortcut('Ctrl+Q')
        load_gpmlAction.setStatusTip('Load a GPML pathway file')
        load_gpmlAction.triggered.connect(self.onLoadGPMLPathway)

        load_wikipathwaysAction = QAction(QIcon(os.path.join(self.plugin.path, 'wikipathways-open.png')), 'Load pathway map from WikiPathways\u2026', self.w)
        load_wikipathwaysAction.setShortcut('Ctrl+Q')
        load_wikipathwaysAction.setStatusTip('Load a GPML pathway from WikiPathways service')
        load_wikipathwaysAction.triggered.connect(self.onLoadGPMLWikiPathways)

        self.addDataToolBar()
        self.addFigureToolBar()

        t = self.addToolBar('GPML')
        t.setIconSize(QSize(16, 16))
        t.addAction(load_gpmlAction)
        t.addAction(load_wikipathwaysAction)

        self.plugin.register_url_handler(self.url_handler)

    def url_handler(self, url):

        #http://@app['id']/app/create
        kind, action = url.split('/')  # FIXME: Can use split here once stop using pathwaynames   
        # Probably want to move to url strings &n= etc. for logicalness

        if action == 'create':
            self.add_viewer()
            pass

        if action == 'import':
            if kind == 'wikipathway':
                # Create a new GPML viewer entity, delegating it to the parent plugin
                g = gpmlPathwayApp(self.plugin, self.m)
                g.load_gpml_wikipathways(id)
                g.generate()
                self.plugin.instances.append(g)

    def onLoadGPMLPathway(self):
        """ Open a GPML pathway file """
        filename, _ = QFileDialog.getOpenFileName(self.w, 'Open GPML pathway file', '', 'GenMAPP Pathway Markup Language (*.gpml)')
        if filename:
            self.config.set('gpml_file', filename)

    def onLoadGPMLWikiPathways(self):
        dialog = dialogWikiPathways(self.w, request_url='http://www.wikipathways.org/wpi/webservice/webservice.php/findPathwaysByText', request_key='query')
        ok = dialog.exec_()
        if ok:
            # Show
            idx = dialog.select.selectedItems()
            for x in idx:
                #gpmlpathway = gpmlPathwayApp( self.m )
                pathway_id = dialog.data[x.text()]
                self.config.set('gpml_wikipathways_id', pathway_id)


class dialogWikiPathways(ui.remoteQueryDialog):
    def __init__(self, parent, request_url=None, request_key=None):
        super(dialogWikiPathways, self).__init__(parent, request_url, request_key)

        self.setWindowTitle("Load GPML pathway from WikiPathways")

    def parse(self, data):
        result = {}
        tree = et.fromstring(data.encode('utf-8'))
        pathways = tree.iterfind('{http://www.wso2.org/php/xsd}result')

        for p in pathways:
            result['%s (%s)' % (p.find('{http://www.wikipathways.org/webservice}name').text, p.find('{http://www.wikipathways.org/webservice}species').text)] = p.find('{http://www.wikipathways.org/webservice}id').text

        return result


class GPML(VisualisationPlugin):

    def __init__(self, *args, **kwargs):
        super(GPML, self).__init__(*args, **kwargs)
        GPMLPathwayApp.plugin = self
        self.register_app_launcher(GPMLPathwayApp)
        self.register_file_handler(GPMLPathwayApp, 'gpml')
