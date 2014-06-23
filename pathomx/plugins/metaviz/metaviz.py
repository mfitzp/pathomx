# -*- coding: utf-8 -*-
from optparse import Values, OptionParser
from collections import defaultdict
import os
import sys
import re
import math
import pydot
#import networkx as nx
import numpy as np
import copy

import operator
import pathomx.ui as ui
import pathomx.utils as utils

from pathomx.plugins import VisualisationPlugin
from pathomx.data import DataSet, DataDefinition
from pathomx.views import SVGView
from pathomx.qt import *

from biocyc import biocyc


# Dialog box for Metabohunter search options
class MetaVizPathwayConfigPanel(ui.ConfigPanel):

    def __init__(self, *args, **kwargs):
        super(MetaVizPathwayConfigPanel, self).__init__(*args, **kwargs)

        #all_pathways = parent.db.dbm.pathways.keys()
        #self.all_pathways = sorted([p.name for id, p in db.dbm.get_pathways()])
        self.all_pathways = [p.name for p in biocyc.known_pathways]

        self.label = defaultdict(dict)
        #selected_pathways = str(  ).split(',')
        self.setupSection('Show', 'show_pathways')  # selected_pathways=[p.name for p in db.dbm.pathways.values() if p.id in selected_pathways] )
        #selected_pathways = str( self.config.get() ).split(',')
        self.setupSection('Hide', 'hide_pathways')  # selected_pathways=[p.name for p in db.dbm.pathways.values() if p.id in selected_pathways] )        

        self.finalise()

    def onRegexpAdd(self):
        label = self.sender().objectName()
        items = self.label[label]['lw_pathways'].findItems(self.label[label]['lw_regExp'].text(), Qt.MatchContains)
        block = self.label[label]['lw_pathways'].blockSignals(True)
        for i in items:
            i.setSelected(True)
        self.label[label]['lw_pathways'].blockSignals(block)
        self.label[label]['lw_pathways'].itemSelectionChanged.emit()

    def onRegexpRemove(self):
        label = self.sender().objectName()
        items = self.label[label]['lw_pathways'].findItems(self.label[label]['lw_regExp'].text(), Qt.MatchContains)
        block = self.label[label]['lw_pathways'].blockSignals(True)
        for i in items:
            i.setSelected(False)
        self.label[label]['lw_pathways'].blockSignals(block)
        self.label[label]['lw_pathways'].itemSelectionChanged.emit()

    def setupSection(self, label, pathway_config):
        # SHOW PATHWAYS
        gb = QGroupBox(label)
        vbox = QVBoxLayout()
        # Populate the list boxes
        self.label[label]['lw_pathways'] = QListWidget()
        self.label[label]['lw_pathways'].setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.label[label]['lw_pathways'].addItems(self.all_pathways)
        self.label[label]['lw_pathways'].sortItems(Qt.AscendingOrder)

        fwd_map = lambda x: biocyc.find_pathway_by_name(x).id
        rev_map = lambda x: biocyc.get(x).name

        self.config.add_handler(pathway_config, self.label[label]['lw_pathways'], (fwd_map, rev_map))
        #for p in selected_pathways:
        #    self.label[label]['lw_pathways'].findItems(p, Qt.MatchExactly)[0].setSelected(True)

        self.label[label]['lw_regExp'] = QLineEdit()

        vbox.addWidget(self.label[label]['lw_pathways'])
        vbox.addWidget(QLabel('Select/deselect matching pathways by name:'))
        vboxh = QHBoxLayout()

        vboxh.addWidget(self.label[label]['lw_regExp'])

        addfr = QPushButton('-')
        addfr.clicked.connect(self.onRegexpRemove)
        addfr.setObjectName(label)
        addfr.setFixedWidth(24)

        remfr = QPushButton('+')
        remfr.clicked.connect(self.onRegexpAdd)
        remfr.setObjectName(label)
        remfr.setFixedWidth(24)

        vboxh.addWidget(addfr)
        vboxh.addWidget(remfr)
        vbox.addLayout(vboxh)

        gb.setLayout(vbox)
        self.layout.addWidget(gb)


