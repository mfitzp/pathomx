import os

# Import PyQt5 classes
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWebKit import *
from PyQt5.QtNetwork import *
from PyQt5.QtWidgets import *
from PyQt5.QtWebKitWidgets import *
from PyQt5.QtPrintSupport import *

from plugins import VisualisationPlugin

import ui, utils, data




class PathwayConnectsView(ui.AnalysisView):
    def __init__(self, plugin, parent, **kwargs):
        super(PathwayConnectsView, self).__init__(plugin, parent, **kwargs)

        self.addDataToolBar()
        
        # Setup data consumer options
        self.data.consumer_defs.append( 
            data.DataDefinition('input', {
            'entities_t':   (['Pathway'], None), 
            })
        )
        
        self.data.consume_any_of( self.m.datasets[::-1] ) # Try consume any dataset; work backwards

        self.data.source_updated.connect( self.generate ) # Auto-regenerate if the source data is modified
        self.generate()


    def url_handler(self, url):

        #http://@app['id']/app/create
        print url
        kind, action = url.split('/') # FIXME: Can use split here once stop using pathwaynames   
        # Probably want to move to url strings &n= etc. for logicalness        

        if action == 'create':
            self.add_viewer()
            pass



    def build_matrix(self, targets, target_links):

        data = []
        for mx in targets:
            row = []
            for my in targets:
                n = len( list( target_links[my] & target_links[mx] ) )
                row.append( n )
    
            data.append( row )
        return data, targets


    def generate(self):
        self.setWorkspaceStatus('active')

        print "Generating..."
        pathways = self.m.db.pathways.keys()
        pathway_compounds = dict()
        
        for k,p in self.m.db.pathways.items():
            pathway_compounds[p.id] = set( [m for m in p.compounds] )

        data_m, labels_m = self.build_matrix(pathways, pathway_compounds)

        pathway_reactions = dict()
        
        for k,p in self.m.db.pathways.items():
            pathway_reactions[p.id] = set( [m for m in p.reactions] )

        data_r, labels_r = self.build_matrix(pathways, pathway_reactions)

        pathway_active_reactions = dict()
        pathway_active_compounds = dict()
        active_pathways = self.data.i['input'].entities[0] #[self.parent.db.pathways[p] for p in self.parent.config.value('/Pathways/Show').split(',')]
        active_pathways_id = []
        
        for p in active_pathways:
            pathway_active_reactions[p.id] = set( [r for r in p.reactions] )
            pathway_active_compounds[p.id] = set( [r for r in p.compounds] )
            active_pathways_id.append(p.id)
    

        data_ar, labels_ar = self.build_matrix(active_pathways_id, pathway_active_reactions)
        data_am, labels_am = self.build_matrix(active_pathways_id, pathway_active_compounds)


        self.render( {
            'figure':  {
                            'type':'circos',
                            'data': data_am,
                            'labels': labels_am,
                            'n':2,  
                            'legend':('Metabolic pathway compound interconnections','Links between pathways indicate proportions of shared compounds between the two pathways in MetaCyc database')
                        },  
                        
            'figures': [[
                        {
                            'type':'circos',
                            'data': data_ar,
                            'labels': labels_ar,
                            'n':1,  
                            'legend':('Metabolic pathway reaction interconnections','Links between pathways indicate proportions of shared reactions between the two pathways in MetaCyc database')                             
                        },
                        {
                            'type':'circos',
                            'data': data_am,
                            'labels': labels_am,
                            'n':2,  
                            'legend':('Metabolic pathway compound interconnections','Links between pathways indicate proportions of shared compounds between the two pathways in MetaCyc database')
                        },                                             
                    ]],
                    })

        self.setWorkspaceStatus('done')
        self.clearWorkspaceStatus()




class PathwayConnects(VisualisationPlugin):


    def __init__(self, **kwargs):
        super(PathwayConnects, self).__init__(**kwargs)
        self.register_app_launcher( self.app_launcher )

    # Create a new instance of the plugin viewer object to handle all behaviours
    def app_launcher(self):
        self.instances.append( PathwayConnectsView( self, self.m ) )

                     
        
