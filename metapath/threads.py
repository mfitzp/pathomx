# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# Import PyQt5 classes
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWebKit import *
from PyQt5.QtNetwork import *
from PyQt5.QtWidgets import *
from PyQt5.QtWebKitWidgets import *
from PyQt5.QtPrintSupport import *

class Worker(QObject):
    
    def __init__(self, *args, **kwargs):
        super(Worker, self).__init__()
        # Store constructor arguments (re-used for processing)
        self.args = args
        self.kwargs = kwargs

    @pyqtSlot()
    def run(self):
        # Retrieve args/kwargs here; and fire processing using them
        result = self.process(*self.args, **self.kwargs)
        try:
            result = self.process(*self.args, **self.kwargs)
        except:
            self.error.emit() #finished.emit()
            return False

        self.result.emit(result) # Return the result of the processing
        self.finished.emit() # Done
                    
    # Stub to be over-wridden on subclass
    def process(self, *args, **kwargs):
        return False        
        
    finished = pyqtSignal()
    error = pyqtSignal()
    result = pyqtSignal(dict)