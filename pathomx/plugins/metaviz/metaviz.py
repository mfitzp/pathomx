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
import pathomx.db as db
import pathomx.threads as threads

from pathomx.plugins import VisualisationPlugin
from pathomx.data import DataSet, DataDefinition
from pathomx.db import ReactionIntermediate
from pathomx.views import SVGView
from pathomx.qt import *

PRUNE_ALL = lambda a, b, c, d: (a, b, c)
PRUNE_IDENTICAL = lambda a, b, c, d: (a, b, c, d)

# Internal URLS
COMPOUND_URL = 'pathomx://db/compound/%s/view'
PATHWAY_URL = 'pathomx://db/pathway/%s/view'
REACTION_URL = 'pathomx://db/reaction/%s/view'
PROTEIN_URL = 'pathomx://db/protein/%s/view'
GENE_URL = 'pathomx://db/gene/%s/view'

# Paper sizes for print scaling printing
METAPATH_PAPER_SIZES = {
    'None': (-1, -1),
    'A0': (33.11, 46.81),
    'A1': (23.39, 33.11),
    'A2': (16.54, 23.39),
    'A3': (11.69, 16.54),
    'A4': (8.27, 11.69),
    'A5': (5.83, 8.27),
}


def add_clusternodes(clusternodes, cluster_key, keys, nodes):
    for key in keys:
        clusternodes[cluster_key][key].extend(nodes)
    return clusternodes


def get_compound_color(analysis, m):
    return analysis[m.id][0] if m.id in analysis else '#cccccc'


def get_pathway_color(analysis, m):
    return analysis[m.id][0] if m.id in analysis else '#cccccc'


def get_reaction_color(analysis, r):
    # For reactions, we need gene and protein data (where it exists)
    colors = []
    if hasattr(r, 'proteins'):  # Dummy ReactionIntermediates will not; til that's fixed!
        for p in r.proteins:
            if p.id in analysis:
                colors.append(analysis[p.id][0])

            for g in p.genes:
                if g.id in analysis:
                    colors.append(analysis[g.id][0])

    if colors == []:
        colors = [utils.rdbu9[5]]  # Mid-grey      

    return '"%s"' % ':'.join(colors)


