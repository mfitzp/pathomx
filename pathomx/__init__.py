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

def pathomx_notebook_start(fn, vars):

    _keep_input_vars = ['styles']
    
    with open(fn, 'r') as f:
        ivars = pickle.load(f)
    
        for k,v in ivars.items():
            vars[k] = v

    vars['_pathomx_exlude_input_vars'] = [x for x in ivars.keys() if x not in _keep_input_vars]
    
    global rcParams
    from matplotlib import rcParams
    
    # Block warnings from deprecated rcParams here
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for k,v in vars['rcParams'].items():
            rcParams[k] = v

    
def pathomx_notebook_stop(fn, vars):
    # Export known variable types from globals
    accepted_types = [
        # int, float, bool, str, unicode,
        np.array, np.ndarray,
        pd.Series, pd.DataFrame,
        Figure, Subplot,
        StylesManager,
        ]

    with open(fn, 'w') as f:
        ovars = {}
        for k,v in vars.items():
            # Check it's an accepted type for passing; and not private (starts with _)
            if not k.startswith('_') and \
               not k in vars['_pathomx_exlude_input_vars'] and \
               type(v) in accepted_types:
                    
                try:
                    pickle.dumps(v)
                except:
                    pass
                else:
                    ovars[k] = v

        pickle.dump(ovars, f)