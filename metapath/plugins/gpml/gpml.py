# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# Import PySide classes
from PySide.QtGui import *
from PySide.QtCore import *
from PySide.QtWebKit import *
from PySide.QtNetwork import *

# Renderer for GPML as SVG
from gpml2svg import gpml2svg


from plugins import VisualisationPlugin

import os
import ui, utils




# Class for data visualisations using GPML formatted pathways
# Supports loading from local file and WikiPathways
class gpmlPathwayView(ui.analysisView):
    def __init__(self, plugin, parent, gpml=None, svg=None, **kwargs):
        super(gpmlPathwayView, self).__init__(parent, **kwargs)

        self.plugin = plugin
        self.m = parent
        self.gpml = gpml # Source GPML file
        self.svg = svg # Rendered GPML file as SVG
        self.metadata = {}

        load_gpmlAction = QAction(QIcon.fromTheme("gpml-open", QIcon( os.path.join( utils.scriptdir,'icons','document-open-gpml.png') )), 'Load a GPML pathway file\u2026', self.m)
        load_gpmlAction.setShortcut('Ctrl+Q')
        load_gpmlAction.setStatusTip('Load a GPML pathway file')
        load_gpmlAction.triggered.connect(self.onLoadGPMLPathway)

        load_wikipathwaysAction = QAction(QIcon.fromTheme("wikipathways-open", QIcon( os.path.join( utils.scriptdir,'icons','wikipathways-open.png') )), 'Load pathway map from WikiPathways\u2026', self.m)
        load_wikipathwaysAction.setShortcut('Ctrl+Q')
        load_wikipathwaysAction.setStatusTip('Load a GPML pathway from WikiPathways service')
        load_wikipathwaysAction.triggered.connect(self.onLoadGPMLWikiPathways)
        
        self.w = QMainWindow()
        t = self.w.addToolBar('GPML')
        t.setIconSize( QSize(16,16) )
        t.addAction(load_gpmlAction)
        t.addAction(load_wikipathwaysAction)
        self.w.setCentralWidget(self.browser)
         
        #self.o.show() 
        self.plugin.register_url_handler( self.id, self.url_handler )
        self.workspace_item = self.m.addWorkspaceItem(self.w, self.plugin.default_workspace_category, 'WikiPathways', is_selected=True) #, icon = None)


    def url_handler(self, url):

        #http://@app['id']/app/create
        kind, action = url.split('/') # FIXME: Can use split here once stop using pathwaynames   
        # Probably want to move to url strings &n= etc. for logicalness        

        if action == 'create':
            self.add_viewer()
            pass

        if action == 'import':
            if kind == 'wikipathway':
                gpmlpathway = gpmlPathwayView( self )
                gpmlpathway.load_gpml_wikipathways(id)
                gpmlpathway.generate()

                self.m.gpmlpathways.append(gpmlpathway)
                
                self.m.tabs.addTab( gpmlpathway.browser, gpmlpathway.metadata['Name'] )
                
                
        
    def load_gpml_file(self, filename):
        f = open(filename,'r')
        self.gpml = f.read()
        f.close()
    
    def load_gpml_wikipathways(self, pathway_id):
        f = urllib2.urlopen('http://www.wikipathways.org//wpi/wpi.php?action=downloadFile&type=gpml&pwTitle=Pathway:%s&revision=0' % pathway_id )
        self.gpml = f.read()
        f.close()
    
    def get_xref_via_unification(self, database, id):
        xref_translate = {
            'Kegg Compound': 'LIGAND-CPD',
            'Entrez Gene': 'ENTREZ',
            'HMDB': 'HMDB',
            'CAS': 'CAS',
            }
        if database in xref_translate:
            obj = self.m.db.get_via_unification( xref_translate[database], id )
            if obj:
                return ('MetaCyc %s' % obj.type, obj.id )
        return None
        
    def get_extended_xref_via_unification_list(self, xrefs):
        if xrefs:
            for xref,id in xrefs.items():
                xref_extra = self.get_xref_via_unification( xref, id )
                if xref_extra:
                    xrefs[ xref_extra[0] ] = xref_extra[1]
        return xrefs
            
    def get_xref(self, obj):
        print obj, obj.type, obj.id
    
        return ('MetaCyc %s' % obj.type, obj.id)
    
    def generate(self):

        # Add our urls to the defaults
        xref_urls = {
            'MetaCyc compound': 'metapath://db/metabolite/%s/view',
            'MetaCyc gene': 'metapath://db/gene/%s/view',
            'MetaCyc protein': 'metapath://db/protein/%s/view',
            'WikiPathways': 'metapath://wikipathway/%s/import',
        }
    
        if self.m.data and self.m.data.analysis:
            # Build color_table
            node_colors = {}
            for m_id, analysis in self.m.data.analysis.items():
                if m_id in self.m.db.metabolites.keys():
                    node_colors[ self.get_xref( self.m.db.metabolites[ m_id ] ) ] = ( utils.rdbu9[ analysis['color'] ], utils.rdbu9c[ analysis['color'] ] )
        else:
            node_colors = {}
        
        if self.gpml:
            self.svg, self.metadata = gpml2svg.gpml2svg( self.gpml, xref_urls=xref_urls, xref_synonyms_fn=self.get_extended_xref_via_unification_list, node_colors=node_colors ) # Add MetaPath required customisations here
            self.render()
        else:
            self.svg = None
        
    def render(self):
        if self.svg is None:
            self.generate()
    
        if self.svg is None:
            html_source = ''
        else:
            html_source = '''<html><body><div id="svg%d" class="svg">''' + self.svg + '''</body></html>'''

        self.browser.setHtml(html_source)


    # Events (Actions, triggers)

    def onLoadGPMLPathway(self):
        """ Open a GPML pathway file """
        filename, _ = QFileDialog.getOpenFileName(self.m, 'Open GPML pathway file', '')
        if filename:
            self.load_gpml_file(filename)
            self.generate()

            if self.workspace_item:
                self.workspace_item.setText(0, self.metadata['Name'])

    def onLoadGPMLWikiPathways(self):
        dialog = dialogWikiPathways(parent=self.m, query_target='http://www.wikipathways.org/wpi/webservice/webservice.php/findPathwaysByText?query=%s')
        ok = dialog.exec_()
        if ok:
            # Show
            idx = dialog.select.selectedItems()
            for x in idx:
                #gpmlpathway = gpmlPathwayView( self.m )
                pathway_id = dialog.data[x.text()]
            
                self.load_gpml_wikipathways(pathway_id)
                self.generate()
                
                if self.workspace_item:
                    self.workspace_item.setText(0, self.metadata['Name'])




class dialogWikiPathways(ui.remoteQueryDialog):
    def __init__(self, parent=None, **kwargs):
        super(dialogWikiPathways, self).__init__(parent, **kwargs)        
    
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
        #self.register_url_handler( self.id, self.url_handler )
        #self.register_menus( 'pathways', [
        #    {'title': u'&Load GPML pathway\u2026', 'action': self.onLoadGPMLPathway, 'status': 'Load a GPML pathway file'},
        #    {'title': u'&Load GPML pathway via WikiPathways\u2026', 'action': self.onLoadGPMLPathway, 'status': 'Load a GPML pathway from WikiPathways service'},        
        #] )
        self.register_app_launcher( self.app_launcher )
    
    # Create a new instance of the plugin viewer object to handle all behaviours
    def app_launcher(self):
        self.instances.append( gpmlPathwayView( self, self.m ) )
