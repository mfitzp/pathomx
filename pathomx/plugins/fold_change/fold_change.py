import pandas as pd
import numpy as np

_experiment_test = config['experiment_test']
_experiment_control = config['experiment_control']

# We need classes to do the classification; should check and raise an error
class_idx = input_data.index.names.index('Class')
classes = [v[class_idx] for v in input_data.index.values]


# Replace zero values with minima (if setting)
if config['use_baseline_minima']:
    # Add option for column or global minima here
    data_minima = input_data[input_data > 0].min().min() / 2
    input_data[input_data <= 0] = data_minima

control_data = input_data.xs(_experiment_control, level=class_idx)

# Get the dso filtered by class if we're not doing a global match
if _experiment_test != "*":
    test_data = input_data.xs(_experiment_test, level=class_idx)
    test_classes = [_experiment_test]
else:
    excl = [c for c in classes if c != _experiment_control]
    test_data = input_data.loc[(slice(None), excl), :]
    test_classes = [c for c in classes if c != _experiment_control]

input_data

control_data

test_data

dlist = []
c = control_data.values
t = test_data.values
print c.shape, t.shape

c = np.nanmean(c, axis=0)
t = np.nanmean(t, axis=0)
print c.shape, t.shape

o = t.copy()
o[t > c] = np.array(t / c)[t > c]
o[t < c] = -np.array(t / c)[t < c]
o[t == c] = 0

o = np.reshape(o, (-1, t.shape[0]))

output_data = pd.DataFrame(o)
output_data.columns = input_data.columns

output_data

test_data = None

control_data = None
