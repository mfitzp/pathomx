import numpy as np

center = np.mean(input_data, axis=0)
output_data = input_data - center

# Generate simple result figure (using pathomx libs)
from pathomx.figures import spectra

View = spectra(output_data, styles=styles)
