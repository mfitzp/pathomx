# -*- coding: utf-8 -*-
# Experimental data manager
# Loads a csv data file and extracts key information into usable structures for analysis

# Import PyQt5 classes
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWebKit import *
from PyQt5.QtNetwork import *
from PyQt5.QtWidgets import *
from PyQt5.QtWebKitWidgets import *
from PyQt5.QtPrintSupport import *

import os, sys, re, base64
import numpy as np

import operator

from copy import copy, deepcopy

# DataManager allows a view/analysis class to handle control of consumable data sources
class DataManager( QObject ):

    # Signals
    source_updated = pyqtSignal()

    def __init__(self, parent, view, *args, **kwargs):
        super(DataManager, self).__init__( *args, **kwargs)

        self.m = parent
        self.v = view

        self.consumer_defs = [] # Holds data-consumer definitions 
        self.consumes = [] # Holds list of data objects that are consumed

        self.provides = [] # A list of dataset objects available from this manager

        self.i = {} # Input
        self.o = {} # Output

        
    
    def addo(self, target, dso=None, provide=True):
        if dso==None:
            dso = DataSet( manager=self)
            
        self.o[ target ] = dso
        if provide:
            self.provides.append( dso )
        
        # If we're in a constructed view we will have a reference to the global data table
        # This feels a bit hacky
        try:
            self.m.datasets.append( dso )
        except:
            pass
            
        
        
    def remove_data(self, data ):
        self.stop_providing( data )
        self.provides.remove( data )

    # Handle consuming of a data object; assignment to internal tables and processing triggers (plus child-triggers if appropriate)
    # Build import/hooks for this consumable object (need interface logic here; standardise where things will end up)
    def can_consume(self, data):
        for consumer_def in self.consumer_defs:
            if consumer_def.can_consume(data):
                return True
        return False
        
    # Check if a manager has a consumable data object
    def has_consumable(self, manager):
        for data in manager.provides:
            if self.can_consume( data ):
                return True
        return False
        
    def consume(self, data):
        for consumer_def in self.consumer_defs:
            if consumer_def.can_consume(data):
                # Handle import/hook building for this consumable object (need interface logic here; standardise)# Handle import/hook building for this consumable object (need interface logic here; standardise)
                # FIXME: Handle possibility that >1 consumer definition will match; provide options OR first only (unless pre-existing?!)
                # Register this as an attribute in the current object
                self.i[ consumer_def.target ] = data
                self.consumes.append( data )
                data.consumers.append( self )
                return True
                
    def consume_from_manager(self, manager):
        for data in manager.provides:
            if self.consume( data ):
                return True # Stop if we manage it
                
    def consume_any_of(self, data_l):
        for dso in data_l:
            if self.consume(dso):
                return True
            
    def provide(self, target):
        self.provides.append( self.o[target] )
                
    def stop_consuming(self, target ):
        self.consumes.remove( self.i[ target ])
        del self.i[ target ]

    def stop_providing(self, data):
        data.remove_all_consumers()
        self.provides.remove(data)
        

    def refresh_consumed_data(self):
        self.source_updated.emit() # Trigger recalculation

    def refresh_consumers(self):
        managers = []
        [ managers.extend( dso.consumers ) for dso in self.provides ]
        print managers
        for manager in set(managers):
            manager.refresh_consumed_data()
        # Data object is the object that has refreshed
        #self.refresh() # Global data recalculate



# Provider/Consumer classes define data availability and requirements for a given dataManager object.
# Object can accept input from any Provider that offers it's Consumer requirements; process it; and then provide it downstream
# view it's own Provider class definition.

def at_least_one_element_in_common(l1, l2):
    return len( set(l1) & set(l2) ) > 0

