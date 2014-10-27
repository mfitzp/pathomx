import pandas as pd
import csv
import base64
from collections import defaultdict
import xml.etree.ElementTree as et


def decode(s):
    s = base64.decodestring(s)
    # Each number stored as a 4-chr representation (ascii value, not character)
    l = []
    for i in range(0, len(s), 4):
        c = s[i:i + 4]
        val = 0
        for n, v in enumerate(c):
            val += ord(v) * 10 ** (3 - n)
        l.append(str(val))
    return l

# Determine if we've got a csv or peakml file (extension)

# Read data in from peakml format file
xml = et.parse(config['filename'])

# Get sample ids, names and class groupings
sets = xml.iterfind('header/sets/set')
midclass = {}
classes = set()
measurements = []
masses = {}

for aset in sets:
    id = aset.find('id').text
    mids = aset.find('measurementids').text
    for mid in decode(mids):
        midclass[mid] = id
        measurements.append(mid)

    classes.add(id)

# We have all the sample data now, parse the intensity and identity info
peaksets = xml.iterfind('peaks/peak')
quantities = defaultdict(dict)
all_identities = []

for peakset in peaksets:

# Find metabolite identities
    annotations = peakset.iterfind('annotations/annotation')
    identities = False
    for annotation in annotations:
        if annotation.find('label').text == 'identification':
            identities = annotation.find('value').text.split(', ')
            all_identities.extend(identities)
            break

    if identities:
        # PeakML supports multiple alternative metabolite identities,currently we don't so duplicate
        # We have identities, now get intensities for the different samples
        chromatograms = peakset.iterfind('peaks/peak')  # Next level down

        for chromatogram in chromatograms:
            mid = chromatogram.find('measurementid').text
            intensity = float(chromatogram.find('intensity').text)
            mass = float(chromatogram.find('mass').text)

            # Write out to each of the identities table (need to buffer til we have the entire list)
            for identity in identities:
                quantities[mid][identity] = intensity

            # Write out to each of the identities table (need to buffer til we have the entire list)
            for identity in identities:
                masses[identity] = mass

# Sort the identities/masses into consecutive order
data = np.zeros((len(measurements), len(all_identities)))
for mid, identities in list(quantities.items()):
    for identity, intensity in list(identities.items()):
        r = measurements.index(mid)
        c = all_identities.index(identity)

        data[r, c] = intensity

output_data = pd.DataFrame(data)
output_data.index = pd.MultiIndex.from_tuples(zip(measurements, [midclass[mid] for mid in measurements]), names=["Sample", "Class"])
output_data.columns = pd.MultiIndex.from_tuples(zip(range(len(all_identities)), all_identities, [float(masses[i]) for i in all_identities]), names=['Measurement', 'HMDB', 'Scale'])

output_data

# Generate simple result figure (using pathomx libs)
from pathomx.figures import spectra

View = spectra(output_data, styles=styles)
