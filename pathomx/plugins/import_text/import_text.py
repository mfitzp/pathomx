import pandas as pd
import numpy as np
import csv

if config['autodetect_format']:
    try:
        f = open(config['filename'], 'rb')
        dialect = csv.Sniffer().sniff(f.read(1024))
        f.close()
    except:
        pass
    else:
        format_dict = dict()
else:
    dialect = None
    format_dict = dict(
        sep=config['delimiter'],
        quotechar=config['quotechar'],
        escapechar=config['escapechar'],
        quoting=config['quoting'],
        skipinitialspace=config['skipinitialspace'])

if config['column_headers'] == 1:
    column_headers = 0
elif config['column_headers'] > 1:
    column_headers = range(config['column_headers'])
else:
    column_headers = None

if config['row_headers'] == 0:
    row_headers = None
else:
    row_headers = range(config['row_headers'])


with open(config['filename'], 'rU') as f:

    if config['transpose']:

        # We're samples across
        output_data = pd.read_csv(f,
                                  header=row_headers,
                                  index_col=column_headers,
                                  dialect=dialect,
                                  **format_dict)
        output_data = output_data.T
    else:
        output_data = pd.read_csv(f,
                                  header=column_headers,
                                  index_col=row_headers,
                                  dialect=dialect,
                                  **format_dict)

# Check if we've got a singluar index (not multiindex) and convert
if not isinstance(output_data.index, pd.MultiIndex):
    output_data.index = pd.MultiIndex.from_tuples(
        zip(output_data.index.values, range(1, len(output_data.index.values) + 1)),
        names=['Sample'])


if not isinstance(output_data.columns, pd.MultiIndex):
    output_data.columns = pd.MultiIndex.from_tuples(
        zip(output_data.columns.values, range(1, len(output_data.columns.values) + 1)),
        names=['Label', 'Measurement'])


# Fill in header defaults where items are missing
if any([c is None for c in output_data.index.names]):
    labels = config['row_header_defaults'].split(',')
    output_data.index.names = [l if l is not None else labels[n] for n, l in enumerate(output_data.index.names)]

if any([c is None for c in output_data.columns.names]):
    labels = config['column_header_defaults'].split(',')
    output_data.columns.names = [l if l is not None else labels[n] for n, l in enumerate(output_data.columns.names)]

# If we get here and don't have a sample Class entry on the index, create it
if 'Class' not in output_data.index.names:
    output_data['Class'] = [''] * output_data.shape[0]
    output_data.set_index(['Class'], append=True, inplace=True)

# Generate simple result figure (using pathomx libs)
from pathomx.figures import spectra, heatmap

Spectra = spectra(output_data, styles=styles)
Heatmap = heatmap(output_data)
