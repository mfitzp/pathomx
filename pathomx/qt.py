from __future__ import unicode_literals
import sys
import os
import logging

PYSIDE = 0
PYQT4 = 1
PYQT5 = 2

USE_QT_PY = None

# ReadTheDocs
ON_RTD = os.environ.get('READTHEDOCS', None) == 'True'
if not ON_RTD:

    QT_API_ENV = os.environ.get('QT_API')

    ETS = dict(pyqt=PYQT4, pyqt5=PYQT5, pyside=PYSIDE)

    # Check environment variable
    if QT_API_ENV and QT_API_ENV in ETS:
        USE_QT_PY = ETS[QT_API_ENV]

    # Check if one already importer
    elif 'PyQt4' in sys.modules:
        USE_QT_PY = PYQT4
    elif 'PyQt5' in sys.modules:
        USE_QT_PY = PYQT5
    else:
        # Try importing in turn
        try:
            import PyQt5
            USE_QT_PY = PYQT5
        except:
            try:
                import PyQt4
                USE_QT_PY = PYQT4
            except ImportError:
                try:
                    import PySide
                    USE_QT_PY = PYSIDE
                except:
                    pass

    # Import PyQt classes accessible in elsewhere through from qt import *
    if USE_QT_PY == PYQT5:
        from PyQt5.QtGui import *
        from PyQt5.QtCore import *
        from PyQt5.QtWebKit import *
        from PyQt5.QtNetwork import *
        from PyQt5.QtWidgets import *
        from PyQt5.QtWebKitWidgets import *
        from PyQt5.QtPrintSupport import *

    elif USE_QT_PY == PYSIDE:
        from PySide.QtGui import *
        from PySide.QtCore import *
        from PySide.QtNetwork import *

        pyqtSignal = Signal


    elif USE_QT_PY == PYQT4:
        import sip
        sip.setapi('QString', 2)
        sip.setapi('QVariant', 2)
        from PyQt4.QtGui import *
        from PyQt4.QtCore import *
        from PyQt4.QtWebKit import *
        from PyQt4.QtNetwork import *

        QFileDialog.getOpenFileName_ = QFileDialog.getOpenFileName
        QFileDialog.getSaveFileName_ = QFileDialog.getSaveFileName


        class QFileDialog(QFileDialog):
            @staticmethod
            def getOpenFileName(*args, **kwargs):
                return QFileDialog.getOpenFileName_(*args, **kwargs), None

            @staticmethod
            def getSaveFileName(*args, **kwargs):
                return QFileDialog.getSaveFileName_(*args, **kwargs), None

    # Create a Qt application
    app = QApplication(sys.argv)
    app.setStyle('fusion')
    app.setOrganizationName("Pathomx")
    app.setOrganizationDomain("pathomx.org")
    app.setApplicationName("Pathomx")

else:

    # For Qt a Mock in the conf.py will not work for ReadTheDocs so we have to Mock
    # separately here. Any class used in Qt must end up here and accessed attributes added.

    class QMockObject(object):
        def __init__(self, *args, **kwargs):
            super(QMockObject, self).__init__()

        def __call__(self, *args, **kwargs):
            return None


    class QApplication(QMockObject):
        pass


    class pyqtSignal(QMockObject):
        pass


    class pyqtSlot(QMockObject):
        pass


    class QObject(QMockObject):
        pass


    class QAbstractItemModel(QMockObject):
        pass


    class QModelIndex(QMockObject):
        pass


    class QTabWidget(QMockObject):
        pass


    class QWebPage(QMockObject):
        pass


    class QTableView(QMockObject):
        pass


    class QWebView(QMockObject):
        pass


    class QAbstractTableModel(QMockObject):
        pass


    class Qt(QMockObject):
        DisplayRole = None


    class QWidget(QMockObject):
        pass


    class QPushButton(QMockObject):
        pass


    class QDoubleSpinBox(QMockObject):
        pass


    class QListWidget(QMockObject):
        pass


    class QDialog(QMockObject):
        pass


    class QSize(QMockObject):
        pass


    class QTableWidget(QMockObject):
        pass


    class QMainWindow(QMockObject):
        pass


    class QTreeWidget(QMockObject):
        pass


    class QAbstractItemDelegate(QMockObject):
        pass


    class QColor(QMockObject):
        pass


    class QGraphicsItemGroup(QMockObject):
        pass


    class QGraphicsItem(QMockObject):
        pass


    class QGraphicsPathItem(QMockObject):
        pass


    class QGraphicsTextItem(QMockObject):
        pass


    class QGraphicsRectItem(QMockObject):
        pass


    class QGraphicsScene(QMockObject):
        pass


    class QGraphicsView(QMockObject):
        pass

    app = None
