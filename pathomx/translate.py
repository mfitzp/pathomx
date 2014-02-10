#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# Import PyQt5 classes
from PyQt5.QtGui import *
from PyQt5.QtCore import *

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