# Dialog box for Metabohunter search options
class MetaVizViewConfigPanel(ui.ConfigPanel):

    def __init__(self, *args, **kwargs):
        super(MetaVizViewConfigPanel, self).__init__(*args, **kwargs)

        show_pathway_linksAction = QPushButton(QIcon(os.path.join(utils.scriptdir, 'icons', 'node-select-all.png')), ' Show Links to Hidden Pathways', self.parent())
        show_pathway_linksAction.setStatusTip('Show links to pathways currently not visible')
        show_pathway_linksAction.setCheckable(True)
        self.config.add_handler('show_pathway_links', show_pathway_linksAction)

        showenzymesAction = QPushButton('Show proteins/enzymes', self.parent())
        showenzymesAction.setStatusTip('Show protein/enzymes on reactions')
        showenzymesAction.setCheckable(True)
        self.config.add_handler('show_enzymes', showenzymesAction)

        show2ndAction = QPushButton(QIcon(os.path.join(utils.scriptdir, 'icons', 'compounds-small.png')), ' Show 2° compounds', self.parent())
        show2ndAction.setStatusTip('Show 2° compounds on reaction paths')
        show2ndAction.setCheckable(True)
        self.config.add_handler('show_secondary', show2ndAction)

        showmolecularAction = QPushButton(QIcon(os.path.join(utils.scriptdir, 'icons', 'compound-structure.png')), ' Show molecular structures', self.parent())
        showmolecularAction.setStatusTip('Show molecular structures instead of names on pathway maps')
        showmolecularAction.setCheckable(True)
        self.config.add_handler('show_molecular', showmolecularAction)

        showanalysisAction = QPushButton('Show network analysis', self.parent())
        showanalysisAction.setStatusTip('Show network analysis hints and molecular importance')
        showanalysisAction.setCheckable(True)
        self.config.add_handler('show_analysis', showanalysisAction)

        showgibbsAction = QPushButton(QIcon(os.path.join(utils.scriptdir, 'icons', 'visualization.png')), ' Show Gibbs reaction', self.parent())
        showgibbsAction.setStatusTip('Show Gibbs reaction rates')
        showgibbsAction.setCheckable(True)
        self.config.add_handler('show_gibbs', showgibbsAction)

        highlightcolorsAction = QPushButton(QIcon(os.path.join(utils.scriptdir, 'icons', 'visualization.png')), ' Highlight Reaction Pathways', self.parent())
        highlightcolorsAction.setStatusTip('Highlight pathway reactions by color')
        highlightcolorsAction.setCheckable(True)
        self.config.add_handler('highlightpathways', highlightcolorsAction)

        highlightregionAction = QPushButton(QIcon(os.path.join(utils.scriptdir, 'icons', 'visualization.png')), ' Highlight regions', self.parent())
        highlightregionAction.setStatusTip('Highlight regions')
        highlightregionAction.setCheckable(True)
        self.config.add_handler('highlightregions', highlightregionAction)

        self.cluster_control = QComboBox()
        self.cluster_control.addItems(['pathway', 'compartment'])
        self.config.add_handler('cluster_by', self.cluster_control)

        vw = QVBoxLayout()
        vw.addWidget(show_pathway_linksAction)
        vw.addWidget(showenzymesAction)
        vw.addWidget(show2ndAction)
        vw.addWidget(showmolecularAction)
        vw.addWidget(showanalysisAction)
        vw.addWidget(showgibbsAction)
        gb = QGroupBox('Annotate')
        gb.setLayout(vw)

        self.layout.addWidget(gb)

        vw = QVBoxLayout()
        vw.addWidget(highlightcolorsAction)
        vw.addWidget(highlightregionAction)
        vw.addWidget(self.cluster_control)
        gb = QGroupBox('Highlight')
        gb.setLayout(vw)

        self.layout.addWidget(gb)

        self.finalise()


class MetaVizApp(ui.AnalysisApp):

    notebook = 'metaviz.ipynb'

    legacy_inputs = {'input': 'compound_data', 'data': 'compound_data'}

    def __init__(self, *args, **kwargs):
        super(MetaVizApp, self).__init__(*args, **kwargs)

        self.addDataToolBar()
        self.addFigureToolBar()

        self.data.add_input('suggested_pathways')  # Add input slot
        self.data.add_input('compound_data')  # Add input slot
        self.data.add_input('gene_data')  # Add input slot
        self.data.add_input('protein_data')  # Add input slot

        # Setup data consumer options
        self.data.consumer_defs.extend([
            DataDefinition('suggested_pathways', {
            'entities_t': (None, ['Pathway']),
            }, 'Show pathways'),
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

        # Define default settings for pathway rendering
        self.config.set_defaults({
            'show_pathways': ['PWY66-400'],
            'hide_pathways': [],
            
            'cluster_by': 'pathway',
            'show_enzymes': True,
            'show_secondary': True,
            'show_molecular': True,
            'show_network_analysis': True,
            'show_gibbs': False,

            'highlightpathways': True,
            'highlightregions': True,

            'show_pathway_links': False,
            'output_format': 'svg',
        })

        self.addConfigPanel(MetaVizPathwayConfigPanel, 'Pathways')
        self.addConfigPanel(MetaVizViewConfigPanel, 'Settings')

    def url_handler(self, url):

        kind, id, action = url.split('/')  # FIXME: Can use split here once stop using pathwaynames           

        # url is Qurl kind
        # Add an object to the current view
        if action == 'add':

            # FIXME: Hacky test of an idea
            if kind == 'pathway' and db.dbm.pathway(id) is not None:
                # Add the pathway and regenerate
                pathways = self.config.get('show_pathways').split(',')
                pathways.append(urllib.parse.unquote(id))
                self.config.set('show_pathways', ','.join(pathways))
                self.generateGraphApp()

        # Remove an object to the current view
        if action == 'remove':

            # FIXME: Hacky test of an idea
            if kind == 'pathway' and db.dbm.pathway(id) is not None:
                # Add the pathway and regenerate
                pathways = self.config.get('show_pathways').split(',')
                pathways.remove(urllib.parse.unquote(id))
                self.config.set('show_pathways', ','.join(pathways))
                self.generateGraphApp()


class MetaViz(VisualisationPlugin):

    def __init__(self, *args, **kwargs):
        super(MetaViz, self).__init__(*args, **kwargs)
        MetaVizApp.plugin = self
        self.register_app_launcher(MetaVizApp)
