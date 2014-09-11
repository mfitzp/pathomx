Spectra Peak Shifting and Scaling
=================================

Shift (frequency) and scale (amplitude) spectra using a reference peak (e.g. TMSP).  
[Martin A. Fitzpatrick][]

Introduction
------------

Scaling and shifting is a simple method to compensate for processing and acquisition effects in NMR of biological samples. For example scaling to TMSP can account for acquisition amplification differences and post-buffer dilution from pH adjustment. Similarly scaling on creatinine can account for urinary dilution effects. Aligning to a single reference peak is a useful first step prior to more advanced alignment algorithms such as *icoshift*.

Quick start
-----------

[Select source data][] input and enter the experimental comparison on the data and the spectra will be shown in the view tab. Adjust the algorithm and the spectra view will update to show the resulting normalised dataset. The affect of the normalisation can be seen on the ‘Change’ tab.

  [Martin A. Fitzpatrick]: http://martinfitzpatrick.name/
  [Select source data]: pathomx://@view.id/default_actions/data_source/add