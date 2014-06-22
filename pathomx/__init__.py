import os
import numpy as np
import pandas as pd

try:
    import cPickle as pickle
except:
    import pickle

from matplotlib.figure import Figure
from matplotlib.axes import Subplot

from mplstyler import StylesManager

import warnings
from . import displayobjects

MAGIC_TYPES = [
        np.array, np.ndarray,
        pd.Series, pd.DataFrame,
        Figure, Subplot,
        StylesManager,
        displayobjects.Svg, displayobjects.Html,
        ]


def pathomx_notebook_start(fn, vars):

    _keep_input_vars = ['styles']

    '''
    # Wipeout variables possibly hang around from previous runs
    # NB: Not a problem as we're no longer re-using runners
    for k in list( vars.keys() ):
        if type(vars[k]) in MAGIC_TYPES:
            del vars[k]
    '''

    with open(fn, 'r') as f:
        ivars = pickle.load(f)

        for k, v in ivars.items():
            vars[k] = v

    vars['_pathomx_exlude_input_vars'] = [x for x in ivars.keys() if x not in _keep_input_vars]
    vars['_pathomx_tempdir'] = os.path.dirname(fn)

    global rcParams
    from matplotlib import rcParams

    # Block warnings from deprecated rcParams here
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for k, v in vars['rcParams'].items():
            rcParams[k] = v

    
def pathomx_notebook_stop(fn, vars):
    # Export known variable types from globals


    with open(fn, 'wb') as f:
        ovars = {}
        for k, v in vars.items():
            # Check it's an accepted type for passing; and not private (starts with _)
            if not k.startswith('_') and \
               not k in vars['_pathomx_exlude_input_vars'] and \
               type(v) in MAGIC_TYPES:

                #try:
                #    # Horrible hack to test picklability of each var before, er, pickling.
                #    pickle.dumps(v, -1)
                #except:
                #    pass
                #else:
                #
                ovars[k] = v
        del k, v
        pickle.dump(ovars, f, -1)
