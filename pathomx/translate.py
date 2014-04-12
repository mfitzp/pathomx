#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
logging.debug('Loading translate.py')

# Import PyQt5 classes
from .qt import QCoreApplication


def tr(s, *args, **kwargs):
    try:
        return QCoreApplication.translate('@default', s, *args, **kwargs)
    except:
        return s

#Workspace
#tr("Home")
#tr("Data")
#tr("Processing")
#tr("Identification")
#tr("Analysis")
#tr("Visualisation")

#Database
#tr("Genes")
#tr("Proteins")
#tr("Enzymes")
#tr("Compounds")
#tr("Pathways")
#tr("Databases")
