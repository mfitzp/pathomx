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

from poster.encode import multipart_encode
from poster.streaminghttp import register_openers
import io

try:
    from urllib.request import urlopen, Request
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse
    from urllib import urlopen
    from urllib2 import Request


# Class for data visualisations using KEGG formatted pathways
# Supports loading from KEGG site
class KEGGPathwayApp(ui.AnalysisApp):

    def __init__(self, gpml=None, svg=None, **kwargs):
        super(KEGGPathwayApp, self).__init__(**kwargs)

        self.svg = None  # Rendered GPML file as SVG
        self.metadata = {}
        #self.browser = ui.QWebViewExtend(self)
        #self.views.addTab(self.browser,'App')

        self.data.add_input('input')  # Add input slot
        # Setup data consumer options
        self.data.consumer_defs.append(
            DataDefinition('input', {
            'entities_t': (None, ['Compound', 'Gene']),
            }, 'Relative concentration data'),
        )

        self.views.addView(HTMLView(self), 'View')

        self.addDataToolBar(default_pause_analysis=True)
        self.addFigureToolBar()

        self.kegg_pathway_t = QLineEdit()
        self.kegg_pathway_t.setText('hsa00010')
        self.kegg_pathway_t.textChanged.connect(self.autogenerate)

        t = self.addToolBar('KEGG')
        t.setIconSize(QSize(16, 16))
        t.addWidget(self.kegg_pathway_t)

        self.finalise()

    def generate(self, input=None, **kwargs):
        dsi = input
        opener = register_openers()
        url = 'http://www.kegg.jp/kegg-bin/mcolor_pathway'

        data = io.StringIO()

        node_colors = {}
        if dsi:
            mini, maxi = min(abs(np.median(dsi.data)), 0), max(abs(np.median(dsi.data)), 0)
            mini, maxi = -2.0, +2.0  # Fudge; need an intelligent way to determine (2*median? 2*mean?)
            scale = utils.calculate_scale([mini, 0, maxi], [9, 1], out=np.around)  # rdbu9 scale

            #for n, m in enumerate(dsi.entities[1]):
            #    xref = self.get_xref( m )

            for n, m in enumerate(dsi.entities[1]):
                if m:

                    if 'LIGAND-CPD' in m.databases:
                        kegg_id = m.databases['LIGAND-CPD']
                        ecol = utils.calculate_rdbu9_color(scale, dsi.data[0, n])
                        if kegg_id is not None and ecol is not None:
                            node_colors[kegg_id] = ecol

                    elif 'NCBI-GENE' in m.databases:
                        kegg_id = m.databases['NCBI-GENE']
                        ecol = utils.calculate_rdbu9_color(scale, dsi.data[0, n])
                        if kegg_id is not None and ecol is not None:
                            node_colors[kegg_id] = ecol

        tmp = open(os.path.join(QDir.tempPath(), 'kegg-pathway-data.txt'), 'w')
        tmp.write('#hsa\tData\n')
        for k, c in list(node_colors.items()):
            tmp.write('%s\t%s\n' % (k, c[0]))
        tmp = open(os.path.join(QDir.tempPath(), 'kegg-pathway-data.txt'), 'r')

        values = {
                  'map': self.kegg_pathway_t.text(),
                  'mapping_list': tmp,
                  'mode': 'color',
                  'submit': 'Exec',
                 }

        self.status.emit('waiting')

        datagen, headers = multipart_encode(values)
        # Create the Request object
        # Actually do the request, and get the response
        request = Request(url, datagen, headers)

        try:
            response = urlopen(request)
        except urllib.error.HTTPError as e:
            print(e)
            return

        return {'html': response.read()}

    def prerender(self, html=''):

        # We've got the html page; pull out the image
        # <img src="/tmp/mark_pathway13818418802193/hsa05200.1.png" name="pathwayimage" usemap="#mapdata" border="0" />
        m = re.search('\<img src="(.*)" name="pathwayimage"', html)
        img = m.group(1)

        m = re.search('^KEGG PATHWAY: (.*)$', html, flags=re.MULTILINE)
        title = m.group(1)
        self.set_name(title)
        output_html = '<html><body><img src="http://www.kegg.jp%s"></body></html>' % img

        return {'View': {'html': output_html}}


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

    def __init__(self, **kwargs):
        super(KEGG, self).__init__(**kwargs)
        KEGGPathwayApp.plugin = self
        self.register_app_launcher(KEGGPathwayApp)
