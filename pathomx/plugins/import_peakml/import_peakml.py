# -*- coding: utf-8 -*-
import os

import csv
import xml.etree.cElementTree as et
from collections import defaultdict

import base64

import numpy as np

import pathomx.ui as ui
import pathomx.db as db
import pathomx.utils as utils

from pathomx.data import DataSet
from pathomx.plugins import ImportPlugin


class ImportPeakMLApp(ui.ImportDataApp):

    import_filename_filter = "PeakML (MzMatch) Data Files (*.peakml);;All files (*.*)"
    import_description = "Open experimental data from PeakML data files"

    def decode(self, s):
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
    # Data file import handlers (#FIXME probably shouldn't be here)

    def load_datafile(self, filename):
        # Determine if we've got a csv or peakml file (extension)
        #self.data.o['output'].empty()
        dso = DataSet()

        # Read data in from peakml format file
        xml = et.parse(filename)

        # Get sample ids, names and class groupings
        sets = xml.iterfind('header/sets/set')
        midclass = {}
        classes = set()
        measurements = []
        masses = {}

        for aset in sets:
            id = aset.find('id').text
            mids = aset.find('measurementids').text
            for mid in self.decode(mids):
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


        # Quantities table built; class table built; now rearrange into dso
        dso.empty((len(measurements), len(all_identities)))
        dso.labels[0] = measurements
        dso.classes[0] = [midclass[mid] for mid in measurements]

        dso.labels[1] = all_identities
        db_hmdbids = self.m.db.unification['HMDB']
        dso.entities[1] = [db_hmdbids[hmdbid] if hmdbid in db_hmdbids else None for hmdbid in all_identities]
        dso.scales[1] = [float(masses[i]) for i in all_identities]

        for mid, identities in list(quantities.items()):
            for identity, intensity in list(identities.items()):
                r = measurements.index(mid)
                c = all_identities.index(identity)

                dso.data[r, c] = intensity

        dso.name = os.path.basename(filename)
        dso.description = 'Imported PeakML file'
        self.set_name(dso.name)

        return {'output': dso}


class ImportPeakML(ImportPlugin):

    def __init__(self, **kwargs):
        super(ImportPeakML, self).__init__(**kwargs)
        self.register_app_launcher(ImportPeakMLApp)
