# Layout manager
# Loads predefined layouts

import os, sys, re
from utils import UnicodeReader, UnicodeWriter
from collections import defaultdict

import utils

import xml.etree.cElementTree as et

# Map layout object; stores metabolite positions (manual layout; e.g. using KEGG resources)
# Needs to support loading, parsing map types and object lookup -> x,y
# Ability to combine multiple maps would be nice ( map + map = new map )
class layoutManager(object):

    # kegg, csv metabolite:x/y, dot?
    def __init__(self,filename):
        self.load_layoutfile(filename)
        
    def load_layoutfile(self, filename):
        # Determine if we've got a kgml or csv
        fn, fe = os.path.splitext(filename)
        formats = { # Run specific loading function for different source data types
        #        '.csv': self.load_csv,
                '.xml': self.load_kgml, # Pass to xml-type test wrapper
                '.kgml': self.load_kgml,
                '.gpml': self.load_gpml,
            }
                
        if fe in formats.keys():
            print "Loading..."
            # Set up defaults
            self.objects = dict() # Metabolite ids, linking to (x,y) tuple
        
            # Load using handler for matching filetype
            formats[fe](filename)

        else:
            print "Unsupported file format."
            
        
    def load_kgml(self, filename):
        
        # Read data in from peakml format file
        xml = et.parse( filename )

        # Get object entries
        entries = xml.iterfind('entry')
        for entry in entries:
            if entry.attrib['type'] == 'compound':
            
                null, compound_id = entry.attrib['name'].split(':')
                obj = entry.find('graphics')
                
                coords = ( float(obj.attrib['x'])/12, -float(obj.attrib['y'])/12 )
                self.objects[ compound_id ] = coords


    def load_gpml(self, filename):
   
        # Read data in from gpml format file
        xml = et.parse( filename )

        # Get object entries
        datanodes = xml.iterfind('{http://genmapp.org/GPML/2010a}DataNode')

        for datanode in datanodes:
            if datanode.attrib['Type'] == 'Metabolite':
                
                compound_name = datanode.attrib['TextLabel']
                
                obj = datanode.find('{http://genmapp.org/GPML/2010a}Graphics')
                coords = ( float(obj.attrib['CenterX'])/12, -float(obj.attrib['CenterY'])/12 )

                obj = datanode.find('{http://genmapp.org/GPML/2010a}Xref')
                compound_id = obj.attrib['ID']

                # Store both name and id, in case translation fails
                self.objects[ compound_id ] = coords
                self.objects[ compound_name ] = coords


    def translate(self, db):
        # Translate loaded map objects to metacyc system
        for o in self.objects.keys():
            if o.lower() in db.synrev:
                transid = db.synrev[ o.lower() ].id
                self.objects[ transid ] = self.objects.pop( o )
