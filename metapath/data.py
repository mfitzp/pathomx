# -*- coding: utf-8 -*-
# Experimental data manager
# Loads a csv data file and extracts key information into usable structures for analysis

# Import PyQt5 classes
from PyQt5.QtGui import *
from PyQt5.QtCore import *
#from PyQt5.QtWebKit import *
from PyQt5.QtNetwork import *
from PyQt5.QtWidgets import *
#from PyQt5.QtWebKitWidgets import *
from PyQt5.QtPrintSupport import *

import os, sys, re, base64
import numpy as np

from collections import defaultdict
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

        self.i = {} # Input: dict of 'interface' tuples: (origin,interface)
        self.o = {} # Output

        self.watchers = defaultdict( set ) # List of watchers on each output interface
        
    # Get a dataset through input interface id;
    # This provides indirect access to a copy of the object (local link in self.i = {})
    def get(self, interface):
        if interface in self.i:
            # Add ourselves to the watcher for this interface
            dso = self.i[interface]
            dso.manager.watchers[ dso.manager_interface ].add( self )
            return deepcopy( self.i[interface] )
        return False
        
    def unget(self, interface):
        if interface in self.i:
            dso = self.i[interface]
            dso.manager.watchers[ dso.manager_interface ].remove( self )
    
    # Output a dataset through output interface id
    # Advertise object for consumption; needs to handle notification of all consumers
    # independent of the object itself (so can overwrite instead of warping)
    def put(self, interface, dso, update_consumers = True):
        if interface in self.o:
            self.o[interface].import_data(dso)
            self.o[interface].manager = self
            self.o[interface].manager_interface = interface
            # Update consumers / refresh views
            self.o[interface].as_table.refresh()            
            self.notify_watchers(interface)
            return True
        return False
            
    def add_interface(self, interface, dso=None):
        if dso==None:
            dso = DataSet(manager=self)
            
        self.o[ interface ] = dso
        
        # If we're in a constructed view we will have a reference to the global data table
        # This feels a bit hacky
        try:
            self.m.datasets.append( dso )
        except:
            pass
        
    def remove_interface(self, interface):
        if interface in self.o:
            watchers = self.watchers[interface]
            del self.o[ interface ]
            self.notify_watchers( interface )
            del self.watchers[ interface ]            
            return True
        return False
        
            
    def notify_watchers(self, interface):
        for manager in self.watchers[interface]:
            manager.source_updated.emit()
        
    # Handle consuming of a data object; assignment to internal tables and processing triggers (plus child-triggers if appropriate)
    # Build import/hooks for this consumable object (need interface logic here; standardise where things will end up)
    def can_consume(self, data, consumer_defs=None):
        if data.manager == self:
            return False

        if consumer_defs == None:
            consumer_defs = self.consumer_defs

        for consumer_def in consumer_defs:
            if consumer_def.can_consume(data):
                return True
        return False
        
    def can_consume_which_of(self, datalist, consumer_defs=None):
        which = []
        for data in datalist:
            if self.can_consume(data, consumer_defs):
                which.append(data)
        return which
        
    # Check if a manager has a consumable data object
    def has_consumable(self, manager):
        for data in manager.provides:
            if self.can_consume( data ):
                return True
        return False
        
    def _consume(self, data, consumer_defs=None):
        # Handle import/hook building for this consumable object (need interface logic here; standardise)# Handle import/hook building for this consumable object (need interface logic here; standardise)
        # FIXME: Handle possibility that >1 consumer definition will match; provide options OR first only (unless pre-existing?!)
        # Register this as an attribute in the current object
        if data.manager == self:
            return False
        
        if consumer_defs == None:
            consumer_defs = self.consumer_defs
            
        for consumer_def in consumer_defs:
            if consumer_def.can_consume(data):
                self.i[ consumer_def.target ] = data
                self.consumes.append( data )
                data.consumers.append( self )
                return True    
        
    def consume(self, data):
        if self._consume(data):
            self.source_updated.emit()
            return True
        return False
                
    def consume_any_of(self, data_l):
        for dso in data_l:
            if self._consume(dso):
                self.source_updated.emit()
                return True
                
    def consume_with(self, data, consumer_def):
        if self._consume(data, [consumer_def]):
            self.source_updated.emit()
            return True
        
            
    def provide(self, target):
        self.provides.append( self.o[target] )
                
    def stop_consuming(self, target ):
        if target in self.i:
            self.consumes.remove( self.i[ target ])
            del self.i[ target ]

    def stop_providing(self, data):
        data.remove_all_consumers()
        self.provides.remove(data)
        

    def refresh_consumed_data(self):
        self.source_updated.emit() # Trigger recalculation


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
    
    def __init__(self, target, definition, title=None, *args, **kwargs):
        super(DataDefinition, self).__init__(*args, **kwargs)
    
        # Store consumer/provider description as entity entries from dict
        self.target = target # Target attribute for imported data - stored under this in dataManager
                             # When assigning data; should check if pre-existing and warn to overwrite (or provide options)
        self.definition = definition
        
        self.title = title if title else target
            
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
    def __init__(self, dso, *args, **kwargs):        
        super(QTableInterface, self).__init__(*args, **kwargs)
        self.dso = dso
        
    def rowCount(self, parent):
        return self.dso.shape[0]

    def columnCount(self, parent):
        if len(self.dso.shape)>0:
            return self.dso.shape[1]
        
    def data(self, index, role):
        if not index.isValid():
            return None
        elif role != Qt.DisplayRole:
            return None
            
        return float( self.dso.data[ index.row(), index.column()] )
            
    def headerData(self, col, orientation, role):
        
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            try:
                return self.dso.labels[1][col]
            except:
                pass
            
        elif orientation == Qt.Vertical and role == Qt.DisplayRole:
            try:
                return self.dso.labels[0][col]
            except:
                pass
            
        return None
        
    def refresh(self):
        self.headerDataChanged.emit(Qt.Horizontal,0,self.columnCount(None))
        self.headerDataChanged.emit(Qt.Vertical,0,self.rowCount(None))
        self.layoutChanged.emit()
        
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
        super(DataSet, self).__init__(*args, **kwargs)

        # DataSet must be assigned to a data manager for inter-object updates/communication to work
        self.manager = manager
        self.manager_interface = None
        
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
    
    # Metaclasses for copying the dataset object; copy is fine as the default implementation
    # but we need deepcopy that stops at the db boundary.
    # def __copy__(self):

    def __deepcopy__(self, memo):

        o = DataSet( size=self.shape )
        o.manager = None # Maintain the manager link
        o.manager_interface = None # Interface the manager is advertising this on
        
        o.name = deepcopy(self.name, memo)
        o.description = deepcopy(self.description, memo)
        o.type = deepcopy(self.type, memo)

        o.labels = deepcopy(self.labels, memo)
        o.entities = [copy(x) for x in self.entities] # deepcopy(self.entities, memo) ; this is full of pointers to database objects
        o.scales = deepcopy(self.scales, memo)
        o.classes = deepcopy(self.classes, memo)

        o.data = deepcopy(self.data)
        
        return o
    
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

        self.axes = []
        
        self.data = np.zeros( size ) #np.array([]) # Data container  
        
        self.metadata = {}
              
    
    def import_data(self, dso):
        
        self.name = copy(dso.name)
        self.description = copy(dso.description)
        self.type = copy(dso.type)

        self.axes = deepcopy(dso.axes)

        self.labels = deepcopy(dso.labels)
        self.entities = dso.entities[:]
        self.scales = deepcopy(dso.scales)
        self.classes = deepcopy(dso.classes)

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
            
    # Types (most useful on entities)
    @property
    def entities_t(self):
        return self._t( self.entities )  
        
    @property
    def scales_t(self):
        return self._t( self.scales )          

    @property
    def labels_t(self):
        return self._t( self.labels )  

    @property
    def classes_t(self):
        return self._t( self.classes )  
        
    @property
    def shape(self):
        return self.data.shape
        
    @property
    def dimensions(self):
        return len(self.shape)

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

        return dso    
        
    # Compress the dataset object in 'd' dimension; 
    # being compressed in d dimension by the fn function
    # Compression only if classes, labels and entities are equal. Scale is treated the same as data (fn function)
    def as_summary(self, fn=np.mean, dim=1, match_attribs=['classes','labels','entities']):
    
        available_match_attribs = ['classes','labels','entities'] # If anything not specified collapse/wipe object entities
    
        dso = DataSet()
        dso.import_data( self ) # We'll overwrite the wrongly dimensional data anyway

        # Build combined (class, label, entity) tuples as matching value
        # We match only on those specified as match_attribs
        #print "!!", [ dso.__dict__[ma][dim] for ma in match_attribs ]
        identities = [ tuple(o) for o in zip( *[ dso.__dict__[ma][dim] for ma in match_attribs ] )  ]#dso.classes[dim], dso.labels[dim], dso.entities[dim]) ]

        unique = tuple( set( identities ) )
        
        old_shape, new_shape = dso.data.shape, list( dso.data.shape )
        new_shape[ dim ] = len( unique )
        print 'Reshape from %s to %s' % (old_shape,new_shape)
        dso.crop( new_shape )
        
        for n,u in enumerate( unique ):
            for ma in match_attribs:
                dso.__dict__[ma][dim][n] = u
                
            # Build mask against the original identities file
            mask = np.array([ True if u == i else False for i in identities ])
            # Mask of T F T T T F if the identity at this position matches our unique value
            # Apply this mask to the data; then use specified np.function to reduce it in our dimension
            if dim == 0:
                data = self.data[ mask, :] #np.ma.array(self.data, mask=mask)
                summarised_data = fn( data, axis=dim) #, keepdims=True )
                dso.data[n,:] = summarised_data
                # FIXME: We wipe but could combine to keep record

            elif dim ==1:
                data = self.data[ :, mask] #np.ma.array(self.data, mask=mask)
                summarised_data = fn( data, axis=dim) #, keepdims=True )
                dso.data[:,n] = summarised_data

            # Fix existing class markers
            for mn, ma in enumerate(match_attribs):
                dso.__dict__[ma][dim][n] = unique[n][ mn ]

            # Wipe out compressed attributes
            for ma in set(match_attribs) - set(available_match_attribs):
                dso.__dict__[ma][dim] = [None]*new_shape[dim]
            

        return dso
    
    # Filter data by labels/entities on a given axis    
    def as_filtered(self, dim=1, scales=None, classes=None, labels=None, entities=None):
        
        dso = DataSet()
        dso.import_data( self ) # We'll overwrite the wrongly dimensional data anyway

        old_shape, new_shape = dso.data.shape, list( dso.data.shape )

        # Build consecutive mask
        iter = [
            (dso.entities[dim], entities),
            (dso.classes[dim], classes),
            (dso.scales[dim], scales),
            (dso.labels[dim], labels),
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
        # FIXME: Hacky; what about 3d arrays
        if dim == 0:
            dso.data = self.data[ mask, : ]
        else:
            dso.data = self.data[ :, mask ]

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
            if s<len(self.labels[d]): # Only allow crop
                self.labels[d] = self.labels[d][:s]
                self.entities[d] = self.entities[d][:s]
                self.scales[d] = self.scales[d][:s]
                final_shape[d] = shape[d]
                
        self.data.resize( final_shape )
        
    
    
    
    
