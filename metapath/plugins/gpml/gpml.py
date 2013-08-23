# Import PySide classes
from PySide.QtGui import *
from PySide.QtCore import *
from PySide.QtWebKit import *
from PySide.QtNetwork import *

# Renderer for GPML as SVG
from gpml2svg import gpml2svg


from plugins import VisualisationPlugin

import ui




# Class for data visualisations using GPML formatted pathways
# Supports loading from local file and WikiPathways
class gpmlPathwayView(ui.analysisView):
    def __init__(self, parent, gpml=None, svg=None, **kwargs):
        super(gpmlPathwayView, self).__init__(parent, **kwargs)

        self.gpml = gpml # Source GPML file
        self.svg = svg # Rendered GPML file as SVG
        self.metadata = {}
    
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
            obj = self.parent.db.get_via_unification( xref_translate[database], id )
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
            'MetaCyc compound': 'metapath://metabolite/%s/view',
            'MetaCyc gene': 'metapath://gene/%s/view',
            'MetaCyc protein': 'metapath://protein/%s/view',
            'WikiPathways': 'metapath://wikipathway/%s/import',
        }
    
        if self.parent.data and self.parent.data.analysis:
            # Build color_table
            node_colors = {}
            for m_id, analysis in self.parent.data.analysis.items():
                if m_id in self.parent.db.metabolites.keys():
                    node_colors[ self.get_xref( self.parent.db.metabolites[ m_id ] ) ] = ( core.rdbu9[ analysis['color'] ], core.rdbu9c[ analysis['color'] ] )
        else:
            node_colors = {}
        
        if self.gpml:
            self.svg, self.metadata = gpml2svg.gpml2svg( self.gpml, xref_urls=xref_urls, xref_synonyms_fn=self.get_extended_xref_via_unification_list, node_colors=node_colors ) # Add MetaPath required customisations here
            self.render()
            print self.svg
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

    id = 'gpml'

    def __init__(self, **kwargs):
        super(GPML, self).__init__(**kwargs)
    
        self.register_url_handler( self.id, self.url_handler )
        self.register_menus( 'pathways', [
            {'title': u'&Load GPML pathway\u2026', 'action': self.onLoadGPMLPathway, 'status': 'Load a GPML pathway file'},
            {'title': u'&Load GPML pathway via WikiPathways\u2026', 'action': self.onLoadGPMLPathway, 'status': 'Load a GPML pathway from WikiPathways service'},        
        ] )
        self.register_app_launcher( self.app_launcher )
    
    # Add a new visualiser viewer; 
    # Create an new analysis browser instance, assign an identifier (based on plugin identifier; + iterator)
    # Attach the browser window to the parent
    def app_launcher(self):
        gpmlpathway = gpmlPathwayView( self.m )
        #pathway_id = dialog.data[x.text()]
    
        #gpmlpathway.load_gpml_wikipathways(pathway_id)
        gpmlpathway.generate()

        self.m.gpmlpathways.append(gpmlpathway)
        self.m.tabs.setCurrentIndex( 
            self.m.tabs.addTab( gpmlpathway.browser, 'WikiPathways') #gpmlpathway.metadata['Name'] )
             )
        

    def url_handler(self, url):

        #http://@app['id']/app/create
        print url
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
                
                self.add
                self.m.tabs.addTab( gpmlpathway.browser, gpmlpathway.metadata['Name'] )
                
                
    def onLoadGPMLPathway(self):
        """ Open a GPML pathway file """
        filename, _ = QFileDialog.getOpenFileName(self.m, 'Open GPML pathway file', '')
        if filename:
    
            gpmlpathway = gpmlPathwayView( self.m )

            gpmlpathway.load_gpml_file(filename)
            gpmlpathway.generate()

            self.m.gpmlpathways.append(gpmlpathway)
            self.m.tabs.addTab( gpmlpathway.browser, gpmlpathway.metadata['Name'] )

    def onLoadGPMLWikiPathways(self):
        dialog = dialogWikiPathways(parent=self.m, query_target='http://www.wikipathways.org/wpi/webservice/webservice.php/findPathwaysByText?query=%s')
        ok = dialog.exec_()
        if ok:
            # Show
            idx = dialog.select.selectedItems()
            for x in idx:
                gpmlpathway = gpmlPathwayView( self.m )
                pathway_id = dialog.data[x.text()]
            
                gpmlpathway.load_gpml_wikipathways(pathway_id)
                gpmlpathway.generate()

                self.m.gpmlpathways.append(gpmlpathway)
                self.m.tabs.addTab( gpmlpathway.browser, gpmlpathway.metadata['Name'] )
