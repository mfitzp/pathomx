Peak Picking
============

Algorithmically pick peaks in NMR spectra data. [Martin A. Fitzpatrick][]

Introduction
------------

Peak picking is a method to identify regions of interest in source spectra based. Peaks are isolated by threshold (size) to exclude noise in the background from subsequent analysis. This plugin allows automated picking on peaks from spectra, with an optional additional peak-separation optimisation to avoid adjacent peak interference.

Quick start
-----------

[Select source data][] input and enter the experimental comparison on the data and the spectra will be shown in the view tab. Adjust the threshold and peak separation from the main toolbar and the spectra view will update to show the resulting reduced dataset.

Notes
-----

Peaks are picked on a mean summary across all spectra then values for each peak taken across each individual spectra. Further optimisations, including clustering and banding to compensate for peak wobble are planned in future.

  [Martin A. Fitzpatrick]: http://martinfitzpatrick.name/
  [Select source data]: pathomx://@view.id/default_actions/data_source/add
