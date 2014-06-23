# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
logging.debug('Loading threads.py')

# Import PyQt5 classes
from .qt import *
import sys
import traceback
from copy import deepcopy

threadpool = QThreadPool()
threadpool.setExpiryTimeout(1000)


def run(fn, success_callback=None, error_callback=None, *args, **kwargs):

    worker = Worker(fn, *args, **kwargs)
    if success_callback:
        worker.signals.success.connect(success_callback, Qt.QueuedConnection)
    if error_callback:
        worker.signals.error.connect(error_callback, Qt.QueuedConnection)

    threadpool.start(worker)
    logging.info("Started new thread (current %d/%d active threads)" % (threadpool.activeThreadCount(), threadpool.maxThreadCount()))


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
    success = pyqtSignal()
    error = pyqtSignal(tuple)


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

    def __init__(self, fn, *args, **kwargs):
        super(Worker, self).__init__()
        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()
        self.setAutoDelete(True)

    @pyqtSlot()
    def run(self):
        '''
        Initialise the runner function with passed args, kwargs.
        '''
        # Retrieve args/kwargs here; and fire processing using them
        try:
            result = self.fn(*self.args, **self.kwargs)
        except:
            # Error callback
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((value, traceback.format_exc()))
        else:
            # Success callback; deepcopy so we're not keeping a ref
            self.signals.success.emit()
