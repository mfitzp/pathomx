# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# Import PyQt5 classes
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWebKit import *
from PyQt5.QtNetwork import *

import numpy as np

# Renderer for GPML as SVG
from gpml2svg import gpml2svg


from plugins import VisualisationPlugin

import os
import ui, utils



class AnalysisEquilibriaView(ui.AnalysisHeatmapView):
    def __init__(self, *args, **kwargs):
        super(analysisEquilibriaView, self).__init__(*args, **kwargs)
    
        self.nucleosides = [
            ['AMP', 'ADP', 'ATP'],
            ['CMP', 'CDP', 'CTP'],
            ['GMP', 'GDP', 'GTP'],
            ['UMP', 'UDP', 'UTP'],
            ['TMP', 'TDP', 'TTP'],
            #---
            ['DAMP', 'DADP', 'DATP'],
            ['DCMP', 'DCDP', 'DCTP'],
            ['DGMP', 'DGDP', 'DGTP'],
            ['DUMP', 'DUDP', 'DUTP'],
            ['DTMP', 'DTDP', 'DTTP'],
            #---
            ['Pi', 'PPI', 'PI3','PI4'],
            #---
            ['NAD','NADP'],            
            ['NADH','NADPH'],
        ]
        
        self.proton = [
            ['NAD', 'NADH'],
            ['NADP','NADPH'],
            ['FAD','FADH','FADH2'],
        ]
        
        redox = [
            ['OXYGEN-MOLECULE', 'WATER'],
            ['', 'PROTON'],
            ['NAD', 'NADH'],
            ['NADP','NADPH'],
            ['FAD','FADH','FADH2'],
        ]
        
        proton_carriers = {'WATER':1,'PROTON':1,'NADH':1,'NADPH':1,'FADH':1,'FADH2':2} # Double count for H2

        phosphate_carriers = {
            'AMP':1, 'ADP':2, 'ATP':3,
            'GMP':1, 'GDP':2, 'GTP':4, 
            #---
            'Pi':1,  'PPI':2, 'PI3':3, 'PI4':4,
            #---
            'NADP':1, 'NADPH':1,
            }
                
        phosphate = [
            ['AMP', 'ADP'],
            ['ADP', 'ATP'],
            ['GMP', 'GDP'],
            ['GDP', 'GTP'],
            #---
            ['Pi',  'PPI'],
            ['PPI', 'PI3'],
            ['PI3', 'PI4'],
            #---
            ['NAD','NADP'],            
            ['NADH','NADPH'],
        ]
        
        # Build redox reaction table
        # Iterate database, find any reactions with a PROTON in left/right reaction
        # - or NAD->NADH or, or, or
        # If on left, swap
        # Store entry for Min,Mout
        self.redox = self.equilibrium_table_builder( proton_carriers ) 
        self.phosphate = self.equilibrium_table_builder( phosphate_carriers ) 

    def equilibrium_table_builder(self, objs):
        result = []
        for rk,r in self.parent.db.reactions.items():
            inH = sum( [objs[m.id] for m in r.smtins if m.id in objs] )
            outH = sum( [objs[m.id] for m in r.smtouts if m.id in objs] )


            balance = inH-outH
            add_it = False
            if balance > 0:
                add_it = ( r.mtins, r.mtouts )
            elif balance < 0: # Reverse
                add_it = ( r.mtouts, r.mtins )
                
            if add_it:
                for mtin in add_it[0]:
                    for mtout in add_it[1]:
                        result.append( [mtin.id, mtout.id] )  
        return result               

    def cofactor_table_builder(self, objs):
        result = []
        for p in objs:
            pin = self.parent.db.metabolites[ p[0] ] if p[0] in self.parent.db.metabolites.keys() else False
            pout = self.parent.db.metabolites[ p[1] ] if p[1] in self.parent.db.metabolites.keys() else False

            if pin and pout:
                for rk,r in self.parent.db.reactions.items():
                    add_it = False
                    if pin in r.smtins and pout in r.smtouts:
                        add_it = ( r.mtins, r.mtouts )
                    elif pout in r.smtins and pin in r.smtouts:
                        add_it = ( r.mtouts, r.mtins )

                    if add_it:
                        for mtin in add_it[0]:
                            for mtout in add_it[1]:
                                result.append( [mtin.id, mtout.id] )  

        return result

    def generate(self):

        labelsX=[ 'Phosphorylated','Dephosphorylated' ]
        labelsY=['→'.join(n) for n in self.phosphate]
        data_phosphate = self.build_heatmap_buckets( labelsX, labelsY, self.build_log2_change_table_of_classtypes( self.phosphate, labelsX ), remove_empty_rows=True, sort_data=True  )

        labelsX=[ 'Pi','PPI','PI3','PI4' ]
        labelsY=['→'.join(n) for n in self.nucleosides]
        data_nuc = self.build_heatmap_buckets( labelsX, labelsY, self.build_log2_change_table_of_classtypes( self.nucleosides, labelsX ), sort_data=True)

        labelsX=[ 'Reduced','Oxidised' ]
        labelsY=['→'.join(n) for n in self.redox]
        data_redox = self.build_heatmap_buckets( labelsX, labelsY, self.build_log2_change_table_of_classtypes( self.redox, labelsX ), remove_incomplete_rows=True, sort_data=True )

        labelsX=[ '-','H','H2' ]
        labelsY=['→'.join(n) for n in self.proton]
        data_proton = self.build_heatmap_buckets( labelsX, labelsY, self.build_log2_change_table_of_classtypes( self.proton, labelsX ), sort_data=True )
  
        self.render( {
            'htmlbase': os.path.join( utils.scriptdir,'html'),
            'figures': [ 
                        [{
                            'type':'heatmap',
                            'data':data_redox,
                            'legend':('Redox reaction balance.','Relative quantities of metabolites on oxidative and reductive reaction. \
                            Left-to-right is oxidative.'),
                            'scale':'Δlog2',
                            'n':1,
                        },[
                            [{
                                'type':'heatmap',
                                'data':data_phosphate, 
                                'legend':('Redox reaction balance.','Relative quantities of metabolites on oxidative and reductive reaction. \
                                Left-to-right is oxidative.'),
                                'scale':'Δlog2',
                                'n':2,
                            },
                            {
                                'type':'heatmap',
                                'data':data_nuc, 
                                'legend':('Nucleoside phosphorylation balance.','Relative quantities of nucleosides in each experimental class grouping. \
                                Left-to-right shows increasing phosphorylation.'),
                                'scale':'Δlog2',
                                'n':3,
                            }],[{
                            'type':'heatmap',
                            'data':data_proton, 
                            'legend':('Redox carrier  balance.','Relative quantities of redox potential carriers. \
                            Left-to-right shows increasing reduction.'),
                            'scale':'Δlog2',
                            'n':4,
                            }],
                        ],
                        ],
                        ],
            'figure':  {
                            'type':'heatmap',
                            'data':data_redox,
                            'legend':('Redox reaction balance.','Relative quantities of metabolites on oxidative and reductive reaction. \
                            Left-to-right is oxidative.'),
                            'scale':'Δlog2',
                            'n':1,
                        },                        
        })
        


