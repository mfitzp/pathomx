# -*- coding: utf-8 -*-

import os, copy

import numpy as np
import nmrglue as ng

import pathomx.ui as ui
import pathomx.db as db
import pathomx.utils as utils

from pathomx.plugins import ProcessingPlugin
from pathomx.data import DataSet, DataDefinition
from pathomx.views import MplSpectraView
from pathomx.qt import *


# Dialog box for Metabohunter search options
class PeakAdjConfigPanel(ui.ConfigPanel):
    
    def __init__(self, *args, **kwargs):
        super(PeakAdjConfigPanel, self).__init__(*args, **kwargs)        

        self.peak_targets = {
            'TMSP': (0.0, 0.25),
            'Creatinine @4.0': (4.045, 0.25),
            'Creatinine @3.0': (3.030, 0.25),
            'Custom': (None, None),
        }
        
        vw = QGridLayout()
        self.peak_target_cb = QComboBox()
        self.peak_target_cb.addItems( [k for k,v in list(self.peak_targets.items()) ] )
        self.peak_target_cb.currentIndexChanged.connect(self.onSetPredefinedTarget)
        self.config.add_handler('peak_target', self.peak_target_cb )
        vw.addWidget(self.peak_target_cb,0,0,1,2)        

        self.ppm_spin = QDoubleSpinBox()
        self.ppm_spin.setDecimals(2)
        self.ppm_spin.setRange(-1,15)
        self.ppm_spin.setSuffix('ppm')
        self.ppm_spin.setSingleStep(0.05)
        self.ppm_spin.valueChanged.connect(self.onSetCustomTarget) # Additional; to handle alternation
        self.config.add_handler('peak_target_ppm', self.ppm_spin )
        vw.addWidget(self.ppm_spin,1,1,1,1)

        self.ppm_tolerance_spin = QDoubleSpinBox()
        self.ppm_tolerance_spin.setDecimals(2)
        self.ppm_tolerance_spin.setRange(0,1)
        self.ppm_tolerance_spin.setSuffix('ppm')
        self.ppm_tolerance_spin.setSingleStep(0.05)
        self.ppm_tolerance_spin.valueChanged.connect(self.onSetCustomTarget) # Additional; to handle alternation
        self.config.add_handler('peak_target_ppm_tolerance', self.ppm_tolerance_spin )
        tl = QLabel('±')
        tl.setAlignment(Qt.AlignRight)
        vw.addWidget(tl,2,0,1,1)
        vw.addWidget(self.ppm_tolerance_spin,2,1,1,1)

        gb = QGroupBox('Peak target')
        gb.setLayout(vw)
        self.layout.addWidget(gb)

        vw = QVBoxLayout()
        self.toggle_shift = QPushButton( QIcon( os.path.join(  self.v.plugin.path, 'icon-16.png' ) ), 'Shift spectra', self.m)
        self.toggle_shift.setCheckable( True )
        self.config.add_handler('shifting_enabled', self.toggle_shift )
        vw.addWidget(self.toggle_shift)
        
        self.toggle_scale = QPushButton( QIcon( os.path.join(  self.v.plugin.path, 'icon-16.png' ) ), 'Scale spectra', self.m)
        self.toggle_scale.setCheckable( True )
        self.config.add_handler('scaling_enabled', self.toggle_scale )
        vw.addWidget(self.toggle_scale)    
         
        gb = QGroupBox('Toggle shift and scale')
        gb.setLayout(vw)
        self.layout.addWidget(gb)
        
        self.finalise()
        

    def onSetCustomTarget(self):
        if self._automated_update_config == False:
            self.peak_target_cb.setCurrentText('Custom')        
         
    def onSetPredefinedTarget(self):
        ppm, ppm_tol = self.peak_targets[ self.peak_target_cb.currentText() ]
        if ppm is not None:
            self._automated_update_config = True
            self.config.set('peak_target_ppm', ppm)
            self.config.set('peak_target_ppm_tolerance', ppm_tol)
            self._automated_update_config = False


class NMRPeakAdjApp( ui.DataApp ):

    def __init__(self, **kwargs):
        super(NMRPeakAdjApp, self).__init__(**kwargs)
        
        self.addDataToolBar()
        self.addFigureToolBar()
        
        self.data.add_input('input') # Add input slot        
        self.data.add_output('output')
        self.data.add_output('region')
        self.table.setModel(self.data.o['output'].as_table)

        self.views.addView(MplSpectraView(self), 'View')
        self.views.addView(MplSpectraView(self), 'Region')
    
        
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
        

        self.region_dso = None
        self._automated_update_config = False

        self.addConfigPanel( PeakAdjConfigPanel, 'Settings')

        self.finalise()
    
    def generate(self,input=None):
        dso, dsor = self.shiftandscale( input ) #, self._bin_size, self._bin_offset)
        return {'output':dso,'region':dsor}

    def prerender(self,output,region):
        return {
            'View':{'dso':output},
            'Region':{'dso':region},
            }




    # Shift and scale NMR spectra to target peak
    def shiftandscale(self, dsi):
        # Get the target region from the spectra (will be using this for all calculations;
        # then applying the result to the original data)
        scale = dsi.scales[1]
        
        target_ppm = self.config.get('peak_target_ppm')
        tolerance_ppm = self.config.get('peak_target_ppm_tolerance')
        start_ppm = target_ppm - tolerance_ppm
        end_ppm = target_ppm + tolerance_ppm
        
        start = min(list(range(len(scale))), key=lambda i: abs(scale[i]-start_ppm))        
        end = min(list(range(len(scale))), key=lambda i: abs(scale[i]-end_ppm))        
        
        self.set_name('%s align @%.2f ±%.2f' % ( self.config.get('peak_target'), target_ppm, tolerance_ppm) )

        # Shift first; then scale
        d = 1 if end>start else -1
        data = dsi.data[:,start:end:d]
        region_scales = dsi.scales[1][start:end:d]
        region_labels = dsi.labels[1][start:end:d]
        region_entities = dsi.entities[1][start:end:d]
        
        print(d, region_scales, region_labels, region_entities)
        
        pcentre = min(list(range(len(region_scales))), key=lambda i: abs(region_scales[i]-target_ppm))  # Base centre point to shift all spectra to

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

        print(reference_peaks)

        if self.config.get('shifting_enabled'):
            print('shifting')
            # Now shift the original spectra to fit
            for n,refp in enumerate(reference_peaks):
                if refp:
                    # Shift the spectra
                    shift = (pcentre-refp['location']) * d
                    print(shift)
                    if shift > 0:
                        dsi.data[n, shift:-1] = dsi.data[n, 0:-(shift+1)]
                    elif shift < 0:
                        dsi.data[n, 0:shift-1] = dsi.data[n, abs(shift):-1]
                    
        
        if self.config.get('scaling_enabled'):
            # Get mean reference peak size
            reference_peak_mean = np.mean( [r['scale'] for r in reference_peaks if r ] )
            print('Reference peak mean %s' % reference_peak_mean)
            
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
        NMRPeakAdjApp.plugin = self
        self.register_app_launcher( NMRPeakAdjApp )
