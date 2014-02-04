# -*- coding: utf-8 -*-
# Database manager
# Loads compounds, reactions and pathways on initialisation. Provides interface to 
# filter sets, list etc. 
# Database is a key-based store of each dataset

import os, sys, re
from utils import UnicodeReader, UnicodeWriter
from collections import defaultdict

import utils
import numpy as np

from translate import tr

# Databases that have sufficiently unique IDs that do not require additional namespacing
database_link_synonyms = [
    'UCSC', 'ENSEMBL', 'HMDB', 'CAS',
]

# Internal URLS
COMPOUND_URL = 'pathomx://db/compound/%s/view'
PATHWAY_URL = 'pathomx://db/pathway/%s/view'
REACTION_URL = 'pathomx://db/reaction/%s/view'
PROTEIN_URL = 'pathomx://db/protein/%s/view'
GENE_URL = 'pathomx://db/gene/%s/view'

# Global Pathomx db object class to simplify object display, synonym referencing, etc. 
class _PathomxObject(object):
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
        return type(self) == type(other) and self.id == other.id
        

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
class Compound(_PathomxObject):
    type = 'compound'
    type_name = tr('Compound')
    def as_csv(self):
        return [
            self.id,
            self.name,
            self.type,
            self.get_db_str(self.databases) ]
    @property
    def url(self):
        return COMPOUND_URL % self.id

class Pathway(_PathomxObject):
    type = 'pathway'
    type_name = tr('Pathway')    
    def as_csv(self):
        return [
            self.id,
            self.name,
            self.get_db_str(self.databases) ]
    @property
    def url(self):
        return PATHWAY_URL % self.id

class Reaction(_PathomxObject):
    type = 'reaction'
    type_name = tr('Reaction')        
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
    def url(self):
        return REACTION_URL % self.id

    @property
    def compounds(self):
        return self.mtins + self.mtouts

    @property
    def secondary_compounds(self):
        return self.smtins + self.smtouts
        
class Protein(_PathomxObject):
    type = 'protein'
    type_name = tr('Protein')    
    def as_csv(self):
        return [
            self.id,
            self.name,
            self.get_piped_str(self.genes),
            self.get_piped_str(self.compartments),
            self.get_db_str(self.databases) ]
            
    @property
    def url(self):
        return PROTEIN_URL % self.id

class Gene(_PathomxObject):
    type = 'gene'
    type_name = tr('Gene')        
    def as_csv(self):
        return [
            self.id,
            self.name,
            self.get_db_str(self.databases) ]

    @property
    def url(self):
        return GENE_URL % self.id


            
# Dummy class to handle reaction intermediate compounds/reaction steps
class ReactionIntermediate(_PathomxObject):
    # Standard values
    type = 'dummy'
    type_name = 'n/a'
    name = 'n/a'

