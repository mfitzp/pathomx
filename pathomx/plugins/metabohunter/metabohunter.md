MetaboHunter
============

Automated identification from NMR spectra via the MetaboHunter web service.  
[Dan Tulpan][] <small>MetaboHunter</small>, [Martin A. Fitzpatrick][] <small>Python interface</small>

Introduction
------------

MetaboHunter<sup>[1][],[2][1]</sup> is a web service for automated assignment of 1D raw, bucketed or peak picked NMR spectra. Identification is performed in comparison to two publicly available databases ([HMDB][], [MMCD][]) of NMR standard measurements. This plugin offers an interface to all the options available through the web service on loaded data.

Quick start
-----------

Select source data to import and set the data submission parameters. Submission takes \~30seconds depending on the size of the dataset for analysis. The resulting labels and annotations are shown in the table, with a spectra view showing mappings overlaid on the spectra. Where entities are known in the internal database these are mapped automatically, otherwise the HMDB label is shown.

Notes
-----

MetaboHunter makes use of 867 HMDB and 448 MMCD NMR spectra. All spectra have been manually curated.

References
----------

1.  Tulpan, D., Leger, S., Belliveau, L., Culf, A., Cuperlovic-Culf, M. (2011). [MetaboHunter: semi-automatic identification of 1H-NMR metabolite spectra in complex mixtures][]. BMC Bioinformatics 2011, 12:400
2.  [MetaboHunter web service][]


  [Dan Tulpan]: http://nrc-ca.academia.edu/DanTulpan
  [Martin A. Fitzpatrick]: http://martinfitzpatrick.name/
  [1]: #ref-1
  [HMDB]: http://www.hmdb.ca
  [MMCD]: http://mmcd.nmrfam.wisc.edu/
  [MetaboHunter: semi-automatic identification of 1H-NMR metabolite spectra in complex mixtures]: http://www.biomedcentral.com/1471-2105/12/400
  [MetaboHunter web service]: http://www.nrcbioinformatics.ca/metabohunter/

We've loaded the data now and have all entity info etc. so construct a Pandas dataframe for output.