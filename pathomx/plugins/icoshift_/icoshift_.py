from icoshift import icoshift
import pandas as pd

spectra = input_data.values

xCS, ints, ind, target = icoshift(config.get('target'), spectra, inter=config.get('alignment_mode'), n=config.get('maximum_shift'))

output_data = input_data
output_data[:] = spectra

# Generate simple result figure (using pathomx libs)
from pathomx.figures import spectra

View = spectra(output_data, styles=styles)

