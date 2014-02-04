#!/usr/local/bin/python
# -*- coding: utf-8 -*-

# Recommended base import:
# METHIONINE-DEG1-PWY,GLYCINE-SYN2-PWY,HYDROXYPRODEG-PWY,GLYCOLYSIS,PWY-6134,PROUT-PWY,ALANINE-DEG3-PWY,ARG-PRO-PWY,TYRFUMCAT-PWY,OXIDATIVEPENT-PWY,PWY-5177,SERDEG-PWY,PWY-5046,GLYSYN-PWY,VALDEG-PWY,PWY-4921,PWY-6158,PWY-5130,PWY-5652,PWY-5651,PWY-6307,PWY-5329,PWY-5084,SERSYN-PWY,PWY-4984,ASPARAGINE-DEG1-PWY,PWY-6405,PWY-6281,PWY0-1021,BETA-ALA-DEGRADATION-I-PWY,CYSTEINE-DEG-PWY,CITRULLINE-DEG-PWY,GLNSYN-PWY,PWY-5172,PWY-5690,PWY-4981,PROPIONMET-PWY,PWY-4983,ADENOSYLHOMOCYSCAT-PWY,PWY-6482,MALATE-ASPARTATE-SHUTTLE-PWY,LEU-DEG2-PWY,GLUDEG-I-PWY,PROSYN-PWY,ASPARAGINE-BIOSYNTHESIS,ARGININE-SYN4-PWY,PWY-6938,PWY-5921,GLYCGREAT-PWY,PWY-5030,CITRULBIO-PWY,PWY-6334,ILEUDEG-PWY,GLYCLEAV-PWY,PWY-6318,GLUTDEG-PWY,PYRUVDEHYD-PWY,PWY-5766,HISHP-PWY,PWY-5481,PWY66-367,ARGASEDEG-PWY,GLUTAMINDEG-PWY,PWY-5905,PWY-5331,THREONINE-DEG2-PWY,PWY-3982,GLUTAMATE-SYN2-PWY,ASPARTATESYN-PWY,PWY-6100,PWY66-368,GLYSYN-ALA-PWY,PWY-6755,ALANINE-SYN2-PWY,LYSINE-DEG1-PWY,PWY-6118,HOMOCYSDEGR-PWY,PHENYLALANINE-DEG1-PWY,PWY-5326,LCYSDEG-PWY,NONOXIPENT-PWY

import os, sys, re, math, htmlentitydefs
#import csv
import urllib
import itertools
import time


from optparse import OptionParser
from collections import defaultdict

import HTMLParser
pars = HTMLParser.HTMLParser()

try:
    import xml.etree.cElementTree as et
except ImportError:
    import xml.etree.ElementTree as et

import utils
from utils import UnicodeReader, UnicodeWriter

# Pathomx classes
import db, utils

parser = OptionParser()

parser.add_option("-p", "--pathways", dest="pathways", default='',
                  help="pathways to import from MetaCyc")

parser.add_option("-r", "--reactions", dest="reactions", default='',
                  help="directly import non-pathway reactions")
                  

parser.add_option("-i", "--iterate", action="store_true", dest="recursive", default=False,
                  help="iterate tree to find subpathways recursively (on pathomxways only)")

parser.add_option("-s", "--search", dest="search", default=None,
                  help="only load pathways matching this regex")

(options, args) = parser.parse_args()

reaction_directions = {
    'LEFT-TO-RIGHT':'forward',
    'RIGHT-TO-LEFT':'back',
    'REVERSIBLE':'both',
    'IRREVERSIBLE-LEFT-TO-RIGHT':'forward',
    'IRREVERSIBLE-RIGHT-TO-LEFT':'back',
    'PHYSIOL-LEFT-TO-RIGHT':'forward',
    'PHYSIOL-RIGHT-TO-LEFT':'back'
    }
    
