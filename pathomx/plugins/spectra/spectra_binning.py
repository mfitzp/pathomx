import numpy as np
import pandas as pd

if input_data is None:
    raise Exception('No input data')

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

bin_size, bin_offset = config.get('bin_size'), config.get('bin_offset')

r = min(scale), max(scale)

bins = np.arange(r[0] + bin_offset, r[1] + bin_offset, bin_size)
number_of_bins = len(bins) - 1

# Can't increase the size of data, if bins > current size return the original
if number_of_bins >= len(scale):
    output_data = input_data

else:

    output_data = pd.DataFrame(np.zeros((input_data.shape[0], number_of_bins)))

    for n, d in enumerate(input_data.values):
        binned_data = np.histogram(scale, bins=bins, weights=d)
        binned_num = np.histogram(scale, bins=bins)  # Number of data points that ended up contributing to each bin
        output_data.ix[n, :] = binned_data[0] / binned_num[0]  # Mean

    new_scale = [float(x) for x in binned_data[1][:-1]]

    # Binning is low->high only, if the resulting scale is reversed to the source data flip it and the data
    original_dir = (scale[0] - scale[1]) / abs((scale[0] - scale[1]))
    new_dir = (new_scale[0] - new_scale[1]) / abs((new_scale[0] - new_scale[1]))

    if original_dir != new_dir:  # Flip horizontal

        new_scale = new_scale[::-1]
        for n, d in enumerate(output_data.values):
            output_data.ix[n, :] = np.fliplr(np.reshape(d, (-1, number_of_bins)))

    output_data.columns = pd.Index(new_scale, name='Scales')
    output_data.index = input_data.index

output_data.dropna(axis=1, inplace=True)

# Generate simple result figure (using pathomx libs)
from pathomx.figures import spectra, difference

View = spectra(output_data, styles=styles)

Difference = difference(input_data, output_data, styles=styles)
