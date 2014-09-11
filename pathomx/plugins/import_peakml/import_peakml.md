PeakML/mzMatch
==============

Import data from mzMatch via the PeakML XML format.  
[Martin A. Fitzpatrick][]

Introduction
------------

mzMatch<sup>[1][]</sup> is a modular, open source, platform independent data processing pipeline for metabolomics LC/MS data. It provides a number of small tools covering common processing tasks for LC/MS data. The mzMatch environment was based entirely on the PeakML file format and core library, which provides a common framework for all the tools.

The PeakML format allows mzMatch to export and share data with other software. This plugin allows for importing of PeakML into Pathomx.

Quick start
-----------

This plugin imports data, annotations and identities from the PeakML file. Identities marked with HMDB identities will be directly mapped to internal metabolites where they exist in the current database. Sample classes are loaded by number. Scale ppm is also loaded and can be viewed under the View tab.

References
----------

1.  Richard A. Scheltema, Andris Jankevics, Ritsert C. Jansen, Morris A. Swertz, and Rainer Breitling [PeakML/mzMatch: A File Format, Java Library, R Library, and Tool-Chain for Mass Spectrometry Data Analysis][] *Analytical Chemistry* **2011** 83 (7), pp 2786-2793


  [Martin A. Fitzpatrick]: http://martinfitzpatrick.name/
  [1]: #ref-1
  [PeakML/mzMatch: A File Format, Java Library, R Library, and Tool-Chain for Mass Spectrometry Data Analysis]: http://pubs.acs.org/doi/abs/10.1021/ac2000994