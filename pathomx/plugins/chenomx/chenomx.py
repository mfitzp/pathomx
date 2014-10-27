import pandas as pd
import numpy as np

import os
import csv

slabels = []
data = []

# First read the header and get the labels and entities
with open(config['filename'], 'rU') as f:
    reader = csv.reader(f, delimiter=',', dialect='excel')

    hrow = next(reader)  # Get top row
    if hrow[0] != 'Profiled Data Type':  # Is a Chenomx output file; use the other columns to map data scale/etc. once implemented
        assert False, 'Not valid input file: Wrong file type.'

    header_rows = {
        'pH': 'Label',
        'InChI': 'InChI',
        'HMDB Accession Number': 'HMDB',
        'KEGG Compound ID': 'KEGG',
        'PubChem Compound': 'PUBCHEM',
        'ChEBI ID': 'CHEBI',
                 }

    indexes = dict()

    found_data = False
    for n, row in enumerate(reader):
        if row[0] in header_rows.keys():
            indexes[header_rows[row[0]]] = row[1:]

        elif '.cnx' in row[0]:
            found_data = True
            break

if not found_data:
    assert False, 'Not valid input file: No data.'

with open(config['filename'], 'rU') as f:

# n has the row number for start of data
    output_data = pd.read_csv(f, skiprows=n + 1, index_col=[0])

indexl = indexes.keys()
indext = []

for n, _ in enumerate(indexes[indexl[0]]):
    indext.append(tuple([indexes[l][n] for l in indexl]))

col_index = pd.MultiIndex.from_tuples(indext, names=indexl)
output_data.columns = col_index

output_data

# Generate simple result figure (using pathomx libs)
from pathomx.figures import spectra

View = spectra(output_data, styles=styles)
