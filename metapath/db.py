# Database manager
# Loads metabolites, reactions and pathways on initialisation. Provides interface to 
# filter sets, list etc. 
# Database is a key-based store of each dataset

import os, sys, re
from utils import UnicodeReader, UnicodeWriter
from collections import defaultdict

import utils

# Databases that have sufficiently unique IDs that do not require additional namespacing
database_link_synonyms = [
    'UCSC', 'ENSEMBL', 'HMDB', 'CAS',
]

# Global MetaPath db object class to simplify object display, synonym referencing, etc. 
class _MetaPathObject(object):
    def __unicode__(self):
        return self.name
        
    def __repr__(self):
        return unicode(self)

    def __init__(self, **entries):
        object.__init__(self)
        self.__dict__.update(entries)
        
    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return self.id == other.id
        

    def get_piped_str(self,l):
        l = list( set( l ) ) # Remove duplicates from list when saving
        return '|'.join( [o if type(o) is str or type(o) is unicode else str(o.id) for o in l])
    
    def get_db_str(self,dbs):
        if dbs:
            dbtbl = list()
            for k, v in dbs.items():
                dbtbl.append( '%s:%s' % (k,v) )
            return ';'.join( dbtbl)
        else:
            return ''
        
    def synonym_str(self):
        return ', '.join(self.synonyms)
    

# Dummy wrapper classes for readability
class Metabolite(_MetaPathObject):
    type = 'compound'
    def as_csv(self):
        return [
            self.id,
            self.name,
            self.type,
            self.get_db_str(self.databases) ]
            
class Pathway(_MetaPathObject):
    type = 'pathway'
    def as_csv(self):
        return [
            self.id,
            self.name,
            self.get_db_str(self.databases) ]

class Reaction(_MetaPathObject):
    type = 'reaction'
    def as_csv(self):
        return [
            self.id,
            self.name,
            self.get_piped_str(self.mtins),
            self.get_piped_str(self.mtouts),
            self.get_piped_str(self.smtins),
            self.get_piped_str(self.smtouts),
            self.get_piped_str(self.proteins),
            self.dir,
            self.get_piped_str(self.pathways),
            self.get_db_str(self.databases) ]

    @property
    def metabolites(self):
        return self.mtins + self.mtouts

    @property
    def secondary_metabolites(self):
        return self.smtins + self.smtouts
        
class Protein(_MetaPathObject):
    type = 'protein'
    def as_csv(self):
        return [
            self.id,
            self.name,
            self.get_piped_str(self.genes),
            self.get_piped_str(self.compartments),
            self.get_db_str(self.databases) ]

class Gene(_MetaPathObject):
    type = 'gene'
    def as_csv(self):
        return [
            self.id,
            self.name,
            self.get_db_str(self.databases) ]



            
# Dummy class to handle reaction intermediate metabolites/reaction steps
class ReactionIntermediate(_MetaPathObject):
    # Standard values
    type = 'dummy'
    name = 'n/a'

