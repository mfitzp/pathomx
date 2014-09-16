import numpy as np
import pandas as pd

if input_data is None:
    raise Exception('No input data')

if type(input_data.columns) == pd.Index or type(input_data.columns) == pd.Float64Index:
    scale = input_data.columns.values.tolist()
elif type(input_data.columns) == pd.MultiIndex:
    for cn in ['ppm', 'Scale', 'Label']:
        if cn in input_data.columns.names:
            scidx = input_data.columns.names.index(cn)
            break
    else:
        raise Exception("Can't find a valid ppm index.")
        
    scale = [c[scidx] for c in input_data.columns.values]

output_data = input_data
max_ppm = max(scale)
min_ppm = min(scale)

for n in range(4):
    i = n+1
    
    if config.get('exclude_%d' % i) == False:
        continue

    start_ppm = config.get('exclude_%d_start' % i)
    if start_ppm < min_ppm:
        start_ppm = min_ppm
        
    end_ppm = config.get('exclude_%d_end' % i)
    if end_ppm > max_ppm:
        end_ppm = max_ppm
    
    # Convert ppm to nearest index
    start_idx = scale.index( min(scale, key=lambda x:abs(x-start_ppm)) )
    end_idx = scale.index( min(scale, key=lambda x:abs(x-end_ppm)) )
    
    if start_idx > end_idx:
        start_idx, end_idx = end_idx, start_idx
    
    output_data = output_data.drop(output_data.columns[start_idx:end_idx], axis=1)
    
# Generate simple result figure (using pathomx libs)
from pathomx.figures import spectra

View = spectra(output_data, styles=styles);
