import pandas as pd
import metabohunter as mh

# Generate a table of ppms (from index, Scale) and peaks (from mean of data table)
if type(input_data.columns) == pd.MultiIndex:
    if 'Scale' in input_data.columns.names:
        i = input_data.columns.names.index('Scale')
    else:
        i = input_data.columns.names.index('Label')
            
    ppms = input_data.columns.labels[i]
else:
    ppms = input_data.columns.values

peaks = input_data.mean().values

hmdbs = mh.request(ppms, peaks)

output_data = input_data

# Add to the existing column MultiIndex

def tupler(*args):
    return tuple(args)

if type(input_data.columns) == pd.MultiIndex:
    cur_index_vals = output_data.columns.values
    cur_index_names = list(output_data.columns.values)
    new_index = [tupler(hmdb_id,*cur_index_vals[n]) for n,hmdb_id in enumerate(hmdbs)]
else:
    new_index = zip(hmdbs,ppms)
    cur_index_names = ['Scale']
    
output_data.columns = pd.MultiIndex.from_tuples( new_index, names=['HMDB'] + cur_index_names )

output_data

# Generate simple result figure (using pathomx libs)
from pathomx.figures import spectra

View = spectra(output_data, styles=styles);
