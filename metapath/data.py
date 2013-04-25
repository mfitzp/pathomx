# Experimental data manager
# Loads a csv data file and extracts key information into usable structures for analysis

import os, sys, re, base64
import csv
import numpy as np

from collections import defaultdict
import operator

import utils
import xml.etree.cElementTree as et


class dataManager():

    # metabolites, reactions, pathways = dict()
    def __init__(self,filename):
        self.load_datafile(filename)
        
    def load_datafile(self, filename):
        # Determine if we've got a csv or peakml file (extension)
        fn, fe = os.path.splitext(filename)
        formats = { # Run specific loading function for different source data types
                '.csv': self.load_csv,
                '.peakml': self.load_peakml,
                '': self.load_txt,
            }
            
        if fe in formats.keys():
            print "Loading..."
            # Set up defaults
            self.filename = filename
            self.data = dict()
            self.metabolites = list()
            self.quantities = dict()
    
            self.statistics = dict()
            self.statistics['ymin'] = 0
            self.statistics['ymax'] = 0
            self.statistics['excluded'] = 0
            self.classes = set()
            
            # Scale list; will be filled with 9 values (rdbu9)
            self.scale = None
            self.scale_type = None
        
            # Load using handler for matching filetype
            formats[fe](filename)

            self.classes = list( self.classes ) # makes easier to handle later
            self.metabolites = list( set( self.metabolites ) ) # Remove duplicates
            self.analysis = None
            self.analysis_timecourse = None
            self.analysis_suggested_pathways = None

        else:
            print "Unsupported file format."


###### LOAD WRAPPERS; ANALYSE FILE TO LOAD WITH OTHER HANDLER

    def load_csv(self, filename):
        print "Loading .csv..."
        # Wrapper function to allow loading from alternative format CSV files
        # Legacy is experiments in ROWS, limited number by Excel so also support experiments in COLUMNS
        reader = csv.reader( open( filename, 'rU'), delimiter=',', dialect='excel')
        hrow = reader.next() # Get top row
        
        if hrow[0].lower() == 'sample':
            if hrow[1].lower() == 'class':
                self.load_csv_R(filename)
            else:
                self.load_csv_C(filename)


    def load_txt(self, filename):
        print "Loading text file..."
        # Wrapper function to allow loading from alternative format txt files
        # Currently only supports Metabolights format files
        reader = csv.reader( open( filename, 'rU'), delimiter='\t', dialect='excel')
        hrow = reader.next() # Get top row
        
        if hrow[0].lower() == 'database_identifier': # M format metabolights
            self.load_metabolights(filename)

        if hrow[0].lower() == 'identifier': # A format metabolights
            self.load_metabolights(filename, id_col=0, name_col=2, data_col=19)


