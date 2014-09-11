output_data = input_data
output_data.dropna()

# Generate simple result figure (using pathomx libs)
from pathomx.figures import spectra

View = spectra(output_data);

