Gene Expression Omnibus (GEO)
=============================

Import public data from NCBI Gene Expression Omnibus (GEO). [Martin A. Fitzpatrick][]

Introduction
------------

This plugin supports loading in data from NCBI GEO using the standard SOFT format. Loading prepared datasets will import class labels and supporting information.

Quick start
-----------

Download a sample database from the [Gene Expression Omnibus][] in SOFT format. Import the data using this plugin

  [Martin A. Fitzpatrick]: http://martinfitzpatrick.name/
  [Gene Expression Omnibus]: http://www.ncbi.nlm.nih.gov/geo/

We've loaded the data now and have all entity info etc. so construct a Pandas dataframe for output.