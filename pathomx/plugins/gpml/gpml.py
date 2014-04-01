# -*- coding: utf-8 -*-

# Renderer for GPML as SVG
from gpml2svg import gpml2svg

import os

import pathomx.ui as ui
import pathomx.db as db
import pathomx.threads as threads
import pathomx.utils as utils

from pathomx.plugins import VisualisationPlugin
from pathomx.data import DataSet, DataDefinition
from pathomx.views import HTMLView
from pathomx.qt import *

try:
    from urllib.request import urlopen
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse
    from urllib import urlopen

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
            self.w.set_name(metadata['Name'])


# Class for data visualisations using GPML formatted pathways
# Supports loading from local file and WikiPathways
class GPMLPathwayApp(ui.AnalysisApp):
    def __init__(self, gpml=None, svg=None, filename=None, **kwargs):
        super(GPMLPathwayApp, self).__init__(**kwargs)

        self.gpml = None  # Source GPML file
        self.svg = None  # Rendered GPML file as SVG
        self.metadata = {}

        #self.browser = ui.QWebViewExtend(self)
        self.views.addView(GPMLView(self), 'View')

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

        load_gpmlAction = QAction(QIcon(os.path.join(self.plugin.path, 'document-open-gpml.png')), 'Load a GPML pathway file\u2026', self.m)
        load_gpmlAction.setShortcut('Ctrl+Q')
        load_gpmlAction.setStatusTip('Load a GPML pathway file')
        load_gpmlAction.triggered.connect(self.onLoadGPMLPathway)

        load_wikipathwaysAction = QAction(QIcon(os.path.join(self.plugin.path, 'wikipathways-open.png')), 'Load pathway map from WikiPathways\u2026', self.m)
        load_wikipathwaysAction.setShortcut('Ctrl+Q')
        load_wikipathwaysAction.setStatusTip('Load a GPML pathway from WikiPathways service')
        load_wikipathwaysAction.triggered.connect(self.onLoadGPMLWikiPathways)

        self.addDataToolBar()
        self.addFigureToolBar()

        t = self.addToolBar('GPML')
        t.setIconSize(QSize(16, 16))
        t.addAction(load_gpmlAction)
        t.addAction(load_wikipathwaysAction)

        if filename:
            self.load_gpml_file(filename)

        #self.o.show()
        self.plugin.register_url_handler(self.url_handler)

        self.finalise()

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

    def load_gpml_file(self, filename):
        f = open(filename, 'r')
        self.gpml = f.read()
        f.close()

    def load_gpml_wikipathways(self, pathway_id):
        f = urlopen('http://www.wikipathways.org//wpi/wpi.php?action=downloadFile&type=gpml&pwTitle=Pathway:%s&revision=0' % pathway_id)
        self.gpml = f.read()
        f.close()

    def get_xref_via_unification(self, database, id):
        xref_translate = {
            'Kegg Compound': 'LIGAND-CPD',
            'Entrez Gene': 'NCBI-GENE',
            'HMDB': 'HMDB',
            'CAS': 'CAS',
            }
        if database in xref_translate:
            obj = self.m.db.get_via_unification(xref_translate[database], id)
            if obj:
                return ('MetaCyc %s' % obj.type, obj.id)
        return None

    def get_extended_xref_via_unification_list(self, xrefs):
        if xrefs:
            for xref, id in list(xrefs.items()):
                xref_extra = self.get_xref_via_unification(xref, id)
                if xref_extra:
                    xrefs[xref_extra[0]] = xref_extra[1]
        return xrefs

    def get_xref(self, obj):
        if obj is not None:
            return ('MetaCyc %s' % obj.type, obj.id)

    def generate(self, compound_data=None, gene_data=None, protein_data=None, **kwargs):

        if self.gpml == None:
            # No pathway loaded; check config for stored source to use
            if self.config.get('gpml_file'):
                self.load_gpml_file(self.config.get('gpml_file'))

            elif self.config.get('gpml_wikipathways_id'):
                self.load_gpml_wikipathways(self.config.get('gpml_wikipathways_id'))

        return {'compound_data': compound_data, 'gene_data': gene_data, 'protein_data': protein_data, 'gpml': self.gpml}

    def prerender(self, compound_data=None, gene_data=None, protein_data=None, gpml=None):

        node_colors = {}

        for dso in compound_data, gene_data, protein_data:
            if dso == None:
                continue

            mini, maxi = min(abs(np.median(dso.data)), 0), max(abs(np.median(dso.data)), 0)
            mini, maxi = -1.0, +1.0  # Fudge; need an intelligent way to determine (2*median? 2*mean?)
            scale = utils.calculate_scale([mini, 0, maxi], [9, 1], out=np.around)  # rdbu9 scale

            for n, m in enumerate(dso.entities[1]):
                xref = self.get_xref(m)
                ecol = utils.calculate_rdbu9_color(scale, dso.data[0, n])
                #print xref, ecol
                if xref is not None and ecol is not None:
                    node_colors[xref] = ecol
        #logging.debug("Calculated node colors: %s" % (','.join(node_colors)) )

        return {'View': {'gpml': gpml, 'node_colors': node_colors}}
    # Events (Actions, triggers)

    def onLoadGPMLPathway(self):
        """ Open a GPML pathway file """
        filename, _ = QFileDialog.getOpenFileName(self.m, 'Open GPML pathway file', '', 'GenMAPP Pathway Markup Language (*.gpml)')
        if filename:
            self.load_gpml_file(filename)
            self.generate()
            self.config.set('gpml_file', filename)

    def onLoadGPMLWikiPathways(self):
        dialog = dialogWikiPathways(parent=self.m, query_target='http://www.wikipathways.org/wpi/webservice/webservice.php/findPathwaysByText?query=%s')
        ok = dialog.exec_()
        if ok:
            # Show
            idx = dialog.select.selectedItems()
            for x in idx:
                #gpmlpathway = gpmlPathwayApp( self.m )
                pathway_id = dialog.data[x.text()]

                self.load_gpml_wikipathways(pathway_id)
                self.generate()
                self.config.set('gpml_wikipathways_id', pathway_id)


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


class GPML(VisualisationPlugin):

    def __init__(self, **kwargs):
        super(GPML, self).__init__(**kwargs)
        GPMLPathwayApp.plugin = self
        self.register_app_launcher(GPMLPathwayApp)
        self.register_file_handler(GPMLPathwayApp, 'gpml')
