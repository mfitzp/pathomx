# We're using a development version of IPython so for now we need to get it via git
cwd=$(pwd)
mkdir /tmp/pathomx-install
cd /tmp/pathomx-install
git clone --recursive https://github.com/ipython/ipython.git
cd ipython
sudo pip3 install --upgrade .
rm -rf /tmp/pathomx-install
cd $cwd

# Now install all other dependencies via apt-get or pip
sudo apt-get install python3-pyqt4 python3-numpy python3-scipy python3-yapsy python3-matplotlib python3-requests python3-pip ipython3 ipython3-qtconsole ipython3-notebook
sudo pip3 install --upgrade pandas dill pyqtconfig mplstyler mistune biocyc jsonschema

# The following may error, but is not essential
sudo pip3 install scikits.learn 