def generator(pathways, options, db, analysis=None, layout=None, verbose=True):

    #id,origin,dest,enzyme,dir,pathway
    #options.fit_paper = 'A4'

    if options.focus:
        focus_re = re.compile('.*(' + options.focus + ').*', flags=re.IGNORECASE)

    # Internode counter (create dummy nodes for split compounds)
    intno = 0

    # Pathway colour list
    #                   black       blue        green       red         orange      purple      yellow      pink
    colors = ['#000000', '#1f78b4', '#33a02c', '#e31a1c', '#ff7f00', '#392c85', '#ffff00', '#ff4398']  # sat 100
    colorslight = ['#aaaaaa', '#ccccff', '#b3ffb3', '#ffb3b3', '#ffedcc', '#ffb3fe', '#ffffcc', '#ffcce3']  # sat 20
    colorslighter = ['#cccccc', '#f2f2ff', '#f2fff2', '#fff2f2', '#fffbf2', '#fff2ff', '#fffff2', '#fff2f8']  # sat 5

    prunekey = PRUNE_IDENTICAL if (options.show_enzymes or options.show_secondary) else PRUNE_ALL

    # Store data about dummy nodes needing layout (on predefined layouts; where none supplied)
    layoutsrequired = dict()

    print("Building... ")
    # Subgraphs of metabolic pathways

    nodes = list()
    edges = list()
    edgesprune = list()
    #nodepathway = defaultdict( list )

    focus_compounds = list()
    inter_node = 0
    itr = 0

    clusternodes = dict()
    clusternodes['pathway'] = defaultdict(list)
    clusternodes['compartment'] = defaultdict(list)

    edgecluster = dict()
    edgecluster['pathway'] = defaultdict(list)
    edgecluster['compartment'] = defaultdict(list)

    clusters = dict()
    clusters['pathway'] = set(pathways)
    clusters['compartment'] = set()

    cluster_key = options.cluster_by
    clusters['compartment'].add('Non-compartmental')  # Need to override the color on this later

    # Store alternative pathways for reactions, for use when pruning deletes reactions
    pathway_edges_alternates = defaultdict(tuple)  # Dict of tuples pathway => 

    for p in pathways:
        for r in db.pathways[p.id].reactions:
        # Check that this edge is between items in one of the specified pathways
            compartments = [c for pr in r.proteins for c in pr.compartments]
            if compartments == []:
                compartments = ['Non-compartmental']
            clusters['compartment'] |= set(compartments)  # Add to cluster set
            # Store edge cluster data (reaction)
            edgecluster['pathway'][r].append(p)
            edgecluster['compartment'][r].extend(compartments)

            if options.focus:
                focus_match = list()
                focus_match.extend([l for l in r.mtins for m in [focus_re.search(l)] if m])
                focus_match.extend([l for l in r.mtouts for m in [focus_re.search(l)] if m])
                if len(focus_match) > 0:
                    visible = True
                    focus_compounds.extend(r.mtins)
                    focus_compounds.extend(r.mtouts)
                else:
                    visible = False
            else:
                visible = True

            nmtins = set()
            nmtouts = set()

            for mtin in r.mtins:
                for mtout in r.mtouts:
                    # Use a in/out/enzyme tuple to delete duplicates
                    if prunekey(mtin, mtout, r.dir, r.proteins) in edgesprune:
                        continue
                    else:
                        edgesprune.append(prunekey(mtin, mtout, r.dir, r.proteins))
                    nmtins.add(mtin)
                    nmtouts.add(mtout)

            if nmtins and nmtouts:

                mtins = list(nmtins)
                mtouts = list(nmtouts)

                # Make a copy of the reaction object, so we can add link data
                inter_react = copy.copy(r)  # FIXME:? This was a deepcopy, but causing recursion - switched to simple copy and still works
                inter_react.name = ''
                inter_react.proteins = []  # Hide the enzyme name, it'll be on the other object
                inter_react.smtins = []  # Hide the small compounds
                inter_react.smtouts = []  # Hide the small compounds

                edgecluster['pathway'][inter_react].append(p)
                edgecluster['compartment'][inter_react].extend(compartments)

                # If multiple ins/outs create dummy split-nodes
                # RXNINXX, RXNOUTXX
                if len(mtins) > 1:
                    intno += 1  # Increment no
                    inter_node = ReactionIntermediate(**{'id': "DUMMYRXN-IN%d" % intno, 'type': 'dummy'})
                    for mtin in mtins:
                        edges.append([inter_react, mtin, inter_node, visible])
                        clusternodes = add_clusternodes(clusternodes, 'pathway', [p], [mtin])
                        clusternodes = add_clusternodes(clusternodes, 'compartment', compartments, [mtin])

                    clusternodes = add_clusternodes(clusternodes, 'pathway', [p], [inter_node])
                    clusternodes = add_clusternodes(clusternodes, 'compartment', compartments, [inter_node])

                    nodes.append([inter_node, False, visible])
                    # Overwrite with the dummy name, use this as the basis of the main detail below
                    mtin = inter_node
                    if layout and [m for m in mtins if m.id in layout.objects] != []:
                        layoutsrequired["DUMMYRXN-IN%d" % intno] = [(layout.objects[m.id][0], layout.objects[m.id][1]) for m in mtins if m.id in layout.objects]
                else:
                    mtin = mtins[0]

                if len(mtouts) > 1:
                    intno += 1  # Increment no
                    inter_node = ReactionIntermediate(**{'id': "DUMMYRXN-OUT%d" % intno, 'type': 'dummy'})
                    for mtout in mtouts:
                        edges.append([inter_react, inter_node, mtout, visible])
                        clusternodes = add_clusternodes(clusternodes, 'pathway', [p], [mtout])
                        clusternodes = add_clusternodes(clusternodes, 'compartment', compartments, [mtout])

                    clusternodes = add_clusternodes(clusternodes, 'pathway', [p], [inter_node])
                    clusternodes = add_clusternodes(clusternodes, 'compartment', compartments, [inter_node])

                    nodes.append([inter_node, False, visible])
                    # Overwrite with the dummy name, use this as the basis of the main detail below
                    mtout = inter_node
                    if layout and [m for m in mtouts if m.id in layout.objects] != []:
                        layoutsrequired["DUMMYRXN-OUT%d" % intno] = [(layout.objects[m.id][0], layout.objects[m.id][1]) for m in mtouts if m.id in layout.objects]
                else:
                    mtout = mtouts[0]

                edges.append([r, mtin, mtout, visible])

                # Store clustering data for layout
                clusternodes = add_clusternodes(clusternodes, 'pathway', [p], [mtin])
                clusternodes = add_clusternodes(clusternodes, 'compartment', compartments, [mtin])
                clusternodes = add_clusternodes(clusternodes, 'pathway', [p], [mtout])
                clusternodes = add_clusternodes(clusternodes, 'compartment', compartments, [mtout])

    # id,type,names
    for m in list(db.compounds.values()):

        # It's in one of our pathways (union)
        if set(m.pathways) & set(pathways):
            fillcolor = False

            if analysis:
                if m.id in analysis:
                # We found it by one of the names
                    fillcolor = analysis[m.id]

            # This node is in one of our pathways, store it
            nodes.append([m, fillcolor, visible])


    # Add pathway annotations
    if options.show_pathway_links:

        visible_reactions = [r for r, x1, x2, x3 in edges]
        visible_nodes = [n for n, x1, x2 in nodes]

        pathway_annotate = set()
        pathway_annotate_dupcheck = set()
        for id, r in list(db.reactions.items()):

        # Check that a reaction for this isn't already on the map
            if r not in visible_reactions:
                # Now find out which end of it is (one side's compounds [or both])
                for p in r.pathways:
                    pathway_node = ReactionIntermediate(**{'id': '%s' % p.id, 'name': p.name, 'type': 'pathway'})

                    for mt in r.mtins:
                        if mt in visible_nodes and (p, mt) not in pathway_annotate_dupcheck:  # Compound is already on the graph
                            print(mt)
                            mp = db.compounds[mt.id].pathways[0]
                            pathway_annotate.add((p, mp, pathway_node, mt, pathway_node, r.dir))
                            pathway_annotate_dupcheck.add((p, mt))
                            break

                    for mt in r.mtouts:
                        if mt in visible_nodes and (p, mt) not in pathway_annotate_dupcheck:  # Compound is already on the graph
                            mp = db.compounds[mt.id].pathways[0]
                            pathway_annotate.add((p, mp, pathway_node, pathway_node, mt, r.dir))
                            pathway_annotate_dupcheck.add((p, mt))
                            break

    
        for p, mp, pathway_node, mtin, mtout, dir in list(pathway_annotate):
            itr += 1
            #nodepathway[mp].append(pathway_node)
            inter_react = ReactionIntermediate(**{'id': "DUMMYPATHWAYLINK-%s" % itr, 'type': 'dummy', 'dir': dir, 'pathways': [mp]})
            edges.append([inter_react, mtin, mtout, True])

            if analysis:  # and options.mining:
                # Not actually used for color, this is a ranking value (bud-sized on pathway link)
                p_compound_scores = [analysis[m.id] for m in p.compounds if m.id in analysis]
                print(p_compound_scores)
                if p_compound_scores:
                    fillcolor = sum(p_compound_scores) / len(p_compound_scores)
                else:
                    fillcolor = None
                # fillcolor = max(1, 11-analysis['mining_ranked_remaining_pathways'].index( p.id ) ) if p.id in analysis['mining_ranked_remaining_pathways'] else 1
            else:
                fillcolor = None

            nodes.append([pathway_node, fillcolor, True])

    # Generate the analysis graph from datasets
    graph = pydot.Dot('\u200C', graph_type='digraph', sep="+15,+10", esep="+5,+5", labelfloat='false', outputMode='edgeslast', fontname='Calibri', splines=options.splines, gcolor='white', pad=0.5, model='mds', overlap="vpsc")  # , model='mds') #, overlap='ipsep', mode='ipsep', model='mds')
    subgraphs = list()
    clusterclu = dict()

    nodes_added = set()  # Store nodes that are added, can use simplified adding for subsequent pathways

    # Handle positioning of our dummy points on positioned elements
    # Must do this or they'll be pushed off the map
    # Overlapping will cause a crash as the map attempts to scale them away from one another
    if layout:
        clashcheck = []
        shifts = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]
        mult = 2
        for id, xys in list(layoutsrequired.items()):
            xy = (np.mean([xy[0] for xy in xys]), np.mean([xy[1] for xy in xys]))
            while xy in clashcheck:
                for s in shifts:
                    nxy = (xy[0] + (s[0] * mult), xy[1] + (s[1] * mult))
                    if nxy not in clashcheck:
                        xy = nxy
                    break
                mult += 1

            layout.objects[id] = xy
            clashcheck.append(xy)

    # Arrange layout grouping (e.g. by pathway, compartment, etc.)
    for sgno, cluster in enumerate(clusters[cluster_key]):
        clusterclu[cluster] = (sgno % 7) + 1

        if options.highlightregions:
            if options.cluster_by == 'compartment':
                bcolor = colorslight[clusterclu[cluster]]
                bgcolor = colorslighter[clusterclu[cluster]]
                style = 'rounded'
            else:
                bcolor = '#eeeeee'
                bgcolor = 'transparent'
                style = 'solid'
        else:
            bcolor = 'transparent'
            bgcolor = 'transparent'
            style = 'solid'

        subgraph = pydot.Cluster(str(sgno), label='%s' % cluster, graph_type='digraph', fontname='Calibri', splines=options.splines, color=bcolor, bgcolor=bgcolor, style=style, fontcolor=bcolor, labeljust='left', pad=0.5, margin=12, labeltooltip='%s' % cluster, URL='non')  # PATHWAY_URL % cluster.id )
        # Read node file of compounds to show
        # TODO: Filter this by the option specification
        for n in clusternodes[cluster_key][cluster]:
            subgraph.add_node(pydot.Node(n.id))
        graph.add_subgraph(subgraph)


    # Add nodes to map

    for m, node_color, visible in nodes:

        if m in nodes_added:  # Previously added, another pathway: use simplified add (speed up)
            graph.add_node(pydot.Node(m.id))
            continue  # Next

        label = ' '
        color = 'black'
        shape = 'rect'
        fontcolor = 'black'
        fillcolor = '#eeeeee'
        colorscheme = 'rdbu9'
        url = COMPOUND_URL
        width, height = 0.75, 0.5

                    
        if visible:
            style = 'filled'
        else:
            style = 'invis'

        if m.type == 'dummy':
            shape = 'point'
            fillcolor = 'black'
            border = 0
            width, height = 0.01, 0.01
            url = 'pathomx://null/%s'  # Null, don't navigate FIXME

        elif m.type == 'pathway':
            shape = 'point'
            label = '%s' % m.name
            size = len(db.pathways[m.id].compounds)
            width, height = size / 24., size / 24.
            if node_color is None:
                fillcolor = '#cccccc'
                color = '#cccccc'
            else:
                color = node_color[0]
            border = 0
            url = PATHWAY_URL

        else:
            label = label = "%s" % m.name  # {%s |{ | | } } "
            if node_color == False:
                if analysis:  # Showing data
                    fillcolor = '#ffffff'
                else:
                    fillcolor = '#eeeeee'
            else:
                shape = 'box'
                style = 'filled'
                fontcolor = node_color[1]
                fillcolor = node_color[0]

            if options.show_network_analysis:
                border = min(len(m.reactions) / 2, 5)
            else:
                border = 0

        if options.show_molecular and hasattr(m, 'image'):
            label = ' '
            if analysis and node_color and isinstance(node_color[2], int):
                image = m.imagecolor % int(node_color[2])
            else:
                image = m.image
            style = 'solid'
            shape = 'none'
        else:
            image = False

        if layout and m.id in list(layout.objects.keys()):
            pos = '%s,%s!' % layout.objects[m.id]
                # Fugly duplication, but appears to be no way to set a 'none' position
            graph.add_node(pydot.Node(m.id, width=width, height=height, style=style, shape=shape, color=color, penwidth=border, fontname='Calibri', colorscheme=colorscheme, fontcolor=fontcolor, fillcolor=fillcolor, label=label, labeltooltip=label, URL=url % m.id, pos=pos))  # http://metacyc.org/META/substring-search?object=%s                
        else:
            if image:
                graph.add_node(pydot.Node(m.id, width=width, height=height, image=image, style=style, shape=shape, color=color, penwidth=border, fontname='Calibri', colorscheme=colorscheme, fontcolor=fontcolor, fillcolor=fillcolor, label=label, labeltooltip=label, URL=url % m.id))  # http://metacyc.org/META/substring-search?object=%s
            else:
                graph.add_node(pydot.Node(m.id, width=width, height=height, style=style, shape=shape, color=color, penwidth=border, fontname='Calibri', colorscheme=colorscheme, fontcolor=fontcolor, fillcolor=fillcolor, label=label, labeltooltip=label, URL=url % m.id))  # http://metacyc.org/META/substring-search?object=%s

        nodes_added.add(m)
    # Add graph edges to the map

    style = ' '
    for r, origin, dest, visible in edges:
        label = list()
        arrowhead = 'normal'
        arrowtail = 'empty'
        color = '#888888'
        url = REACTION_URL
        length = 2
        penwidth = 1
        weight = 1
        dir = r.dir

        # End of any edge touching a DUMMY-RXN is left blank
        if dest.type == 'dummy':
            arrowhead = 'none'
            length = 1.3

        if origin.type == 'dummy':
            arrowtail = 'none'
            length = 1.3

        if visible:
            style = ' '
        else:
            style = 'invis'

        if analysis:
            color = get_reaction_color(analysis, r)
            colorscheme = 'rdbu9'

        elif options.highlightpathways:
            #color=1+( ] % 11) # Length of colorscheme -1
            r_clusterclu = list(set(edgecluster[cluster_key][r]) & set(clusterclu))
            color = '"%s"' % ':'.join([colors[n] for n in sorted([clusterclu[c] for c in r_clusterclu])])
            colorscheme = 'paired12'

        if r.type == 'dummy':
            color = '#cccccc'
        else:

            if options.show_enzymes:
                label.append('%s' % r.name)

            if options.show_enzymes and hasattr(r, 'proteins') and r.proteins:
                if analysis:
                    prgenestr = ''
                    for pr in r.proteins:
                        if pr.id in analysis:
                            prgenestr += '<font color="%s">&#x25C6;</font>' % analysis[pr.id][0]
                        for g in pr.genes:
                            if g.id in analysis:
                                prgenestr += '<font color="%s">&#x25cf;</font>' % analysis[g.id][0]
                    label.append('%s' % prgenestr)  # pr.genes

            if options.show_secondary and (hasattr(r, 'smtins')):  # If there's an in there's an out
                if len(r.smtins + r.smtouts) > 0:
                    # Process to add colors if compound in db
                    smtins, smtouts = [], []
                    for sm in r.smtins:
                        if analysis and sm.id in analysis:
                            smtins.append('<font color="%s">%s</font>' % (analysis[sm.id][0], sm))  # We found it by one of the names
                        else:
                            smtins.append('%s' % sm)

                    for sm in r.smtouts:
                        if analysis and sm.id in analysis:
                            smtouts.append('<font color="%s">%s</font>' % (analysis[sm.id][0], sm))  # We found it by one of the names
                        else:
                            smtouts.append('%s' % sm)

                    label.append('%s &rarr; %s' % (', '.join(smtins), ', '.join(smtouts)))

        #if options.show_network_analysis:
        #    width = min( len( r.pathways ), 5)
        #else:
        #    width = 1

        if hasattr(r, 'gibbs'):
            penwidth = abs(r.gibbs['deltaG_w'])

        e = pydot.Edge(origin.id, dest.id, weight=weight, len=length, penwidth=penwidth, dir=dir, label='<' + '<br />'.join(label) + '>', colorscheme=colorscheme, color=color, fontcolor='#888888', fontsize='10', arrowhead=arrowhead, arrowtail=arrowtail, style=style, fontname='Calibri', URL=url % r.id, labeltooltip=' ')
        graph.add_edge(e)

    return graph


