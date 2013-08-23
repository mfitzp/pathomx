from plugins import VisualisationPlugin

import os


class MetaVizView(object):
    pass





class MetaViz(VisualisationPlugin):

    id = 'metaviz'

    def __init__(self, **kwargs):
        super(MetaViz, self).__init__(**kwargs)

        self.register_url_handler( self.id, self.url_handler )

    def url_handler(self, url):

        kind, id, action = url.split('/') # FIXME: Can use split here once stop using pathwaynames           
        
        # url is Qurl kind
        # Add an object to the current view
        if action == 'add':

            # FIXME: Hacky test of an idea
            if kind == 'pathway' and id in self.m.db.pathways:
                # Add the pathway and regenerate
                pathways = self.m.config.value('/Pathways/Show').split(',')
                pathways.append( urllib2.unquote(id) )
                self.m.config.setValue('/Pathways/Show', ','.join(pathways) )
                self.m.generateGraphView()   

        # Remove an object to the current view
        if action == 'remove':

            # FIXME: Hacky test of an idea
            if kind == 'pathway' and id in self.m.db.pathways:
                # Add the pathway and regenerate
                pathways = self.m.config.value('/Pathways/Show').split(',')
                pathways.remove( urllib2.unquote(id) )
                self.m.config.setValue('/Pathways/Show', ','.join(pathways))
                self.m.generateGraphView()


        if action == 'import':
            if kind == 'wikipathway':
                gpmlpathway = gpmlPathwayView( self )
                gpmlpathway.load_gpml_wikipathways(id)
                gpmlpathway.generate()

                self.m.gpmlpathways.append(gpmlpathway)
                self.m.tabs.addTab( gpmlpathway.browser, gpmlpathway.metadata['Name'] )

                        
