# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
logging.debug('Loading threads.py')

# Import PyQt5 classes
from .qt import *
import sys
import traceback


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

    :param callback: The function callback to run on this worker thread. Supplied args and 
                     kwargs will be passed through to the runner.
    :type callback: function
    :param args: Arguments to pass to the callback function
    :param kwargs: Keywords to pass to the callback function

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
        '''
        Initialise the runner function with passed args, kwargs.
        '''

        # Retrieve args/kwargs here; and fire processing using them
        try:
            result = self.callback(*self.args, **self.kwargs)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)  # Return the result of the processing
        finally:
            self.signals.finished.emit()  # Done

    # Stub to be over-wridden on subclass
    def process(self, *args, **kwargs):
        return False
