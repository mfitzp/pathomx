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

import ui, utils
from data import DataSet, DataDefinition

import numpy as np

from db import Compound, Gene, Protein




class PathwayMiningView( ui.AnalysisView ):
    def __init__(self, plugin, parent, **kwargs):
        super(PathwayMiningView, self).__init__(plugin, parent, **kwargs)

        # Define automatic mapping (settings will determine the route; allow manual tweaks later)
        
        self.addDataToolBar()
        self.addExperimentToolBar()
        
        self.data.add_interface('output')
        self.table = QTableView()        
        self.table.setModel( self.data.o['output'].as_table )
        self.tabs.addTab(self.table, 'Table')
        # Setup data consumer options
        self.data.consumer_defs.append( 
            DataDefinition('input', {
            'entities_t':   (None,['Compound','Gene','Protein']), 
            })
        )
        
        self.data.source_updated.connect( self.onDataChanged ) # Auto-regenerate if the source data is modified
        self.data.consume_any_of( self.m.datasets[::-1] ) # Try consume any dataset; work backwards
        self.generate()

    def generate(self):
        self.suggest()


    def onMiningSettings(self):
        """ Open the mining setup dialog to define conditions, ranges, class-comparisons, etc. """
        dialog = dialogMiningSettings(parent=self)
        ok = dialog.exec_()
        if ok:
            self.config.setValue('/Data/MiningDepth', dialog.sb_miningDepth.value() )
            self.config.setValue('/Data/MiningType', METAPATH_MINING_TYPE_CODE[ dialog.cb_miningType.currentIndex() ] )
            self.config.setValue('/Data/MiningRelative', dialog.xb_miningRelative.isChecked() )
            self.config.setValue('/Data/MiningShared', dialog.xb_miningShared.isChecked() )

            # Update the toolbar dropdown to match
            self.sb_miningDepth.setValue( dialog.sb_miningDepth.value() )        

    def onModifyMiningDepth(self):
        """ Change mine depth via toolbar spinner """    
        self.config.setValue('/Data/MiningDepth', self.sb_miningDepth.value())

            
    def onDefineExperiment(self):
        """ Open the experimental setup dialog to define conditions, ranges, class-comparisons, etc. """
        dialog = dialogDefineExperiment(parent=self)
        ok = dialog.exec_()
        if ok:
            # Regenerate the graph view
            self.experiment['control'] = dialog.cb_control.currentText()
            self.experiment['test'] = dialog.cb_test.currentText()      
        
            # Update toolbar to match any change caused by timecourse settings
            self.update_view_callback_enabled = False # Disable to stop multiple refresh as updating the list
            self.cb_control.clear()
            self.cb_test.clear()

            self.cb_control.addItems( [dialog.cb_control.itemText(i) for i in range(dialog.cb_control.count())] )
            self.cb_test.addItems( [dialog.cb_test.itemText(i) for i in range(dialog.cb_test.count())] )
            
            #if dialog.le_timecourseRegExp.text() != '':
            #    self.experiment['timecourse'] = dialog.le_timecourseRegExp.text()
            #elif 'timecourse' in self.experiment:                
            #    del(self.experiment['timecourse'])
        
            # Update the toolbar dropdown to match
            self.cb_control.setCurrentIndex( self.cb_control.findText( self.experiment['control'] ) )
            self.cb_test.setCurrentIndex( self.cb_test.findText( self.experiment['test'] ) )
                  
            analysisv = analysisCompoundView( self )
            analysisv.generate()
            self.tabs.addTab( analysisv.browser, '&Compounds' )
            
            analysise = analysisEquilibriaView( self )
            analysise.generate()
            self.tabs.addTab( analysise.browser, 'E&quilibria' )

            analysisw = analysisEnergyWasteView( self )
            analysisw.generate()
            self.tabs.addTab( analysisw.browser, '&Energy and Waste' )
            
            #self.tabs.addTab( analysisv.browser, 'Genes' )
            #self.tabs.addTab( analysisv.browser, 'Proteins' )            
    
        
    def onModifyExperiment(self):
        """ Change control or test settings from toolbar interaction """
        # Cheat a bit, simply change both - only one will be incorrect
        self._experiment_control = self.toolbars['experiment'].cb_control.currentText()
        self._experiment_test = self.toolbars['experiment'].cb_test.currentText()
        self.generate()


    # Generate pathway suggestions from the database based on a given data analysis (use set options)
    def suggest(self, mining_type='c', mining_depth=5):
        self.setWorkspaceStatus('active')

        # Iterate all the compounds in the current analysis
        # Assign score to each of the compound's pathways
        # Sum up, crop and return a list of pathway_ids to display
        # Pass this in as the list to view
        # + requested pathways, - excluded pathways
        dsi = self.data.get('input')
        dso = DataSet()       
        db = self.m.db

        pathway_scores = defaultdict( int )
        print "Mining using '%s'" % mining_type
        
        for n, entity in enumerate(dsi.entities[1]):
            if entity == None:
                continue # Skip

            score = dsi.data[0,n]
            #score = self.analysis[ m_id ]['score']
            
            # 1' neighbours; 2' neighbours etc. add score
            # Get a list of methods in connected reactions, add their score % to this compound
            # if m_id in db.compounds.keys():
            #    n_compounds = [r.compounds for r in db.compounds[ m_id ].reactions ]
            #     print n_compounds
            #     n_compounds = [m for ml in n_compounds for m in ml if n_m.id in self.analysis and m.id != m_id ]
            #     for n_m in n_compounds:
            #         score += self.analysis[ n_m.id ]['score'] * 0.5

            # Get the entity's pathways
            pathways = entity.pathways
            if pathways == []:
                continue   
                
            if "s" in mining_type:
                # Share the change score between the associated pathways
                # this prevents compounds having undue influence
                score = score / len(pathways)    
        
            for p in pathways:
                mining_val = {
                    'c': abs( score),
                    'u': max( 0, score),
                    'd': abs( min( 0, score ) ),
                    'm': 1.0
                    }
                pathway_scores[ p ] += mining_val[ mining_type[0] ]
                    
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
            print "- %d. %s [%.2f]" % (n+1, p[0].name, p[1])

        #self.analysis['mining_ranked_remaining_pathways'] = []
                        
        #if remaining_pathways:
        #    print "Note: Next pathways by current scoring method are..."
        #    for n2,p in enumerate(remaining_pathways):
        #        print "- %d. %s [%.2f]" % (n+n2+1, db.pathways[ p[0] ].name, p[1])
        #        self.analysis['mining_ranked_remaining_pathways'].append( p[0] )

        #self.analysis_suggested_pathways = [db.pathways[p[0]] for p in pathway_scorest]
        dso.empty(size=(1, len(keep_pathways)))
        dso.entities[0] = [k for k,v in keep_pathways]
        dso.labels[0] = [k.name for k,v in keep_pathways]
        dso.data = np.array( [v for k,v in keep_pathways] )

        self.data.put('output',dso)

        self.setWorkspaceStatus('done')
        self.clearWorkspaceStatus()
        
        
class PathwayMining(AnalysisPlugin):

    def __init__(self, **kwargs):
        super(PathwayMining, self).__init__(**kwargs)
        self.register_app_launcher( self.app_launcher )

    def app_launcher(self):
        #self.load_data_file()
        self.instances.append( PathwayMiningView( self, self.m ) ) 
