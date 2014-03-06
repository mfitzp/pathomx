Developer Installation
**********************

If you would like to help with Pathomx development you will need to install a source
version of the code. Note: This is not necessary if you just want to contribute plugins,
as these can be developed against the binary installation.

Getting Started
===============

The development code is hosted on `Github`_. To contribute to development you should first
create an account on Github (if you don't have one already), then fork the pathomx/pathomx
repo so you have a personal copy of the code. If you're not familiar with Github, there is a 
`useful guide`_ available here.

On your version of the repo (should be <username>/pathomx) you will see an url to clone
the repo to your desktop. Take this and then from the command line (in a folder where 
you want the code to live) enter::

    git clone <repository-url>

After a while you will get a folder named pathomx containing the code.

The following sections list platform-specific setup instructions required to make Pathomx
run. Follow the instructions from the section and then you should be ready to run from the
command line using::

    python -m pathomx.Pathomx


Windows
=======

Install Qt5_ (Qt5.2) for Windows. Make the decision at this point whether you're installing
64bit or 32bit and stick to it.

Install Python 2.7.6 Windows installer from the `Python download site`_.

You can get Windows binaries for all required Python libraries from `the Pythonlibs library`_. 
At a minimum you will need to install NumPy_, SciPy_, `Scikit-Learn`_, Matplotlib_. Make sure that the installed
binaries match the architecture (32bit/64bit) of the installed Python.

For NMR data processing, you will need to install NMRGlue_ binaries.

For the dynamic pathway drawing plugin MetaViz you will also need to install Graphviz_.

To run Pathomx from the command line, change to the cloned git folder and then enter::

    python -m pathomx.Pathomx


MacOS X
=======

The simplest approach to setting up a development environment is through the 
MacOS X package manager Homebrew_. It should be feasible to build all these tools from 
source, but I'd strongly suggest you save yourself the bother.

Install Homebrew as follows::

    ruby -e "$(curl -fsSL https://raw.github.com/Homebrew/homebrew/go/install)"

Once that is in place use brew install to install python, PyQt5 (which will 
automatically install Qt5) and graphviz. Install pip for Python and add the packages 
numpy, scipy, pydot, nmrglue, gpml2svg, poster, wheezy, sklearn, icoshift, matplotlib. 
This can be done in a one liner with pip::

    pip install numpy scipy pydot nmrglue gpml2svg poster wheezy sklearn icoshift matplotlib

That should be enough to get Pathomx up and running from the command line. For development a
useful tool to install is `Total Terminal`_, which gets you access to the command line
via a hotkey.

To run Pathomx from the command line, change to the cloned git folder and then enter::

    python -m pathomx.Pathomx


Linux
=====

The development version (available via git) supports Python 3 and so can now be run on
Linux (tested on Ubuntu Saucy Salamander). Note: Python 3 PyQt5 is only available from 13.10.
To install on earlier releases of Ubuntu you will need to install from source.

There are a number of packages that need to be installed first::

.. code-block:: bash
    sudo apt-get install python3-pyqt5 python3-matplotlib python3-requests python3-numpy python3-scipy python3-yapsy

    pip3 install scikit-learn

Once installation of the above has completed you're ready to go.

To run Pathomx from the command line, change to the cloned git folder and then enter::

    python -m pathomx.Pathomx

.. _Github: http://github.com/pathomx/pathomx
.. _useful guide: https://help.github.com/articles/set-up-git

.. _Qt5: https://qt-project.org/downloads

.. _NMRGlue: http://code.google.com/p/nmrglue/downloads/list?q=label:Type-Installer
.. _Graphviz: http://graphviz.org/
.. _Python download site: http://www.python.org/getit/
.. _the Pythonlibs library: http://www.lfd.uci.edu/~gohlke/pythonlibs/
.. _NumPy: http://www.lfd.uci.edu/~gohlke/pythonlibs/#numpy
.. _SciPy: http://www.lfd.uci.edu/~gohlke/pythonlibs/#scipy
.. _Scikit-Learn: http://www.lfd.uci.edu/~gohlke/pythonlibs/#scikit-learn
.. _Matplotlib: http://www.lfd.uci.edu/~gohlke/pythonlibs/#matplotlib

.. _Homebrew: http://brew.sh/

.. _Total Terminal: http://totalterminal.binaryage.com/
