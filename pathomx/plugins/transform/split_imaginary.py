real = input_data
imag = input_data
real.loc[:] = real.values.real
imag.loc[:] = imag.values.imag

# Generate simple result figure (using pathomx libs)
from pathomx.figures import spectra

Real = spectra(real);
Imag = spectra(imag);

