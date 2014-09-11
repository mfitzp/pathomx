Binning
=======

Data pre-processing technique to reduce minor observation errors and reduce data size.  
[Martin A. Fitzpatrick][]

Introduction
------------

Data binning is a widely used data pre-processing technique that can be used to reduce the effects of minor observational errors. It can also be used to reduce the size of a dataset for easier processing. Regions of the data (bins) are defined, within which data is replaced with a representative value, e.g. a mean, median or central value. It is a form of quantization.

It is important to remember that binning results in a loss of data, and may introduce artefacts. This plugin attempts to mitigate some of these problems by providing information on data loss, and offering adaptive binning approaches.

Quick start
-----------

This plugin can bin any data in 1 dimension, e.g. NMR spectra. Simply select the data source and the data will be automatically binned. You can adjust the bin size using the toolbar, together with a bin offset. You can view the result of the binning a tabular, or spectral view. Importantly, this plugin also presents a difference view that shows the data loss associated with a given binning strategy, together with a summary view.

Tip
---

Resulting data output can be fed into statistical analysis, for example PCA, where the effects of binning can be observed live.

  [Martin A. Fitzpatrick]: http://martinfitzpatrick.name/