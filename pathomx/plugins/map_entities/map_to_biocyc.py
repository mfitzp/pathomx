from biocyc import biocyc
import pandas as pd
import os
import csv

biocyc.set_organism('HUMAN')

def map_generator(table):
    map_dict = {}
    with open( os.path.join(_pathomx_tool_path, table), 'rU') as f:
        reader = csv.reader(f)
        for row in reader:
            map_dict[ row[1] ] = row[0]
            
    return lambda x: map_dict[x] if x in map_dict else None

def reverse_map_generator(table):
    map_dict = {}
    with open( os.path.join(_pathomx_tool_path, table), 'rU') as f:
        reader = csv.reader(f)
        for row in reader:
            map_dict[ row[0] ] = row[1]
            
    return lambda x: map_dict[x] if x in map_dict else None

lku = {
    'Any': biocyc.find_by_name,
    'Gene': biocyc.find_gene_by_name,
    'Protein': biocyc.find_protein_by_name,
    'Compound': biocyc.find_compound_by_name,
    # ----
    'BiGG': map_generator('bigg'),
    'BioPath': map_generator('biopath'),
    'BRENDA': map_generator('brenda'),
    'FIMA': map_generator('fima'),
    'HMDB': map_generator('hmdb'),
    'KEGG': map_generator('kegg'),
    'LIPID MAPS': map_generator('lipidmaps'),
    'SEED': map_generator('seed'),
    'UPA': map_generator('upa'),
    }[config.get('map_object_type')]

# Get the index; plus the existing one if available
if type(input_data.columns) == pd.MultiIndex:
    for li in ['Label','HMDB']:
        if li in input_data.columns.names:
            lidx = input_data.columns.names.index('Label')
            break
    else:
        raise Exception('No source labels found')
        
    labels = [l[lidx] for l in input_data.columns.values ]

    if 'BioCyc' in input_data.columns.names:
        bidx = input_data.columns.names.index('BioCyc')
        current_biocyc = [ l[bidx] for l in input_data.columns.values ]
    else:
        current_biocyc = [None] * len(labels)
        
else:
    labels = input_data.columns.values
    current_biocyc = [None] * len(labels)

count = 0;
for n, l in enumerate(labels):
    if current_biocyc[n] is not None:
        continue
        
    o = lku(l)
    # Note that the BioCyc module returns an object, so we need to convert to ID if it is
    if hasattr(o, 'id'):
        current_biocyc[n] = o
        count += 1;
 
    elif type(o) is str:
        try:
            current_biocyc[n] = biocyc.get(o)
        except:
            current_biocyc[n] = None   
        else:
            count += 1;
            
    else:
        current_biocyc[n] = None

print("Matched %d identifiers" % count)

cross_maps = {}
if 1 == 0:
    for m,f in {'BiGG':'bigg','HMDB':'hmdb','KEGG':'kegg'}.items():
        lku = reverse_map_generator(f)
        cm = []
        for o in current_biocyc:
            if o:
                nid = lku(o.id)
                cm.append(nid)
            else:
                cm.append(None)

        cross_maps[m] = cm   
        print("Cross-mapped %s to %d identifiers" % (m, len(cm)))

output_data = input_data

index_dict = {k:[v[output_data.columns.names.index(k)] for v in output_data.columns.values] for k in output_data.columns.names if k is not None}
index_dict['Label'] = labels
index_dict['BioCyc'] = current_biocyc
for k,v in cross_maps.items():
    index_dict[k] = v

idx = pd.MultiIndex.from_tuples( zip(*index_dict.values()), names=index_dict.keys() )
output_data.columns = idx

output_data