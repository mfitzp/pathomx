Principal Component Analysis (PCA)
==================================

Principal component analysis using singular value decomposition (SVD). [Martin A. Fitzpatrick][]

Introduction
------------

Principal component analysis (PCA) is a mathematical method for transforming a set of possibly-correlated observations into a set of linearly uncorrelated variables called ‘principal components’. The transformation is applied such that the largest variance is represented in the first principal component, with the next largest variance in the second orthogonal component.

This plugin uses singular value decomposition (SVD) to generate a PCA model from source data. Data points are identified and colour-coded by the classes in the source data.

Quick start
-----------

[Select source data][] and a PCA model will automatically be generated.

  [Martin A. Fitzpatrick]: http://martinfitzpatrick.name/
  [Select source data]: pathomx://@view.id/default_actions/data_source/add