class analysisMetaboliteView(ui.AnalysisHeatmapView):
    def generate(self):
        # Sort by scores
        ms = [ (k,v['score']) for k,v in self.parent.data.analysis.items() ]
        sms = sorted(ms,key=lambda x: abs(x[1]), reverse=True )
        metabolites = [m for m,s in sms]

        labelsY = metabolites[:30]
        labelsX = sorted( self.parent.data.quantities[labelsY[0]].keys() )

        data1 = self.build_heatmap_buckets( labelsX, labelsY, self.build_log2_change_control_vs_multi(labelsY, labelsX), remove_empty_rows=True, sort_data=True)
        data2 = self.build_heatmap_buckets( labelsX, labelsY, self.build_raw_change_control_vs_multi(labelsY, labelsX), remove_empty_rows=True, sort_data=True)
  
        self.render( {
            'htmlbase': os.path.join( utils.scriptdir,'html'),
            'figures': [[
                        {
                            'type':'heatmap',
                            'data':data1, 
                            'legend':('Relative change in metabolite concentration vs. control (%s) under each experimental condition.' % self.parent.experiment['control'],
                                      'Scale indicates Log2 concentration change in original units, mean centered to zero. Red up, blue down.'),
                            'scale':'Δlog2',
                            'n':1,                            
                        },
                        {
                            'type':'heatmap',
                            'data':data2, 
                            'legend':('Raw metabolite concentration changes vs. control (%s) under each experimental condition.' % self.parent.experiment['control'],
                                    'Scale indicates linear concentration change in original unites, mean centered to zero. Red up, blue down.'),
                            'scale':'Δlog2',
                            'n':2,
                        },
                    ]],
        })
        



