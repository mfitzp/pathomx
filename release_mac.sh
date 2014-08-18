#!/bin/sh
#python setup.installers.py bdist_mac --qt-menu-nib=/usr/local/Cellar/qt5/5.2.1/plugins/platforms/
python setup.mac.py py2app

# https://bitbucket.org/ronaldoussoren/py2app/issue/26/bundled-python-executable-not-working
cp /Library/Frameworks/Python.framework/Versions/2.7/Resources/Python.app/Contents/MacOS/Python ./dist/Pathomx.app/Contents/MacOS/python
install_name_tool -change /Library/Frameworks/Python.framework/Versions/2.7/Python @executable_path/../Frameworks/Python.framework/Versions/2.7/Python dist/Pathomx.app/Contents/MacOS/python
