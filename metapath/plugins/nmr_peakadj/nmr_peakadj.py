# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# Import PyQt5 classes
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWebKit import *
from PyQt5.QtNetwork import *
from PyQt5.QtWidgets import *
from PyQt5.QtPrintSupport import *

import os, copy

from plugins import ProcessingPlugin

import numpy as np
import nmrglue as ng

import ui, db, utils
from data import DataSet, DataDefinition


class NMRPeakAdjView( ui.DataView ):
    def __init__(self, plugin, parent, auto_consume_data=True, **kwargs):
        super(NMRPeakAdjView, self).__init__(plugin, parent, **kwargs)
        
        self.addDataToolBar()
        self.addFigureToolBar()
        
        self.data.add_input('input') # Add input slot        
        self.data.add_output('output')
        self.data.add_output('region')
        self.table.setModel(self.data.o['output'].as_table)

        self.region =  ui.QWebViewExtend(self)
        self.tabs.addTab(self.region, 'Region')
    
        
        # Setup data consumer options
        self.data.consumer_defs.append( 
            DataDefinition('input', {
            'labels_n':     ('>1', None),
            'entities_t':   (None, None), 
            'scales_t': (None, ['float']),
            })
        )
        
        # Define default settings for pathway rendering
        self.config.set_defaults({
            # Peak target
            'peak_target': 'TMSP',
            'peak_target_ppm': 0.0,
            'peak_target_ppm_tolerance': 0.5,
            # Shifting
            'shifting_enabled': True,
            
            # Scaling
            'scaling_enabled': True,
        })        
        

        th = self.addToolBar('Peak Adjustments')

        self.peak_targets = {
            'TMSP': (0.0, 0.25),
            'Creatinine @4.0': (4.045, 0.25),
            'Creatinine @3.0': (3.030, 0.25),
            'Custom': (None, None),
        }
        
        self.region_dso = None

        self._automated_update_config = False
        self.peak_target_cb = QComboBox()
        self.peak_target_cb.addItems( [k for k,v in self.peak_targets.items() ] )
        self.peak_target_cb.currentIndexChanged.connect(self.onSetPredefinedTarget)
        self.config.add_handler('peak_target', self.peak_target_cb )
        tl = QLabel('Target')
        tl.setIndent(5)
        th.addWidget(tl)
        th.addWidget(self.peak_target_cb)        

        self.ppm_spin = QDoubleSpinBox()
        self.ppm_spin.setDecimals(2)
        self.ppm_spin.setRange(-1,15)
        self.ppm_spin.setSuffix('ppm')
        self.ppm_spin.setSingleStep(0.05)
        self.ppm_spin.valueChanged.connect(self.onSetCustomTarget) # Additional; to handle alternation
        self.config.add_handler('peak_target_ppm', self.ppm_spin )
        th.addWidget(tl)
        th.addWidget(self.ppm_spin)

        self.ppm_tolerance_spin = QDoubleSpinBox()
        self.ppm_tolerance_spin.setDecimals(2)
        self.ppm_tolerance_spin.setRange(0,1)
        self.ppm_tolerance_spin.setSuffix('ppm')
        self.ppm_tolerance_spin.setSingleStep(0.05)
        self.ppm_tolerance_spin.valueChanged.connect(self.onSetCustomTarget) # Additional; to handle alternation
        self.config.add_handler('peak_target_ppm_tolerance', self.ppm_tolerance_spin )
        tl = QLabel('±')
        th.addWidget(tl)
        th.addWidget(self.ppm_tolerance_spin)

        th.addSeparator()  
        
        self.toggle_shift = QAction( QIcon( os.path.join(  self.plugin.path, 'icon-16.png' ) ), 'Toggle spectra shifting on and off \u2026', self.m)
        self.toggle_shift.setStatusTip('Toggle on and off spectral alignment to reference peak')
        self.toggle_shift.setCheckable( True )
        self.config.add_handler('shifting_enabled', self.toggle_shift )
        th.addAction(self.toggle_shift)
        
        self.toggle_scale = QAction( QIcon( os.path.join(  self.plugin.path, 'icon-16.png' ) ), 'Toggle spectra scaling on and off \u2026', self.m)
        self.toggle_scale.setStatusTip('Toggle on and off spectral scaling to reference peak')
        self.toggle_scale.setCheckable( True )
        self.config.add_handler('scaling_enabled', self.toggle_scale )
        th.addAction(self.toggle_scale)      
        
        th.addSeparator()  

        self.configuration = QAction( QIcon( os.path.join(  self.plugin.path, 'icon-16.png' ) ), 'Configure scale and shift parameters \u2026', self.m)
        self.configuration.setStatusTip('Set parameters for scaling and shifting to reference peak')
        #self.configuration.triggered.connect(self.onMetaboHunterSettings)
        th.addAction(self.configuration)

        self.data.source_updated.connect( self.autogenerate ) # Auto-regenerate if the source data is modified        
        if auto_consume_data:
            self.data.consume_any_of( self.m.datasets[::-1] ) # Try consume any dataset; work backwards    
        self.config.updated.connect( self.autogenerate ) # Auto-regenerate if the configuration
    
    
    def generate(self):
        dso = self.data.get('input')
        dso, dsor = self.shiftandscale( self.data.get('input') ) #, self._bin_size, self._bin_offset)
        self.data.put('output',dso)
        self.region_dso = dsor
        self.render({})
        
    def render(self, metadata):
        super(NMRPeakAdjView, self).render({})
        dsor = self.region_dso

        if dsor and float in [type(t) for t in dsor.scales[1]]:
            metadata['htmlbase'] = os.path.join( utils.scriptdir,'html')

            dso_z = zip( dsor.scales[1], dsor.entities[1], dsor.labels[1] )
            metadata['figure'] = {
                'data':zip( dsor.scales[1], dsor.data.T ), # (ppm, [dataa,datab])
                'compounds': self.build_markers( dso_z, 1, self._build_entity_cmp ),
                'labels': self.build_markers( dso_z, 2, self._build_label_cmp ),
            }

            template = self.m.templateEngine.get_template('d3/spectra.svg')
            self.region.setSVG(template.render( metadata ))

            f = open('/Users/mxf793/Desktop/test9.svg','w')
            f.write( template.render( metadata ) )
            f.close()        


    def onChangeScalingParameters(self):
        self._peak_threshold = float( self.threshold_spin.value() )
        self._peak_separation = float( self.separation_spin.value() )
        self._peak_algorithm = self.algorithm_cb.currentText()
        self.generate()

    def onSetCustomTarget(self):
        if self._automated_update_config == False:
            self.peak_target_cb.setCurrentText('Custom')
    
    def onSetPredefinedTarget(self):
        ppm, ppm_tol = self.peak_targets[ self.peak_target_cb.currentText() ]
        if ppm is not None:
            self._automated_update_config = True
            self.ppm_spin.setValue( ppm )
            self.ppm_tolerance_spin.setValue( ppm_tol )
            self._automated_update_config = False


    # Shift and scale NMR spectra to target peak
    def shiftandscale(self, dsi):
        # Get the target region from the spectra (will be using this for all calculations;
        # then applying the result to the original data)
        scale = dsi.scales[1]
        
        target_ppm = self.config.get('peak_target_ppm')
        tolerance_ppm = self.config.get('peak_target_ppm_tolerance')
        start_ppm = target_ppm - tolerance_ppm
        end_ppm = target_ppm + tolerance_ppm
        
        start = min(range(len(scale)), key=lambda i: abs(scale[i]-start_ppm))        
        end = min(range(len(scale)), key=lambda i: abs(scale[i]-end_ppm))        
        
        self.set_name('%s align @%.2f ±%.2f' % ( self.config.get('peak_target'), target_ppm, tolerance_ppm) )

        # Shift first; then scale
        d = 1 if end>start else -1
        data = dsi.data[:,start:end:d]
        region_scales = dsi.scales[1][start:end:d]
        region_labels = dsi.labels[1][start:end:d]
        region_entities = dsi.entities[1][start:end:d]
        
        print d, region_scales, region_labels, region_entities
        
        pcentre = min(range(len(region_scales)), key=lambda i: abs(region_scales[i]-target_ppm))  # Base centre point to shift all spectra to

        reference_peaks = []
        for sdata in data:
            baseline = np.max( sdata ) * .9 # 90% baseline of maximum peak within target region
            locations, scales, amps = ng.analysis.peakpick.pick(sdata, pthres=baseline, algorithm='connected', est_params = True, cluster=False, table=False)
            if len(locations) > 0:
                reference_peaks.append({
                    'location':locations[0][0], #FIXME: better behaviour when >1 peak
                    'scale':scales[0][0],
                    'amplitude':amps[0],
                })
            else:
                reference_peaks.append(None)

        print reference_peaks

        if self.config.get('shifting_enabled'):
            print 'shifting'
            # Now shift the original spectra to fit
            for n,refp in enumerate(reference_peaks):
                if refp:
                    # Shift the spectra
                    shift = (pcentre-refp['location']) * d
                    print shift
                    if shift > 0:
                        dsi.data[n, shift:-1] = dsi.data[n, 0:-(shift+1)]
                    elif shift < 0:
                        dsi.data[n, 0:shift-1] = dsi.data[n, abs(shift):-1]
                    
        
        if self.config.get('scaling_enabled'):
            # Get mean reference peak size
            reference_peak_mean = np.mean( [r['scale'] for r in reference_peaks if r ] )
            print 'Reference peak mean %s' % reference_peak_mean
            
            # Now scale; using the same peak regions & information (so we don't have to worry about something
            # being shifted out of the target region in the first step)
            for n,refp in enumerate(reference_peaks):
                if refp:
                    # Scale the spectra
                    amplitude = reference_peak_mean/refp['amplitude']
                    dsi.data[n,:] = dsi.data[n,:] * amplitude

        # -- optionally use the line widths and take max within each of these for each spectra (peak shiftiness)
        # Filter the original data with those locations and output\
        
        dsor = dsi.as_copy()
        dsor.data = data
        dsor.scales[1] = region_scales
        dsor.labels[1] = region_labels
        dsor.entities[1] = region_entities
        
        return dsi, dsor

 
class NMRPeakAdj(ProcessingPlugin):

    def __init__(self, **kwargs):
        super(NMRPeakAdj, self).__init__(**kwargs)
        self.register_app_launcher( self.app_launcher )

    def app_launcher(self, **kwargs):
        return NMRPeakAdjView( self, self.m, **kwargs )
