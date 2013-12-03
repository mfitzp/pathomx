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

from plugins import VisualisationPlugin

from collections import defaultdict

import os
from copy import copy

import numpy as np
from sklearn.decomposition import PCA

import ui, db, utils
from data import DataSet, DataDefinition

from poster.encode import multipart_encode

from poster.streaminghttp import register_openers
import urllib, urllib2, cookielib



class ZeitgeistView( ui.AnalysisView ):
    def __init__(self, plugin, parent, auto_consume_data=True, **kwargs):
        super(ZeitgeistView, self).__init__(plugin, parent, **kwargs)

        # Define automatic mapping (settings will determine the route; allow manual tweaks later)
        
        self.addDataToolBar()
        self.addFigureToolBar()
        
        self.data.add_input('input') # Add input slot
        
        #self.table = QTableView()
        #self.table.setModel(self.data.o['output'].as_table)
        #self.tabs.addTab(self.table,'Table')
        
        self.predefined_geist = {
            'Omics':['metabolomics','genomics','transcriptomics','proteomics','metabonomics'],
            'Arthritis':['rheumatoid arthritis','sle','osteoarthritis','juvenile arthritis','reactive arthritis'],
            'Cytokines':['IL-1alpha','IL-1beta','IL-10','IL-10R','IL17','IL-2','IL-3','IL-30','IL-4','IL-5','IL-6','TNFa'],
            'Viruses':['H1N1','H5N1', 'EBV', 'HIV','HPV','HSV','HPV5','HPV8']
        }
        
        self._show_predefined_geist = 'Omics'
        
        t = self.addToolBar('Zeitgeist')
        t.zg_control = QComboBox()
        t.zg_control.currentIndexChanged.connect(self.onChangeGeist)
        t.zg_control.addItems( [h for h in self.predefined_geist.keys()] )
        t.addWidget(t.zg_control)
        self.toolbars['zeitgeist'] = t

        
        # Setup data consumer options
        self.data.consumer_defs.append( 
            DataDefinition('input', {
                'entities_t':(None, ['Metabolite','Pathway','Gene','Protein']),
            })
        )

        self.data.source_updated.connect( self.onDataChanged ) # Auto-regenerate if the source data is modified
        self.data.consume_any_of( self.m.datasets[::-1] ) # Try consume any dataset; work backwards

    def onChangeGeist(self):
        self._show_predefined_geist = self.toolbars['zeitgeist'].zg_control.currentText()
        self.set_name( self._show_predefined_geist )
        self.generate()
        

    def onDataChanged(self):
        self.generate()
        
    def batches(self, data, batch_size):
        for i in range(0, len(data), batch_size):
                yield data[i:i+batch_size]    
     
    # Do the PCA analysis
    def generate(self):    
        
        dso = self.data.get('input') # Get the dataset
        
        # Build a list object of class, x, y
        #terms = ['IL1','IL-6','TNF-a','TNF-alpha','IL-10','IL-21','IL-12']
        #terms = ['glucose','lactate','pyruvate','succinate','maleate']
        #terms = ['metabolomics','genomics','transcriptomics','proteomics','metabonomics']
        if self._show_predefined_geist:
            terms = self.predefined_geist[ self._show_predefined_geist ]
 
                
        figure_data = []
        
        # Request data from the MLTrends site; in batches of 5 (query limit)
        # http://www.ogic.ca/mltrends/?search_type=titles%20and%20abstracts;norm_type=word%20count;graph_scale=log;query=glucose%20AND%20lactate%2C%20glucose%2C%20lactate;Graph%21=Graph%21&DOWNLOAD=1
        values = {
            # Raw data download doesn't pay attention to scaling, etc. boo!
            'search_type':'titles', # and abstracts',
            'norm_type':'none',
            'graph_scale':'linear',
            'DOWNLOAD':'1',
            }
        
        for termset in self.batches( terms, 5): # Iterate in 5s using a generator (query limit)
            
            query = values
            query['query']=','.join( ['"%s"' %t if ' ' in t else t for t in termset] )
            print query['query']
            
            data = urllib.urlencode(values)

            request = urllib2.Request('http://www.ogic.ca/mltrends/', data)

            try:
                response = urllib2.urlopen(request)
            except urllib2.HTTPError, e:
                print e
                sys.exit()

            except urllib2.URLError, e:
                print e
                sys.exit()

            tsv = response.read()
            rows = tsv.split("\n")
            # The first row gives us our headers
            headers = [ h.strip('"') for h in rows[0].split("\t")[1:] ]
            year_cache = dict()
            last_year = None
            for row in rows[1:-2]: # Skip latest year (-2 for blank line at end)
                cols = row.split("\t")
                year = cols[0]
                for n, col in enumerate(cols[1:]):
                    value = int('0'+col)
                    year_data = ( year, headers[n], value )
                    year_cache[ (year,headers[n]) ] = value

                    if last_year and value > 0:
                        last_year_value = year_cache[ (last_year, headers[n]) ]
                        delta_value = value - last_year_value
                        figure_data.append( ( year, headers[n], value, delta_value/float(value)) )   # tuple year, term, count )
                last_year = year
                
        metadata = {
            'figure':{
                'data':figure_data,
                },
        }
        
        self.render(metadata, template='d3/zeitgeist.svg')
        
                

class Zeitgeist(VisualisationPlugin):

    def __init__(self, **kwargs):
        super(Zeitgeist, self).__init__(**kwargs)
        self.register_app_launcher( self.app_launcher )

    def app_launcher(self, **kwargs):
        return ZeitgeistView( self, self.m, **kwargs )
        
        
