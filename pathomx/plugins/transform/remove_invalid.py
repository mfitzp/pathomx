output_data = input_data
output_data.dropna(axis=1, inplace=True)

# Generate simple result figure (using pathomx libs)
from pathomx.figures import spectra

View = spectra(output_data)
