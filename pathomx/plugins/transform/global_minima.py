import numpy as np

minima = input_data[input_data > 0].min().min() / 2  # 
# Get the dso filtered by class
input_data[input_data <= 0] = minima

output_data = input_data

# Generate simple result figure (using pathomx libs)
from pathomx.figures import spectra

View = spectra(output_data)

