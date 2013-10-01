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

import numpy as np

# Renderer for GPML as SVG
from gpml2svg import gpml2svg


from plugins import VisualisationPlugin

import os
import ui, utils
from data import DataSet, DataDefinition



class AnalysisMetaboliteView(ui.AnalysisHeatmapView):
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
class HeatmapView(ui.AnalysisHeatmapView):
    def __init__(self, plugin, parent, **kwargs):
        super(HeatmapView, self).__init__(plugin, parent, **kwargs)
         
        self.addDataToolBar()
        self.addFigureToolBar()
            
        # Setup data consumer options
        self.data.consumer_defs.append( 
            DataDefinition('input', {
            'entities_t':   (None,['Compound']), 
            })
        )
        
            
        t = self.addToolBar('Heatmap')
        t.hm_control = QComboBox()
        t.hm_control.currentIndexChanged.connect(self.onChangeHeatmap)
        self.initialise_predefined_views()
        t.hm_control.addItems( [h for h in self.predefined_heatmaps.keys()] )
        t.addWidget(t.hm_control)
        self.toolbars['heatmap'] = t
        
        self.data.consume_any_of( self.m.datasets[::-1] ) # Try consume any dataset; work backwards

        self.data.source_updated.connect( self.generate ) # Auto-regenerate if the source data is modified
        self.generate()

    def equilibrium_table_builder(self, objs):
        result = []
        for rk,r in self.m.db.reactions.items():
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
            pin = self.m.db.metabolites[ p[0] ] if p[0] in self.m.db.metabolites.keys() else False
            pout = self.m.db.metabolites[ p[1] ] if p[1] in self.m.db.metabolites.keys() else False

            if pin and pout:
                for rk,r in self.m.db.reactions.items():
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


    # Build lookup tables for pre-defined views (saves regenerating on view)
    def initialise_predefined_views(self):
        
        self._show_predefined_heatmap = 'Phosphorylation'

        self.predefined_heatmaps = {
            'Phosphorylation': self._phosphorylation,
            'Phosphate balance': self._phosphate_balance,
            'Redox': self._redox,
            'Proton Balance': self._proton_balance,
            'Energy/Waste': self._energy_waste,
            'Top Metabolites': self._top_metabolites,
            'Top Metabolites (+)': self._top_metabolites_up,
            'Top Metabolites (-)': self._top_metabolites_down,
            }


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
        
        self.redox = [
            ['OXYGEN-MOLECULE', 'WATER'],
            ['', 'PROTON'],
            ['NAD', 'NADH'],
            ['NADP','NADPH'],
            ['FAD','FADH','FADH2'],
        ]

        self.phosphate = [
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
        
        proton_carriers = {'WATER':1,'PROTON':1,'NADH':1,'NADPH':1,'FADH':1,'FADH2':2} # Double count for H2

        phosphate_carriers = {
            'AMP':1, 'ADP':2, 'ATP':3,
            'GMP':1, 'GDP':2, 'GTP':4, 
            #---
            'Pi':1,  'PPI':2, 'PI3':3, 'PI4':4,
            #---
            'NADP':1, 'NADPH':1,
            }
                

        # Build redox reaction table
        # Iterate database, find any reactions with a PROTON in left/right reaction
        # - or NAD->NADH or, or, or
        # If on left, swap
        # Store entry for Min,Mout
        self.redox = self.equilibrium_table_builder( proton_carriers ) 
        self.phosphate = self.equilibrium_table_builder( phosphate_carriers ) 

    def _phosphorylation(self):
        dso = self.data.get('input')
        return self.build_heatmap_buckets( [ 'Phosphorylated','Dephosphorylated' ], [' → '.join(n) for n in self.phosphate], self.build_change_table_of_entitytypes( dso, self.phosphate, [ 'Phosphorylated','Dephosphorylated' ] ), remove_empty_rows=True, sort_data=True  )

    def _phosphate_balance(self):
        dso = self.data.get('input')
        return self.build_heatmap_buckets( [ 'Pi','PPI','PI3','PI4' ], [' → '.join(n) for n in self.nucleosides], self.build_change_table_of_entitytypes( dso, self.nucleosides, [ 'Pi','PPI','PI3','PI4' ] ), sort_data=True)

    def _redox(self):
        dso = self.data.get('input')
        return self.build_heatmap_buckets( [ 'Reduced','Oxidised' ], [' → '.join(n) for n in self.redox], self.build_change_table_of_entitytypes( dso, self.redox, [ 'Reduced','Oxidised' ] ), remove_incomplete_rows=True, sort_data=True )

    def _proton_balance(self):
        dso = self.data.get('input')
        return self.build_heatmap_buckets( [ '-','H','H2' ], [' → '.join(n) for n in self.proton], self.build_change_table_of_entitytypes( dso, self.proton, [ '-','H','H2' ] ), sort_data=True )
    
    def _energy_waste(self):
        dso = self.data.get('input')
        return non

    def _top_metabolites(self, fn=abs):
        dso = self.data.get('input')
        # Flatten data input (0 dim) to get average 'score' for each metabolite; then take top 30
        fd = np.mean( dso.data, axis=0 )
        fdm = zip( dso.labels[1], fd )
        sms = sorted(fdm,key=lambda x: fn(x[1]), reverse=True )
        metabolites = [m for m,s in sms]

        labelsY = metabolites[:30]
        labelsX = dso.classes[0]

        return self.build_heatmap_buckets( labelsX, labelsY, self.build_change_table_of_classes(dso, labelsY, labelsX), remove_empty_rows=True, sort_data=True)

        #return self.build_heatmap_buckets( labelsX, labelsY, self.build_log2_change_control_vs_multi(labelsY, labelsX), remove_empty_rows=True, sort_data=True)
        #data2 = self.build_heatmap_buckets( labelsX, labelsY, self.build_raw_change_control_vs_multi(labelsY, labelsX), remove_empty_rows=True, sort_data=True)
    
    def _top_metabolites_up(self):
        fn = lambda x: x if x>0 else 0
        return self._top_metabolites(fn)

    def _top_metabolites_down(self):
        fn = lambda x: abs(x) if x<0 else 0
        return self._top_metabolites(fn)


    def generate(self):
        self.setWorkspaceStatus('active')
    
        self.render( {
            'htmlbase': os.path.join( utils.scriptdir,'html'),
            'figure':  {
                            'type':'heatmap',
                            'data': self.predefined_heatmaps[ self._show_predefined_heatmap ](),
                        },                        
        }, template_name='heatmap')

        self.setWorkspaceStatus('done')
        self.clearWorkspaceStatus()
        
    def onChangeHeatmap(self):
        self._show_predefined_heatmap = self.toolbars['heatmap'].hm_control.currentText()
        self.set_name( self._show_predefined_heatmap )
        self.generate()
        
        


class Heatmap(VisualisationPlugin):

    def __init__(self, **kwargs):
        super(Heatmap, self).__init__(**kwargs)
        self.register_app_launcher( self.app_launcher )
    
    # Create a new instance of the plugin viewer object to handle all behaviours
    def app_launcher(self):
        self.instances.append( HeatmapView( self, self.m ) )
        

                     
