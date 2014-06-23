# -*- coding: utf-8 -*-
import os

import pathomx.ui as ui
import pathomx.utils as utils
import pathomx.db as db

from pathomx.plugins import VisualisationPlugin
from pathomx.data import DataSet, DataDefinition
from pathomx.views import D3CircosView


class PathwayConnectsApp(ui.AnalysisApp):

    def __init__(self, *args, **kwargs):
        super(PathwayConnectsApp, self).__init__(*args, **kwargs)

        self.addDataToolBar()

        self.data.add_input('input')  # Add input slot        
        # Setup data consumer options
        self.data.consumer_defs.append(
            DataDefinition('input', {
            'entities_t': (None, ['Pathway']),
            })
        )

        self.views.addView(D3CircosView(self), 'Reactions')
        self.views.addView(D3CircosView(self), 'Metabolites')

        self.finalise()

    def url_handler(self, url):

        #http://@app['id']/app/create
        print(url)
        kind, action = url.split('/')  # FIXME: Can use split here once stop using pathwaynames   
        # Probably want to move to url strings &n= etc. for logicalness

        if action == 'create':
            self.add_viewer()
            pass

    def build_matrix(self, targets, target_links):

        data = []
        for mx in targets:
            row = []
            for my in targets:
                n = len(list(target_links[my] & target_links[mx]))
                row.append(n)

            data.append(row)
        return data, targets

    def generate(self, input=None):

        pathways = [k for k, v in db.dbm.get_pathways()]
        pathway_compounds = dict()

        for k, p in db.dbm.get_pathways():
            pathway_compounds[p.id] = set([m for m in p.compounds])

        data_m, labels_m = self.build_matrix(pathways, pathway_compounds)

        pathway_reactions = dict()

        for k, p in list(db.dbm.pathways.items()):
            pathway_reactions[p.id] = set([m for m in p.reactions])

        data_r, labels_r = self.build_matrix(pathways, pathway_reactions)

        pathway_active_reactions = dict()
        pathway_active_compounds = dict()
        active_pathways = input.entities[1]
        active_pathways_id = []

        for p in active_pathways:
            pathway_active_reactions[p.id] = set([r for r in p.reactions])
            pathway_active_compounds[p.id] = set([r for r in p.compounds])
            active_pathways_id.append(p.id)

        data_ar, labels_ar = self.build_matrix(active_pathways_id, pathway_active_reactions)
        data_am, labels_am = self.build_matrix(active_pathways_id, pathway_active_compounds)

        dim = len(data_ar)

        dso_r = DataSet(size=(dim, dim))
        dso_r.data = data_ar
        dso_r.labels[1] = labels_ar

        dso_m = DataSet(size=(dim, dim))
        dso_m.data = data_am
        dso_m.labels[1] = labels_am

        return {'dso_r': dso_r, 'dso_m': dso_m}

    def prerender(self, dso_r=None, dso_m=None):
        return {'Metabolites': {'dso': dso_m}, 'Reactions': {'dso': dso_r}}


class PathwayConnects(VisualisationPlugin):

    def __init__(self, *args, **kwargs):
        super(PathwayConnects, self).__init__(*args, **kwargs)
        PathwayConnectsApp.plugin = self
        self.register_app_launcher(PathwayConnectsApp)
