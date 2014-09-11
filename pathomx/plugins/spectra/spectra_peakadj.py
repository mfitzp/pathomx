import nmrglue as ng
import numpy as np
import pandas as pd

# Get the target region from the spectra (will be using this for all calculations;
# then applying the result to the original data)

if type(input_data.columns) in [pd.Index, pd.Float64Index]:
    scale = input_data.columns.values
elif type(input_data.columns) == pd.MultiIndex:
    try:
        scidx = input_data.columns.names.index('ppm')
    except:
        scidx = input_data.columns.names.index('Label')
        
    scale = [c[scidx] for c in input_data.columns.values]
    
target_ppm = config.get('peak_target_ppm')
tolerance_ppm = config.get('peak_target_ppm_tolerance')
start_ppm = target_ppm - tolerance_ppm
end_ppm = target_ppm + tolerance_ppm

start = min(list(range(len(scale))), key=lambda i: abs(scale[i]-start_ppm))        
end = min(list(range(len(scale))), key=lambda i: abs(scale[i]-end_ppm))        

# Shift first; then scale
d = 1 if end>start else -1
data = input_data.iloc[:,start:end:d]
region_scales = scale[start:end:d]
#region_labels = labels[start:end:d]
#region_entities = dsientities[1][start:end:d]

pcentre = min(list(range(len(region_scales))), key=lambda i: abs(region_scales[i]-target_ppm))  # Base centre point to shift all spectra to


reference_peaks = []
for index, sdata in data.iterrows():
    baseline = sdata.max() * .9 # 90% baseline of maximum peak within target region
    locations, scales, amps = ng.analysis.peakpick.pick(sdata, pthres=baseline, algorithm='connected', est_params = True, cluster=False, table=False)
    if len(locations) > 0:
        reference_peaks.append({
            'location':locations[0][0], #FIXME: better behaviour when >1 peak
            'scale':scales[0][0],
            'amplitude':amps[0],
        })
    else:
        reference_peaks.append(None)


if config.get('shifting_enabled'):
    # Take a np array for speed on shifting
    shift_array = input_data.values
    # Now shift the original spectra to fi
    for n,refp in enumerate(reference_peaks):
        if refp:
            # Shift the spectra
            shift = (pcentre-refp['location']) * d
            # FIXME: This is painfully slow
            if shift > 0:
                shift_array[n, shift:-1] = shift_array[n, 0:-(shift+1)]
            elif shift < 0:
                shift_array[n, 0:shift-1] = shift_array[n, abs(shift):-1]

    input_data = pd.DataFrame( shift_array, index=input_data.index, columns=input_data.columns)


if config.get('scaling_enabled'):
    # Get mean reference peak size
    reference_peak_mean = np.mean( [r['scale'] for r in reference_peaks if r ] )
    print('Reference peak mean %s' % reference_peak_mean)

    # Now scale; using the same peak regions & information (so we don't have to worry about something
    # being shifted out of the target region in the first step)
    for n,refp in enumerate(reference_peaks):
        if refp:
            # Scale the spectra
            amplitude = reference_peak_mean/refp['amplitude']
            input_data.iloc[n] *= amplitude
            

# -- optionally use the line widths and take max within each of these for each spectra (peak shiftiness)
# Filter the original data with those locations and output\

output_data = input_data

region = output_data.iloc[:,start:end:d]

# Generate simple result figure (using pathomx libs)
from pathomx.figures import spectra

View = spectra(output_data, styles=styles);
Region = spectra(region, styles=styles);

data = None;
