# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# Import PyQt5 classes
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWebKit import *
from PyQt5.QtNetwork import *
from PyQt5.QtWidgets import *
from PyQt5.QtWebKitWidgets import *
from PyQt5.QtPrintSupport import *


# Renderer for GPML as SVG
from gpml2svg import gpml2svg


from plugins import VisualisationPlugin

import os, re
import ui, utils
from data import DataSet, DataDefinition


import urllib2

import numpy as np

try:
    import xml.etree.cElementTree as et
except ImportError:
    import xml.etree.ElementTree as et

from poster.encode import multipart_encode
from poster.streaminghttp import register_openers
import StringIO
import urllib, urllib2


# Class for data visualisations using GPML formatted pathways
# Supports loading from local file and WikiPathways
class gpmlPathwayView(ui.AnalysisView):
    def __init__(self, plugin, parent, gpml=None, svg=None, **kwargs):
        super(gpmlPathwayView, self).__init__( plugin, parent, **kwargs)

        self.gpml = gpml # Source GPML file
        self.svg = svg # Rendered GPML file as SVG
        self.metadata = {}

        #self.browser = ui.QWebViewExtend(self)
        #self.tabs.addTab(self.browser,'View')

        #self.data = data.DataManager()
        # Setup data consumer options
        self.data.consumer_defs.append( 
            DataDefinition('input', {
            'entities_t':   (None, ['Compound','Gene']), 
            },'Relative concentration data'),
        )

                
        self.addDataToolBar(default_pause_analysis=True)
        self.addFigureToolBar()

        self.kegg_pathway_t = QLineEdit()
        self.kegg_pathway_t.setText('hsa00010')
        self.kegg_pathway_t.textChanged.connect(self.generate)

        t = self.addToolBar('KEGG')
        t.setIconSize( QSize(16,16) )
        t.addWidget( self.kegg_pathway_t)
         
        self.data.source_updated.connect( self.autogenerate ) # Auto-regenerate if the source data is modified
        self.data.consume_any_of( self.m.datasets[::-1] )
                

    def generate(self):

        self.setWorkspaceStatus('active')
        dsi = self.data.get('input')

        opener = register_openers()

        url = 'http://www.kegg.jp/kegg-bin/mcolor_pathway'

        data = StringIO.StringIO()

        node_colors = {}
        if dsi:
            sf = utils.calculate_scaling_factor( dsi.data, 9) # rdbu9 scale
            print "Sf %s" % sf
            for n, m in enumerate(dsi.entities[1]):
                if m and 'LIGAND-CPD' in m.databases:
                    kegg_id = m.databases['LIGAND-CPD']
                    ecol = utils.calculate_rdbu9_color( sf, dsi.data[0,n] )
                    if kegg_id is not None and ecol is not None:
                        node_colors[ kegg_id ] = ecol
               
        tmp = open( os.path.join(QDir.tempPath(),'kegg-pathway-data.txt') , 'w')
        tmp.write('#hsa\tData\n')
        for k,c in node_colors.items():
            tmp.write('%s\t%s\n' % (k,c[0]) )
        tmp = open( os.path.join(QDir.tempPath(),'kegg-pathway-data.txt') , 'r')

        values = {
                  'map'          : self.kegg_pathway_t.text(),
                  'mapping_list' : tmp,
                  'mode'         : 'color',
                  'submit'       : 'Exec',
                 }

        self.setWorkspaceStatus('waiting')

        datagen, headers = multipart_encode(values)
        # Create the Request object
        # Actually do the request, and get the response
        request = urllib2.Request(url, datagen, headers)

        try:
            response = urllib2.urlopen(request)
        except urllib2.HTTPError, e:
            print e
            return


        html = response.read()

        # We've got the html page; pull out the image
        # <img src="/tmp/mark_pathway13818418802193/hsa05200.1.png" name="pathwayimage" usemap="#mapdata" border="0" />
        m = re.search('\<img src="(.*)" name="pathwayimage"', html)
        img = m.group(1)

        m = re.search('^KEGG PATHWAY: (.*)$', html, flags=re.MULTILINE)
        title = m.group(1)
        self.set_name( title )
        
        output_html = '<html><body><img src="http://www.kegg.jp%s"></body></html>' % img
        print output_html
        self.browser.setHtml(output_html)

        self.setWorkspaceStatus('done')
        self.clearWorkspaceStatus()            
        
    def render(self):
        self.generate()






class dialogWikiPathways(ui.remoteQueryDialog):
    def __init__(self, parent=None, query_target=None, **kwargs):
        super(dialogWikiPathways, self).__init__(parent, query_target, **kwargs)        
    
        self.setWindowTitle("Load GPML pathway from WikiPathways")

    def parse(self, data):
        result = {}
        tree = et.fromstring( data.encode('utf-8') )
        pathways = tree.iterfind('{http://www.wso2.org/php/xsd}result')
    
        for p in pathways:
            result[ '%s (%s)' % (p.find('{http://www.wikipathways.org/webservice}name').text, p.find('{http://www.wikipathways.org/webservice}species').text ) ] = p.find('{http://www.wikipathways.org/webservice}id').text
        
        return result        



class GPML(VisualisationPlugin):

    def __init__(self, **kwargs):
        super(GPML, self).__init__(**kwargs)
        self.register_app_launcher( self.app_launcher )
    
    # Create a new instance of the plugin viewer object to handle all behaviours
    def app_launcher(self):
        self.instances.append( gpmlPathwayView( self, self.m ) )
