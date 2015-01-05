# We're using a development version of IPython so for now we need to get it via git
cwd=$(pwd)
mkdir /tmp/pathomx-install
cd /tmp/pathomx-install
git clone --recursive https://github.com/ipython/ipython.git
cd ipython
sudo pip install --upgrade .
rm -rf /tmp/pathomx-install
cd $cwd

# Now install all other dependencies via apt-get or pip
sudo apt-get install python-qt4 python-numpy python-scipy python-yapsy python-requests python-matplotlib python-scikits-learn python-pip ipython ipython-notebook ipython-notebook-common ipython-qtconsole python-pygments
sudo pip install --upgrade pandas dill pyqtconfig mplstyler mistune biocyc pydot jsonschema

