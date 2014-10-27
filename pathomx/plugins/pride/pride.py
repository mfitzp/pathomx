import pandas as pd
import numpy as np

import os
import csv
import tempfile
import zipfile
from collections import defaultdict

# Unzip into temporary folder
folder = tempfile.mkdtemp()
zf = zipfile.ZipFile(config['filename'])
zf.extract('peptides.txt', folder)

datafile = os.path.join(folder, 'peptides.txt')

# Read in data for the graphing metabolite, with associated value (generate mean)
with open(datafile, 'r') as f:
    reader = csv.reader(f, delimiter='\t', dialect='excel')

    # Get top row
    row = reader.next()

    # Get columns for protein identities; leading is the top-ranked use preferentially
    # else use the proteins col (should use all identities?)
    proteins_col = row.index('Proteins') if 'Proteins' in row else None
    lead_protein_col = row.index('Leading razor protein') if 'Leading razor protein' in row else None

    # Row labels for quants is give as Intensity followed by the class name
    # so find all cols with Intensity\s<something> headers and extract the labels + data
    labels = []
    labelsc = []

    for n, c in enumerate(row):
        if 'Intensity ' in c:
            # Quantification column
            labelsn = c.replace('Intensity ', '')
            labels.append(labelsn)
            labelsc.append(n)

    raw_data = []
    entities = []

    # Now get data
    for n, row in enumerate(reader):

        datar = [float(row[x]) for x in labelsc]
        raw_data.append(datar)

        entity = None

        # Identify protein
        if lead_protein_col:
            entity = row[lead_protein_col]

        if entity is None and proteins_col:
            entity = row[proteins_col].split(';')[0]

        entities.append(entity)

output_data = pd.DataFrame(np.array(raw_data).T)
output_data.index = pd.MultiIndex.from_tuples(zip(labels), names=["Sample"])
output_data.columns = pd.MultiIndex.from_tuples(zip(range(n + 1), entities), names=["Measurement", "UniProt"])

output_data

# Generate simple result figure (using pathomx libs)
from pathomx.figures import spectra

View = spectra(output_data, styles=styles)