###### LOAD HANDLERS

    def load_csv_C(self, filename): # Load from csv with experiments in COLUMNS, metabolites in ROWS
        
        # Read in data for the graphing metabolite, with associated value (generate mean)
        reader = csv.reader( open( filename, 'rU'), delimiter=',', dialect='excel')
        
        hrow = reader.next() # Discard top row (sample no's)
        hrow = reader.next() # Get 2nd row
        self.classes = hrow[1:]
        self.metabolites = []
        
        for row in reader:
            metabolite = row[0]
            self.metabolites.append( row[0] )
            self.quantities[ metabolite ] = defaultdict(list)

            for n, c in enumerate(row[1:]):
                if self.classes[n] != '.':
                    try:
                        c = float(c)
                    except:
                        c = 0
                    self.quantities[metabolite][ self.classes[n] ].append( c )
                    self.statistics['ymin'] = min( self.statistics['ymin'], c )
                    self.statistics['ymax'] = max( self.statistics['ymax'], c )

        self.statistics['excluded'] = self.classes.count('.')
        self.classes = set( [c for c in self.classes if c != '.' ] )
        
                
    def load_csv_R(self, filename): # Load from csv with experiments in ROWS, metabolites in COLUMNS
       
        # Read in data for the graphing metabolite, with associated value (generate mean)
        reader = csv.reader( open( filename, 'rU'), delimiter=',', dialect='excel')
        
        hrow = reader.next() # Get top row
        self.metabolites = hrow[2:]

        # Build quants table for metabolite classes
        for metabolite in self.metabolites:
            self.quantities[ metabolite ] = defaultdict(list)
        
        for row in reader:
            if row[1] != '.': # Skip excluded classes # row[1] = Class
                self.classes.add( row[1] )  
                for metabolite in self.metabolites:
                    metabolite_column = hrow.index( metabolite )   
                    if row[ metabolite_column ]:
                        self.quantities[metabolite][ row[1] ].append( float(row[ metabolite_column ]) )
                        self.statistics['ymin'] = min( self.statistics['ymin'], float(row[ metabolite_column ]) )
                        self.statistics['ymax'] = max( self.statistics['ymax'], float(row[ metabolite_column ]) )
                    else:
                        self.quantities[metabolite][ row[1] ].append( 0 )
            else:
                self.statistics['excluded'] += 1
 
        
    def load_peakml(self, filename):
        print "Loading PeakML..."

        def decode(s):
            s = base64.decodestring(s)
            # Each number stored as a 4-chr representation (ascii value, not character)
            l = []
            for i in xrange(0, len(s), 4):
                c = s[i:i+4]
                val = 0
                for n,v in enumerate(c):
                    val += ord(v) * 10**(3-n)
                l.append( str(val) )
            return l
        
        # Read data in from peakml format file
        xml = et.parse( filename )

        # Get sample ids, names and class groupings
        sets = xml.iterfind('header/sets/set')
        midclass = {}
        for set in sets:
            id = set.find('id').text
            mids = set.find('measurementids').text
            for mid in decode(mids):
                midclass[mid] = id
            self.classes.add(id)

        #meaurements = xml.iterfind('peakml/header/measurements/measurement')
        #samples = {}
        #for measurement in measurements:
        #    id = measurement.find('id').text
        #    label = measurement.find('label').text
        #    sampleid = measurement.find('sampleid').text
        #    samples[id] = {'label':label, 'sampleid':sampleid}
        
        # We have all the sample data now, parse the intensity and identity info
        peaksets = xml.iterfind('peaks/peak')
        metabolites = {}
        quantities = {}
        for peakset in peaksets:
            
            # Find metabolite identities
            annotations = peakset.iterfind('annotations/annotation')
            identities = False
            for annotation in annotations:
                if annotation.find('label').text == 'identification':
                    identities = annotation.find('value').text.split(', ')
                    break

            if identities:
                # PeakML supports multiple alternative metabolite identities,currently we don't so duplicate
                for identity in identities:
                    if not identity in self.quantities:
                        self.quantities[ identity ] = defaultdict(list)
                    self.metabolites.append(identity)
            
                # We have identities, now get intensities for the different samples            
                chromatograms = peakset.iterfind('peaks/peak') # Next level down
                quants = defaultdict(list)
                for chromatogram in chromatograms:
                    mid = chromatogram.find('measurementid').text
                    intensity = float( chromatogram.find('intensity').text )
                    
                    classid = midclass[mid]
                    quants[classid].append(intensity)

                for classid, q in quants.items():
                    for identity in identities:
                        self.quantities[ identity ][ classid ].extend( q )


    def load_metabolights(self, filename, id_col=0, name_col=4, data_col=18): # Load from csv with experiments in COLUMNS, metabolites in ROWS
        print "Loading Metabolights..."
        
        # Read in data for the graphing metabolite, with associated value (generate mean)
        reader = csv.reader( open( filename, 'rU'), delimiter='\t', dialect='excel')
        
        hrow = reader.next() # Get top row
        self.classes = hrow[data_col:]
        self.metabolites = []
        print self.classes
        for row in reader:
            for m_col in [id_col,name_col]: # This is a bit fugly; we're pulling the data *twice* to account for IDs and names columns
                                # an improvement would be to rewrite backend to allow synonyms to be supplied from the data
                                # then implement multi-step translations
                metabolite = row[m_col]
                self.metabolites.append( row[m_col] )
                self.quantities[ metabolite ] = defaultdict(list)

                for n, c in enumerate(row[data_col:]):
                    if self.classes[n] != '.':
                        try:
                            c = float(c)
                        except:
                            c = 0
                        self.quantities[metabolite][ self.classes[n] ].append( c )
                        self.statistics['ymin'] = min( self.statistics['ymin'], c )
                        self.statistics['ymax'] = max( self.statistics['ymax'], c )

        self.statistics['excluded'] = self.classes.count('.')
        self.classes = set( [c for c in self.classes if c != '.' ] )



