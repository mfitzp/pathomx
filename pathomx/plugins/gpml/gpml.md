WikiPathways & GPML
===================

Visualise data on GPML pathway maps loaded from file or the WikiPathways web service. [Martin A. Fitzpatrick][]

Introduction
------------

WikiPathways<sup>[1][]</sup> is a open, collaborative pathway wiki for the exchange, development and maintenance of pathway information by the biological community. Pathways are stored in GenMAPP Pathway Markup Language (GPML)<sup>[2][]</sup> format used by the GenMAPP software and the PathVisio pathway layout software.

This plugin allows the import of GPML pathways from saved files (e.g. exported from PathVisio) or alternatively directly from WikiPathways via the WikiPathways web service<sup>[3][]</sup>

Quick start
-----------

Pathways can be loaded from local .gpml files or from the web service available via the WikiPathways button on the toolbar. Metabolite, gene or protein annotations and identities are loaded from the GPML file and mapped to known database entities (e.g. HMDB, CAS) where they exist in the current database.

If a data source is connected to the visualisation the relative metabolite concentrations will be shown with an adapted scale. Scaling and colour schemes can be altered using the scaling toolbar.

References
----------

1.  Kelder T, van Iersel MP, Hanspers K, Kutmon M, Conklin BR, Evelo C, Pico AR. (2011) [WikiPathways: building research communities on biological pathways][]. NAR [doi:10.1093/nar/gkr1074][]
2.  Dahlquist KD, Salomonis N, Vranizan K, Lawlor SC & Conklin BR [GenMAPP, a new tool for viewing and analyzing microarray data on biological pathways][] Nature Genetics 31, 19 - 20 (2002) [doi:10.1038/ng0502-19][]
3.  Kelder T, Pico AR, Hanspers K, van Iersel MP, Evelo C, Conklin BR. [Mining Biological Pathways Using WikiPathways Web Services][]. (2009) PLoS ONE 4(7): [doi:10.1371/journal.pone.0006447][]


  [Martin A. Fitzpatrick]: http://martinfitzpatrick.name/
  [1]: #ref-1
  [2]: #ref-2
  [3]: #ref-3
  [WikiPathways: building research communities on biological pathways]: http://nar.oxfordjournals.org/content/early/2011/11/16/nar.gkr1074.abstract
  [doi:10.1093/nar/gkr1074]: http://dx.doi.org/10.1093/nar/gkr1074
  [GenMAPP, a new tool for viewing and analyzing microarray data on biological pathways]: http://www.nature.com/ng/journal/v31/n1/full/ng0502-19.html
  [doi:10.1038/ng0502-19]: http://dx.doi.org/10.1038/ng0502-19
  [Mining Biological Pathways Using WikiPathways Web Services]: http://www.plosone.org/article/info:doi/10.1371/journal.pone.0006447
  [doi:10.1371/journal.pone.0006447]: http://dx.doi.org/doi:10.1371/journal.pone.0006447