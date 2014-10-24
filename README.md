# Pathomx

*Latest stable release v3.0.2 (24th October 2014).*

Pathomx is an interactive tool for the analysis and visualisation of scientific data.
Built on IPython it allows rapid, workflow-based exploration of complex datasets through
configurable tool-scripts. Originally designed for the processing of metabolomics data
it can equally be applied to the analysis of other biological or scientific data.

Metabolomics-specific tools include NMR data import and export, spectra processing inc. normalisation, alignment,
and binning, and metabolic pathway mining and visualisation. It ships with set of the the [MetaCyc][metacyc] database
derived from the public API containing most key metabolic pathways. Annotations from the MetaCyc database are
available including synonyms, associated reactions and pathways and database unification links.

**Stable** The current trunk of Pathomx is stable and can be built using cx_Freeze (as-is on Windows, with some tweaks on Mac). The latest version (3.0.0) is now available to download
[Windows 7 & 8 (x64)][pathomx-windows] &bull; [Mac OS X Mountain Lion .app][pathomx-mac] &bull; [Github][pathomx-github]

![Screenshot](http://pathomx.org/images/software/pathomx/annotation_demo.png)

It is developed in Python, using Qt5/PyQt5, Matplotlib (for graphing), numpy/scipy (for number handling), nmrglue (for NMR data import), scikit-learn (for statistical analysis methods).

**Download** [Windows 7 & 8 (x64)][pathomx-windows] &bull; [Mac OS X Mountain Lion .app][pathomx-mac] &bull; [Github][pathomx-github]

> Pathomx requires installation of [Graphviz][graphviz] for pathway drawing.

# License

Pathomx is available free for any use under the [GPLv3 license](http://www.gnu.org/licenses/gpl.html).

> Pathomx uses data from the [MetaCyc](http://metacyc.org) pathway database itself part of
the [BioCyc](http://biocyc.org) family. The supplied database is generated via the 
MetaCyc API and stored locally. Licenses for the entire MetaCyc database
[are also available](http://metacyc.org/contact.shtml) free of charge for academic
and government use.

 [pathomx-github]: https://github.com/pathomx/pathomx
 [pathomx-github-issues]: https://github.com/pathomx/pathomx/issues
 [metacyc]: http://metacyc.org
 [pathomx-mac]: http://download.pathomx.org/Pathomx-latest.dmg
 [pathomx-windows]: http://download.pathomx.org/Pathomx-latest.exe
 [graphviz]: http://www.graphviz.org/
 
