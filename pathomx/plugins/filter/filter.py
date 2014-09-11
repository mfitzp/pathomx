import pandas as pd
import re
from collections import OrderedDict

classes = [i[ input_data.index.names.index('Class') ] for i in input_data.index.values ]
samples = [i[ input_data.index.names.index('Sample') ] for i in input_data.index.values ]

classes_f = []
search = config.get('match')

if config.get('target') == 'Class' or config.get('target') == 'None':

    for c in classes:
        match = re.search(search, c)
        if match:
            classes_f.append(replace)
        else:
            classes_f.append(c)

elif config.get('target') == 'Sample':
    
    for n, s in enumerate(samples):
        match = re.search(search, str(s) )
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
output_data.index = pd.MultiIndex.from_tuples( new_index_tuples, names=indexes.keys() )

output_data

# Generate simple result figure (using pathomx libs)
from pathomx.figures import spectra

View = spectra(output_data, styles=styles);