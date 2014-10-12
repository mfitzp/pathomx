import os
from biocyc import biocyc, Pathway, Gene, Compound, Protein
biocyc.set_organism('HUMAN')
biocyc.secondary_cache_paths.append(os.path.join(_pathomx_database_path, 'biocyc'))

import metaviz
import tempfile

import pandas as pd
import numpy as np

import matplotlib as mpl
import matplotlib.cm as cm
from matplotlib.colors import rgb2hex

from pathomx.utils import luminahex

if compound_data is not None or gene_data is not None or protein_data is not None:

    datasets = []
    for data in compound_data, gene_data, protein_data:
        if data is None:
            continue

        # We need BioCyc identifiers to work with the MetaViz module
        if 'BioCyc' not in data.columns.names:
            continue

        datasets.append(data)

    analysis = {}
    mins, maxes = [], []
    for data in datasets:
        # Find mapping ranges
        mins.append(np.min(data.values))
        maxes.append(np.max(data.values))

    overall_min = min(mins)
    overall_max = max(maxes)

    data = None
    # Prevent export

    if overall_min < 0 and overall_max > 0:
        # If crossing zero use a diverging map; else use a linear
        colormap = cm.RdBu_r
        # Set min/max to the negative and positive of the max abs of both
        # so extends in both directions equally
        overall_max = max(abs(overall_min), overall_max)
        overall_min = -(overall_max)

    elif overall_min < 0:
        colormap = cm.Blues_r

    elif overall_min >= 0:
        colormap = cm.Reds

    norm = mpl.colors.SymLogNorm(linthresh=0.001, vmin=overall_min, vmax=overall_max, clip=True)
    mapper = cm.ScalarMappable(norm=norm, cmap=colormap)

    for data in datasets:
        ids = [e[data.columns.names.index('BioCyc')] for e in data.columns.values]
        # We can only use a single row at the moment, so process through fold change etc. first
        values = data.iloc[0]
        for e, v in zip(ids, values):
            if type(e) in [Gene, Compound, Protein]:
                hexcol = rgb2hex(mapper.to_rgba(v))
                l = luminahex(hexcol)
                if l < 0.5:
                    contrasthexcol = '#ffffff'
                else:
                    contrasthexcol = '#000000'

                analysis[e] = (hexcol, contrasthexcol)

    print "Range %.2f..%.2f" % (overall_min, overall_max)

else:
    analysis = None


if suggested_pathways is not None:
    # Pathways should come in as a column set named 'BioCyc' but containing Pathway objects
    if 'BioCyc' in suggested_pathways.columns.names:
        if type(suggested_pathways.columns) == pd.Index:
            ps = suggested_pathways.columns.values
        elif type(suggested_pathways.columns) == pd.MultiIndex:
            ps = suggested_pathways.columns.values[suggested_pathways.columns.names.index('BioCyc')]

    pathways = []
    for p in ps:
        if type(p) == Pathway:
            pathways.append(p)
        else:
            try:
                p = biocyc.get(id)
            except:
                pass
            else:
                if type(p) == Pathway:
                    pathways.append(p)
else:
    pathways = []
pathways.extend([biocyc.get(p) for p in config['show_pathways']])
pathways = [p for p in pathways if p.id not in config['hide_pathways']]

pathways = list(set(pathways))

print("Forcing display of %s" % config['show_pathways'])
print("Suppressing display of %s" % config['hide_pathways'])

reactions = ['PYRUVDEH-RXN']  # Fix this; add some way to manually add reactions (UI)

# By default use the generated pathomx file to view
filename = tempfile.mkstemp(suffix='svg')
graph = metaviz.generate(pathways, analysis=analysis, reactions=reactions, **{
    'cluster_by': config['cluster_by'],
    'show_enzymes': config['show_enzymes'],
    'show_secondary': config['show_secondary'],
    'show_molecular': config['show_molecular'],
    'show_network_analysis': config['show_network_analysis'],
    'show_gibbs': config['show_gibbs'],

    'highlightpathways': config['highlightpathways'],
    'highlightregions': config['highlightregions'],

    'show_pathway_links': config['show_pathway_links'],
})
graph.write(filename[1], format=config['output_format'], prog='neato')

from IPython.core.display import SVG
with open(filename[1], 'rU') as f:
    svg = f.read()
View = SVG(svg)
View
