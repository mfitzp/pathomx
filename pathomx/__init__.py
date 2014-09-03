import os, sys
import numpy as np
import pandas as pd

import pickle, dill

from matplotlib.figure import Figure, AxesStack
from matplotlib.axes import Subplot

from mplstyler import StylesManager

import warnings
from . import displayobjects
from .utils import scriptdir, basedir
from IPython.core import display


MAGIC_TYPES = [
        np.array, np.ndarray,
        pd.Series, pd.DataFrame,
        Figure, Subplot,
        StylesManager,
        displayobjects.Svg, displayobjects.Html,
        display.SVG
        ]


def pathomx_notebook_start(varsi, vars):
    
    _keep_input_vars = ['styles']
    # Wipeout variables possibly hang around from previous runs
    for k in list( vars.keys() ):
        if type(vars[k]) in MAGIC_TYPES and \
            not k.startswith('_'):
                del vars[k]
    
    for k, v in varsi.items():
        vars[k] = v    
    
    vars['_pathomx_exclude_input_vars'] = [x for x in varsi.keys() if x not in _keep_input_vars]
    #vars['_pathomx_tempdir'] = os.path.dirname(fn)

    # Handle IO magic
    for k,v in vars['_io']['input'].items():
        if v in vars:
            vars[k] = vars[v]
        else:
            vars[k] = None

    global rcParams
    from matplotlib import rcParams

    # Block warnings from deprecated rcParams here
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for k, v in vars['rcParams'].items():
            rcParams[k] = v


def pathomx_notebook_stop(vars):
    # Handle IO magic
    for k,v in vars['_io']['output'].items():
        if k in vars:
            vars[v] = vars[k]
        else:
            vars[v] = None

    varso = {}
    for k, v in vars.items():
        # Check it's an accepted type for passing; and not private (starts with _)
        if not k.startswith('_') and \
            not k in vars['_io']['input'].keys() and \
            type(v) in MAGIC_TYPES:
    
            varso[k] = v

    vars['varso'] = varso