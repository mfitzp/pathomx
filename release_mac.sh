#!/bin/sh
python setup.installers.py bdist_mac --qt-menu-nib=/usr/local/Cellar/qt5/5.2.1/plugins/platforms/
value=`cat VERSION`
echo "$value"

cd /usr/local/lib/python2.7/site-packages
cp -r jsonschema ~/repos/pathomx/build/Pathomx-3.0.0a3.app/Contents/MacOS

