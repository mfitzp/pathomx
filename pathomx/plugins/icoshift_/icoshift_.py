from icoshift import icoshift
import pandas as pd
import numpy as np

spc = input_data.values

if config['intervals'] == 'whole':
    intervals = 'whole'

elif config['intervals'] == 'number_of_intervals':
    intervals = config['number_of_intervals']

elif config['intervals'] == 'length_of_intervals':
    intervals = config['length_of_intervals']

elif config['intervals'] == 'selected_intervals':
    regions = config['selected_data_regions']
    if regions is None or regions == []:
        intervals = 'whole'
    else:
        intervals = []

        if type(input_data.columns) == pd.Index or type(input_data.columns) == pd.Float64Index:
            scale = input_data.columns.values
        elif type(input_data.columns) == pd.MultiIndex:
            for cn in ['ppm', 'Scale', 'Label']:
                if cn in input_data.columns.names:
                    scidx = input_data.columns.names.index(cn)
                    break
            else:
                raise Exception("Can't find a valid ppm index.")
            scale = [c[scidx] for c in input_data.columns.values]


        def find_index_of_nearest(l, v):
            return min(range(len(l)), key=lambda i: abs(l[i] - v))

        for r in regions:
            if r[0] == 'View':
                x0, y0, x1, y1 = r[1:]
                # Convert from data points to indexes
                intervals.append((find_index_of_nearest(scale, x0), find_index_of_nearest(scale, x1)))

if config['maximum_shift'] == 'n':
    maximum_shift = config['maximum_shift_n']
else:
    maximum_shift = config['maximum_shift']


if config['target'] == 'input_target':
    target = input_target.values

elif config['target'] == 'spectra_number':
    target = spc[config['spectra_number'], :].reshape(1, -1)

else:
    target = config['target']

xCS, ints, ind, target = icoshift(target, spc,
                                  inter=intervals,
                                  n=maximum_shift,
                                  coshift_preprocessing=config['coshift_preprocessing'],
                                  coshift_preprocessing_max_shift=config['coshift_preprocessing_max_shift'],
                                  average2_multiplier=config['average2_multiplier'],
                                  fill_with_previous=config['fill_with_previous'],
                                                               )

output_data = input_data.copy()
output_data[:] = xCS

# Generate simple result figure (using pathomx libs)
from pathomx.figures import spectra, difference

regions = []
ymin, ymax = np.min(spc.flatten()), np.max(spc.flatten())
for r in config['selected_data_regions']:
    x0, y0, x1, y1 = r[1:]
    regions.append((x0, ymax, x1, ymin))

View = spectra(output_data, styles=styles, regions=regions)
Difference = difference(input_data, output_data)
spc = None
