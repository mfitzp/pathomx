import pandas as pd
import numpy as np

import os
import csv
from collections import defaultdict

from biocyc import biocyc
biocyc.set_organism('HUMAN')
biocyc.secondary_cache_paths.append(os.path.join(_pathomx_database_path, 'biocyc'))


def preprocess_soft(reader, f=None):
    # Preprocess into the chunks (then can manageable process them in turn)
    soft_data = defaultdict(list)
    for n, row in enumerate(reader):
        if row[0].startswith('^'):  # Control row
            section = row[0]
            continue
        soft_data[section].append(row)

    return soft_data


def get_soft_metadata(rows, while_starts_with='!'):

    metadata = {}

    for row in rows:
        if not row[0].startswith('!'):
            break

        key, value = row[0][1:].split(' = ')  # Remove the ! and then split, removing the ' = '
        metadata[key] = value

    return metadata


def get_float(x):
    try:
        x = float(x)
    except:
        if x == 'null':
            x = None
    return x


def get_soft_data(rows, starts, ends):
    headers = False
    data = {}
    headers_at = False
    for n, row in enumerate(rows):
        if row[0] == starts:
            headers_at = n + 1
            start_at = n + 2
            break

    if not headers_at:
        return False

    headers = rows[headers_at]

    for row in rows[start_at:]:
        if row[0] == ends:
            break

        # Rewrite to account for null values; skip header (left column)
        row_data = row
        #row_data[1:] = [get_float(x) for x in row[1:]]
        data[row[0]] = dict(list(zip(headers, row_data)))

    return data


# SOFT files are a /sort of/ bastardized csv with data in tab-separated columns
# So, we use the csv reader to get that, accounting for most stuff being single field with
# slightly strange identifiers
with open(config['filename'], 'rU') as f:
    reader = csv.reader(f, delimiter='\t', dialect='excel')

    soft_data = preprocess_soft(reader, f=f)
    # soft_data now contains lists of sections with ^ markers

    database = {}
    dataset = {}
    dataset_data = {}
    subsets = {}

    for section, rows in list(soft_data.items()):

        if section.startswith('^DATABASE'):
            database = get_soft_metadata(rows)

        elif section.startswith('^DATASET'):
            dataset.update(get_soft_metadata(rows))  # update because seems can be >1 entry to dataset
            data = get_soft_data(rows, '!dataset_table_begin', '!dataset_table_end')
            dataset_data = data

        elif section.startswith('^SUBSET'):
            key, subset_id = section.split(' = ')
            subsets[subset_id] = get_soft_metadata(rows)
            subsets[subset_id]['subset_sample_id'] = subsets[subset_id]['subset_sample_id'].split(',')  # Turn to list of ids

    # We now have the entire dataset loaded; but in a bit of a messed up format
    # Build a dataset object to fit and map the data in
    sample_ids = []
    for k, subset in list(subsets.items()):
        sample_ids.extend(subset['subset_sample_id'])
    sample_ids = sorted(list(set(sample_ids)))   # Get the samples sorted so we keep everything lined up

    class_lookup = {}
    for class_id, s in list(subsets.items()):
        for s_id in s['subset_sample_id']:
            class_lookup[s_id] = "%s (%s)" % (s['subset_description'] if 'subset_description' in s else '', class_id)

    xdim = len(dataset_data)  # Use first sample to access the gene list
    ydim = len(sample_ids)

data = np.zeros((ydim, xdim))
gene_ids = sorted(dataset_data.keys())  # Get the keys sorted so we keep everything lined up

for xn, gene_id in enumerate(gene_ids):
    for yn, sample_id in enumerate(sample_ids):

        try:
            data[yn, xn] = float(dataset_data[gene_id][sample_id])
        except:
            data[yn, xn] = np.nan
# = Entrez Gene identifier
#UniGene title = Entrez UniGene name
#UniGene symbol = Entrez UniGene symbol
#UniGene ID = Entrez UniGene identifier
#Nucleotide Title = Entrez Nucleotide title
#GI = GenBank identifier

output_data = pd.DataFrame(data)
output_data.index = pd.MultiIndex.from_tuples(zip(sample_ids, [class_lookup[s_id] for s_id in sample_ids]), names=['Sample', 'Class'])
# build column index from possible sets
index_tuples = []
passthru = lambda x: x
headers = [
    ('IDENTIFIER', passthru, 'Label'),
    ('Gene ID', passthru, 'Entrez Gene'),
    ('UniGene ID', passthru, 'UNIGENE'),
    ('IDENTIFIER', lambda x: biocyc.find_gene_by_name(x), 'BioCyc')  # Auto-map to BioCyc
]
for n, gene_id in enumerate(gene_ids):

    t = tuple([n, ] + [fn(dataset_data[gene_id][cl]) for cl, fn, ci in headers if cl in dataset_data[gene_id]])
    index_tuples.append(t)

index_names = ['Measurement'] + [ci for cl, fn, ci in headers if cl in dataset_data[gene_id]]
output_data.columns = pd.MultiIndex.from_tuples(index_tuples, names=index_names)
#output_data.columns = [dataset_data[gene_id]['IDENTIFIER'] for gene_id in gene_ids]
output_data

# Generate simple result figure (using pathomx libs)
from pathomx.figures import spectra

View = spectra(output_data, styles=styles)