class DataDefinition( QObject ):

    cmp_map = {
         '<': operator.lt,
        '<=': operator.le,
         '=': operator.eq,
        '!=': operator.ne,
         '>': operator.gt,
        '>=': operator.ge,
        'aloeic': at_least_one_element_in_common,
    }
    
    def __init__(self, target, definition):
        # Store consumer/provider description as entity entries from dict
        self.target = target # Target attribute for imported data - stored under this in dataManager
                             # When assigning data; should check if pre-existing and warn to overwrite (or provide options)
        self.definition = definition


    def get_cmp_fn(self,s):
        if type( s ) == list:
            return self.cmp_map['aloeic'], s
            
        s = str(s) # Treat all input as strings
        for k,v in self.cmp_map.items():
            if k in s:
                return v, s.replace(k,'')
        return self.cmp_map['='], s
        
    def can_consume(self, data):
        # Prevent self-consuming (inf. loop)
        #FIXME: Need a reference to the manager in self for this to work? Add to definition?
        #if data.manager == self:
        #    print "Don't consume oneself."
        #    return False
        # Retrieve matching record in provider; see if provides requirement
        # if we fail at any point return False
        # self.interface holds the interface for this 
        # Test each option; if we get to the bottom we're alright!
        print "CONSUME? [%s]" % data.name
        print self.definition
        for k,v in self.definition.items():
            t = getattr( data, k )
            print " COMPARE: %s %s %s" % (k,v,t)
            # t = (1d,2d,3d)
            # Dimensionality check
            if len(v) != len(t):
                print "  dimensionality failure %s %s" %( len(v), len(t) )
                return False
                
            for n, cr in enumerate(v):
                if cr == None: # No restriction on this definition
                    print '  pass'
                    continue 

                cmp_fn, crr = self.get_cmp_fn( cr )
                try:
                    crr = type(t[n])(crr) 
                except:
                    # If we can't match equivalent types; it's nonsense so fail
                    print "  type failure %s %s" %( type(t[n]), type(crr) )
                    return False

                "  comparison %s %s %s = %s" %( t[n], cmp_fn, crr, cmp_fn( t[n], crr))
                if not cmp_fn( t[n], crr):
                    print "  comparison failure %s %s %s" %( t[n], cmp_fn, crr )
                    return False                                
            
        print " successful"
        return True


# QAbstractTableModel interface to loaded dataset. 
class QTableInterface(QAbstractTableModel):
    def __init__(self, parent, *args, **kwargs):        
        super(QTableInterface, self).__init__(*args, **kwargs)
        self.d = parent

    def rowCount(self, parent):
        return self.d.shape[0]

    def columnCount(self, parent):
        return self.d.shape[1]
        
    def data(self, index, role):
        if not index.isValid():
            return None
        elif role != Qt.DisplayRole:
            return None
            
        return float( self.d.data[ index.row(), index.column()] )
            
    def headerData(self, col, orientation, role):
        
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.d.labels[1][col]
        elif orientation == Qt.Vertical and role == Qt.DisplayRole:
            return self.d.labels[0][col]
        else:
            return None
        
    def sort(self, col, order):
        """sort table by given column number col"""
        self.emit(SIGNAL("layoutAboutToBeChanged()"))
        self.table = sorted(self.table,
        key=operator.itemgetter(col))
        if order == Qt.DescendingOrder:
            self.table.reverse()
            self.emit(SIGNAL("layoutChanged()"))


#### FIXME: Other data managers may need to be provided e.g. for 2D/3D datasets. Interfaces should be consistent.
## TODO: Chaining and update notification/re-processing 