secondary_metabolites = [
                    # Nuceleosides
                    'AMP', 'ADP', 'ATP',
                    'CMP', 'CDP', 'CTP',
                    'GMP', 'GDP', 'GTP',
                    'UMP', 'UDP', 'UTP',
                    'TMP', 'TDP', 'TTP',
                    # Deoxy-nucleosides (only 
                    'DAMP', 'DADP', 'DATP',
                    'DCMP', 'DCDP', 'DCTP',
                    'DGMP', 'DGDP', 'DGTP',
                    'DUMP', 'DUDP', 'DUTP',
                    'DTMP', 'DTDP', 'DTTP',
                    # Reducing
                    'NAD','NAD-P-OR-NOP','NADP',
                    'NADH','NADH-P-OR-NOP','NADPH',
                    'CPD-653','CPD0-2472', # NADHX-S and -R
                    'FAD',
                    'FADH','FADH2',
                    # Protons
                    'PROTON','Donor-H2','Acceptor',
                    # Molecules
                    'CARBON-DIOXIDE','WATER','OXYGEN-MOLECULE',
                    # Metal ions
                    'CA','CA+2',
                    'FE','FE+2','FE+3',
                    #Inorganic phosphate
                    'Pi','PPI','P3I','P4I',                     
                    # Miscellaneous
                    'HCO3', #SO3, #AMMONIA
                    'Menaquinones',
                    'Unspecified-Degradation-Products','Demethylated-methyl-acceptors',
                    # Ubiquino
                    'Ubiquinones','Ubiquinols',#'UBIQUINONE-8',#'CPD-9956','CPD-9958',
                    # Co-Enzymes
                    'CO-A', 'BIOTIN',
                    #'BIOTIN','THIAMINE-PYROPHOSPHATE', 'PYRIDOXAL_PHOSPHATE', 'THF', 
                    
                    # Energy
                    'UV-Light','Light',
                    ]

# Create database accessor, to add things, save etc.
mdb = db.databaseManager()

# Count accesses to the MetaCyc DB
total_connections = 0 

# A table for excluded entries, to stop hammering MetaCyc with repeated duff requests.
# May consider adding this to the database to allow excluded items to be retrieved later.
exclusions = list()
synonyms = defaultdict( list )


def get_db_unification( xmliters ):
    # Extract database unification links and store to db
    databases = dict()
    for xdb in xmliters:
        databases[xdb.find('dblink-db').text] = xdb.find('dblink-oid').text
    return databases

def get_names(xml, types, default):
    names = list()

    for type in types:
        xcn = xml.find('%s/common-name' % type)
        if xcn is not None:
            names.append( xcn.text )

    for xsyn in xml.iter('synonym'):
        names.append( xsyn.text )

    names.append(default)
    return [ pars.unescape( strip_html( name ) ) for name in names ]

if options.search:
    search_re = re.compile(options.search, flags=re.IGNORECASE)

def strip_html(data):
    p = re.compile(r'<.*?>')
    return p.sub('', data)

def get_xml_for_id(id):
    global total_connections
    f = urllib.urlopen('http://websvc.biocyc.org/getxml?HUMAN:%s' % id ) #&detail=low
    xml = et.parse(f)
    f.close()
    total_connections += 1
    return xml