class databaseManager():

    # compounds, reactions, pathways = dict()
    def __init__(self):
    
        # Initialise variables
        self.synfwd = defaultdict(set) # ID -> Synonyms
        self.synrev = dict() # Synonym -> ID

        # A namespace index
        self.index = dict()

        # Separate subtypes
        self.pathways = dict() #Pathway)

        self.reactions = dict() #Reaction)
        self.compounds = dict() #Compound)

        self.proteins = dict() #Protein)
        self.genes = dict() #Gene)

        self.unification = defaultdict(dict)

        
        # Load the data
        self.load_pathways()
        self.load_compounds()

        self.load_genes()
        self.load_proteins()

        self.load_reactions()

        # Load synonym interface for conversion and data-interpreting
        self.load_synonyms()
        self.load_identities()
        self.load_xrefs()
        
        # Load additional chemical data
        self.load_gibbs()

    # Helper functions
    def get_via_unification(self, database, id):
        try:
            return self.unification[database][id]
        except:
            return None

    # Helper functions
    def get_via_synonym(self, id):
        try:
            return self.synrev[id]
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
    

    # Synonym interface for compounds, reactions and pathways (shared namespace)
    # Can call with filename to load a specific synonym file, e.g. containing peak ids
    def load_synonyms(self, filename = os.path.join( utils.scriptdir,'database/synonyms') ): 
        reader = UnicodeReader( open(filename, 'rU'), delimiter=',', dialect='excel')
        for id, name in reader:
            if id in self.synfwd: # Protection 
                self.add_synonym(id, name)

    def load_compounds(self):
        import urllib
        reader = UnicodeReader( open(os.path.join( utils.scriptdir,'database/compounds'),'rU'), delimiter=',', dialect='excel')
        for id, name, type, db_unification in reader:
            self.add_compound(id, {
                'name': name,
                'type': type,
                'databases': self.extract_db_unification( db_unification ),
                })
                        
    def load_reactions(self):
        reader = UnicodeReader( open(os.path.join( utils.scriptdir,'database/reactions'),'rU'), delimiter=',', dialect='excel')
        for id, name, origin, dest, smtins, smtouts, proteins, dir, pathways, db_unification in reader:
            self.add_reaction(id, {
                'name': name,        
                # Build internal db links to compounds
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
        reader = UnicodeReader( open(os.path.join( utils.scriptdir,'database/pathways'),'rU'), delimiter=',', dialect='excel')
        for id, name, db_unification in reader:
            self.add_pathway(id, {
                'name': name,
                'databases': self.extract_db_unification( db_unification ),
            })
            
    def load_proteins(self):
        reader = UnicodeReader( open(os.path.join( utils.scriptdir,'database/proteins'),'rU'), delimiter=',', dialect='excel')
        for id, name, genes, compartments, db_unification in reader:
            self.add_protein(id, {
                'name': name,
                'genes': [self.index[gid] for gid in genes.split('|') if gid != ''],
                'compartments': [c for c in compartments.split('|') if c != ''],
                'databases': self.extract_db_unification( db_unification ),
                })

    def load_genes(self):
        reader = UnicodeReader( open(os.path.join( utils.scriptdir,'database/genes'),'rU'), delimiter=',', dialect='excel')
        for id, name, db_unification in reader:
            self.add_gene(id, {
                'name': name,
                'databases': self.extract_db_unification( db_unification ),
                })
                      
    def load_gibbs(self):
    
        def sum_gibbs_in_outs( key, ins, outs):
            return sum([ m.gibbs[key] for m in ins if hasattr(m,'gibbs')] ) - sum([ m.gibbs[key] for m in outs if hasattr(m,'gibbs')] )
    
        reader = UnicodeReader( open(os.path.join( utils.scriptdir,'database/gibbs'),'rU'), delimiter=',', dialect='excel')
        
        # Add reactions from each compound that we have gibbs data for
        gibbs_reactions = set()
        
        for kegg_id, deltag, uncertainty, charge in reader:
            if kegg_id in self.unification['KEGG']:
                
                self.unification['KEGG'][kegg_id].gibbs = {
                        'deltaG':   float(deltag), # + 8314 * 310.15 * np.log(2), # G = G° + RTln(C2/C1) n.b. 310.15K = 37°C; R= 8.314 gas constant
                        'deltaG_bio': float(deltag),
                        'uncertainty': float(uncertainty),
                        'charge': float(charge)
                    }
                gibbs_reactions.update( self.unification['KEGG'][kegg_id].reactions )
        
        for r in list( gibbs_reactions ):
            # Do we have gibbs data for all reactants (excl. H+ and?)
            # Some are uncalculated (e.g. pseudoatom H so can't be included - how to treat, could mark these somehow from original source data
            ins =  r.mtins + r.smtins
            outs = r.mtouts + r.smtouts

            deltag = sum_gibbs_in_outs( 'deltaG', ins, outs )
            
            # Swap reaction directions on birectional reactions to match gibbs
            #if r.dir == 'both' and deltag > 0:
            #    print r, "swap!"
            #    tmtins, tsmtins = r.mtins, r.smtins
            #    r.mtins, r.smtins = r.mtouts, r.smtouts
            #    r.mtouts, r.smtouts = tmtins, tsmtins
            #    deltag = -deltag
            
            # Calculate penwidth for deltag viz
            if deltag == 0:
                deltag_w = 1
            else:
                deltag_w = 1+ (np.log2( abs(deltag) )+1) * deltag/abs(deltag) # Signed log2

            r.gibbs = {
                    'deltaG': deltag, # sum_gibbs_in_outs( 'deltaG', ins, outs ),
                    'deltaG_bio': deltag, # sum_gibbs_in_outs( 'deltaG', ins, outs ),
                    'deltaG_w': deltag_w,
                    'uncertainty': sum_gibbs_in_outs( 'uncertainty', ins, outs ),
                    'charge': sum_gibbs_in_outs( 'charge', ins, outs ),
                }
            
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
        
            for db, key in databases.items():
                self.index[id].databases[db] = key
            
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
        
        # Add pathway links to compounds
        for m in self.reactions[id].mtins + self.reactions[id].mtouts:
            # The follow instead of extend to remove duplicates
            if hasattr(m,'id'):
                self.compounds[m.id].pathways.extend( [ p for p in self.reactions[id].pathways if p not in self.compounds[m.id].pathways ] )
                self.compounds[m.id].reactions.append( self.reactions[id] )

                for p in self.reactions[id].pathways:
                    if self.compounds[m.id] not in self.pathways[p.id].compounds:
                        self.pathways[p.id].compounds.append( self.compounds[m.id] ) 
        
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
            {'id': id, 'synonyms': self.synfwd[id], 'reactions':[], 'compounds':[], 'proteins':[], 'genes':[], }.items() + attr.items())
        )
    
        # Store id and names in the synonym database
        self.index[id] = self.pathways[id]
        self.add_synonym(id, attr['name'])
        
    def add_compound(self, id, attr):
        self.compounds[id] = Compound(**dict(
            {'id': id, 'synonyms': self.synfwd[id], 'reactions':[], 'pathways':[], }.items() + attr.items())
        )
            
        # Store id and name in the synonym database
        self.index[id] = self.compounds[id]
        self.add_synonym(id, attr['name'])
        self.add_db_synonyms(id, self.compounds[id].databases )
        
        # Check if we have a compound image for this compound (KEGG Sourced)
        if 'LIGAND-CPD' in self.compounds[id].databases.keys():
            self.compounds[id].image = os.path.join(utils.scriptdir,'database','figures','%s.png' % id)
            self.compounds[id].imagecolor= os.path.join(utils.scriptdir,'database','figures','%d','%s.png' % id)

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
    def save_compounds(self):
        writer = UnicodeWriter(open('./database/compounds', 'wb'), delimiter=',')
        for compound in self.compounds.values():
            writer.writerow( compound.as_csv() )  

    def save_reactions(self):
        writer = UnicodeWriter(open('./database/reactions', 'wb'), delimiter=',')
        for reaction in self.reactions.values():
            writer.writerow( reaction.as_csv() )  

    def save_pathways(self):
        writer = UnicodeWriter(open('./database/pathways', 'wb'), delimiter=',')
        for pathway in self.pathways.values():
            writer.writerow( pathway.as_csv() )      
            
    def save_proteins(self):
        writer = UnicodeWriter(open('./database/proteins', 'wb'), delimiter=',')
        for protein in self.proteins.values():
            writer.writerow( protein.as_csv() )      
            
    def save_genes(self):
        writer = UnicodeWriter(open('./database/genes', 'wb'), delimiter=',')
        for gene in self.genes.values():
            writer.writerow( gene.as_csv() )          
        
    def save_synonyms(self):
        writer = UnicodeWriter(open('./database/synonyms', 'wb'), delimiter=',')
        for synk,synv in self.synfwd.items():
            for syn in synv:
                row = [ synk, syn ]
                writer.writerow( row )      
    
    

    

    
