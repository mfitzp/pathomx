import re
import pandas as pd
from collections import defaultdict

classes = [i[input_data.index.names.index('Class')] for i in input_data.index.values]
samples = [i[input_data.index.names.index('Sample')] for i in input_data.index.values]

slice_n = []
search = config.get('match')
i = input_data.index.names.index(config.get('target'))
new_index = []

for n in range(input_data.shape[0]):  # Down first axis
    print(i, n)

    c = str(input_data.index.values[n][i])
    match = re.search(search, c)
    if match:
        slice_n.append(n)
        new_index.append(
            (input_data.index.values[n])
        )

output_data = input_data.iloc[slice_n]

index_lists = defaultdict(list)
for n in range(len(new_index[0])):
    for i in new_index:
        index_lists[n].append(i[n])

# Rebuild index
index = pd.MultiIndex.from_arrays(index_lists.values(), names=input_data.index.names)
output_data = output_data.set_index(index)

# Generate simple result figure (using pathomx libs)
from pathomx.figures import spectra

View = spectra(output_data, styles=styles)
