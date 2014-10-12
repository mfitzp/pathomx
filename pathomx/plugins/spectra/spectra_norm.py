import numpy as np
import pandas as pd

# Abs the data (so account for negative peaks also)
data_a = np.abs(input_data.values)
# Sum each spectra (TSA)
data_as = np.sum(data_a, axis=1)
# Identify median
median_s = np.median(data_as)
# Scale others to match (*(median/row))
scaling = median_s / data_as
# Scale the spectra
tsa_data = input_data.T * scaling
tsa_data = tsa_data.T

if config['algorithm'] == 'TSA':
    output_data = tsa_data

elif config['algorithm'] == 'PQN':
    # Take result of TSA normalization
    # Calculate median spectrum (median of each variable)
    median_s = np.median(tsa_data, axis=0)
    # For each variable of each spectrum, calculate ratio between median spectrum variable and that of the considered spectrum
    spectra_r = median_s / np.abs(input_data)
    # Take the median of these scaling factors
    scaling = np.median(spectra_r, axis=1)
    #Apply to the entire considered spectrum
    output_data = input_data.T * scaling
    output_data = output_data.T
    
data = None
# Clear so not expored
data_a = None

data_as = None

media_as = None

scaling = None

spectra_r = None

tsa_data = None


# Generate simple result figure (using pathomx libs)
from pathomx.figures import spectra

View = spectra(output_data, styles=styles)

View
