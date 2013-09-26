# -*- coding: utf-8 -*-
import os

from plugins import ProcessingPlugin

# Import PyQt5 classes
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWebKit import *
from PyQt5.QtNetwork import *
from PyQt5.QtWidgets import *
from PyQt5.QtWebKitWidgets import *
from PyQt5.QtPrintSupport import *


import utils
import csv
import xml.etree.cElementTree as et
from collections import defaultdict

import numpy as np

import ui, db
from data import DataSet, DataDefinition


class AnnotateView( ui.DataView ):

    import_name = "Annotations"
    import_filename_filter = "All compatible files (*.csv *.txt *.tsv);;Comma Separated Values (*.csv);;Plain Text Files (*.txt);;Tab Separated Values (*.tsv);;All files (*.*)"
    import_description =  "Import data annotations (classes, labels, scales) for current dataset"

    def __init__(self, plugin, parent, **kwargs):
        super(AnnotateView, self).__init__(plugin, parent, **kwargs)
        # Annotations is a list of dicts; each list a distinct annotation        
        # Targets is their mapping to the data; e.g. ('scales', 1) for scales[1]
        self._annotations = defaultdict( list )
        self._annotations_targets = dict()

        # Source object for the data      
        self.addDataToolBar()

        self.data.add_interface('output') # Add output slot
        self.table.setModel(self.data.o['output'].as_table)
        
        t = self.addToolBar('Annotate')
        t.setIconSize( QSize(16,16) )

        import_dataAction = QAction( QIcon( os.path.join(  utils.scriptdir, 'icons', 'disk--arrow.png' ) ), 'Load annotations from file\u2026', self.m)
        import_dataAction.setStatusTip('Load annotations from .csv. file')
        import_dataAction.triggered.connect(self.onLoadAnnotations)
        t.addAction(import_dataAction)

        annotations_dataAction = QAction( QIcon( os.path.join(  utils.scriptdir, 'icons', 'pencil-field.png' ) ), 'Edit annotation settings\u2026', self.m)
        annotations_dataAction.setStatusTip('Import additional annotations for a dataset including classes, labels, scales')
        annotations_dataAction.triggered.connect(self.onEditAnnotationsSettings)
        t.addAction(annotations_dataAction)
        
        self.toolbars['annotations'] = t
    
        # We need an input filter for this type; accepting *anything*
        self.data.consumer_defs.append( 
            DataDefinition('input', {})
        )
        
        self.data.consume_any_of( self.m.datasets[::-1] ) # Try consume any dataset; work backwards

        self.data.source_updated.connect( self.apply_annotations ) # Auto-regenerate if the source data is modified
        self.apply_annotations() # Generate unchanged output


    def onLoadAnnotations(self):
        """ Open a annotations file"""
        filename, _ = QFileDialog.getOpenFileName(self.m, self.import_description, '', self.import_filename_filter)
        if filename:
            self.load_annotations( filename )
            self.apply_annotations()

            #self.file_watcher = QFileSystemWatcher()            
            #self.file_watcher.fileChanged.connect( self.onFileChanged )
            #self.file_watcher.addPath( filename )
            
            self.workspace_item.setText(0, os.path.basename(filename))
            
        return False
        
    def onEditAnnotationsSettings(self):
        """ Open a data file"""
        filename, _ = QFileDialog.getOpenFileName(self.m, self.annotations_description, '', self.annotations_filename_filter)
        if filename:
            self.load_annotations( filename )
            self.apply_annotations()

            self.workspace_item.setText(0, os.path.basename(filename))
    
   
    def apply_annotations(self):
        # Iterate over the list of annotations and apply them to the dataset in i['input']
        # to produce the o['output'] result
        self.setWorkspaceStatus('active')
        print 'Applying annotations...'
        dso = self.data.get('input')

        for source, (target, index) in self._annotations_targets.items():
            annotation = self._annotations[ source ]
            print ':',source, target, index
            if len( annotation ) == len( dso.__dict__[ target ][ index ] ):
                print 'Applying annotation %s to %s' % (source, target)
                dso.__dict__[ target ][ index ] = annotation
        
        self.data.put('output',dso)
        
        self.clearWorkspaceStatus()
   
    def load_annotations(self, filename):
        # Load the annotation file and attempt to apply it in the most logical way possible
        reader = csv.reader( open( filename, 'rU'), delimiter=',', dialect='excel')

        for row in reader:
            if type(row) != list:
                row = [row] # So we accept multiple columns below
            for c,r in enumerate(row):
                self._annotations['%s/%s' % (filename, c)].append(r)
                
        dsi = self.data.get('input')
        # FIXME: Map to targets (we should be a bit more intelligent; accept/reject & a ui)
        for k, a in self._annotations.items():
        
            for n, i in enumerate(dsi.scales):
                print '?/', len(a), len(i)
                if len(a) == len(i):
                    # Annotations match the length of a dimension # TEST 1
                    for target in ['labels','classes','scales']:
                        # Look for the summary attributes labels_t for a list of label variable types; if it == None it must be unset!
                        if getattr(dsi, target+'_t' )[n] == ['NoneType']: # Current not set # TEST 2
                            self._annotations_targets[k] = (target, n) # Save
                            break # Leave the loop; only apply once on each axis
            

class Annotate(ProcessingPlugin):

    def __init__(self, **kwargs):
        super(Annotate, self).__init__(**kwargs)
        self.register_app_launcher( self.app_launcher )

    def app_launcher(self):
        #self.load_data_file()
        self.instances.append( AnnotateView( self, self.m ) )
