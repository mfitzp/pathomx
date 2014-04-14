# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
logging.debug('Loading resources.py')

import time
import os

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
    import rpy2.robjects as robjects
except:
    robjects = False

from .custom_exceptions import PathomxExternalResourceUnavailableException, PathomxExternalResourceTimeoutException
from .utils import which

class AbstractResource(object):
    '''
    An abstract resource handler.
    
    Resource handlers manage a given external resource (e.g. MATLAB, R) that are made 
    available for tools. In particular they handle managing instances of single-instance
    objects (multi-instance later) and gracefully rejecting when these are not available.
    
    Plugins that depend on a resource that is not available will not be made available 
    in the editor.
    '''
    interface = None
    
class MATLABResource(AbstractResource):
    
    exec_path = 'matlab'
    _is_available = None

    def init(self):
        if self.interface == None:
            try:
                self.interface = mlabwrap.init( which(self.exec_path) )
            except IOError:
                self.interface._mlab = None # Complete shutdown            
                self.interface = mlabwrap.init( which(self.exec_path) )

        return self.interface

    @property
    def is_available(self):
        if self._is_available == None:
            self._is_available = which(self.exec_path) != None
        return self._is_available
        
    def stop(self):
        if self.interface != None:
            try:
                self.interface._do('quit force')
            except:
                pass
            self.interface = None

        # We don't re-init as we'll get there automatically when needed            
        self._is_available = None # Leave unknown til next needed

    def set_exec_path(self, newpath):
        if self.exec_path != newpath:
            self.exec_path = newpath
            self.stop()

           
class RResource(AbstractResource):
    
    @property
    def is_available(self):
        return robjects != False       
    
    
matlab = MATLABResource()
r = RResource() 

lock_id = 0

class AbstractLock(object):

    lock = False
        
    def wait_for_lock(self):
        if self.lock_resource.is_available == False:
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
    lock_resource = matlab

r_lock = False       
class RLock(AbstractLock):
    lock = r_lock
    lock_resource = r


