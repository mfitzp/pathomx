from sklearn.cross_decomposition import PLSRegression

import pandas as pd
import numpy as np

_experiment_test = config['experiment_test']
_experiment_control = config['experiment_control']

plsr = PLSRegression(n_components=config['number_of_components'], scale=config['autoscale']) #, algorithm=self.config.get('algorithm'))

# We need classes to do the classification; should check and raise an error
class_idx = input_data.index.names.index('Class')
classes = list( input_data.index.levels[ class_idx ] )

Y = input_data.index.labels[ class_idx ]

plsr.fit(input_data.values, Y)

# Build scores into a dso no_of_samples x no_of_principal_components
scores = pd.DataFrame(plsr.x_scores_)  
scores.index = input_data.index

scoresl =[]
for n,s in enumerate(plsr.x_scores_.T):
    scoresl.append( 'Latent Variable %d' % (n+1) ) #, plsr.y_weights_[0][n]) 
scores.columns = scoresl
    

weights = pd.DataFrame( plsr.x_weights_.T )
weights.columns = input_data.columns

dso_lv = {}


# Generate simple result figure (using pathomx libs)
from pathomx.figures import spectra, scatterplot

weightsdc=[]
for n in range(0, plsr.x_weights_.shape[1] ):
    lvd =  pd.DataFrame( plsr.x_weights_[:,n:n+1].T )
    lvd.columns = input_data.columns
    
    vars()['LV%d' % (n+1)]  = spectra(lvd, styles=styles)
    
    #weightsdl.append("Weights on LV %s" % (n+1))
    weightsdc.append("LV %s" % (n+1))

weights.index = weightsdc

Scores = scatterplot(scores, styles=styles)

weightsd = None; # Clean up
lvd = None; # Clean up

Scores