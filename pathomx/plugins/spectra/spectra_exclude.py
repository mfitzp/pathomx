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
ymin, ymax = np.min(input_data.values.flatten()), np.max(input_data.values.flatten())


regions = []
index_mask = np.array( range(output_data.shape[1]) )

for region in config['selected_data_regions']:
    _, start_ppm, y0, end_ppm, y1 = region

    if start_ppm < min_ppm:
        start_ppm = min_ppm

    if end_ppm > max_ppm:
        end_ppm = max_ppm
        
    if start_ppm < end_ppm:
        start_ppm, end_ppm = end_ppm, start_ppm

    # Convert ppm to nearest index
    start_idx = scale.index(min(scale, key=lambda x: abs(x - start_ppm)))
    end_idx = scale.index(min(scale, key=lambda x: abs(x - end_ppm)))

    if start_idx > end_idx:
        start_idx, end_idx = end_idx, start_idx
        
    index_mask = index_mask[ ~np.logical_and(index_mask >start_idx, index_mask < end_idx) ] 
    regions.append( (start_ppm, ymax, end_ppm, ymin) )


output_data = output_data.iloc[:, index_mask]


# Generate simple result figure (using pathomx libs)
from pathomx.figures import spectra

View = spectra(output_data, styles=styles, regions=regions)