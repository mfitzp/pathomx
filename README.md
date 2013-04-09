# Introduction

MetaPath is a tool for the analysis of metabolic pathway and associated visualisation
of experimental data. Built on the [MetaCyc][metacyc] database it provides an interactive map in which multiple pathways can be simultaneously visualised. Multiple annotations from the MetaCyc database are available including synonyms, associated reactions and pathways and database unification links.

Metabolomics change data can be imported via simple CSV formats for visualisation on
targeted pathways. Pathways can be mined and removed algorithmically to identify key
regulated pathways within in a given dataset providing a simper route to metabolic
function.

**Download** [Mac OS X Mountain Lion .app][metapath-macapp] &bull; [Github][metapath-github] &bull; [Python .eggs or .gz source][metapath-pypi].

> MetaPath requires installation of [Graphviz][graphviz] for pathway drawing.

# License

MetaPath is available free for any use under the [GPLv3 license](http://www.gnu.org/licenses/gpl.html).

> MetaPath is built on the [MetaCyc](http://metacyc.org) pathway database itself part of 
the [BioCyc](http://biocyc.org) family. The supplied database is generated via the 
MetaCyc API and stored locally. Licenses for the entire MetaCyc database
[are also available](http://metacyc.org/contact.shtml) free of charge for academic
and government use.

 [metapath-github]: https://github.com/mfitzp/metapath/issues
 [metapath-github-issues]: https://github.com/mfitzp/metapath
 [metacyc]: http://metacyc.org
 [metapath-macapp]: http://download.martinfitzpatrick.name/MetaPath.dmg
 [metapath-pypi]: https://pypi.python.org/pypi/metapath 
 [graphviz]: http://www.graphviz.org/
 