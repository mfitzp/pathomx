# Pathomx

**Stable** The current trunk of Pathomx is stable and can be built using cx_Freeze (as-is on Windows, with some tweaks on Mac). The latest version (2.5.0) is now available to download
[Windows 7 & 8 (x64)][pathomx-windows] &bull; [Mac OS X Mountain Lion .app][pathomx-mac] &bull; [Github][pathomx-github] &bull; [Python .eggs or .gz source][pathomx-pypi].

![Screenshot](http://pathomx.org/images/software/pathomx/pathomx-v2-visual-editor.png)

Pathomx is an interactive tool for the analysis and visualisation of metabolic data.
Built on the [MetaCyc][metacyc] database it allows rapid exploration of complex datasets
through configurable and extensible plugin. Multiple annotations from the MetaCyc database are 
available including synonyms, associated reactions and pathways and database unification links.

Metabolomics and genomic data can be imported via various routes for visualisation on
targeted pathways. Pathways can be mined and removed algorithmically to identify key
regulated pathways within in a given dataset providing a simper route to metabolic
function.

It is developed in Python, using Qt5/PyQt5, Matplotlib (for graphing), numpy/scipy (for number handling), nmrglue (for NMR data import), scikit-learn (for statistical analysis methods) and the d3.js visualisation engine for pretty interactive graphs. **Developers are very welcome to contribute, just get in touch!**

**Download** [Windows 7 & 8 (x64)][pathomx-windows] &bull; [Mac OS X Mountain Lion .app][pathomx-mac] &bull; [Github][pathomx-github] &bull; [Python .eggs or .gz source][pathomx-pypi].

> Pathomx requires installation of [Graphviz][graphviz] for pathway drawing.

# License

Pathomx is available free for any use under the [GPLv3 license](http://www.gnu.org/licenses/gpl.html).

> Pathomx is built on the [MetaCyc](http://metacyc.org) pathway database itself part of 
the [BioCyc](http://biocyc.org) family. The supplied database is generated via the 
MetaCyc API and stored locally. Licenses for the entire MetaCyc database
[are also available](http://metacyc.org/contact.shtml) free of charge for academic
and government use.

 [pathomx-github]: https://github.com/pathomx/pathomx
 [pathomx-github-issues]: https://github.com/pathomx/pathomx/issues
 [metacyc]: http://metacyc.org
 [pathomx-mac]: http://download.pathomx.org/Pathomx-2.5.0.dmg
 [pathomx-windows]: http://download.pathomx.org/Pathomx-2.5.0-amd64.msi
 [pathomx-pypi]: https://pypi.python.org/pypi/Pathomx 
 [graphviz]: http://www.graphviz.org/
 
