from pathomx.displayobjects import Html
import scipy as sp
from scipy import stats
import numpy as np
import matplotlib.pyplot as plt

a = input_data.xs(config['experiment_control'], level=input_data.index.names.index('Class'))
b = input_data.xs(config['experiment_test'], level=input_data.index.names.index('Class'))

# Select or flatten along the variable axis (use something else for multivariate)
a = a.mean(axis=1)
b = b.mean(axis=1)

if config['related_or_independent'] == 'Independent':
    description = 'Independent t-test%s.' % (' assuming equal variances in the groups' if config['assume_equal_variances'] else '')

    t, prob = sp.stats.ttest_ind(a, b, axis=0, equal_var=config['assume_equal_variances'])

elif config['related_or_independent'] == 'Related':
    description = 'Related t-test'

    t, prob = sp.stats.ttest_rel(a, b, axis=0)

else:
    raise Exception('Invalid t-test type.')

Result = Html('''
<table>
<tr><th>t statistic</th><td>%.4f</td></tr>
<tr><th>p value</th><td>%.4f</td></tr>
<tr><th>n</th><td>%d (a), %d (b)</td></tr>
</table>
<p>%s</p>
 ''' % (t, prob, a.shape[0], b.shape[0], description))


if config['plot_distribution']:
    bins = bins = np.linspace(min(np.min(a.values), np.min(b.values)), max(np.max(a.values), np.max(b.values)), 10)
    # Plot a histogram distribution for the source data (both)
    Distribution = plt.figure()
    ax = Distribution.add_subplot(1, 1, 1)
    ax.hist(a.values, bins, facecolor=styles.get_style_for_class(config['experiment_control']).color, alpha=0.75, label=config['experiment_control'])
    ax.hist(b.values, bins, facecolor=styles.get_style_for_class(config['experiment_test']).color, alpha=0.75, label=config['experiment_test'])

    ax.legend(loc='upper right')

# Clear up output
a, b = None, None
