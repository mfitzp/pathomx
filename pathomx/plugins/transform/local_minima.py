import numpy as np

data = input_data.values

dmin = np.ma.masked_less_equal(data, 0).min(0) / 2
inds = np.where(np.logical_and(data == 0, np.logical_not(np.ma.getmask(dmin))))
data[inds] = np.take(dmin, inds[1])

output_data = input_data
output_data[:] = data

data = None;

# Generate simple result figure (using pathomx libs)
from pathomx.figures import spectra

View = spectra(output_data);

output_data