#!/bin/sh

source ~/.bash_profile
ruby -e "$(curl -fsSL https://raw.github.com/Homebrew/homebrew/go/install)"

brew install python pyqt pandoc hdf5 libpng zeromq freetype pandoc

pip install numpy scipy pandas yapsy requests matplotlib scikit-learn dill pyqtconfig mplstyler
pip install ipython[all]

#brew install graphviz
#pip install pydot nmrglue gpml2svg icoshift biocyc metaviz
