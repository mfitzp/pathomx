NMR Import
==========

Load raw NMR spectroscopy data from Bruker spectrometers.  
[Martin A. Fitzpatrick][]

Introduction
------------

Nuclear magnetic resonance spectroscopy (NMR spectroscopy) is a research method used to exploit the magnetic properties of atomic nuclei to determine the chemical makeup of biological samples. Resulting NMR spectra consist of multiple peaks, representing the structure of the molecule around the target atom (e.g. <sup>1</sup>H).

Major NMR spectroscopy systems save the spectroscopy data in proprietary formats. NMR Glue is a Python package which provides a consistent API for the loading of these various formats. This plugin utilises NMR Glue to import raw NMR data into the internal Pathomx data format for subsequent analysis.

Quick start
-----------

Select source data from your spectroscopy provider. Loading data may take a while, but once complete a spectra plot will be shown for individual and mean spectra.


  [Martin A. Fitzpatrick]: http://martinfitzpatrick.name/