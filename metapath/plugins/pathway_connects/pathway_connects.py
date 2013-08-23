import os

# Import PySide classes
from PySide.QtGui import *
from PySide.QtCore import *
from PySide.QtWebKit import *
from PySide.QtNetwork import *

from plugins import VisualisationPlugin

import ui, utils




class PathwayConnectsView(ui.analysisCircosView):
    def __init__(self, parent):
        self.parent = parent
        self.browser = ui.QWebViewExtend( parent.onBrowserNav )
        parent.tab_handlers.append( self )


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
        pathways = self.parent.db.pathways.keys()
        pathway_metabolites = dict()
        
        for k,p in self.parent.db.pathways.items():
            pathway_metabolites[p.id] = set( [m for m in p.metabolites] )

        data_m, labels_m = self.build_matrix(pathways, pathway_metabolites)

        pathway_reactions = dict()
        
        for k,p in self.parent.db.pathways.items():
            pathway_reactions[p.id] = set( [m for m in p.reactions] )

        data_r, labels_r = self.build_matrix(pathways, pathway_reactions)


        pathway_active_reactions = dict()
        pathway_active_metabolites = dict()
        active_pathways = [self.parent.db.pathways[p] for p in self.parent.config.value('/Pathways/Show').split(',')]
        active_pathways_id = []
        
        for p in active_pathways:
            pathway_active_reactions[p.id] = set( [r for r in p.reactions] )
            pathway_active_metabolites[p.id] = set( [r for r in p.metabolites] )
            active_pathways_id.append(p.id)
    

        data_ar, labels_ar = self.build_matrix(active_pathways_id, pathway_active_reactions)
        data_am, labels_am = self.build_matrix(active_pathways_id, pathway_active_metabolites)


        self.render( {
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
                            'legend':('Metabolic pathway metabolite interconnections','Links between pathways indicate proportions of shared metabolites between the two pathways in MetaCyc database')
                        },                                             
                    ]],
                    })

"""                        
                        {
                            'type':'circos',
                            'data': data_m,
                            'labels': labels_m,
                            'n':1,  
                            'legend':('Metabolic pathway interconnections','Complete set of shared metabolites for pathways in current database')
                                                      
                        },
                        {
                            'type':'circos',
                            'data': data_r,
                            'labels': labels_r,
                            'n':2,  
                            'legend':('Metabolic pathway interconnections','Complete set of shared metabolites for pathways in current database')
                                                      
                        }],
                        [


                            {
                            'type':'corrmatrix',
                            'data': [
                              {'group':"setosa","sepal length":1, "sepal width":5, "petal length":3, "petal width":2},
                              {'group':"versicolor","sepal length":2, "sepal width":5, "petal length":3, "petal width":1},
                              {'group':"virginica","sepal length":3, "sepal width":5, "petal length":3, "petal width":1},
                              {'group':"setosa","sepal length":4, "sepal width":5, "petal length":3, "petal width":0},
                              {'group':"versicolor","sepal length":5, "sepal width":5, "petal length":3, "petal width":1},
                              {'group':"virginica","sepal length":6, "sepal width":5, "petal length":3, "petal width":2},
                            ],
                            'traits': ["sepal length", "sepal width", "petal length", "petal width"],
                            'groups': ["setosa", "versicolor", "virginica"],
                            'n':5,
                            'legend':('a','b'),
"""   
                    
        



class PathwayConnects(VisualisationPlugin):

    id = 'pathway_connects'

    def __init__(self, **kwargs):
        super(PathwayConnects, self).__init__(**kwargs)
    
        self.register_url_handler( self.id, self.url_handler )
        self.register_app_launcher( self.app_launcher )

    
    # Add a new visualiser viewer; 
    # Create an new analysis browser instance, assign an identifier (based on plugin identifier; + iterator)
    # Attach the browser window to the parent
    def app_launcher(self):

        pathwayconnectview = PathwayConnectsView( self.m )
        #pathway_id = dialog.data[x.text()]
    
        #gpmlpathway.load_gpml_wikipathways(pathway_id)
        pathwayconnectview.generate()
        self.m.tabs.setCurrentIndex( 
            self.m.tabs.addTab( pathwayconnectview.browser, 'PathwayX') #gpmlpathway.metadata['Name'] )
         )
        

    def url_handler(self, url):

        #http://@app['id']/app/create
        print url
        kind, action = url.split('/') # FIXME: Can use split here once stop using pathwaynames   
        # Probably want to move to url strings &n= etc. for logicalness        

        if action == 'create':
            self.add_viewer()
            pass
        