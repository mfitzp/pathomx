# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import time
import logging
'''
Interfaces to MATLAB, R and any other resources that are single-threaded and require
queuing before running. If defined interfaces are added as dependencies of jobs
the job will wait until the resource is available. The defined managers handle resource
allocation and locking.
'''

try:
    import mlabwrap
except:
    mlabwrap = False
    
try:
    import rpy2
except:
    rpy2 = False

from custom_exceptions import PathomxExternalResourceUnavailableException, PathomxExternalResourceTimeoutException

lock_id = 0

class AbstractLock(object):

    lock = False
        
    def wait_for_lock(self):
        if self.lock_object == False:
            raise PathomxExternalResourceUnavailableException
        global lock_id
        lock_id += 1
        
        logging.debug('Waiting for lock on %s' % self.__class__)
        # Loop until we have lock; this approach ensures we don't give to the lock simultaneously to two tools
        for n in range(0, 15): # Wait for maximum 15secs for completion
            if self.lock == False:
                self.lock = lock_id
                break
            time.sleep(1)
        print self.lock    
        if self.lock != lock_id:                    
            logging.debug('Lock failed on %s' % self.__class__)
            raise PathomxExternalResourceTimeoutException
        logging.debug('Got lock on %s' % self.__class__)

    def release_lock(self):
        logging.debug('Lock released on %s' % self.__class__)
        self.lock = False
        
matlab_lock = False
class MATLABLock(AbstractLock):
    lock = matlab_lock
    lock_object = mlabwrap

r_lock = False       
class RLock(AbstractLock):
    lock = r_lock
    lock_object = rpy2
