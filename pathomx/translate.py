#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# Import PyQt5 classes
from PyQt5.QtGui import *
from PyQt5.QtCore import *

def tr(*args, **kwargs):
    return QCoreApplication.translate('@default',*args, **kwargs)
    
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
