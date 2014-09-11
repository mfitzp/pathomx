import nmrglue as ng
import pandas as pd
import numpy as np

# Generate bin values for range start_scale to end_scale
# Calculate the number of bins at binsize across range

algorithms = {
    'Connected':'connected',
    'Threshold':'thres',
    'Threshold (fast)':'thres-fast',
    'Downward':'downward',
        }

threshold =  config['peak_threshold']
algorithm = algorithms[ config['peak_algorithm'] ]
msep = ( config['peak_separation'],)


# Take input dataset and flatten in first dimension (average spectra)
data_avg = input_data.mean() #np.mean( input.data, axis=0)
# pick peaks and return locations; 
#nmrglue.analysis.peakpick.pick(data, pthres, nthres=None, msep=None, algorithm='connected', est_params=True, lineshapes=None, edge=None, diag=False, c_struc=None, c_ndil=0, cluster=True, table=True, axis_names=['A', 'Z', 'Y', 'X'])[source]¶
locations, scales, amps = ng.analysis.peakpick.pick(data_avg.values, threshold, msep=msep, algorithm=algorithm, est_params = True, cluster=False, table=False)



#n_cluster = max( cluster_ids )
n_locations = len( locations )

new_shape = list( input_data.shape )
new_shape[1] = n_locations # correct number; tho will be zero indexed

# Convert to numpy arrays so we can do clever things
scales = input_data.columns.values
scales = [scales[l[0]] for l in locations ]


output_data = pd.DataFrame( np.zeros(new_shape) )

# Iterate over the clusters (1 to n)
for n, l in enumerate(locations):
    #l = locations[ cluster_ids == n ]
    #peak_data = np.amax( peak_data, axis=1 ) # max across cols
    print n, l
    output_data.iloc[:,n] = input_data.values[:, l[0]]

output_data.index = input_data.index
output_data.columns = scales

# FIXME:
# Extract the location numbers (positions in original spectra)
# Get max value in each row for those regions
# Append that to n position in new dataset

# -- optionally use the line widths and take max within each of these for each spectra (peak shiftiness)
# Filter the original data with those locations and output\


output_data

# Generate simple result figure (using pathomx libs)
from pathomx.figures import spectra

View = spectra(output_data, styles=styles);