import pandas as pd

real = pd.DataFrame(input_data.values.real)
real.columns = input_data.columns
real.index = input_data.index

imag = pd.DataFrame(input_data.values.imag)
imag.columns = input_data.columns
imag.index = input_data.index

# Generate simple result figure (using pathomx libs)
from pathomx.figures import spectra

Real = spectra(real)

Imag = spectra(imag)