def download_reaction_data( reactions_get ):

    global total_connections
    global secondary_metabolites

    reactions_added_this_time = 0

    metabolites = list()
    proteins = list()
    genes = list()
    
    # Accumulate the total un-fulfilled reactions in the set, to merge and see if achieves something useful
    dud_reactions = list()

    print "Getting reaction metadata..."
    for reaction_id, reaction in reactions_get.items():
        if reaction_id in exclusions: # Can't skip reactions already in the database, as we may need to allocate them to >1 pathway. Improve this once adding is part of the db class
            # print "*** Already excluded, skipping"
            continue
            
        elif reaction_id in mdb.reactions.keys(): # Already in the database, add additional pathways, then skip
            print "'%s' already in database, append additional pathway %s" % (reaction_id, reaction['pathways'][0])            
            mdb.reactions[reaction_id].pathways.append( reaction['pathways'][0] )
            reactions_added_this_time += 1
            continue

        else:     
            print u'Reaction: %s in %s' % (reaction_id, reaction['pathways'][0])

            xml = get_xml_for_id(reaction_id)
    
            rnames = get_names(xml, ['Reaction'], reaction_id)  # Will always be at least one, preferably the common-name
            reaction['name'] = rnames[0]
                
            dir = xml.find('Reaction/reaction-direction')
            reaction['dir'] = reaction_directions[ dir.text ] if dir is not None else 'both'

            xins = xml.iterfind('Reaction/left/Compound')
            mtins = list()
            smtins = list()
            for xin in xins:
                mt = xin.attrib['frameid']
                if mt in secondary_metabolites:
                    smtins.append( mt )
                else:
                    mtins.append( mt )
                
            xouts = xml.iterfind('Reaction/right/Compound')
            mtouts = list()
            smtouts = list()
            for xout in xouts:
                mt = xout.attrib['frameid']
                if mt in secondary_metabolites:
                    smtouts.append( mt )
                else:
                    mtouts.append( mt )

            # Add all to the metabolites listing; we need to add sm metabolites also
            metabolites.extend( mtouts )
            metabolites.extend( mtins )
            metabolites.extend( smtouts )
            metabolites.extend( smtins )

            for syn in rnames[:-1]: # Don't iterate to final item (id)
                mdb.add_synonym(reaction_id, syn )
                
            # Get reaction-associated proteins
            reaction['proteins'] = list()
            xprots = xml.iterfind('Reaction/enzymatic-reaction/Enzymatic-Reaction/enzyme/Protein')
            for xprot in xprots:
                prot = xprot.attrib['frameid']
                proteins.append(prot)
                reaction['proteins'].append(prot)

            # Reverse the reaction so all are forward (or both), improves readability of final graphs
            if reaction['dir'] == 'back':   
                mtouts, mtins = mtins, mtouts
                smtouts, smtins = smtins, smtouts
                reaction['dir'] = 'forward'
            
            reaction['mtins'] = mtins
            reaction['mtouts'] = mtouts
    
            reaction['smtins'] = smtins
            reaction['smtouts'] = smtouts
            
            # Extract database unification links and store to db
            reaction['databases'] = get_db_unification( xml.iterfind('Reaction/dblink') )
            
            if 'pathways' not in reaction:
                # Need to add a pathway for this object, then assign
                mdb.add_pathway(reaction_id, {'name': reaction['name'], 'databases': reaction['databases']}) 
                reaction['pathways'] = [ mdb.pathways[reaction_id] ] # Non-pathway reaction; copy name through

            # We do this down here, so we can append the full completed reaction construct to the meta-set
            if not mtins or not mtouts:
                print "Didn't find metabolites for one side of this reaction, excluding and skipping"
                exclusions.append( reaction_id )
                # Build a dud reactions table, for final combination testing
                dud_reactions.append( reaction ) 
                continue
                        
            print "%s (%s) => %s (%s)" % ( ', '.join(mtins), ', '.join(smtins), ', '.join(mtouts), ', '.join(smtouts) ) 

            # CREATE THE OBJECT IN THE DATABASE
            mdb.add_reaction(reaction_id, reaction)
            reactions_added_this_time += 1
        
    # HANDLE FUNKY PATHWAYS intermediate non-metabolite steps e.g. pyruvate decarboxylation to acetyl coA (via PROTEIN)
    # Improve to stitch all dud reactions together, eg. IN --> intermediate --> OUT = IN --> OUT (IS THIS NEEDED ANYWHERE?)
    if reactions_added_this_time == 0:
        reaction_accum = defaultdict(list)
        for dr in dud_reactions:
            reaction_accum['mtins'].extend( dr['mtins'] )
            reaction_accum['mtouts'].extend( dr['mtouts'] )
            reaction_accum['smtins'].extend( dr['smtins'] )
            reaction_accum['smtouts'].extend( dr['smtouts'] )
            reaction_accum['proteins'].extend( dr['proteins'] )
            reaction_accum['dir'] = dr['dir']

        if reaction_accum['mtins'] and reaction_accum['mtouts']:
            print "Built reaction from constitent pathway steps, adding;"
            
            reaction_accum['name'] = u'%s (reaction)' % dud_reactions[0]['pathways'][0].name
            reaction_accum['databases'] = dud_reactions[0]['databases']
            reaction_accum['pathways'] = dud_reactions[0]['pathways']

            mdb.add_reaction('%s-RXN' % dud_reactions[0]['pathways'][0].id, reaction_accum)
            reactions_added_this_time += 1
            
            
    print "Writing reactions..."
    mdb.save_reactions()

    print "Getting metabolite metadata..."
    for metabolite_id in metabolites: #+smts
        
        if metabolite_id in mdb.metabolites.keys() :
            # print "*** Already in database, skipping"
            continue

        print u'Metabolite: %s' % metabolite_id

        xml = get_xml_for_id(metabolite_id)

        metabolite = dict()

        mnames = get_names(xml, ["Compound"], metabolite_id)  # Will always be at least one, preferably the common-name
        metabolite['name'] = mnames[0]
        
        for syn in mnames[:-1]: # Don't iterate to final item (id)
            mdb.add_synonym(metabolite_id, syn )
        
        if metabolite_id in secondary_metabolites:
            metabolite['type'] = 'secondary'
        else:
            metabolite['type'] = 'compound' 
            
        # Extract database unification links and store to db
        metabolite['databases'] = get_db_unification( xml.iterfind('Compound/dblink') )
    
        # Check if has a KEGG identifier, if so get the KEGG figure
        if 'LIGAND-CPD' in metabolite['databases']:
            kegg_id = metabolite['databases']['LIGAND-CPD']
            urllib.urlretrieve ('http://www.kegg.jp/Fig/compound_small/%s.gif' % kegg_id, "./db/figures/originals/%s.gif" % metabolite_id)
            
        mdb.add_metabolite(metabolite_id, metabolite)
    
    print "Writing metabolites..."
    mdb.save_metabolites()
    
    genes = list()
    
    # Collect genes as we iterate the proteins
    print "Getting protein metadata..."
    for protein_id in proteins: 
        
        if protein_id in mdb.proteins.keys() :
            # print "*** Already in database, skipping"
            continue

        print u'Protein: %s' % protein_id
            
        xml = get_xml_for_id(protein_id)

        protein = dict()

        pnames = get_names(xml, ["Protein"], protein_id)  # Will always be at least one, preferably the common-name
        protein['name'] = pnames[0]
        
        
        for syn in pnames[:-1]: # Don't iterate to final item (id)
            mdb.add_synonym(protein_id, syn )

        protein['compartments'] = list()
        xcomps = xml.iterfind('Protein/location/cco')
        for xcomp in xcomps:
            comp = xcomp.attrib['frameid']
            protein['compartments'].append(comp)
        
        # Get gene data for this protein (should there ever be more than one?!)
        protein['genes'] = list()
        xgenes = xml.iterfind('Protein/gene/Gene')
        for xgene in xgenes:
            gene = xgene.attrib['frameid']
            genes.append(gene)
            protein['genes'].append(gene)

        # Extract database unification links and store to db
        protein['databases'] = get_db_unification( xml.iterfind('Protein/dblink') )

        mdb.add_protein(protein_id, protein)
    
    print "Writing proteins..."
    mdb.save_proteins()

    print "Getting gene metadata..."
    for gene_id in genes: 
        
        if gene_id in mdb.genes.keys() :
            # print "*** Already in database, skipping"
            continue

        print u'Gene: %s' % gene_id
            
        xml = get_xml_for_id(gene_id)

        gene = dict()
        
        gnames = get_names(xml, ["Gene"], gene_id)  # Will always be at least one, preferably the common-name
        gene['name'] = gnames[0]
        
        for syn in gnames[:-1]: # Don't iterate to final item (id)
            mdb.add_synonym(gene_id, syn )

        # Extract database unification links and store to db
        gene['databases'] = get_db_unification( xml.iterfind('Gene/dblink') )

        mdb.add_gene(gene_id, gene)

    print "Writing genes..."
    mdb.save_genes()
    
    return reactions_added_this_time
        

