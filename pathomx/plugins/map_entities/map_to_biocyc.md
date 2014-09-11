Map to Biocyc
=============

Map named entities to BioCyc objects, to create an additional column annotation.
[Martin A. Fitzpatrick][]



  [Martin A. Fitzpatrick]: http://martinfitzpatrick.name/

Now iterate the labels, and if we find something assign to BioCyc.
This won't overwrite existing labels if we don't find one, but will if we do

Now perform cross-mapping if enabled.

Now take a copy of the data and build a new index.