class analysisEnergyWasteView(ui.AnalysisHeatmapView):

    def generate(self):
        # Standard energy sources (CHO)
        m_energy = ['GLC','GLN',
        # Standard energy modulators (co-factors, carriers, etc.)
                    'CARNITINE',
        # Standard waste metabolites
                    'L-LACTATE',]

        # Build table of metabolic endpoints
        # i.e. metabolites not at the 'in' point of any reactions (or in a bidirectional)
        endpoints = []
        for k,m in self.parent.db.metabolites.items():
            if m.type == 'compound':
                for r in m.reactions:
                    if m in r.mtins or r.dir == 'both':
                        break    
                else:
                    # Only if we find no reactions
                    endpoints.append(m.id)


        labelsY = endpoints
        labelsX = sorted( self.parent.data.quantities[labelsY[0]].keys() ) 
        endpoint_data = self.build_heatmap_buckets( labelsX, labelsY, self.build_log2_change_control_vs_multi( labelsY, labelsX), sort_data=True )

        labelsY = m_energy
        energy_data = self.build_heatmap_buckets( labelsX, labelsY, self.build_log2_change_control_vs_multi( labelsY, labelsX), sort_data=True )

        metadata = { 'htmlbase': os.path.join( utils.scriptdir,'html'),
                   # Buckets is an array x,y,value x = class, y metabolite, value 
                    'figures': [[
                                {
                                    'type':'heatmap',
                                    'data':endpoint_data,
                                    'legend':('Relative change in concentration of metabolic endpoints vs. control (%s) under each experimental condition.' % self.parent.experiment['control'],
                                              'Scale indicates Log2 concentration change in original units, mean centered to zero. Red up, blue down. Metabolic endpoint in this context refers to \
                                              metabolites for which there exists no onward reaction in the database.'),
                                    'scale':'Δlog2',
                                    'n':1,
                                    
                                },
                                {
                                    'type':'heatmap',
                                    'data':energy_data,
                                    'legend':('Relative change in concentration of common energy sources, carriers and sinks vs. control (%s) under each experimental condition.' % self.parent.experiment['control'],
                                              'Scale indicates Log2 concentration change in original units, mean centered to zero. Red up, blue down.'),
                                    'scale':'Δlog2',
                                    'n':2,
                                }                    
                               ]],                   
                    }                   

        self.render(metadata)
        
        
        
        
        
        

# Class for data visualisations using GPML formatted pathways
# Supports loading from local file and WikiPathways
class BarView(AnalysisEquilibriaView):
    def __init__(self, plugin, parent, gpml=None, svg=None, **kwargs):
        super(BarView, self).__init__(parent, **kwargs)

        self.plugin = plugin
        self.m = parent
         
        self.generate()
        #self.o.show() 
        #self.plugin.register_url_handler( self.id, self.url_handler )
        
        # Horrible
        icon = QIcon.fromTheme("data", QIcon( os.path.join( utils.scriptdir,'icons',
                os.path.join( os.path.dirname( os.path.realpath(__file__) ), 'bar-type-icon.png') 
                ) ) )       
        self.workspace_item = self.m.addWorkspaceItem(self.browser, self.plugin.default_workspace_category, 'Bar', is_selected=True, icon=icon) #, icon = None)






class Bar(VisualisationPlugin):

    def __init__(self, **kwargs):
        super(Bar, self).__init__(**kwargs)
        self.register_app_launcher( self.app_launcher )
    
    # Create a new instance of the plugin viewer object to handle all behaviours
    def app_launcher(self):
        self.instances.append( HeatmapView( self, self.m ) )
