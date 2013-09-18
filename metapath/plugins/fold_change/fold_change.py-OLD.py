from plugins import AnalysisPlugin

import numpy as np

import data, ui, db

class FoldChange( ui.DataView, data.DataManager ):
    def __init__(self, plugin, parent, **kwargs):
        super(FoldChange, self).__init__(plugin, parent, **kwargs)
        
        
###### PRE-PROCESS
    def analyse(self, experiment):
        self.analysis = None
        self.analysis_timecourse = None
        self.analysis_suggested_pathways = None

        if 'timecourse' in experiment:
            self.analyse_timecourse( [experiment['control']], [experiment['test']], experiment['timecourse'])
        else:
            self.analyse_single( [experiment['control']], [experiment['test']])           


    def analyse_single(self, control, test):
        self.analysis = self._analyse(control, test)

    def analyse_timecourse(self, control, test, timecourse):
    
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



    def print_name(self):
        print "This is MetaViz"
