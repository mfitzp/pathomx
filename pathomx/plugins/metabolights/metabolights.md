MetaboLights Import
===================

Import data from the MetaboLights database of metabolomics experiments.  
[Martin A. Fitzpatrick][]

Introduction
------------

MetaboLights is a cross-species, cross-technique database of metabolomics experiments and derived information. It aims to cover metabolite structures, reference spectra and biological roles, locations and concentrations, together with experimental data from metabolomic experiments. It hosts a number of metabolomic datasets which can be freely downloaded for analysis.

Quick start
-----------

This plugin supports the import of identity-annotated metabolite quantity files only, these are named beginning with ‘m\_’. Support for other MetaboLights file types and formats will be implemented in future. To import the data simply load the file. Metabolite name labels and data quantities will be shown on the ‘Table’ tab, however no automatic mapping to entities is currently supported.

References
----------

1.  Kenneth Haug, Reza M. Salek, Pablo Conesa, Janna Hastings, Paula de Matos, Mark Rijnbeek, Tejasvi Mahendrakar, Mark Williams, Steffen Neumann, Philippe Rocca-Serra, Eamonn Maguire, Alejandra GonzÃ¡lez-BeltrÃ¡n, Susanna-Assunta Sansone, Julian L. Griffin and Christoph Steinbeck. [MetaboLights– an open-access general-purpose repository for metabolomics studies and associated meta-data.][] Nucl. Acids Res. (2013) doi: 10.1093/nar/gks1004


  [Martin A. Fitzpatrick]: http://martinfitzpatrick.name/
  [MetaboLights– an open-access general-purpose repository for metabolomics studies and associated meta-data.]: http://nar.oxfordjournals.org/content/41/D1/D781

We've loaded the data now and have all entity info etc. so construct a Pandas dataframe for output.