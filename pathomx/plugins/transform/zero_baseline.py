import numpy as np


minima = np.min(input_data)
output_data = input_data + -minima

# Generate simple result figure (using pathomx libs)
from pathomx.figures import spectra

View = spectra(output_data);

