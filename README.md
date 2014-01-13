# MetaPath

**Stable** The current trunk of MetaPath is stable and can be built using cx_Freeze (as-is on Windows, with some tweaks on Mac). The latest version (2.0.0) is now available to download
[Windows 7 & 8 (x64)][metapath-windows] &bull; [Mac OS X Mountain Lion .app][metapath-mac] &bull; [Github][metapath-github] &bull; [Python .eggs or .gz source][metapath-pypi].

![Screenshot](http://getmetapath.org/images/software/metapath/metapath-v2-visual-editor.png)

MetaPath is an interactive tool for the analysis and visualisation of metabolic data.
Built on the [MetaCyc][metacyc] database it allows rapid exploration of complex datasets
through configurable and extensible plugin. Multiple annotations from the MetaCyc database are 
available including synonyms, associated reactions and pathways and database unification links.

Metabolomics and genomic data can be imported via various routes for visualisation on
targeted pathways. Pathways can be mined and removed algorithmically to identify key
regulated pathways within in a given dataset providing a simper route to metabolic
function.

It is developed in Python, using Qt5/PyQt5, Matplotlib (for graphing), numpy/scipy (for number handling), nmrglue (for NMR data import), scikit-learn (for statistical analysis methods) and the d3.js visualisation engine for pretty interactive graphs. **Developers are very welcome to contribute, just get in touch!**

**Download** [Windows 7 & 8 (x64)][metapath-windows] &bull; [Mac OS X Mountain Lion .app][metapath-mac] &bull; [Github][metapath-github] &bull; [Python .eggs or .gz source][metapath-pypi].

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
 [metapath-mac]: http://download.getmetapath.org/MetaPath-2.0.0.dmg
 [metapath-windows]: http://download.getmetapath.org/MetaPath-2.0.0-amd64.msi
 [metapath-pypi]: https://pypi.python.org/pypi/metapath 
 [graphviz]: http://www.graphviz.org/
 