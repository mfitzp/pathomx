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

from plugins import AnalysisPlugin

from collections import defaultdict

import os
from copy import copy
import numpy as np

import ui, db, utils
from data import DataSet, DataDefinition


class FoldChangeView( ui.AnalysisView ):
    
    def __init__(self, plugin, parent, **kwargs):
        super(FoldChangeView, self).__init__(plugin, parent, **kwargs)

        # Define automatic mapping (settings will determine the route; allow manual tweaks later)
        
        self.addDataToolBar()
        self.addExperimentToolBar()
        
        self.data.add_output('output')
        self.table = QTableView()
        self.table.setModel(self.data.o['output'].as_table)
        
        self.tabs.addTab(self.table,'Table')
        
        self.register_url_handler(self.url_handler)
        
        self.data.add_input('input') # Add input slot
        # Setup data consumer options
        self.data.consumer_defs.append( 
            DataDefinition('input', {
            'classes_n':(">1",None), # At least one class
            })
        )

        self.config.set_defaults({
            'use_baseline_minima':True,
        })

        t = self.addToolBar('Fold change')
        t.cb_baseline_minima = QCheckBox('Auto minima')
        self.config.add_handler('use_baseline_minima', t.cb_baseline_minima )
        t.cb_baseline_minima.setStatusTip('Replace zero values with half of the smallest value')
        t.addWidget( t.cb_baseline_minima)
        self.toolbars['fold_change'] = t


        self.data.source_updated.connect( self.onDataChanged ) # Auto-regenerate if the source data is modified
        self.data.consume_any_of( self.m.datasets[::-1] ) # Try consume any dataset; work backwards

        self.config.updated.connect( self.generate ) # Auto-regenerate if the configuration is changed


    def onModifyExperiment(self):
        """ Update the experimental settings for analysis then regenerate """    
        self.config.set('experiment_control', self.toolbars['experiment'].cb_control.currentText() )
        self.config.set('experiment_test', self.toolbars['experiment'].cb_test.currentText() )
            
    def onDefineExperiment(self):
        """ Open the experimental setup dialog to define conditions, ranges, class-comparisons, etc. """
        dialog = dialogDefineExperiment(parent=self)
        ok = dialog.exec_()
        if ok:
            # Regenerate the graph view
            self.experiment['control'] = dialog.cb_control.currentText()
            self.experiment['test'] = dialog.cb_test.currentText()      
            # Update toolbar to match any change caused by timecourse settings
            #self.update_view_callback_enabled = False # Disable to stop multiple refresh as updating the list
            #self.cb_control.clear()
            #self.cb_test.clear()

            #self.cb_control.addItems( [dialog.cb_control.itemText(i) for i in range(dialog.cb_control.count())] )
            #self.cb_test.addItems( [dialog.cb_test.itemText(i) for i in range(dialog.cb_test.count())] )
            
            #if dialog.le_timecourseRegExp.text() != '':
            #    self.experiment['timecourse'] = dialog.le_timecourseRegExp.text()
            #elif 'timecourse' in self.experiment:                
            #    del(self.experiment['timecourse'])
        
            # Update the toolbar dropdown to match
            self.toolbars['experiment'].cb_control.setCurrentIndex( self.cb_control.findText( self.experiment['control'] ) )
            self.toolbars['experiment'].cb_test.setCurrentIndex( self.cb_test.findText( self.experiment['test'] ) )
            self.generate()

    def generate(self):
        self.setWorkspaceStatus('active')
    
        self._experiment_control = self.config.get('experiment_control')
        self._experiment_test = self.config.get('experiment_test')
        
        dsi = self.data.get('input')
        dso = self.analyse( dsi )

        self.setWorkspaceStatus('done')
        self.data.put('output', dso)
        # self.render({})

        self.clearWorkspaceStatus()  
            

    
    def analyse(self, dso):
    
        # Get config (convenience)
        _experiment_test = self.config.get('experiment_test')
        _experiment_control = self.config.get('experiment_control')
        _use_baseline_minima = self.config.get('use_baseline_minima')
        
        
        # Get the dso filtered by class if we're not doing a global match
        if _experiment_test != "*":
            dso = dso.as_filtered(dim=0, classes=[_experiment_control, _experiment_test])
        
        # Replace zero values with minima (if setting)
        if _use_baseline_minima:
            #minima = np.min( dso.data[ dso.data > 0 ] ) / 2 # Half the smallest value by default
            #dsoc.data[ dsoc.data <= 0] = minima
            #print 'Fold change minima', np.min(dsoc.data)

            # Get all columns where at least 1 row != 0
            #nzmask = (dsoc.data > 0).sum(0)
            #mdata = dsoc.data[ :, nzmask != 0] # Get all non-zero columns
            # Get copy, set zeros to Nan
            #dso.data[dso.data==0] = np.nan
            dmin = np.ma.masked_less_equal(dso.data,0).min(0)/2
            inds = np.where( np.logical_and( dso.data==0, np.logical_not( np.ma.getmask(dmin) ) ) )
            dso.data[inds]=np.take(dmin,inds[1])

            #minima = np.amin( dso.data[ dso.data > 0 ], axis=0 ) / 2 # Half the smallest value (in each column) by default


        # Compress to extract the two rows identified by class control and test
        dso = dso.as_summary(dim=0, match_attribs=['classes'])
        
        # We have a dso with two rows, one for each class
        # Process by calculating the fold change from row 1 to row 2
        # Output: delta log2, deltalog10, fold change (optionally calculate)
        data = copy(dso.data)
        ci = dso.classes[0].index( _experiment_control )
        if _experiment_test == "*": # Do all comparisons vs. control
            tests = sorted([t for t in dso.classes[0] if t != _experiment_control])
        else:
            tests = [_experiment_test]
        
        for n, test in enumerate(tests):
            print dso.classes[0]
            ti = dso.classes[0].index( test )

            print 'Indices for fold change;',ci,ti
            # Fold change is performed to give negative values for reductions
            # May make this optional in future?
            # i.e. t > c  fc =  t/c;   t < c    fc = -c/t

            c = data[ci,:]
            t = data[ti,:]
        
            dso.data[n, t>c ] = np.array(t/c)[t>c]
            dso.data[n, t<c ] = - np.array(c/t)[t<c]
            dso.data[n, c==t ] = 0
        

        #dsoc.data[0,:] = data[ci,:] / data[ti,:]

        final_shape = list(dso.data.shape)
        final_shape[0]=len(tests) # 1 dimensional (final change value)

        for n,test in enumerate(tests):
            dso.labels[0][n]='fc %s:%s' % ( _experiment_control, test )
            dso.entities[0][n]=None
            dso.classes[0][n]='%s' % (test)

        dso.crop(final_shape)

        return dso        

        '''
        cont_log = ( np.log2( analysis[metabolite]['control']['mean']) ) if analysis[metabolite]['control']['mean']>0 else minlog
        test_log = ( np.log2( analysis[metabolite]['test']['mean']) ) if analysis[metabolite]['test']['mean']>0 else minlog

        analysis[metabolite]['delta']['meanlog'] = (test_log - cont_log)

        # Calculate color using palette (rbu9) note red is 1 blue is 9 so need to reverse scale (-)
        analysis[metabolite]['color'] = round( 5 -( 2* analysis[metabolite]['delta']['meanlog'] ), 0 )
        analysis[metabolite]['color'] = int( max( min( analysis[metabolite]['color'], 9), 1) )

        # Ranking score for picking pathways; meanlog scaled to control giving rel log change
        analysis[metabolite]['score'] = min( max( analysis[metabolite]['delta']['meanlog'],-4),+4) #/  ( np.log(analysis[metabolite]['control']['mean'])  / np.log(logN) )
                
        
        
        
        # Get detection limits (smallest detected concentration)
        minima, maxima = 1e10, 0
        minimad, maximad = 1e10, 0
        maxfold = 0
        ranged = 0
        
        experiment = {
            'control': control,
            'test': test,
            }
            
        for metabolite in self.metabolites:
            quants = self.quantities[metabolite]
            
            analysis[metabolite] = dict()
            
            for k,v in experiment.items():
                analysis[metabolite][k] = dict()
                analysis[metabolite][k]['data'] = list()
                # Allow multiple-class comparisons
                for c in v:
                    analysis[metabolite][k]['data'].extend( quants[c] ) 

                # No empty values allowed
                analysis[metabolite][k]['data'] = [x for x in analysis[metabolite][k]['data'] if x != '']

                # If either of the control/test datasets are empty break out of this loop
                if len(analysis[metabolite][k]['data']) == 0: # Or max = 0?
                    del(analysis[metabolite])
                    break 
                    
                analysis[metabolite][k]['mean'] = np.mean( analysis[metabolite][k]['data'] )
                analysis[metabolite][k]['stddev'] = np.std( analysis[metabolite][k]['data'] )
                analysis[metabolite][k]['log2'] = np.log2( analysis[metabolite][k]['mean'] )
                analysis[metabolite][k]['log10'] = np.log10( analysis[metabolite][k]['mean'] )

                if analysis[metabolite][k]['mean'] > 0 and analysis[metabolite][k]['mean'] < minima:
                    minima = analysis[metabolite][k]['mean']
                elif analysis[metabolite][k]['mean'] > maxima:
                    maxima = analysis[metabolite][k]['mean']
  
            if metabolite in analysis: # We've not dropped it, calculate
  
                analysis[metabolite]['delta'] = dict()
                analysis[metabolite]['delta']['mean'] = analysis[metabolite]['test']['mean'] - analysis[metabolite]['control']['mean']
    
    
    
    
###### TIMECOURSE ANALYSIS (from earlier MetaPath version) KEEP for future use    
###### PRE-PROCESS
    def ___analyse(self, experiment):
        self.analysis = None
        self.analysis_timecourse = None

        if 'timecourse' in experiment:
            self.analyse_timecourse( [experiment['control']], [experiment['test']], experiment['timecourse'])
        else:
            self.analyse_single( [experiment['control']], [experiment['test']])           


    def ___analyse_single(self, control, test):
        self.analysis = self._analyse(control, test)

    def ___analyse_timecourse(self, control, test, timecourse):
    
        # Timecourse
        # Iterate the full class list and build 2 lists for comparison: one class global, then each timepoint
            # a10, a20, a30 vs. b10, b20, b30
            # a10 vs b10, a20 vs b20
        
        classes = control + test
        print '^(?P<pre>.*?)(?P<timecourse>%s)(?P<post>.*?)$' % timecourse 
        rx = re.compile('^(?P<pre>.*?)(?P<timecourse>%s)(?P<post>.*?)$' % timecourse )
        classes_glob, classes_time = defaultdict(list), defaultdict(list)

        tcx = re.compile('(?P<int>\d+)') # Extract out the numeric only component of the timecourse filter
        
        for c in self.classes: 
            m = rx.match(c)
            if m:
                remainder_class = m.group('pre') + m.group('post')
                if remainder_class in classes:
                    classes_glob[ remainder_class ].append( c )

                    # Extract numeric component of the timecourse filtered data
                    tc = m.group('timecourse')
                    tpm = tcx.match(tc)
                    classes_time[ tpm.group('int') ].append( c ) 

        # defaultdict(<type 'list'>, {'MPO': ['MPO56'], 'HSA': ['HSA56']}) defaultdict(<type 'list'>, {'56': ['HSA56', 'MPO56']})
        # Store the global analysis for this test; used for pathway mining etc.
        self.analysis = self._analyse( classes_glob.items()[0][1], classes_glob.items()[1][1] )        
        self.analysis_timecourse = dict()
        
        # Perform the individual timecourse analysis steps, storing in analysis_timecourse structure
        for tp,tpc in classes_time.items():
            print tp, tpc
            self.analysis_timecourse[tp] = self._analyse( [ tpc[0] ], [ tpc[1] ] )    
    
    def _analyse(self, control, test):
    
        analysis = defaultdict(dict)
        
        # Get detection limits (smallest detected concentration)
        minima, maxima = 1e10, 0
        minimad, maximad = 1e10, 0
        maxfold = 0
        ranged = 0
        
        experiment = {
            'control': control,
            'test': test,
            }
            
        for metabolite in self.metabolites:
            quants = self.quantities[metabolite]
            
            analysis[metabolite] = dict()
            
            for k,v in experiment.items():
                analysis[metabolite][k] = dict()
                analysis[metabolite][k]['data'] = list()
                # Allow multiple-class comparisons
                for c in v:
                    analysis[metabolite][k]['data'].extend( quants[c] ) 

                # No empty values allowed
                analysis[metabolite][k]['data'] = [x for x in analysis[metabolite][k]['data'] if x != '']

                # If either of the control/test datasets are empty break out of this loop
                if len(analysis[metabolite][k]['data']) == 0: # Or max = 0?
                    del(analysis[metabolite])
                    break 
                    

                analysis[metabolite][k]['mean'] = np.mean( analysis[metabolite][k]['data'] )
                analysis[metabolite][k]['stddev'] = np.std( analysis[metabolite][k]['data'] )
                analysis[metabolite][k]['log2'] = np.log2( analysis[metabolite][k]['mean'] )
                analysis[metabolite][k]['log10'] = np.log10( analysis[metabolite][k]['mean'] )

                if analysis[metabolite][k]['mean'] > 0 and analysis[metabolite][k]['mean'] < minima:
                    minima = analysis[metabolite][k]['mean']
                elif analysis[metabolite][k]['mean'] > maxima:
                    maxima = analysis[metabolite][k]['mean']
  
            if metabolite in analysis: # We've not dropped it, calculate
  
                analysis[metabolite]['delta'] = dict()
                analysis[metabolite]['delta']['mean'] = analysis[metabolite]['test']['mean'] - analysis[metabolite]['control']['mean']

        limit = max( abs(minima), maxima)

        # Calculate logN base
        logN = pow(maximad, 1.0/9) #rdbu9 1/2 for + and - range

        # Adjust foldscaling to fit 1-9 range
        # foldscale = 9/maxfold
    
        #llogN = np.log(logN)
        minimadsc = 1.0/minimad
        #minlog = 10 ** np.log2( minima ) -1)
        minlog = np.log2( minima )-1
        
        # Find logN to cover this distance in 9 steps (colorscheme rdbu9)
        print "Detection limit minima %s; maxima %s; minlog %s" % ( minima, maxima, minlog )
        
        # Generate scale
        # avglog = int( np.log2( (minima + maxima) / 2) )
        self.scale = [n for n in range(-4, +5)] # Scale 9 big
        self.scale_type = 'log2'
        self.statistics['minima'] = minima
        self.statistics['maxima'] = maxima
            
        for metabolite in self.metabolites:
            if metabolite in analysis:
                #cont_log = ( np.log( analysis[metabolite]['control']['mean']) / np.log(logN) ) if analysis[metabolite]['control']['mean']>0 else minlog
                #test_log = ( np.log( analysis[metabolite]['test']['mean']) / np.log(logN) ) if analysis[metabolite]['test']['mean']>0 else minlog
                #np.log( abs(-0.000444) ) / np.log(0.045044)

                #if analysis[metabolite]['test']['mean'] > analysis[metabolite]['control']['mean']:
                #    analysis[metabolite]['delta']['fold'] = analysis[metabolite]['test']['mean'] / max(minlog, analysis[metabolite]['control']['mean'])
                #elif analysis[metabolite]['test']['mean'] < analysis[metabolite]['control']['mean']:
                #    analysis[metabolite]['delta']['fold'] = -analysis[metabolite]['control']['mean'] / max(minlog, analysis[metabolite]['test']['mean'])
                #else:
                #    analysis[metabolite]['delta']['fold'] = 0

                cont_log = ( np.log2( analysis[metabolite]['control']['mean']) ) if analysis[metabolite]['control']['mean']>0 else minlog
                test_log = ( np.log2( analysis[metabolite]['test']['mean']) ) if analysis[metabolite]['test']['mean']>0 else minlog

                analysis[metabolite]['delta']['meanlog'] = (test_log - cont_log)
    
                # Calculate color using palette (rbu9) note red is 1 blue is 9 so need to reverse scale (-)
                analysis[metabolite]['color'] = round( 5 -( 2* analysis[metabolite]['delta']['meanlog'] ), 0 )
                analysis[metabolite]['color'] = int( max( min( analysis[metabolite]['color'], 9), 1) )

                # Ranking score for picking pathways; meanlog scaled to control giving rel log change
                analysis[metabolite]['score'] = min( max( analysis[metabolite]['delta']['meanlog'],-4),+4) #/  ( np.log(analysis[metabolite]['control']['mean'])  / np.log(logN) )
                
                #analysis[metabolite]['color'] = int( max( min( 5-round( analysis[metabolite]['delta']['mean']*25 ), 9), 1) )
                #analysis[metabolite]['score'] = analysis[metabolite]['delta']['mean']
        return analysis


        '''      
        
    def url_handler(self, url):

        kind, id, action = url.split('/') # FIXME: Can use split here once stop using pathwaynames           
        
        # url is Qurl kind
        # Add an object to the current view
        if kind == "_readme":
            
            # FIXME: Hacky test of an idea
            if action == 'add' and id == 'data_source':
                # Add the pathway and regenerate
                self.onSelectDataSource()

class FoldChange(AnalysisPlugin):

    def __init__(self, **kwargs):
        super(FoldChange, self).__init__(**kwargs)
        self.register_app_launcher( self.app_launcher )

    def app_launcher(self):
        #self.load_data_file()
        self.instances.append( FoldChangeView( self, self.m ) ) 
        
        
