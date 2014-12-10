iimport pandas as pd
import scipy as sp
import scipy.stats
import numpy as np
import matplotlib.pyplot as plt
Figure = plt.figure

from pathomx.figures import FIGURE_SIZE, FIGURE_DPI

View = Figure(figsize=FIGURE_SIZE, dpi=FIGURE_DPI)
ax = View.add_subplot(1,1,1)

# Perform t-test by experiment values

a = input_data.xs(config['experiment_control'], level=input_data.index.names.index('Class'))
# b = input_data.xs(config['experiment_test'], level=input_data.index.names.index('Class'))

std = np.nanstd( input_data.values )
mean = np.nanmean(input_data.values.flatten())

def ttest_1sampnan( df, popmean=0):
    ts, ps = [], []
    for n in range(df.shape[1]):
        v = df.iloc[:, n ]
        t, p = sp.stats.ttest_1samp( v[ ~np.isnan(v)], popmean=popmean)
        ts.append( t )
        ps.append( p )

    return np.array(ts), np.array(ps)

#t, prob = sp.stats.ttest_ind(a, b, axis=0, equal_var=config['assume_equal_variances'])

t, p = ttest_1sampnan(a, popmean=0)

data = np.nanmean( a.values, axis=0)

p_value_cutoff = 0.05

_FILTER_IN = p <= p_value_cutoff
_FILTER_IN_1SD = np.abs(data) >= std
_FILTER_IN_2SD = np.abs(data) >= std * 2
_FILTER_IN_1SD = _FILTER_IN_1SD & ~ _FILTER_IN_2SD

_FILTER_1SD = _FILTER_IN & _FILTER_IN_1SD
_FILTER_2SD = _FILTER_IN & _FILTER_IN_2SD

_FILTER_IN = _FILTER_1SD | _FILTER_2SD
_FILTER_OUT = ~ _FILTER_IN

def scatter(ax, f, c):
    ax.scatter( data[f], -np.log10( p[f]), c=c, linewidths=0.5, alpha=0.7, s=48)

scatter(ax, _FILTER_OUT, 'gray')
scatter(ax, _FILTER_1SD, 'red')
scatter(ax, _FILTER_2SD, 'green')


ax.axvline(mean, c='k')

ax.axvline(std, c='r')
ax.axvline(-std, c='r')

ax.axvline(std*2, c='g')
ax.axvline(-std*2, c='g')

ax.axhline(-np.log10(p_value_cutoff), c='gray')

ax.set_ylabel('-log10(p)')
ax.set_xlabel('log2 ratio')

a = None