import pandas as pd
import re
from collections import OrderedDict

classes = [i[input_data.index.names.index('Class')] for i in input_data.index.values]
samples = [i[input_data.index.names.index('Sample')] for i in input_data.index.values]

for search, replace, match in config.get('filters'):
    classes_f = []

    if match == 'Class' or match == 'None':

        for c in classes:
            print search, c
            match = re.search(search, c)
            if match:
                classes_f.append(replace)
            else:
                classes_f.append(c)

    elif match == 'Sample':
        for n, s in enumerate(samples):
            match = re.search(search, str(s))
            if match:
                classes_f.append(replace)
            else:
                classes_f.append(classes[n])

    classes = classes_f
# Now have classes in a list; rebuild the MultiIndex using this replacement

output_data = input_data

indexes = OrderedDict()
for n, idx in enumerate(input_data.index.names):
    indexes[idx] = input_data.index.levels[n]

indexes['Class'] = classes

# Build some tuples
new_index_tuples = zip(*indexes.values())
output_data.index = pd.MultiIndex.from_tuples(new_index_tuples, names=indexes.keys())

output_data

# Generate simple result figure (using pathomx libs)
from pathomx.figures import spectra

View = spectra(output_data, styles=styles)

