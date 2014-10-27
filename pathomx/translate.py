# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging

logging.debug('Loading translate.py')

# Import PyQt5 classes
from .qt import *


def tr(s, *args, **kwargs):
    try:
        return QCoreApplication.translate('@default', s, *args, **kwargs)
    except:
        return s
