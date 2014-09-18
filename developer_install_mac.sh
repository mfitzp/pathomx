#!/bin/sh

source ~/.bash_profile
ruby -e "$(curl -fsSL https://raw.github.com/Homebrew/homebrew/go/install)"

brew install python pyqt hdf5 libpng zeromq freetype pandoc
brew link --overwrite python

pip install --upgrade numpy scipy pandas yapsy requests matplotlib scikit-learn pyqtconfig mplstyler
pip install --upgrade ipython[all]

#brew install graphviz
#pip install pydot nmrglue gpml2svg icoshift biocyc metaviz
