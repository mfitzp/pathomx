PRIDE data Import
=================

Import data from the PRIDE PRoteomics IDEntifications (PRIDE) database.  
[Martin A. Fitzpatrick][]

Introduction
------------

The PRIDE PRoteomics IDEntifications (PRIDE) database is a centralized, standards compliant, public data repository for proteomics data, including protein and peptide identifications, post-translational modifications and supporting spectral evidence.

Quick start
-----------

This plugin supports the import of quantified protein data only. To import the data simply load the downloaded file. Known proteins will be mapped to internal MetaCyc database.

References
----------

1.  Kenneth Haug, Reza M. Salek, Pablo Conesa, Janna Hastings, Paula de Matos, Mark Rijnbeek, Tejasvi Mahendrakar, Mark Williams, Steffen Neumann, Philippe Rocca-Serra, Eamonn Maguire, Alejandra González-Beltrán, Susanna-Assunta Sansone, Julian L. Griffin and Christoph Steinbeck. [MetaboLights– an open-access general-purpose repository for metabolomics studies and associated meta-data.][] Nucl. Acids Res. (2013) doi: 10.1093/nar/gks1004


  [Martin A. Fitzpatrick]: http://martinfitzpatrick.name/
  [MetaboLights– an open-access general-purpose repository for metabolomics studies and associated meta-data.]: http://nar.oxfordjournals.org/content/41/D1/D781

We've loaded the data now and have all entity info etc. so construct a Pandas dataframe for output.