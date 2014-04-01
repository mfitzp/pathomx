from __future__ import unicode_literals
import sys

USE_PYQT = None

if 'PyQt5' in sys.modules:
    USE_PYQT = 5
elif 'PyQt4' in sys.modules:
    USE_PYQT = 4
else:
    try:
        import PyQt5
        USE_PYQT = 5
    except ImportError:
        try:
            import PyQt4
            USE_PYQT = 4
        except ImportError:
            USE_PYQT = None
        
if USE_PYQT == 5:

    # Import PyQt5 classes accessible in elsewhere through
    # from qt import *
    from PyQt5.QtGui import *
    from PyQt5.QtCore import *
    from PyQt5.QtWebKit import *
    from PyQt5.QtNetwork import *
    from PyQt5.QtWidgets import *
    from PyQt5.QtWebKitWidgets import *
    from PyQt5.QtPrintSupport import *

elif USE_PYQT == 4:

    # Import PyQt4 classes accessible in elsewhere through
    # from qt import *
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *
    from PyQt4.QtWebKit import *
    from PyQt4.QtNetwork import *

    
    



    
