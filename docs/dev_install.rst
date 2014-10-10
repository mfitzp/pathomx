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

    python Pathomx.py


Windows
=======

Install Qt4_ or Qt5_ for Windows. Currently Qt4 is recommended due to a bug with IPython with PyQt5.
Make the decision at this point whether to use 64bit or 32bit versions and stick to it.

Install Python 2.7.6 Windows installer from the `Python download site`_.

Install PyQt4_ or PyQt5_ (depending on whether you have Qt4 or Qt5 installed)

You can get Windows binaries for most required Python libraries from `the Pythonlibs library`_.
At a minimum you will need to install Pip_, NumPy_, SciPy_, `Scikit-Learn`_, Matplotlib_, IPython_, pyzmq_.
Make sure that the installed binaries match the architecture (32bit/64bit) and the installed Python version.

With those installed you can now add the final dependencies via Pip:

    pip install ipython jsonschema jsonpointer mistune mplstyler pyqtconfig metaviz biocyc

To run Pathomx from the command line, change to the cloned git folder and then enter::

    python Pathomx.py


Windows Using Anaconda
======================

Install Anaconda for Windows. Link to the website is http://continuum.io/downloads.
Make the decision at this point whether to use 64bit or 32bit versions and stick to it.

With Anaconda installed, open the Anaconda command prompt and  you can add the final dependencies.

    pip install mplstyler yapsy pyqtconfig.

To run Pathomx from the command line, change to the cloned git folder and then enter::

    python Pathomx.py

MacOS X
=======

The simplest approach to setting up a development environment is through the
MacOS X package manager Homebrew_. It should be feasible to build all these tools from
source, but I'd strongly suggest you save yourself the bother.

Install Homebrew as follows::

    ruby -e "$(curl -fsSL https://raw.github.com/Homebrew/homebrew/go/install)"

Once that is in place use brew install to install python and PyQt4 (which will
automatically install Qt4). From the command line enter::

    brew install python pyqt

You can opt to install pyqt5 instead, however currently this offers lower performance and requires
bleeding-edge matplotlib/IPython to function.
Next use pip to install all required Python packages. This can be done in a one liner with pip::

    pip install numpy scipy pandas matplotlib scikit-learn poster yapsy pyqtconfig mplstyler
    pip install ipython[all]

You can also optionally install the following for some biological data analysis notebooks::

    brew install graphviz
    pip install pydot nmrglue gpml2svg icoshift biocyc metaviz

That should be enough to get Pathomx up and running from the command line. 
To run Pathomx from the command line, change to the cloned git folder and then enter::

    python Pathomx.py

MacOS X Using Anaconda
======================

Install Anaconda for MacOS X. Link to the website is http://continuum.io/downloads.

With Anaconda installed, open the terminal on Mac and  you can add the final dependencies.

    pip install mplstyler yapsy pyqtconfig

To run Pathomx from the command line, change to the cloned git folder and then enter::

    python Pathomx.py

Troubleshooting 
---------------
1) Since the master branch of Pathomx is tracking the latest dev tag of iPython, and Anaconda pulls in a release version (might not be the latest), there can be import errors. This can be fixed by performing the following steps to pull in the latest release or dev version of iPython:

    a) Try updating iPython to the latest release version:
        - conda update conda
        - conda update ipython

    b) If this doesn't work, try pulling in the latest dev version of iPython:
        - git clone --recursive https://github.com/ipython/ipython.git
        - cd ipython
        - pip install -e ".[notebook]" --user

Linux
=====

The development version (available via git) supports Python 3 and so can now be run on
Linux (tested on Ubuntu Saucy Salamander). Note: Python 3 PyQt5 is only available from 13.10.
To install on earlier releases of Ubuntu you will need to install from source.

Install prerequisites::

    sudo apt-get install g++ python3 python3-dev python3-pip git gfortran libzmq-dev
    sudo apt-get install python3-pyqt5 python3-pyqt4 python3-matplotlib python3-requests python3-numpy python3-scipy python3-yapsy
    sudo apt-get install libblas3gf libblas-dev liblapack3gf liblapack-dev libatlas3gf-base

Build and install latest matplotlib::

    # Ensure that you have source code repositories enabled
    sudo apt-get build-dep python-matplotlib

    git clone git://github.com/matplotlib/matplotlib.git
    cd matplotlib
    sudo python3 setup.py install
    cd -
    rm -r matplotlib

Finally, let's install your develop version of Pantomx::

    sudo pip3 install openpyxl==1.8.6 pyzmq scikit-learn
    cd pantomx
    sudo python3 setup.py develop
    cd -

Note that aside from python3-pyqt5 you can also install the other packages using pip3 (the names on PyPi are
the same as for the packages minus the python3- prefix). Once installation of the above has completed you're ready to go.

To run Pathomx from the command line, change to the cloned git folder and then enter::

    python Pathomx.py

.. _Github: http://github.com/pathomx/pathomx
.. _useful guide: https://help.github.com/articles/set-up-git

.. _Qt4: https://qt-project.org/downloads
.. _Qt5: https://qt-project.org/downloads

.. PyQt4_: http://www.riverbankcomputing.co.uk/software/pyqt/download
.. PyQt5_: http://www.riverbankcomputing.co.uk/software/pyqt/download5

.. _NMRGlue: http://code.google.com/p/nmrglue/downloads/list?q=label:Type-Installer
.. _Graphviz: http://graphviz.org/
.. _Python download site: http://www.python.org/getit/
.. _the Pythonlibs library: http://www.lfd.uci.edu/~gohlke/pythonlibs/
.. _NumPy: http://www.lfd.uci.edu/~gohlke/pythonlibs/#numpy
.. _SciPy: http://www.lfd.uci.edu/~gohlke/pythonlibs/#scipy
.. _Scikit-Learn: http://www.lfd.uci.edu/~gohlke/pythonlibs/#scikit-learn
.. _Matplotlib: http://www.lfd.uci.edu/~gohlke/pythonlibs/#matplotlib
.. _Pip: http://www.lfd.uci.edu/~gohlke/pythonlibs/#pip
.. _IPython: http://www.lfd.uci.edu/~gohlke/pythonlibs/#ipython
.. _pyzmq: http://www.lfd.uci.edu/~gohlke/pythonlibs/#pyzmq

.. _Homebrew: http://brew.sh/

