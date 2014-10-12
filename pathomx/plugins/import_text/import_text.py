import pandas as pd
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
        sep=config['seperator'],
        quotechar=config['quotechar'],
        escapechar=config['escapechar'],
        quoting=config['quoting'],
        skipinitialspace=config['skipinitialspace'])

with open(config['filename'], 'rU') as f:
    csvr = csv.reader(f, dialect=dialect, **format_dict)
    r = next(csvr)
if 'Class' in r[1]:
    # We're samples down
    output_data = pd.read_csv(config['filename'], index_col=[0, 1], dialect=dialect, **format_dict)
else:
    # We're samples across
    output_data = pd.read_csv(config['filename'], header=[0, 1], index_col=[0], dialect=dialect, **format_dict)
    output_data = output_data.T

output_data.index.names = ['Sample', 'Class']

l = output_data.columns.values
output_data.columns = pd.MultiIndex.from_tuples(zip(range(len(l)), l), names=['Measurement', 'Label'])

output_data

# Generate simple result figure (using pathomx libs)
from pathomx.figures import spectra, heatmap

Spectra = spectra(output_data, styles=styles)

Heatmap = heatmap(output_data)


Spectra

Heatmap
