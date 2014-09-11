Spectra normalisation
=====================

Algorithmically normalise spectra using TSA or PQN algorithms.  
[Martin A. Fitzpatrick][]

Introduction
------------

Normalisation is often used with spectra to compensate for gross differences in dilution that may mask the actual biological differences of interest. For example, urine volume varies widely while metabolite excretion (the interesting bit) is often relatively constant. This plugin provides algorithms for performing two common normalisation approaches: Total Spectral Area (TSA) and Probabilistic Quotient Normalization (PQN).

Quick start
-----------

[Select source data][] input and enter the experimental comparison on the data and the spectra will be shown in the view tab. Adjust the algorithm and the spectra view will update to show the resulting normalised dataset. The affect of the normalisation can be seen on the ‘Change’ tab.

  [Martin A. Fitzpatrick]: http://martinfitzpatrick.name/
  [Select source data]: pathomx://@view.id/default_actions/data_source/add