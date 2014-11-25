import os
import sys
import numpy as np
import pandas as pd
import re

from matplotlib.figure import Figure, AxesStack
from matplotlib.axes import Subplot

from mplstyler import StylesManager

import warnings
from . import displayobjects
from .utils import scriptdir, basedir
from IPython.core import display
from copy import deepcopy

MAGIC_TYPES = [
        # Numpy
        np.array, np.ndarray,
        # Pandas
        pd.Series, pd.DataFrame,
        Figure, Subplot,
        StylesManager,
        # View types
        displayobjects.Svg, displayobjects.Html, displayobjects.Markdown,
        display.SVG
        ]


class PathomxTool(object):
    ''' Simple wrapper class that holds the output data for a given tool; This is for user-friendliness
    not for use '''

    def __str__(self):
        return self._name

    def __repr__(self):
        return self._name

    def __init__(self, name, *args, **kwargs):
        self.__dict__.update(kwargs)
        self._name = name


def pathomx_notebook_start(varsi, vars):

    for k, v in varsi.items():
        vars[k] = v

    # Handle IO magic
    for k, v in vars['_io']['input'].items():
        if v in vars:
            vars[k] = deepcopy(vars[v])
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
    for k, v in vars['_io']['output'].items():
        if k in vars:
            vars[v] = vars[k]
        else:
            vars[v] = None

    varso = {}
    for k, v in vars.items():
        # Check it's an accepted type for passing; and not private (starts with _)
        if not k.startswith('_') and \
            not k in vars['_io']['input'].keys():

            if type(v) in MAGIC_TYPES or k in vars['_pathomx_expected_output_vars']:
                varso[k] = v

            elif hasattr(v, '_repr_html_'):
                try:
                    # Check if it is a bound method (not a class definition)
                    v._repr_html_()
                except:
                    pass
                else:
                    varso[k] = displayobjects.Html(v)

    vars['varso'] = varso

    
def progress(progress):
    ''' Output the current progress to stdout on the remote core
        this will be read from stdout and displayed in the UI '''
    print("____pathomx_execute_progress_%.2f____" % progress)


class open_with_progress(file):

    def __init__(self, f, *args, **kwargs):
        super(open_with_progress, self).__init__(f, *args, **kwargs)

        self._fsize = os.path.getsize(f)
        self._progress = None

    def read(self, *args, **kwargs):
        super(open_with_progress, self).read(*args, **kwargs)
        self.check_and_emit_progress()

    def check_and_emit_progress(self):
        # We only output at 2dp so only emit when that changes
        prg = round(self.tell() / self._fsize, 2)
        if prg != self._progress:
            self._progress = prg
            progress(prg)