###### TRANSLATION to METACYC IDENTIFIERS
                        
    def translate(self, db):
        # Translate loaded data names to metabolite IDs using provided database for lookup
        for m in self.metabolites:
            if m.lower() in db.synrev:
                transid = db.synrev[ m.lower() ].id
                self.metabolites[ self.metabolites.index( m ) ] = transid
                self.quantities[ transid ] = self.quantities.pop( m )
        print self.metabolites
        
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
                analysis[metabolite]['color'] = 5 -( analysis[metabolite]['delta']['meanlog'] )
                analysis[metabolite]['color'] = int( max( min( analysis[metabolite]['color'], 9), 1) )

                # Ranking score for picking pathways; meanlog scaled to control giving rel log change
                analysis[metabolite]['score'] = min( max( analysis[metabolite]['delta']['meanlog'],-4),+4) #/  ( np.log(analysis[metabolite]['control']['mean'])  / np.log(logN) )
                
                #analysis[metabolite]['color'] = int( max( min( 5-round( analysis[metabolite]['delta']['mean']*25 ), 9), 1) )
                #analysis[metabolite]['score'] = analysis[metabolite]['delta']['mean']
                
        return analysis




    # Generate pathway suggestions from the database based on a given data analysis (use set options)
    def suggest(self, db, mining_type='n', mining_depth=5):
    
        # Iterate all the metabolites in the current analysis
        # Assign score to each of the metabolite's pathways
        # Sum up, crop and return a list of pathway_ids to display
        # Pass this in as the list to view
        # + requested pathways, - excluded pathways
        
        pathway_scores = defaultdict( int )
        print "Mining using '%s'" % mining_type
        
        for m_id in self.analysis:
            
            score = self.analysis[ m_id ]['score']
            
            # Iterate the metabolite's pathways
            if m_id in db.metabolites.keys():
                pathways = db.metabolites[ m_id ].pathways
            elif m_id in db.proteins.keys():
                pathways = db.proteins[ m_id ].pathways
            elif m_id in db.genes.keys():
                pathways = db.genes[ m_id ].pathways
            else:
                continue # Skip out of the loop        
                
            if "s" in mining_type:
                print "!"
                # Share the change score between the associated pathways
                # this prevents metabolites having undue influence
                score = score / len(pathways)    
        
            for p in pathways:
                mining_val = {
                    'c': abs( score),
                    'u': max( 0, score),
                    'd': abs( min( 0, score ) ),
                    'm': 1.0
                    }
                pathway_scores[ p.id ] += mining_val[ mining_type[0] ]
                    
        # If we're pruning, then remove any pathways not in keep_pathways
        if "r" in mining_type:
            print "Scaling pathway scores to pathway sizes..."
            for p,v in pathway_scores.items():
                pathway_scores[p] = float(v) / len( db.pathways[p].reactions )


    
        pathway_scorest = pathway_scores.items() # Switch it to a dict so we can sort
        pathway_scorest = [(p,v) for p,v in pathway_scorest if v>0] # Remove any scores of 0
        pathway_scorest.sort(key=lambda tup: tup[1], reverse=True) # Sort by scores (either system)
        
        # Get top N defined by mining_depth parameter
        keep_pathways = pathway_scorest[0:mining_depth]
        remaining_pathways = pathway_scorest[mining_depth+1:mining_depth+100]

        print "Mining recommended %d out of %d" % ( len( keep_pathways ), len(pathway_scores) )
       
        for n,p in enumerate(keep_pathways):
            print "- %d. %s [%.2f]" % (n+1, db.pathways[ p[0] ].name, p[1])

        self.analysis['mining_ranked_remaining_pathways'] = []
                        
        if remaining_pathways:
            print "Note: Next pathways by current scoring method are..."
            for n2,p in enumerate(remaining_pathways):
                print "- %d. %s [%.2f]" % (n+n2+1, db.pathways[ p[0] ].name, p[1])
                self.analysis['mining_ranked_remaining_pathways'].append( p[0] )

        self.analysis_suggested_pathways = [db.pathways[p[0]] for p in pathway_scorest]



"""            
                if options.statistic:
                    from scipy import stats 
                    self.analysis[metabolite]['stats'] = dict()
        
                    # If is entirely zero, dump it (wont be significant)
                    if sum( analysis[metabolite]['control']['data']) ==0 and sum(analysis[metabolite]['test']['data'] ) == 0:
                        del analysis[metabolite]
                        continue # Next metabolite
                        
                    if options.statistic == 'trel':
                        t, p = stats.ttest_rel( analysis[metabolite]['control']['data'], analysis[metabolite]['test']['data'] )
                    else:
                        t, p = stats.ttest_ind( analysis[metabolite]['control']['data'], analysis[metabolite]['test']['data']  )
        
                    if p>0.05:
                        del analysis[metabolite]
                        continue # Next metabolite
                    else:
                        analysis[metabolite]['stats']['p'] = p
                        analysis[metabolite]['stats']['sigstars'] = utils.sigstars(p)
"""