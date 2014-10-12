from pathminer import mining
import pandas as pd
import numpy as np
import os

from biocyc import biocyc

biocyc.set_organism('HUMAN')
biocyc.secondary_cache_paths.append(os.path.join(_pathomx_database_path, 'biocyc'))
# Flatten input data to single row

data = []
for input_data in input_1, input_2, input_3, input_4:
    if input_data is not None:
        datam = input_data.mean()
        # We need BioCyc identifiers
        if 'BioCyc' in input_data.columns.names:
            if type(input_data.columns) == pd.MultiIndex:
                entities = [k[input_data.columns.names.index('BioCyc')] for k in input_1.columns.values]
            else:
                entities = input_data.columns.values
            # Map to BioCyc if not already
            biocyc_entities = []
            for e in entities:
                if hasattr(e, 'id'):
                    biocyc_entities.append(e)
                elif type(e) is str:
                    try:
                        biocyc_entities[n] = biocyc.get(o)
                    except:
                        biocyc_entities[n] = None
                else:
                    biocyc_entities.append(None)

            datas = [(e, s) for e, s in zip(biocyc_entities, datam.values) if e is not None]
            data.extend(datas)

print "%d entities with data" % len(data)

results = mining(data, target=config['/Data/MiningTarget'],
                       include=config['include_pathways'],
                       exclude=config['exclude_pathways'],
                       no_of_results=config['/Data/MiningDepth'],
                       algorithm=config['/Data/MiningType'],
                       relative=config['/Data/MiningRelative'],
                       shared=config['/Data/MiningShared'],
                )

# Results in format [(pathway, score)] rebuild a new DataFrame of the data
results

pathways, data = zip(*results)

output_data = pd.DataFrame(np.array(data)).T
output_data.columns = pd.Index([p for p in pathways], name='BioCyc')
output_data
