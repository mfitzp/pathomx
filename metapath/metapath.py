#!/usr/bin/env python
import os, sys, re, math
import csv
import pydot
import numpy as np

from optparse import OptionParser
from collections import defaultdict
import operator

# MetaPath classes and handlers
import utils, db, data, core

from db import databaseManager

#import HTMLParser
#pars = HTMLParser.HTMLParser()

def main():

    parser = OptionParser()

    parser.add_option("-f", "--file", dest="file", default=None,
                      help="load data file by name, name root used as basis for output graph filenames", metavar="FILE")

    parser.add_option("-p", "--pathways", dest="pathways", default=False,
                      help="pathways to map into graph, each pathway is subgraph")

    parser.add_option("--not", dest="hide_pathways", default=False,
                      help="pathways to exclude")

    parser.add_option("-c", "--control", dest="control", default=None,
                      help="regex to match control classes (mean will be used for comparison)")

    parser.add_option("-t", "--test", dest="test", default=None,
                      help="regex to match test classes (mean will be used for comparison)")

    #parser.add_option("-s", "--search", dest="search", default=None,
    #                  help="only show classes matching this regex")

    parser.add_option("-e", "--show-enzymes", action="store_true", dest="show_enzymes", default=False,
                      help="show reaction enzymes on edges")
    parser.add_option("-2", "--show-secondary", action="store_true", dest="show_secondary", default=False,
                      help="show secondary metabolites on edges")

    parser.add_option("-m", "--mining", action="store_true", dest="mining", default=False,
                      help="prune pathways")

    parser.add_option("--md", type="int", dest="mining_depth", default=5,
                      help="prune pathways to this depth")

    parser.add_option("--mt", dest="mining_type", default='c',
                      help="prune pathways by relative (m)etabolite numbers (c)hange metabolite concentration (u)p (d)own; append r (e.g (ar)) to scale relative to the number of metabolites in a given pathway; s to share metabolite score between pathways")

    parser.add_option("-o", "--output", dest="output", default='png',
                      help="output format for the generated graph, defaults to png")

    parser.add_option("--no-splines", action="store_false", dest="splines", default=True,
                      help="don't use splines to draw lines")

    parser.add_option("--colorcode", action="store_true", dest="colorcode", default=False,
                      help="color code reaction sets")

    parser.add_option("--cluster", dest='cluster_by', default = 'pathway', 
                      help="cluster type (pathway|compartment)")


    parser.add_option("--network-analysis", action="store_true", dest="show_network_analysis", default=False,
                      help="show metabolite connections network analysis highlights")
                  
    parser.add_option("--focus", dest="focus", default=False,
                      help="only show edges linking to matching metabolites")

    parser.add_option("--pathway-links", action="store_true", dest="show_pathway_links", default=False,
                      help="show links to currently hidden pathways")

    parser.add_option("--fit_paper", dest="fit_paper", default='None',
                      help="scale graph to fit defined ISO page format")

                  
    #parser.add_option("-r", "--report", action="store_true", dest="generate_report", default=False,
    #                  help="generate summary report of key metabolites, enzymes (flux), small MW balance")           

    (options, args) = parser.parse_args()

    # Load metabolite, reactions, pathways into database
    dbo = db.databaseManager()

    all_pathways = [p.name for k,p in dbo.pathways.items()]

    if not options.pathways:
        print "Specify pathways to generate from: %s" % ', '.join( all_pathways )
        exit()

    if options.pathways:
        pathway_re = re.compile('.*(' + options.pathways + ').*', flags=re.IGNORECASE)
        pathways = filter(lambda x:pathway_re.match(x), all_pathways)
        print "Generating for pathways: %s" % ', '.join(pathways)
        # Convert to id's (match -gui)
        pathways = [ p for k,p in dbo.pathways.items() if p.name in pathways ]

    # Load an process datafile
    if options.file and options.control and options.test:
    # Currently we're only supporting control vs. test mapping, would be nice to do single datasets;
    # would need some alternative processing (e.g. comparing to a zero control set)
        datao = data.dataManager(options.file)
    
        # Translate using data identities
        datao.translate(dbo)
        classes = dict()
        classes['control'] = list()
        classes['test'] = list()

        for label in datao.classes:
    
            match = re.search(options.control, label)
            if match:
                classes['control'].append(label)      
    
            match = re.search(options.test, label)
            if match:
                classes['test'].append(label)  

        print "Filter matching classes gave control '%s' and test '%s'" % (', '.join(classes['control']), ', '.join( classes['test']) )
    
        datao.analyse(classes['control'], classes['test'])
    
    else:
        datao = None


    # Add mining pathways
    if datao and options.mining:
        suggested_pathways = datao.suggest( db, mining_type=options.mining_type, mining_depth=options.mining_depth)
        pathways += suggested_pathways

    if options.hide_pathways:
        hide_pathways_re = re.compile('.*(' + options.not_pathways + ').*', flags=re.IGNORECASE)
        hide_pathways = filter(lambda x:hide_pathways_re.match(x), all_pathways)
        print "Removing pathways: %s" % ', '.join(hide_pathways)
        # Convert to id's (match -gui)
        hide_pathways = [ p for k,p in dbo.pathways.items() if p.name in hide_pathways ]
        pathways = [p for p in pathways if p.id not in hide_pathways]


    # PROCESS THE GRAPH
    if datao:
        graph = core.generator( pathways, options, dbo, analysis=datao.analysis) #, layout=self.layout) 
    else:
        graph = core.generator( pathways, options, dbo) #, layout=self.layout) 
    

    # Extract file root from the edge file name
    if options.file:
        filebase = os.path.splitext(options.file)[0]
        [null, sep, string ] = filebase.partition('-')
        filesuff = sep + string
    else:
        filebase = ''
        filesuff = ''

    if options.control and options.test:
        additional_info = "-%s-%s" % ( options.control, options.test )
    else:
        additional_info = ''

    #graph.write('pathway%s%s.dot' % (additional_info, filesuff), format='dot', prog='neato')
    graph.write('pathway%s%s.%s' % (additional_info, filesuff, options.output), format=options.output, prog='neato')

if __name__ == "__main__":
    main()
