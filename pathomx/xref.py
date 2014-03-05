from __future__ import unicode_literals

import csv
import os
from collections import defaultdict

# Generate identity files from the chem_xref.tsv file
# Extract all the identity information, then output as a series of identity files matching to the metacyc database
taxonomy = defaultdict(dict)

metacyc = dict()
reader = csv.reader(open('chem_xref.tsv', 'rU'), delimiter='\t', dialect='excel')

active = False
for row in reader:

    if active:
        # #XREF    MNX_ID    Evidence    Description
        id, mnxid, evidence, description = row

        tax, id = id.split(':', 1)  # Separate the taxonomy and id
        if tax == 'metacyc':
            metacyc[id] = mnxid
        else:
            if mnxid in taxonomy[tax]:
                taxonomy[tax][mnxid].append(id)
            else:
                taxonomy[tax][mnxid] = [id]

    if row[0] == '#XREF':  # Wait til we're past the comments
        active = True

for tid, tax in list(taxonomy.items()):
    print(tid, len(tax))
    with open(tid, 'wb') as csvfile:
        writer = csv.writer(csvfile, dialect='excel')

        for metacycid, mnxid in list(metacyc.items()):
            if mnxid in tax:
                for id in tax[mnxid]:
                    writer.writerow([metacycid, id])

        csvfile.close()