class DataSet( QObject ):
    def __init__(self, manager=None, size=(0,), name='', description='', *args, **kwargs):

        # DataSet must be assigned to a data manager for inter-object updates/communication to work
        self.manager = manager
        
        self.consumers = [] # List of managers that consume this data object (access; but dont affect)
    
        self.name = name
        self.description = description
        self.type = None
        self.empty(size)
        
        # DEFAULT INTERFACE SETS 
        # Data managers can provide >1 of these, but must handle updating of each from the other
        # e.g. if a table is updated, it must re-write the dataset representation
        # Helpers for doing this should ideally be implemented
        self.interfaces = [] # Interface interface table; for triggering refresh on update
        
        self.register_interface( 'as_table', QTableInterface(self) )
        # self.as_table = #

        # MetaData derived from data formats, inc. statistics etc. [informational only; not prescribed]
    
    # Wipes the data and metadata from the object; but does not alter references to it (or name/description)
    def empty(self, size=(0,)):

        self.labels = []
        self.entities = []
        self.scales = []
        self.classes = []
        
        for s in size:
            self.labels.append( [''] * s )
            self.entities.append( [None] * s )
            self.scales.append( [None] * s )
            self.classes.append( [None] * s ) 
        
        self.data = np.zeros( size ) #np.array([]) # Data container  
        
        self.metadata = {}
              
    
    def import_data(self, dso):
        
        self.name = copy(dso.name)
        self.description = copy(dso.description)
        self.type = copy(dso.type)

        self.labels = [x for x in dso.labels] 
        self.entities = [x for x in dso.entities]
        self.scales = [x for x in dso.scales]
        self.classes = [x for x in dso.classes]

        self.data  = deepcopy(dso.data)
        

    def register_interface(self, interface_name, interface):
        self.__dict__[ interface_name ] = interface
        self.interfaces.append( interface )        
        
    # Helper functions for describing this dataset object; they summarise the data held in a consistent way
    # naming conventionis _l for lists; _n for 'number of' e.g. class_l holds a list of all classes (in each dimension)
    # class_n holds the number of classes (in each dimension). All accessible as properties

    def _l(self, ls):
        return [ list( set( l ) ) for l in ls ]

    def _n(self, ls):
        return [len(l) for l in self._l(ls)]
        
    def _t(self, ls):
        # Entities_l returns [EntityA, EntityB],[EntityC, EntityC]
        # Collapse for each dimension    
        et = []
        for el in self._l( ls ):
            et.append( list( set([e.__class__.__name__ for e in el ] ) ) )
        return et
    
    # List of unique labels, entities, classes
    @property
    def labels_l(self):
        return self._l( self.labels)

    @property
    def entities_l(self):
        return self._l( self.entities)

    @property
    def classes_l(self):
        return self._l( self.classes)

    # Number of unique labels, entities, classes        
    @property
    def labels_n(self):
        return self._n( self.labels)

    @property
    def entities_n(self):
        return self._n( self.entities)

    @property
    def classes_n(self):
        return self._n( self.classes)        

    # Range description (min/max) for scales
    @property
    def scales_n(self):
        return self._n( self.scales)        
    
    @property
    def scales_r(self):
        return [ (min(s), max(s)) for s in self.scales if s is not None ]
            
    @property
    def scales_t(self):
        return self._t( self.scales )  
            
    # Entity types
    @property
    def entities_t(self):
        return self._t( self.entities )  
        
    @property
    def shape(self):
        return self.data.shape
        
    @property
    def dimensions(self):
        return len(self.shape)
    
    def add_consumer(self, manager):
        self.consumers.append( manager )
        
    def remove_consumer(self, manager):
        manager.stop_consuming( self )
        try:
            del self.consumers[manager]
        except:
            pass        
    
    def remove_all_consumers(self):
        for dso in self.consumers:
            self.remove_consumer( dso.manager )

    def refresh_consumers(self):
        # Perform calculations again
        for consumer in self.consumers:
            consumer.refresh_consumed_data()
        
    # Return data table np.array containing supplied classes as grouped means
    # classes is a list, d is dimension to collapse
    # FIXME: This function only works for dim = 0
    def as_class_groups(self, d=0, fn=np.ma.mean, classes=None ):

        # Collapse the classes to a set 
        if classes:
            classmatch = list( set( self.classes[d] ) & set( classes ) ) # Matched the classes
        else:
            classmatch = self.classes_l
        
        sizeR = list( self.shape )
        sizeR[d] = len(classmatch) # Resizing
        
        dso = DataSet()
        dso.import_data( self ) # We'll overwrite the wrongly dimensional data anyway
        dso.data = np.zeros(sizeR)
        
        for n,c in enumerate( classmatch):    
            mask = np.array( [True if c in classmatch else False for c in self.classes[d] ] )
            masked_data = np.ma.array(self.data, mask=np.repeat(mask,self.data.shape[d]))    
            
            calculated_d = fn( masked_data, axis=d)
            dso.data[n,:] = calculated_d
                        
        dso.classes[d] = classmatch
        dso.labels[d] = classmatch

        return dso        

    def as_filtereXXd(self, d=0, classes=None, labels=None, scales=None ):

        dso = DataSet()
        dso.import_data( self ) # We'll overwrite the wrongly dimensional data anyway

        # Build masks
        for match,matcht in [
            (classes,self.classes[d]),
            (labels, self.labels[d]),
            (scales, self.scales[d])]:
            if match == None:
                continue
            mask = np.array( [True if t in match else False for t in matcht ] )
            matcht = [t for t in matcht if t in match]

            dso.data = np.ma.array(dso.data, mask=np.repeat(mask,self.data.shape[d]))    

        print dso.classes
        print dso.labels
        print dso.scales
        print dso.data
        return dso    
        
    # Compress the dataset object in 'd' dimension; 
    # being compressed in d dimension by the fn function
    # Compression only if classes, labels and entities are equal. Scale is treated the same as data (fn function)
    def as_compressed(self, fn=np.mean, dim=1):
    
        print "Entities before compression (own):",self.entities
        dso = DataSet()
        dso.import_data( self ) # We'll overwrite the wrongly dimensional data anyway
        print "Entities before compression (copied):",dso.entities

        # Build combined (class, label, entity) tuples as matching value
        identities = [ (c, l, e) for c,l,e in zip( dso.classes[dim], dso.labels[dim], dso.entities[dim]) ]
        unique = set( identities )
        
        old_shape, new_shape = dso.data.shape, list( dso.data.shape )
        new_shape[ dim ] = len( unique )
        print 'Reshape from %s to %s' % (old_shape,new_shape)
        dso.crop( new_shape )
        
        for n,u in enumerate( unique ):
            dso.classes[dim][n], dso.labels[dim][n], dso.entities[dim][n] = u
            # Build mask against the original identities file
            mask = np.array([ True if u == i else False for i in identities ])
            # Mask of T F T T T F if the identity at this position matches our unique value
            # Apply this mask to the data; then use our function to reduce it in our dimension
            #mask = np.repeat(mask, old_shape[dim])
            #mask= np.reshape( mask, old_shape )
            data = self.data[ :, mask] #np.ma.array(self.data, mask=mask)
            compressed_data = fn( data, axis=dim) #, keepdims=True )
            dso.data[:,n] = compressed_data


        print "Entities after compression:",dso.entities

        return dso
    
    # Filter data by labels/entities on a given axis    
    def as_filtered(self, dim=1, scales=None, labels=None, entities=None):
        
        print 'Entities before filtering:',self.entities
        dso = DataSet()
        dso.import_data( self ) # We'll overwrite the wrongly dimensional data anyway

        old_shape, new_shape = dso.data.shape, list( dso.data.shape )

        # Build consecutive mask
        iter = [
            (dso.entities[dim], entities),
            (dso.labels[dim], labels),
            (dso.scales[dim], scales),
        ]
        
        mask = np.array([ True for i in dso.entities[dim] ])
        
        for dis,ois in iter:
            if ois == None:
                continue
            imask = np.array([ True if di not in ois else False for di in dis ]) 
            mask[imask] = False
            
        new_shape[dim] = list(mask).count(True) # New size of it

        print 'Reshape from %s to %s' % (old_shape,new_shape)

        dso.crop( new_shape )
        dso.data = self.data[ : ,mask ]

        dso.classes[dim] = [v for t,v in zip( mask, self.classes[dim]) if t]
        dso.entities[dim] = [v for t,v in zip( mask, self.entities[dim]) if t]
        dso.labels[dim] = [v for t,v in zip( mask, self.labels[dim]) if t]
        dso.scales[dim] = [v for t,v in zip( mask, self.scales[dim]) if t]

        return dso        
        
    # DESTRUCTIVE resizing of the current dso
    # All entries are simply clipped to size
    def crop(self,shape):

        final_shape = list( self.data.shape )
        for d, s in enumerate( shape ):
            if s<len(self.labels): # Only allow crop
                self.labels[d] = self.labels[d][:s]
                self.entities[d] = self.entities[d][:s]
                self.scales[d] = self.scales[d][:s]
                final_shape[d] = shape[d]
                
        self.data.resize( final_shape )
    
    
    
    
    
