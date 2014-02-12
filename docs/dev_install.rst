Developer Installation
**********************

If you would like to help with Pathomx development you will need to install a source
version of the code. Note: This is not necessary if you just want to contribute plugins,
as these can be developed against the binary installation.


Windows
==================

Install Python 2.7.6 Windows installer from the _Python_download_site.

You can get Windows binaries for all required Python libraries from `the Pythonlibs library`_Pythonlibs. 
At a minimum you will need to install _NumPy, _SciPy, _Scikit_Learn, _Matplotlib. Make sure that the installed
binaries match the architecture (32bit/64bit) of the installed Python.

For NMR data processing, you will need to install _NMRGlue binaries.

For the dynamic pathway drawing plugin MetaViz you will also need to install _Graphviz.


MacOS X
==================

The simplest approach to setting up a development environment is through the 
MacOS X package manager _Homebrew. It should be feasible to build all these tools from 
source, but I'd strongly suggest you save yourself the bother.

Install Homebrew as follows:

ruby -e "$(curl -fsSL https://raw.github.com/Homebrew/homebrew/go/install)"



.. _NMRGlue: http://code.google.com/p/nmrglue/downloads/list?q=label:Type-Installer
.. _Graphviz: http://graphviz.org/
.. _Python_download_site: http://www.python.org/getit/
.. _Pythonlibs: http://www.lfd.uci.edu/~gohlke/pythonlibs/
.. _NumPy: http://www.lfd.uci.edu/~gohlke/pythonlibs/#numpy
.. _SciPy: http://www.lfd.uci.edu/~gohlke/pythonlibs/#scipy
.. _Scikit_Learn: http://www.lfd.uci.edu/~gohlke/pythonlibs/#scikit-learn
.. _Matplotlib: http://www.lfd.uci.edu/~gohlke/pythonlibs/#matplotlib

.. _Homebrew: http://brew.sh/
