# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# Import PyQt5 classes
from PyQt5.QtCore import Qt, QObject, QRunnable, pyqtSignal, pyqtSlot

import sys,traceback

class WorkerSignals(QObject):
    '''
    Defines the signals available from a running worker thread.
    
    Supported signals are:
    
    finished
        No data
        
    error
        `tuple` (exctype, value, traceback.format_exc() )
        
    result
        `dict` data returned from processing
        
    status
        `str` one of standard status flag message types
        
    '''        
    finished = pyqtSignal()
    error = pyqtSignal(tuple)
    result = pyqtSignal(dict)
    status = pyqtSignal(str)
    
class Worker(QRunnable):
    '''
    Worker thread
    
    Inherits from QRunnable to handler worker thread setup, signals and wrap-up.
    '''          
    def __init__(self, callback, *args, **kwargs):
        super(Worker, self).__init__()
        # Store constructor arguments (re-used for processing)
        self.callback = callback
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self):
        # Retrieve args/kwargs here; and fire processing using them
        try:
            result = self.callback(*self.args, **self.kwargs)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit( (exctype, value, traceback.format_exc() ) )
        else:
            self.signals.result.emit(result) # Return the result of the processing
        finally:                
            self.signals.finished.emit() # Done
                    
    # Stub to be over-wridden on subclass
    def process(self, *args, **kwargs):
        return False        

    
    
