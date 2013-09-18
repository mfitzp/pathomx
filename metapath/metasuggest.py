# Import CSV file describing a set of nodes, and edges between them
# Output the data to running ubigraph server to visualise

import os, sys, re, math
import csv
import pydot
import numpy as np

from optparse import OptionParser
from collections import defaultdict

import utils

parser = OptionParser()

parser.add_option("-f", "--file", dest="file", default='plsdump-ranked-overall.csv',
                  help="load edge file by name, name root used as basis for output graph filenames", metavar="FILE")

parser.add_option("-n", "--number", dest="number_of_metabolites", type="int", default=20,
                  help="max number of metabolites to test")
                  
parser.add_option("-m", "--minimum", dest="min_number_metabolites_per_pathway", type="int", default=2,
                  help="minimum number of metabolites required to select a pathway")


(options, args) = parser.parse_args()
# Get running script folder
dirpath = os.path.realpath(__file__).rpartition('/')
    
# Extract file root from the edge file name
filebase = os.path.splitext(options.file)[0]
[null, sep, string ] = filebase.partition('-')
filesuff = sep + string


reader = csv.reader( open(options.file ,'rU'), delimiter=',', dialect='excel')
metabolites = list()
c = 0
for row in reader:
    metabolites.append( row[0] )
    c += 1
    if c > options.number_of_metabolites:
        break

print "We've got %d metabolites to attempt to map to pathways." % len(metabolites)

# Lowercase for match
metabolites = [x.lower() for x in metabolites]

print "Searching metabolite database..."
metabolite_ids = set()
metabolites_unmatched = metabolites
reader = csv.reader( open(os.path.join(dirpath[0],'metabolites.csv'),'rU'), delimiter=',', dialect='excel')
# id,names 
for row in reader:
    id = row[0]
    type = row[1] # Currently unused, always 'compound' if other types support, style differently?
    names = row[2:]
    # If this matches one of our metabolites, store the id
    for name in names:
        if name == '': # Blank columns
            break
        # We found it by one of the names
        if name.lower() in metabolites:
            metabolite_ids.add(id)
            metabolites_unmatched.remove(name.lower())
            break


print "Matched %d/%d metabolites to database:" % ( len(metabolite_ids), len(metabolites) )
print "%s (Not found: %s)" % ( ', '.join( metabolite_ids ), ', '.join(metabolites_unmatched) ) 
        
# We have a list of metabolite ids in database format; now iterate the reactions and check for them being
# used in each pathway. Accumulate a list of pathways, then delete duplicates

pathways = defaultdict( set )

reader = csv.reader( open(os.path.join(dirpath[0],'reactions.csv'),'rU'), delimiter=',', dialect='excel')
#id,origin,dest,enzyme,dir,pathway
for id, origin, dest, smtin, smtout, enzyme, dir, mpathway in reader:
    # Pathway links are | separated, the edge is in 'both' pathways
    # the origin in the first, the destination in the second
    mtins =     origin.split('|') # More than one metabolite into reaction, separated by |
    mtouts =    dest.split('|')
    #smtins =    smtin.split('|')
    #smtouts =   smtout.split('|')

    reactants = set()
    # Extend set using union operator
    reactants |= set( mtins )
    reactants |= set( mtouts )

    # Get intersection of our reactants with known metabolites
    
    reactants = reactants & metabolite_ids

    if len( reactants ) > 0:
        pathways[ mpathway ] |= reactants


filtered_pathways = { x:n for x,n in pathways.items() if len(n) >= options.min_number_metabolites_per_pathway }
filtered_pathways = list( filtered_pathways.keys() )

print "Found %d pathways (filtered to %d by minimum matching of %d metabolites):" % ( len(pathways), len(filtered_pathways), options.min_number_metabolites_per_pathway )
print '|'.join(filtered_pathways)
            
