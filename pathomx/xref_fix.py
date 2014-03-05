#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os

from .utils import UnicodeReader, UnicodeWriter

identities_files = os.listdir('.')
if len(identities_files) > 0:
    for filename in identities_files:
        if filename == 'kegg':
            list = []
            print("- %s" % filename)
            reader = UnicodeReader(open(filename, 'rU'), delimiter=',', dialect='excel')
            for id, db, key in reader:
                list.append([id, db, key])

            writer = UnicodeWriter(open(filename, 'wb'), delimiter=',', dialect='excel')
            for row in list:
                if row[2][0] != 'D':
                    writer.writerow(row)