# MAIN LOOP
# Iterate pathway database to import complex pathways

if options.pathways:
    
    pathways_get = options.pathways.split(',')
    pathways = defaultdict(dict)

    for count, pathway_id in enumerate( pathways_get ):
        if pathway_id in mdb.pathways.keys():
            # print "*** Already in database, skipping"
            continue # Next

        print "Requesting pathway data for %s..." % pathway_id
        f = urllib.urlopen('http://biocyc.org/getxml?HUMAN:%s' % pathway_id )
        xml = et.parse(f)
        f.close()
        total_connections += 1
        print "Done."

        reactions_get = defaultdict(dict)
    
        # Get Metacyc Pathway ID
        # <Pathway ID="HUMAN:PWY-5690" orgid="HUMAN" frameid="PWY-5690" detail="low">
        # Build pathway to add to database
        pathway = dict()
        
        pnames = get_names(xml, ["Pathway"], pathway_id)  # Will always be at least one, preferably the common-name
        pathway['name'] = pnames[0]

        for syn in pnames[:-1]: # Don't iterate to final item (id)
            mdb.add_synonym(pathway_id, syn )
        
        # Extract database unification links and store to db
        pathway['databases'] =  get_db_unification( xml.iterfind('Pathway/dblink') )
        
        if options.recursive:
            # Lot of duplication in the layout here, so compensate
            tmppathwaylist = list()
            for xpathway in itertools.chain( 
                    xml.iterfind('Pathway/reaction-list/Pathway'), 
                    xml.iterfind('Pathway/subclass/Pathway'),
                    xml.iterfind('Pathway/instance/Pathway')
                                            ):
                tmppathwaylist.append( xpathway.attrib['frameid'] )
    
            if len(tmppathwaylist) > 0:        
                print u'%s is a meta-pathway; found %d sub-pathways' % ( pathway_id, len(tmppathwaylist) )
                print ','.join( list( set( tmppathwaylist ) ) )
                pathways_get.extend( list( set( tmppathwaylist ) ) )
    
        #if options.search:
        #    if search_re.search( pathways[pathway]['name'] ) == None:
        #        print u'[%d/%d] Skipping \'%s\' (%s) because of search criteria' % ( count, len(pathways), pathways[pathway]['name'], pathway )
        #        continue
    
        print u"[%d/%d] Finding reactions in pathway '%s' (%s)" % ( count, len(pathways_get), pathway['name'], pathway_id )
        xreactionls = xml.iterfind('Pathway/reaction-list/Reaction')
        reactions_this_pathway = len([x for x in xreactionls])

        xreactionls = xml.iterfind('Pathway/reaction-list/Reaction')
    
        if reactions_this_pathway == 0: # Check if we're a 'pathomxway'
            continue

        print "Found %d reactions." % ( reactions_this_pathway )                
        
        mdb.add_pathway( pathway_id, pathway)
        for xreaction in xreactionls:   
            reactions_get[ xreaction.attrib['frameid'] ]['pathways'] = [ mdb.pathways[pathway_id] ]

        reactions_added_this_time = download_reaction_data( reactions_get )

    
        # If nothing added for this pathway, delete it
        if reactions_added_this_time == 0:
            print "Nothing in pathway %s, deleting." % pathway_id
            continue
        
        print "---------------------------------------------------"
        print "Total connections to MetaCyc database so far: %d" % total_connections
        print "---------------------------------------------------"
        
        mdb.save_pathways()
        mdb.save_synonyms()

        # It's not hammertime
        time.sleep(1) 

if options.reactions:

    reactions_get = options.reactions.split(',')
    reactions = dict()
    for reaction_id in reactions_get:
        mdb.add_pathway(reaction_id, { 'name': reaction_id, 'databases': []} )
        reactions[reaction_id]={ 'pathways': [mdb.pathways[reaction_id]] }
    download_reaction_data( reactions )

    mdb.save_pathways()
    mdb.save_synonyms()

print "Done." 


# Python remove duplicates from file
# uniqlines = set(open('/tmp/foo').readlines())   
