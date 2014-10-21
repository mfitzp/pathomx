from icoshift import icoshift
import pandas as pd

spectra = input_data.values

if config['intervals'] == 'whole':
    intervals = 'whole'
    
elif config['intervals'] == 'number_of_intervals':
    intervals = config['number_of_intervals']
    
elif config['intervals'] == 'length_of_intervals':
    intervals = config['length_of_intervals']
    
if config['maximum_shift'] == 'n':
    maximum_shift = config['maximum_shift_n']
else:
    maximum_shift = config['maximum_shift']


xCS, ints, ind, target = icoshift(config['target'], spectra, 
                                  inter=intervals, 
                                  n=maximum_shift, 
                                  coshift_preprocessing=config['coshift_preprocessing'],
                                  coshift_preprocessing_max_shift=config['coshift_preprocessing_max_shift'],
                                  average2_multiplier=config['average2_multiplier'],
                                  fill_with_previous=config['fill_with_previous'],
                                                               )

output_data = input_data
output_data[:] = xCS

# Generate simple result figure (using pathomx libs)
from pathomx.figures import spectra

View = spectra(output_data, styles=styles)