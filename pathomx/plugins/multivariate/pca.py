from sklearn.decomposition import PCA

pca = PCA(n_components=config['number_of_components'])
pca.fit(input_data.values)

import pandas as pd

# Build scores into a dso no_of_samples x no_of_principal_components
scores = pd.DataFrame( pca.transform(input_data.values) )
scores.index = input_data.index

columns = ['Principal Component %d (%0.2f%%)' % (n + 1, pca.explained_variance_ratio_[0] * 100.) for n in range(0, scores.shape[1]) ]
scores.columns = columns

weights = pd.DataFrame(pca.components_)
weights.columns = input_data.columns


dso_pc = {}
weightsi = []


# Generate simple result figure (using pathomx libs)
from pathomx.figures import spectra, scatterplot

for n in range(0, pca.components_.shape[0]):
    pcd = pd.DataFrame( weights.values[n:n + 1, :] )
    
    pcd.columns = input_data.columns
    vars()['PC%d' % (n+1)]  = spectra(pcd, styles=styles)

    weightsi.append( "PC %d" % (n + 1) )
    
weights.index = weightsi
Scores = scatterplot(scores, styles=styles)

pcd = None; # Clean up

Scores