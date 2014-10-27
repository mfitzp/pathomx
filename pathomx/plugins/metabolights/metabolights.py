import pandas as pd
import numpy as np

import os
import csv
from collections import defaultdict

id_col = 0
name_col = 4
data_col = 18

#sample    1    2    3    4
#class    ADG10003u_007    ADG10003u_008    ADG10003u_009    ADG10003u_010   ADG19007u_192
#2-oxoisovalerate    0.3841    0.44603    0.45971    0.40812
with open(config['filename'], 'rU') as f:
    reader = csv.reader(f, delimiter='\t', dialect='excel')

    # Sample identities from top row ( sample labels )
    hrow = next(reader)
    sample_ids = hrow[1:]

    # Sample classes from second row; crop off after u_
    classes = [c for c in hrow if 'u_' in c]

    data_starts_at = hrow.index(classes[0])
    metabolite_names_at = hrow.index('metabolite_identification')
    database_identifiers_at = hrow.index('database_identifier')
    # inchi, smiles, etc.
    # database_identifier as hmbdNNNN or chebi:NNNN

    classes = [c.split('u_')[0] for c in classes]

    metabolites = []
    metabolite_data = []
    hmdb_ids = []
    chebi_ids = []

    # Read in metabolite data n.b. can have >1 entry / metabolite so need to allow for this
    for row in reader:
        if row[0] != '':  # Skip empty rows
            metabolites.append(row[metabolite_names_at])
            metabolite_data.append([float(x) for x in row[data_starts_at:]])
            dbid = row[database_identifiers_at]
            dbid_hmdb, dbid_chebi = None, None

            if dbid.startswith('HMDB'):
                dbid_hmdb = dbid
            elif dbid.startswith('CHEBI:'):
                dbid_chebi = dbid.split(':')[1]

            hmdb_ids.append(dbid_hmdb)
            chebi_ids.append(dbid_chebi)

output_data = pd.DataFrame(metabolite_data)
output_data = output_data.T
output_data.index = pd.MultiIndex.from_tuples(zip(range(len(classes)), classes), names=['Sample', 'Class'])
output_data.columns = pd.MultiIndex.from_tuples(zip(range(len(metabolites)), metabolites, hmdb_ids, chebi_ids), names=['Measurement', 'Label', 'HMDB', 'CHEBI'])

output_data

# Generate simple result figure (using pathomx libs)
from pathomx.figures import spectra

View = spectra(output_data, styles=styles)
