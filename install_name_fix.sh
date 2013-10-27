install_name_tool -change /usr/local/Cellar/qt5/5.1.1/lib/QtPrintSupport.framework/Versions/5/QtPrintSupport @executable_path/QtPrintSupport build/metapath-0.9.0.app/Contents/MacOS/platforms/libqcocoa.dylib
install_name_tool -change /usr/local/Cellar/qt5/5.1.1/lib/QtWidgets.framework/Versions/5/QtWidgets @executable_path/QtWidgets build/metapath-0.9.0.app/Contents/MacOS/platforms/libqcocoa.dylib
