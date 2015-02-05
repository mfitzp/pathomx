from sklearn.decomposition import PCA

number_of_components = config['number_of_components']

pca = PCA(n_components=number_of_components)
pca.fit(input_data.values)

import pandas as pd
import numpy as np

# Build scores into a dso no_of_samples x no_of_principal_components
scores = pd.DataFrame(pca.transform(input_data.values))
scores.index = input_data.index

columns = ['Principal Component %d (%0.2f%%)' % (n + 1, pca.explained_variance_ratio_[0] * 100.) for n in range(0, scores.shape[1])]
scores.columns = columns

weights = pd.DataFrame(pca.components_)
weights.columns = input_data.columns

dso_pc = {}
weightsi = []

# Generate simple result figure (using pathomx libs)
from pathomx.figures import spectra, scatterplot, plot_point_cov

for n in range(0, pca.components_.shape[0]):
    pcd = pd.DataFrame(weights.values[n:n + 1, :])

    pcd.columns = input_data.columns
    vars()['PC%d' % (n + 1)] = spectra(pcd, styles=styles)

    weightsi.append("PC %d" % (n + 1))

weights.index = weightsi


if config['plot_sample_numbers']:
    label_index = 'Sample'
else:
    label_index = None


# Build a combined grid plot showing all PCA combinations
# Build scores plots for all combinations up to n
#score_combinations = list( set([ (a,b) for a in range(0,nc) for b in range(a+1, nc+1)]) )

if number_of_components == 2:
    Scores = scatterplot(scores.iloc[:,(0,1)], styles=styles, label_index=label_index)

else:
    from pathomx.figures import Figure
    Scores = Figure()
    
    for y in range(0, pca.components_.shape[0]):
        for x in range(0, pca.components_.shape[0]):

            ax = Scores.add_subplot(number_of_components, number_of_components, y*number_of_components+(x+1))

            scatterplot(scores.iloc[:,(x,y)], styles=styles, label_index=label_index, figure=Scores, ax=ax, show_legend=False)
                
            if x > 0:
                ax.axes.get_yaxis().set_visible(False)
            if y < number_of_components-1:
                ax.axes.get_xaxis().set_visible(False)


# Clean up
pcd = None

if config['filter_data']:
    ffilter = None
    for sc in score_combinations:
        e = plot_point_cov( scores.iloc[:, score_combinations[0]])
        filterset = []
        for n in range(0, scores.shape[0]):
            v = scores.iloc[n, score_combinations[0]].values
            filterset.append( e.contains_point(v, radius=0))

        filterset = np.array(filterset, dtype=np.bool)
        if ffilter is not None:
            ffilter = ffilter & filterset
        else:
            ffilter = filterset

    filtered_data = input_data.iloc[filterset]

else:
    filtered_data = None