import pandas as pd
import numpy as np
import nmrglue as ng

import os
import csv
from collections import defaultdict

# Get the target region from the spectra (will be using this for all calculations;
# then applying the result to the original data)
if type(input_data.columns) == pd.MultiIndex:
    scale = input_data.columns.labels[b.columns.names.index('Scale')]
else:
    scale = input_data.columns.values

algorithm = config.get('algorithm')

# Medium algorithm vars
med_mw = config.get('med_mw')
med_sf = config.get('med_sf')
med_sigma = config.get('med_sigma')

# Cbf pc algorithm vars
cbf_last_pc = config.get('cbf_last_pc')

# Cbf explicit algorithm vars
cbf_explicit_start = config.get('cbf_explicit_start')
cbf_explicit_end = config.get('cbf_explicit_start')

for n, dr in enumerate(input_data.values):

    if algorithm == 'median':
        dr = ng.process.proc_bl.med(dr, mw=med_mw, sf=med_sf, sigma=med_sigma)

    elif algorithm == 'cbf_pc':
        dr = ng.process.proc_bl.cbf(dr, last=cbf_last_pc)

    elif algorithm == 'cbf_explicit':
        dr = ng.process.proc_bl.cbf_explicit(dr, calc=slice(cbf_explicit_start, cbf_explicit_end))

    input_data.values[n, :] = dr

output_data = input_data

# Generate simple result figure (using pathomx libs)
from pathomx.figures import spectra

View = spectra(output_data, styles=styles)
