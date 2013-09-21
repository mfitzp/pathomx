from plugins import DataPlugin

class ImportExcel(DataPlugin):

    id = "importexcel"
    
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