class databaseManager():

    # metabolites, reactions, pathways = dict()
    def __init__(self):
    
        # Initialise variables
        self.synfwd = defaultdict(set) # ID -> Synonyms
        self.synrev = dict() # Synonym -> ID

        # A namespace index
        self.index = dict()

        # Separate subtypes
        self.pathways = defaultdict(Pathway)

        self.reactions = defaultdict(Reaction)
        self.metabolites = defaultdict(Metabolite)

        self.proteins = defaultdict(Protein)
        self.genes = defaultdict(Gene)

        self.unification = defaultdict( dict ) 

        
        # Load the data
        self.load_pathways()
        self.load_metabolites()

        self.load_genes()
        self.load_proteins()

        self.load_reactions()

        # Load synonym interface for conversion and data-interpreting
        self.load_synonyms()
        self.load_identities()
        self.load_xrefs()

    # Helper functions
    def get_via_unification(self, database, id):
        try:
            return self.unification[database][id]
        except:
            return None



    # Handler to load all identity files in /identities
    def load_identities(self): 
        identities_files=os.listdir( os.path.join( utils.scriptdir,'identities','synonyms') )
        if len(identities_files)>0:
            print "Loading additional synonyms:"
            for filename in identities_files:
                print "- %s" % filename
                reader = UnicodeReader( open( os.path.join( utils.scriptdir,'identities', 'synonyms', filename), 'rU'), delimiter=',', dialect='excel')
                for id, identity in reader:
                    self.add_identity(id, identity)
            print "Done."
            
    def load_xrefs(self):
        identities_files=os.listdir( os.path.join( utils.scriptdir,'identities','xrefs') )
        if len(identities_files)>0:
            print "Loading additional xrefs:"
            for filename in identities_files:
                print "- %s" % filename
                reader = UnicodeReader( open( os.path.join( utils.scriptdir,'identities', 'xrefs', filename), 'rU'), delimiter=',', dialect='excel')
                for id, db, key in reader:
                    #self.add_xref(id, db, key)
                    self.add_db_synonyms(id, {db:key}) #Hack, fix this up
            print "Done."
    

    # Synonym interface for metabolites, reactions and pathways (shared namespace)
    # Can call with filename to load a specific synonym file, e.g. containing peak ids
    def load_synonyms(self, filename = os.path.join( utils.scriptdir,'db/synonyms') ): 
        reader = UnicodeReader( open(filename, 'rU'), delimiter=',', dialect='excel')
        for id, name in reader:
            if id in self.synfwd: # Protection 
                self.add_synonym(id, name)

    def load_metabolites(self):
        import urllib
        reader = UnicodeReader( open(os.path.join( utils.scriptdir,'db/metabolites'),'rU'), delimiter=',', dialect='excel')
        for id, name, type, db_unification in reader:
            self.add_metabolite(id, {
                'name': name,
                'type': type,
                'databases': self.extract_db_unification( db_unification ),
                })
                        
    def load_reactions(self):
        reader = UnicodeReader( open(os.path.join( utils.scriptdir,'db/reactions'),'rU'), delimiter=',', dialect='excel')
        for id, name, origin, dest, smtins, smtouts, proteins, dir, pathways, db_unification in reader:
            self.add_reaction(id, {
                'name': name,        
                # Build internal db links to metabolites
                'mtins':    [self.index[mid] for mid in origin.split('|')],
                'mtouts':   [self.index[mid] for mid in dest.split('|')],
                'smtins':   [self.index[mid] for mid in smtins.split('|') if mid != ''], #[s for s in smtins.split('|') if s != ''],
                'smtouts':  [self.index[mid] for mid in smtouts.split('|') if mid != ''], #[s for s in smtouts.split('|') if s != ''],
                'proteins': [self.index[prid] for prid in proteins.split('|') if prid != ''],
                'dir':      dir,
                # Reactions can be in >1 pathway
                'pathways':  [self.pathways[pid] for pid in pathways.split('|')],
                'databases': self.extract_db_unification( db_unification ),
            })
            
    def load_pathways(self):
        reader = UnicodeReader( open(os.path.join( utils.scriptdir,'db/pathways'),'rU'), delimiter=',', dialect='excel')
        for id, name, db_unification in reader:
            self.add_pathway(id, {
                'name': name,
                'databases': self.extract_db_unification( db_unification ),
            })
            
    def load_proteins(self):
        reader = UnicodeReader( open(os.path.join( utils.scriptdir,'db/proteins'),'rU'), delimiter=',', dialect='excel')
        for id, name, genes, compartments, db_unification in reader:
            self.add_protein(id, {
                'name': name,
                'genes': [self.index[gid] for gid in genes.split('|') if gid != ''],
                'compartments': [c for c in compartments.split('|') if c != ''],
                'databases': self.extract_db_unification( db_unification ),
                })

    def load_genes(self):
        reader = UnicodeReader( open(os.path.join( utils.scriptdir,'db/genes'),'rU'), delimiter=',', dialect='excel')
        for id, name, db_unification in reader:
            self.add_gene(id, {
                'name': name,
                'databases': self.extract_db_unification( db_unification ),
                })
                      

            
    def extract_db_unification(self, db_unification):
        # Process database links field
        dbs = dict()
        if db_unification:
            for dblink in db_unification.split(';'):
                key, val = dblink.split(":", 1)
                dbs[key] = val 
        return dbs
        
    def add_db_synonyms(self, id, databases):
        if id in self.index:
            self.add_synonyms(id, ['%s:%s' % (db,key) for db, key in databases.items()] )
            self.add_synonyms(id, ['%s' % (key) for db, key in databases.items() if db in database_link_synonyms] )
        
            # Add unification links
            for db, key in databases.items():
                self.unification[db][key] = self.index[id]
                
    def add_reaction(self, id, attr):
        self.reactions[id] = Reaction(**dict(
            {'id': id, 'synonyms': self.synfwd[id]}.items() + attr.items())
        )

        # Store id and names in the synonym database
        self.index[id] = self.reactions[id]
        self.add_synonym(id, attr['name'])
        
        # Build the reverse link
        for pathway in attr['pathways']:
            if hasattr(pathway,'id'):
                self.pathways[pathway.id].reactions.append(self.reactions[id])     
        
        # Add pathway links to metabolites
        for m in self.reactions[id].mtins + self.reactions[id].mtouts:
            # The follow instead of extend to remove duplicates
            if hasattr(m,'id'):
                self.metabolites[m.id].pathways.extend( [ p for p in self.reactions[id].pathways if p not in self.metabolites[m.id].pathways ] )
                self.metabolites[m.id].reactions.append( self.reactions[id] )

                for p in self.reactions[id].pathways:
                    if self.metabolites[m.id] not in self.pathways[p.id].metabolites:
                        self.pathways[p.id].metabolites.append( self.metabolites[m.id] ) 
        
        # Add pathway links to proteins
        for pr in self.reactions[id].proteins:
            if hasattr(pr,'id'):
                self.proteins[pr.id].pathways.extend( [ p for p in self.reactions[id].pathways if p not in self.proteins[pr.id].pathways ] )
                self.proteins[pr.id].reactions.append( self.reactions[id] )

                for p in self.reactions[id].pathways:
                    if self.proteins[pr.id] not in self.pathways[p.id].proteins:
                        self.pathways[p.id].proteins.append( self.proteins[pr.id] ) 

                # Add pathway links to genes
                for g in pr.genes:
                    if hasattr(g,'id'):
                        self.genes[g.id].pathways.extend( [ p for p in self.reactions[id].pathways if p not in self.genes[g.id].pathways ] )
                        self.genes[g.id].reactions.append( self.reactions[id] )

                        for p in self.reactions[id].pathways:
                            if self.genes[g.id] not in self.pathways[p.id].genes:
                                self.pathways[p.id].genes.append( self.genes[g.id] ) 
            


    def add_pathway(self, id, attr):
        self.pathways[id] = Pathway(**dict(
            {'id': id, 'synonyms': self.synfwd[id], 'reactions':[], 'metabolites':[], 'proteins':[], 'genes':[], }.items() + attr.items())
        )
    
        # Store id and names in the synonym database
        self.index[id] = self.pathways[id]
        self.add_synonym(id, attr['name'])
        
    def add_metabolite(self, id, attr):
        self.metabolites[id] = Metabolite(**dict(
            {'id': id, 'synonyms': self.synfwd[id], 'reactions':[], 'pathways':[], }.items() + attr.items())
        )
            
        # Store id and name in the synonym database
        self.index[id] = self.metabolites[id]
        self.add_synonym(id, attr['name'])
        self.add_db_synonyms(id, self.metabolites[id].databases )
        
        # Check if we have a compound image for this metabolite
        if 'LIGAND-CPD' in self.metabolites[id].databases.keys():
            self.metabolites[id].image = os.path.join(utils.scriptdir,'db','figures','%s.png' % id)
            self.metabolites[id].imagecolor= os.path.join(utils.scriptdir,'db','figures','%d','%s.png' % id)

    def add_protein(self, id, attr):
        self.proteins[id] = Protein(**dict(
            {'id': id, 'synonyms': self.synfwd[id], 'reactions':[], 'pathways':[], }.items() + attr.items())
        )
            
        # Store id and name in the synonym database
        self.index[id] = self.proteins[id]
        self.add_synonym(id, attr['name'])
        self.add_db_synonyms(id, self.proteins[id].databases )

    def add_gene(self, id, attr):
        self.genes[id] = Gene(**dict(
            {'id': id, 'synonyms': self.synfwd[id], 'reactions':[], 'pathways':[], }.items() + attr.items())
        )

        # Store id and name in the synonym database
        self.index[id] = self.genes[id]
        self.add_synonym(id, attr['name'])
        self.add_db_synonyms(id, self.genes[id].databases )        
        
    def add_synonym(self, id, synonym):
        self.synfwd[id].add( synonym ) # ID -> Synonyms
        if id in self.index:
            self.synrev[synonym] = self.index[id] # Synonym -> Object
            self.synrev[synonym.lower()] = self.index[id] # lc Synonym -> Object
            self.synrev[id] = self.index[id] # id -> Object
            
    def add_synonyms(self, id, synonyms):
        for syn in synonyms:
            self.add_synonym(id, syn)

    # An identity is a limited version of the synonym (using the same tables as above)
    # linking from database id etc. to a object Id, but not reverse
    def add_identity(self, id, identity):
        if id in self.index:
            self.synrev[identity] = self.index[id] # Synonym -> Object
            self.synrev[identity.lower()] = self.index[id] # lc Synonym -> Object
        
    # Output the current database to disk (Overwrite completely)
    def save_metabolites(self):
        writer = UnicodeWriter(open('./db/metabolites', 'wb'), delimiter=',')
        for metabolite in self.metabolites.values():
            writer.writerow( metabolite.as_csv() )  

    def save_reactions(self):
        writer = UnicodeWriter(open('./db/reactions', 'wb'), delimiter=',')
        for reaction in self.reactions.values():
            writer.writerow( reaction.as_csv() )  

    def save_pathways(self):
        writer = UnicodeWriter(open('./db/pathways', 'wb'), delimiter=',')
        for pathway in self.pathways.values():
            writer.writerow( pathway.as_csv() )      
            
    def save_proteins(self):
        writer = UnicodeWriter(open('./db/proteins', 'wb'), delimiter=',')
        for protein in self.proteins.values():
            writer.writerow( protein.as_csv() )      
            
    def save_genes(self):
        writer = UnicodeWriter(open('./db/genes', 'wb'), delimiter=',')
        for gene in self.genes.values():
            writer.writerow( gene.as_csv() )          
        
    def save_synonyms(self):
        writer = UnicodeWriter(open('./db/synonyms', 'wb'), delimiter=',')
        for synk,synv in self.synfwd.items():
            for syn in synv:
                row = [ synk, syn ]
                writer.writerow( row )      
    
    

    

    