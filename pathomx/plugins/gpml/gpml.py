import pandas as pd
import numpy as np

import os

import matplotlib as mpl
import matplotlib.cm as cm
from matplotlib.colors import rgb2hex

from pathomx.utils import luminahex

from biocyc import biocyc
biocyc.secondary_cache_paths.append(os.path.join(_pathomx_database_path, 'biocyc'))

xref_urls = {
    'BioCyc compound': 'pathomx://db/compound/%s/view',
    'BioCyc gene': 'pathomx://db/gene/%s/view',
    'BioCyc protein': 'pathomx://db/protein/%s/view',
    'WikiPathways': 'pathomx://wikipathway/%s/import',
}

#self.dblinks[ e.find('dblink-db').text ] = e.find('dblink-oid').text

def build_xref_list(data):
    # Supplied with a MultiIndex will build a reference table for all
    # to the BioCyc object type
    xref_translate = {
        'KEGG': ['Kegg Compound', 'Kegg Gene'],
        'NCBI-GENE': ['Entrez Gene'],
        'HMDB': ['HMDB'],

        }

    xrefs = {}

    # Use BioCyc first (dblinks)
    if 'BioCyc' in data.columns.names:
        biocyc_idx = data.columns.names.index('BioCyc')
        for n, c in enumerate(data.columns.values):
            o = c[biocyc_idx]
            if hasattr(o, 'dblinks'):
                for db, dbid in o.dblinks.items():
                    if db in xref_translate:
                        dbl = xref_translate[db]
                    else:
                        dbl = [db]

                    for dbi in dbl:
                        xrefs[(dbi, dbid)] = ('PATHOMX%d' % id(data), n)

    # Use other columns
    for namen, name in enumerate(data.columns.names):
        if name in xref_translate:
            thisrow = [e[namen] for e in data.columns.values]

            # Map to name to that used by GPML
            names = xref_translate[name]

            for sn in names:
                for n, c in enumerate(thisrow):
                    if c is not None:
                        xrefs[(sn, c)] = ('PATHOMX%d' % id(data), n)

    return xrefs

node_colors = {}
xref_syns = {}

if compound_data is not None or gene_data is not None or protein_data is not None:

    datasets = []
    for data in compound_data, gene_data, protein_data:
        if data is None:
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

    print("Range %.2f..%.2f" % (overall_min, overall_max))
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
        # We can only use a single row at the moment, so process through fold change etc. first
        values = data.iloc[0]
        for n, v in enumerate(values):
            color = rgb2hex(mapper.to_rgba(v))
            if luminahex(color) < 0.5:
                contrast = "#FFFFFF"
            else:
                contrast = "#000000"

            node_colors[('PATHOMX%d' % id(data), n)] = (color, contrast)

        xref_syns = dict(xref_syns.items() + build_xref_list(data).items())

else:
    node_colors = None
    #for n, m in enumerate(dso.entities[1]):
    #    xref = self.get_xref(m)
    #    ecol = utils.calculate_rdbu9_color(scale, dso.data[0, n])
    #    #print xref, ecol
    #    if xref is not None and ecol is not None:
    #        node_colors[xref] = ecol

from gpml2svg import gpml2svg
from IPython.core.display import SVG
import requests

# Add our urls to the defaults
xref_urls = {
    'MetaCyc compound': 'pathomx://db/compound/%s/view',
    'MetaCyc gene': 'pathomx://db/gene/%s/view',
    'MetaCyc protein': 'pathomx://db/protein/%s/view',
    'WikiPathways': 'pathomx://wikipathway/%s/import',
}

gpml = None
if config['gpml_file']:
    print("Loaded GPML from WikiPathways")
    with open(config['gpml_file'], 'rU') as f:
        gpml = f.read()

elif config['gpml_wikipathways_id']:
    r = requests.get('http://www.wikipathways.org//wpi/wpi.php', params={
                        'action': 'downloadFile',
                        'type': 'gpml',
                        'pwTitle': 'Pathway:%s' % config['gpml_wikipathways_id'],
                        'revision': 0,
                    })
    if r.status_code == 200:
        print("Loaded GPML from WikiPathways")
        gpml = r.text
    else:
        raise Exception("Error loading GPML from WikiPathways (%d)" % r.status_code)
else:
    raise Exception("Select a source for GPML")

if gpml:

# xref_synonyms_fn=get_extended_xref_via_unification_list,
    svg, metadata = gpml2svg.gpml2svg(gpml, xref_urls=xref_urls, xref_synonyms=xref_syns, node_colors=node_colors)

    View = SVG(svg)

    View