# Dialog box for Metabohunter search options
class MetaVizPathwayConfigPanel(ui.ConfigPanel):

    def __init__(self, *args, **kwargs):
        super(MetaVizPathwayConfigPanel, self).__init__(*args, **kwargs)

        #all_pathways = parent.db.pathways.keys()
        self.all_pathways = sorted([p.name for p in list(self.m.db.pathways.values())])

        self.label = defaultdict(dict)
        #selected_pathways = str(  ).split(',')
        self.setupSection('Show', '/Pathways/Show')  # selected_pathways=[p.name for p in self.m.db.pathways.values() if p.id in selected_pathways] )
        #selected_pathways = str( self.config.get() ).split(',')
        self.setupSection('Hide', '/Pathways/Hide')  # selected_pathways=[p.name for p in self.m.db.pathways.values() if p.id in selected_pathways] )        

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

        fwd_map = lambda x: self.m.db.synrev[x].id
        rev_map = lambda x: self.m.db.pathways[x].name

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

        show_pathway_linksAction = QPushButton(QIcon(os.path.join(utils.scriptdir, 'icons', 'node-select-all.png')), ' Show Links to Hidden Pathways', self.m)
        show_pathway_linksAction.setStatusTip('Show links to pathways currently not visible')
        show_pathway_linksAction.setCheckable(True)
        self.config.add_handler('/Pathways/ShowLinks', show_pathway_linksAction)

        showenzymesAction = QPushButton('Show proteins/enzymes', self.m)
        showenzymesAction.setStatusTip('Show protein/enzymes on reactions')
        showenzymesAction.setCheckable(True)
        self.config.add_handler('/App/ShowEnzymes', showenzymesAction)

        show2ndAction = QPushButton(QIcon(os.path.join(utils.scriptdir, 'icons', 'compounds-small.png')), ' Show 2° compounds', self.m)
        show2ndAction.setStatusTip('Show 2° compounds on reaction paths')
        show2ndAction.setCheckable(True)
        self.config.add_handler('/App/Show2nd', show2ndAction)

        showmolecularAction = QPushButton(QIcon(os.path.join(utils.scriptdir, 'icons', 'compound-structure.png')), ' Show molecular structures', self.m)
        showmolecularAction.setStatusTip('Show molecular structures instead of names on pathway maps')
        showmolecularAction.setCheckable(True)
        self.config.add_handler('/App/ShowMolecular', showmolecularAction)

        showanalysisAction = QPushButton('Show network analysis', self.m)
        showanalysisAction.setStatusTip('Show network analysis hints and molecular importance')
        showanalysisAction.setCheckable(True)
        self.config.add_handler('/App/ShowAnalysis', showanalysisAction)

        highlightcolorsAction = QPushButton(QIcon(os.path.join(utils.scriptdir, 'icons', 'visualization.png')), ' Highlight Reaction Pathways', self.m)
        highlightcolorsAction.setStatusTip('Highlight pathway reactions by color')
        highlightcolorsAction.setCheckable(True)
        self.config.add_handler('/App/HighlightPathways', highlightcolorsAction)

        highlightregionAction = QPushButton(QIcon(os.path.join(utils.scriptdir, 'icons', 'visualization.png')), ' Highlight regions', self.m)
        highlightregionAction.setStatusTip('Highlight regions')
        highlightregionAction.setCheckable(True)
        self.config.add_handler('/App/HighlightRegions', highlightregionAction)

        self.cluster_control = QComboBox()
        self.cluster_control.addItems(['pathway', 'compartment'])
        self.config.add_handler('/App/ClusterBy', self.cluster_control)

        vw = QVBoxLayout()
        vw.addWidget(show_pathway_linksAction)
        vw.addWidget(showenzymesAction)
        vw.addWidget(show2ndAction)
        vw.addWidget(showmolecularAction)
        vw.addWidget(showanalysisAction)
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

    def __init__(self, auto_consume_data=True, **kwargs):
        super(MetaVizApp, self).__init__(**kwargs)

        self.addDataToolBar()
        self.addFigureToolBar()

        self.data.add_input('suggested_pathways')  # Add input slot
        self.data.add_input('compound_data')  # Add input slot
        self.data.add_input('gene_data')  # Add input slot
        self.data.add_input('protein_data')  # Add input slot

        self.views.addView(SVGView(self), 'View')

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
            # Pathways
            '/Pathways/Show': ['GLYCOLYSIS'],
            '/Pathways/Hide': [],
            '/Pathways/ShowLinks': False,
            # App
            '/App/ShowEnzymes': True,
            '/App/Show2nd': True,
            '/App/ShowMolecular': True,
            '/App/ShowAnalysis': True,

            '/App/HighlightPathways': True,
            '/App/HighlightRegions': True,

            '/App/ClusterBy': 'pathway',
        })

        self.addConfigPanel(MetaVizPathwayConfigPanel, 'Pathways')
        self.addConfigPanel(MetaVizViewConfigPanel, 'Settings')

        self.finalise()

    def url_handler(self, url):

        kind, id, action = url.split('/')  # FIXME: Can use split here once stop using pathwaynames           

        # url is Qurl kind
        # Add an object to the current view
        if action == 'add':

            # FIXME: Hacky test of an idea
            if kind == 'pathway' and id in self.m.db.pathways:
                # Add the pathway and regenerate
                pathways = self.config.get('/Pathways/Show').split(',')
                pathways.append(urllib.parse.unquote(id))
                self.config.set('/Pathways/Show', ','.join(pathways))
                self.generateGraphApp()

        # Remove an object to the current view
        if action == 'remove':

            # FIXME: Hacky test of an idea
            if kind == 'pathway' and id in self.m.db.pathways:
                # Add the pathway and regenerate
                pathways = self.config.get('/Pathways/Show').split(',')
                pathways.remove(urllib.parse.unquote(id))
                self.config.set('/Pathways/Show', ','.join(pathways))
                self.generateGraphApp()

    def generate(self, suggested_pathways=None, compound_data=None, gene_data=None, protein_data=None, **kwargs):
        # By default use the generated pathomx file to view
        filename = os.path.join(QDir.tempPath(), 'pathomx-generated-pathway.svg')

        tps = self.generateGraph(filename=filename, suggested_pathways=suggested_pathways, compound_data=compound_data, gene_data=gene_data, protein_data=protein_data, format='svg')
        if tps == None:
            svg_source = [open(filename).read().decode('utf8')]
            tps = [0]
        else:
            filename = self.get_filename_with_counter(filename)
            svg_source = [
                open(os.path.join(QDir.tempPath(), filename % tp)).read().decode('utf8')
                for tp in tps
                ]

        # Add file:// refs to image links (Graphviz bug?)
        svg_source = [s.replace('<image xlink:href="', '<image xlink:href="file://') for s in svg_source]

        #self.browser.setSVG(svg_source[0]) #,"~")
        self.progress.emit(90)
        return {
            'svg': svg_source[0],
        }

    def prerender(self, svg=''):
        return {'View': {'svg': svg}}

    def get_filename_with_counter(self, filename):
        fn, ext = os.path.splitext(filename)
        return fn + "-%s" + ext

    def generateGraph(self, filename, suggested_pathways=[], compound_data=None, gene_data=None, protein_data=None, format='svg'):
        # Build options-like structure for generation of graph
        # (compatibility with command line version, we need to fake it)
        options = Values()

        options._update_loose({
            'file': None,
            #'pathways': self.config.Read('/Pathways/Show'),
            #'not_pathways':'',
            'show_all': False,  # self.config.ReadBool('/Pathways/ShowAll'),
            'search': '',
            'cluster_by': self.config.get('/App/ClusterBy'),
            'show_enzymes': self.config.get('/App/ShowEnzymes'),  # self.config.ReadBool('/App/ShowEnzymes'),
            'show_secondary': self.config.get('/App/Show2nd'),
            'show_molecular': self.config.get('/App/ShowMolecular'),
            'show_network_analysis': self.config.get('/App/ShowAnalysis'),

            'highlightpathways': self.config.get('/App/HighlightPathways'),
            'highlightregions': self.config.get('/App/HighlightRegions'),

            'splines': 'true',
            'focus': False,
            'show_pathway_links': self.config.get('/Pathways/ShowLinks'),
            # Always except when saving the file
            'output': format,

        })

        #pathway_ids = self.config.value('/Pathways/Show').split(',')
        if suggested_pathways:
            pathway_ids = [p.id for p in suggested_pathways.entities[1]]
        else:
            pathway_ids = []

        print(self.config.get('/Pathways/Show'))

        # Add the manually Shown pathways
        pathway_ids_show = self.config.get('/Pathways/Show')
        pathway_ids.extend(pathway_ids_show)

        # Now remove the Hide pathways
        pathway_ids_hide = self.config.get('/Pathways/Hide')
        pathway_ids = [p for p in pathway_ids if p not in pathway_ids_hide]

        # Convert pathways_ids to pathways
        pathways = [self.m.db.pathways[pid] for pid in pathway_ids if pid in list(self.m.db.pathways.keys())]

        
        if pathway_ids == []:
            return None

        
        if compound_data or gene_data or protein_data:

        # Generate independent scales
            node_colors = {}

            for dsi in compound_data, gene_data, protein_data:
                if dsi == None:
                    continue
                #if self.m.data.analysis_timecourse:
                #    # Generate the multiple views
                #    tps = sorted( self.m.data.analysis_timecourse.keys(), key=int )
                #    # Insert counter variable into the filename
                #    filename = self.get_filename_with_counter(filename)
                #    print "Generate timecourse..."
                #    for tp in tps:
                #        print "%s" % tp
                #        graph = generator( pathways, options, self.m.db, analysis=self.m.data.analysis_timecourse[ tp ]) #, layout=self.layout)
                #        graph.write(filename % tp, format=options.output, prog='neato')
                #    return tps
                #else:
                print("Generate map for single control:test...")
                # Build analysis lookup dict; we want a single color for each metabolite
                mini, maxi = min(abs(np.median(dsi.data)), 0), max(abs(np.median(dsi.data)), 0)
                mini, maxi = -1.0, +1.0  # Fudge; need an intelligent way to determine (2*median? 2*mean?)
                scale = utils.calculate_scale([mini, 0, maxi], [9, 1], out=np.around)  # rdbu9 scale

                for n, m in enumerate(dsi.entities[1]):
                    if m is not None:
                        ecol = utils.calculate_rdbu9_color(scale, dsi.data[0, n])
                        #print xref, ecol
                        if ecol is not None:
                            node_colors[m.id] = ecol

            graph = generator(pathways, options, self.m.db, analysis=node_colors)  # , layout=self.layout)
            self.status.emit('waiting')
            self.progress.emit(0.5)
            graph.write(filename, format=options.output, prog='neato')
            return None
        else:
            graph = generator(pathways, options, self.m.db)  # , layout=self.layout)
            self.status.emit('waiting')
            self.progress.emit(0.5)
            graph.write(filename, format=options.output, prog='neato')
            return None


class MetaViz(VisualisationPlugin):

    def __init__(self, **kwargs):
        super(MetaViz, self).__init__(**kwargs)
        MetaVizApp.plugin = self
        self.register_app_launcher(MetaVizApp)
