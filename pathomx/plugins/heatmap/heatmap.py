# -*- coding: utf-8 -*-

import numpy as np

# Renderer for GPML as SVG
from gpml2svg import gpml2svg

import os

import pathomx.ui as ui
import pathomx.utils as utils
import pathomx.db as db

from pathomx.plugins import VisualisationPlugin
from pathomx.data import DataSet, DataDefinition
from pathomx.views import MplHeatmapView
from pathomx.qt import *


# Class for data visualisations using GPML formatted pathways
# Supports loading from local file and WikiPathways
class HeatmapApp(ui.AnalysisApp):

    def __init__(self, *args, **kwargs):
        super(HeatmapApp, self).__init__(*args, **kwargs)

        self.addDataToolBar()
        self.addFigureToolBar()

        self.data.add_input('input')  # Add input slot            
        # Setup data consumer options
        self.data.consumer_defs.append(
            DataDefinition('input', {
            'entities_t': (None, ['Compound', 'Gene', 'Protein', 'Pathway', 'Reaction']),  # Any entity
            })
        )

        self.initialise_predefined_views()
        self.config.set_defaults({
            'predefined_heatmap': 'Top Metabolites',
        
        })

        self.views.addView(MplHeatmapView(self), 'View')

        t = self.addToolBar('Heatmap')
        t.hm_control = QComboBox()
        t.hm_control.addItems([h for h in list(self.predefined_heatmaps.keys())])
        self.config.add_handler('predefined_heatmap', t.hm_control)
        t.addWidget(t.hm_control)

        self.toolbars['heatmap'] = t

        self.finalise()

    def equilibrium_table_builder(self, objs):
        result = []
        for rk, r in list(db.dbm.reactions.items()):
            inH = sum([objs[m.id] for m in r.smtins if m.id in objs])
            outH = sum([objs[m.id] for m in r.smtouts if m.id in objs])

            balance = inH - outH
            add_it = False
            if balance > 0:
                add_it = (r.mtins, r.mtouts)
            elif balance < 0:  # Reverse
                add_it = (r.mtouts, r.mtins)

            if add_it:
                for mtin in add_it[0]:
                    for mtout in add_it[1]:
                        result.append([mtin.id, mtout.id])
        return result

    def cofactor_table_builder(self, objs):
        result = []
        for p in objs:
            pin = db.dbm.metabolites[p[0]] if p[0] in list(db.dbm.metabolites.keys()) else False
            pout = db.dbm.metabolites[p[1]] if p[1] in list(db.dbm.metabolites.keys()) else False

            if pin and pout:
                for rk, r in list(db.dbm.reactions.items()):
                    add_it = False
                    if pin in r.smtins and pout in r.smtouts:
                        add_it = (r.mtins, r.mtouts)
                    elif pout in r.smtins and pin in r.smtouts:
                        add_it = (r.mtouts, r.mtins)

                    if add_it:
                        for mtin in add_it[0]:
                            for mtout in add_it[1]:
                                result.append([mtin.id, mtout.id])

        return result

    # Build table of metabolic endpoints
    # i.e. metabolites not at the 'in' point of any reactions (or in a bidirectional)
    def endpoint_table_builder(self):
        endpoints = []
        for k, m in list(db.dbm.compounds.items()):
            if m.type == 'compound':
                for r in m.reactions:
                    if m in r.mtins or r.dir == 'both':
                        break
                else:
                    # Only if we find no reactions
                    endpoints.append(m.id)
        return endpoints

    # Build lookup tables for pre-defined views (saves regenerating on view)
    def initialise_predefined_views(self):

        self.predefined_heatmaps = {
            'Phosphorylation': self._phosphorylation,
            'Phosphate balance': self._phosphate_balance,
            'Redox': self._redox,
            'Proton Balance': self._proton_balance,
            'Metabolic endpoints': self._endpoints,
            'Energy/Waste': self._energy_waste,
            'Top Metabolites': self._top_metabolites,
            'Top Metabolites (+)': self._top_metabolites_up,
            'Top Metabolites (-)': self._top_metabolites_down,
            
            }

        self.nucleosides = [
            ['AMP', 'ADP', 'ATP'],
            ['CMP', 'CDP', 'CTP'],
            ['GMP', 'GDP', 'GTP'],
            ['UMP', 'UDP', 'UTP'],
            ['TMP', 'TDP', 'TTP'],
            #---
            ['DAMP', 'DADP', 'DATP'],
            ['DCMP', 'DCDP', 'DCTP'],
            ['DGMP', 'DGDP', 'DGTP'],
            ['DUMP', 'DUDP', 'DUTP'],
            ['DTMP', 'DTDP', 'DTTP'],
            #---
            ['Pi', 'PPI', 'PI3', 'PI4'],
            #---
            ['NAD', 'NADP'],
            ['NADH', 'NADPH'],
        ]

        self.proton = [
            ['NAD', 'NADH'],
            ['NADP', 'NADPH'],
            ['FAD', 'FADH', 'FADH2'],
        ]

        self.redox = [
            ['OXYGEN-MOLECULE', 'WATER'],
            ['', 'PROTON'],
            ['NAD', 'NADH'],
            ['NADP', 'NADPH'],
            ['FAD', 'FADH', 'FADH2'],
        ]

        self.phosphate = [
            ['AMP', 'ADP'],
            ['ADP', 'ATP'],
            ['GMP', 'GDP'],
            ['GDP', 'GTP'],
            #---
            ['Pi', 'PPI'],
            ['PPI', 'PI3'],
            ['PI3', 'PI4'],
            #---
            ['NAD', 'NADP'],
            ['NADH', 'NADPH'],
        ]

        proton_carriers = {'WATER': 1, 'PROTON': 1, 'NADH': 1, 'NADPH': 1, 'FADH': 1, 'FADH2': 2}  # Double count for H2

        phosphate_carriers = {
            'AMP': 1, 'ADP': 2, 'ATP': 3,
            'GMP': 1, 'GDP': 2, 'GTP': 4,
            #---
            'Pi': 1, 'PPI': 2, 'PI3': 3, 'PI4': 4,
            #---
            'NADP': 1, 'NADPH': 1,
            }

        # Standard energy sources (CHO)
        self.energy = ['GLC', 'GLN',
        # Standard energy modulators (co-factors, carriers, etc.)
                    'CARNITINE',
        # Standard waste metabolites
                    'L-LACTATE', ]

        self.endpoints = self.endpoint_table_builder()
        # Build redox reaction table
        # Iterate database, find any reactions with a PROTON in left/right reaction
        # - or NAD->NADH or, or, or
        # If on left, swap
        # Store entry for Min,Mout
        self.redox = self.equilibrium_table_builder(proton_carriers)
        self.phosphate = self.equilibrium_table_builder(phosphate_carriers)

    def get_flattened_entity_list(self, input):
        o = []
        [o.extend(i) for i in input]

        return [db.dbm.index[i] for i in o if i in db.dbm.index]

    def _phosphorylation(self, dso=None):
        dso = dso.as_filtered(dim=1, entities=self.get_flattened_entity_list(self.phosphate))
        return self.build_heatmap_dso(['Phosphorylated', 'Dephosphorylated'], [' → '.join(n) for n in self.phosphate], self.build_change_table_of_entitytypes(dso, self.phosphate, ['Phosphorylated', 'Dephosphorylated']), remove_empty_rows=True, sort_data=True)

    def _phosphate_balance(self, dso=None):
        dso = dso.as_filtered(dim=1, entities=self.get_flattened_entity_list(self.nucleosides))
        return self.build_heatmap_dso(['Pi', 'PPI', 'PI3', 'PI4'], [' → '.join(n) for n in self.nucleosides], self.build_change_table_of_entitytypes(dso, self.nucleosides, ['Pi', 'PPI', 'PI3', 'PI4']), sort_data=True)

    def _redox(self, dso=None):
        dso = dso.as_filtered(dim=1, entities=self.get_flattened_entity_list(self.redox))
        return self.build_heatmap_dso(['Reduced', 'Oxidised'], [' → '.join(n) for n in self.redox], self.build_change_table_of_entitytypes(dso, self.redox, ['Reduced', 'Oxidised']), remove_incomplete_rows=True, sort_data=True)

    def _proton_balance(self, dso=None):
        dso = dso.as_filtered(dim=1, entities=self.get_flattened_entity_list(self.proton))
        return self.build_heatmap_dso(['-', 'H', 'H2'], [' → '.join(n) for n in self.proton], self.build_change_table_of_entitytypes(dso, self.proton, ['-', 'H', 'H2']), sort_data=True)

    def _energy_waste(self, dso=None):
        labelsY = self.get_flattened_entity_list(self.energy)
        labelsX = dso.classes[0]
        dso = dso.as_filtered(dim=1, entities=labelsY)
        return self.build_heatmap_dso(labelsX, labelsY, self.build_change_table_of_classes(dso, labelsY, labelsX), sort_data=True)

    def _endpoints(self, dso=None):
        labelsY = self.get_flattened_entity_list(self.endpoints)
        labelsX = dso.classes[0]
        dso = dso.as_filtered(dim=1, entities=labelsY)
        return self.build_heatmap_dso(labelsX, labelsY, self.build_change_table_of_classes(dso, labelsY, labelsX), sort_data=True)

    def _top_metabolites(self, dso=None, fn=abs):
        # Flatten data input (0 dim) to get average 'score' for each metabolite; then take top 30
        fd = np.mean(dso.data, axis=0)
        fdm = list(zip(dso.labels[1], fd))
        sms = sorted(fdm, key=lambda x: fn(x[1]), reverse=True)
        metabolites = [m for m, s in sms]

        labelsY = metabolites[:30]
        labelsX = list(set(dso.classes[0]))
        dso = dso.as_filtered(dim=1, labels=labelsY)

        return self.build_heatmap_dso(labelsX, labelsY, self.build_change_table_of_classes(dso, labelsY, labelsX), remove_empty_rows=True, sort_data=True)

    def _top_metabolites_up(self, dso=None):
        fn = lambda x: x if x > 0 else 0
        return self._top_metabolites(dso, fn)

    def _top_metabolites_down(self, dso=None):
        fn = lambda x: abs(x) if x < 0 else 0
        return self._top_metabolites(dso, fn)

    def generate(self, input=None):
        data = self.predefined_heatmaps[self.config.get('predefined_heatmap')](input)
        return {'output': data}


class Heatmap(VisualisationPlugin):

    def __init__(self, *args, **kwargs):
        super(Heatmap, self).__init__(*args, **kwargs)
        HeatmapApp.plugin = self
        self.register_app_launcher(HeatmapApp)
