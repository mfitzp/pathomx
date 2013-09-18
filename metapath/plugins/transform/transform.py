from plugins import ProcessingPlugin

class Transform(ProcessingPlugin):


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


    def get_log2(self, m, c):
        try:
            ns = self.quantities[m][c]
            ns = [n if n != 0 else self.statistics['minima'] for n in ns ]
                    
        except:
            ns = self.statistics['minima']

        return np.log2( np.mean( ns ) )

    def get_log10(self, m, c):
        try:
            ns = self.quantities[m][c]
            ns = [n if n != 0 else self.statistics['minima'] for n in ns ]
                    
        except:
            ns = self.statitics['minima']

        return np.log10( np.mean( ns ) )

    def print_name(self):
        print "This is MetaViz"
