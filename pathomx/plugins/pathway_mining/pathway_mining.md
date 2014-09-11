Pathway Mining
==============

Calculate scores for pathways (or reactions, compartments) using various simple mining algorithms.    
[Martin A. Fitzpatrick][]

Introduction
------------

In untargeted metabolic studies it is often useful to determine the key areas of metabolic regulation within a system. Pathomx supports pathway-based mining of experimental data, using a number of different scoring algorithms, which has the added benefit of proving context for the identified change.

The scoring algorithm can be altered from the ‘Settings…’ dialog. Scoring can be based on upregulation, downregulation, overall change and by the number of identified metabolites in the sample. Adjusting scores relative to the number of metabolites in a pathway removes the bias towards larger pathways (although this is often preferable for interpretation). You can adjust the pruning threshold from the data toolbar.

  [Martin A. Fitzpatrick]: http://martinfitzpatrick.name/
  [Select source data]: pathomx://@view.id/default_actions/data_source/add