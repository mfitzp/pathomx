import pandas as pd
import numpy as np

import tempfile
import zipfile
import os
import csv

# Unzip into temporary folder
folder = tempfile.mkdtemp()  # os.path.join( QDir.tempPath(),
zf = zipfile.ZipFile(config['filename'])
zf.extractall(folder)
f = os.listdir(folder)
bml_job = f[0]

fns = [
    ('samples_vs_concs_matrix.txt', 'raw'),
    ('samples_vs_concs_matrix_tsanorm.txt', 'tsa'),
    ('samples_vs_concs_matrix_pqnnorm.txt', 'pqn'),
]

# We have the data folder; import each of the complete datasets in turn
# non, PQN, TSA and label appropriately
datasets = {}

for fn, target in fns:
    # Load the data file
    data_path = os.path.join(folder, bml_job, 'overall_result_outputs', fn)

    with open(data_path, 'rb') as f:
        # Find initial line
        cr = csv.reader(f, delimiter='\t')
        for row in cr:
            if len(row) > 0 and row[0] == 'metabolite':
                sample_nos = row[1:-2]
                break
        else:
            continue  # Escape to next file

        num_of_samples = len(sample_nos)

        # Pass the open f to read_csv to get the rest
        # I hate MATLAB strings
        dataset = pd.read_csv(f, header=None, index_col=[0], sep=r'\x00*\t+', converters={n + 1: np.float64 for n in range(num_of_samples)})
        #dataset.convert_objects(convert_numeric=True)
        # Bottom two columns are the metabolite id info, chop off
        dataset = dataset.T
        dataset = dataset[:-2]
        dataset = dataset.astype(float)

        # We've only got sample items, need to add a class column
        sample_nos = [f.replace('(expno_', '').strip(')') for f in sample_nos]
        dataset.index = pd.MultiIndex.from_tuples(zip(sample_nos, [''] * len(sample_nos)), names=['Sample', 'Class'])

        vars()[target] = dataset
        del dataset

# Generate simple result figure (using pathomx libs)
from pathomx.figures import spectra

Raw = spectra(raw, styles=styles)

PQN = spectra(pqn, styles=styles)

TSA = spectra(tsa, styles=styles)
