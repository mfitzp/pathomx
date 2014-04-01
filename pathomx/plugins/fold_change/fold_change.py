# -*- coding: utf-8 -*-
from __future__ import division

from collections import defaultdict

import os
from copy import copy
import numpy as np

import pathomx.ui as ui
import pathomx.db as db
import pathomx.utils as utils

from pathomx.data import DataSet, DataDefinition
from pathomx.plugins import AnalysisPlugin
from pathomx.qt import *


class FoldChangeApp(ui.AnalysisApp):

    def __init__(self, **kwargs):
        super(FoldChangeApp, self).__init__(**kwargs)
        # Define automatic mapping (settings will determine the route; allow manual tweaks later)

        self.addDataToolBar()
        self.addExperimentToolBar()

        self.data.add_output('output')
        self.table = QTableView()
        self.table.setModel(self.data.o['output'].as_table)

        self.views.addView(self.table, 'Table')

        self.register_url_handler(self.url_handler)

        self.data.add_input('input')  # Add input slot
        # Setup data consumer options
        self.data.consumer_defs.append(
            DataDefinition('input', {
            'classes_n': (">1", None),  # At least one class
            })
        )

        self.config.set_defaults({
            'use_baseline_minima': True,
        })

        t = self.addToolBar('Fold change')
        t.cb_baseline_minima = QCheckBox('Auto minima')
        self.config.add_handler('use_baseline_minima', t.cb_baseline_minima)
        t.cb_baseline_minima.setStatusTip('Replace zero values with half of the smallest value')
        t.addWidget(t.cb_baseline_minima)
        self.toolbars['fold_change'] = t

        self.finalise()

    def onModifyExperiment(self):
        """ Update the experimental settings for analysis then regenerate """
        self.config.set('experiment_control', self.toolbars['experiment'].cb_control.currentText())
        self.config.set('experiment_test', self.toolbars['experiment'].cb_test.currentText())

    def onDefineExperiment(self):
        """ Open the experimental setup dialog to define conditions, ranges, class-comparisons, etc. """
        dialog = dialogDefineExperiment(parent=self)
        ok = dialog.exec_()
        if ok:
            # Regenerate the graph view
            self.experiment['control'] = dialog.cb_control.currentText()
            self.experiment['test'] = dialog.cb_test.currentText()
            # Update toolbar to match any change caused by timecourse settings
            #self.update_view_callback_enabled = False # Disable to stop multiple refresh as updating the list
            #self.cb_control.clear()
            #self.cb_test.clear()

            #self.cb_control.addItems( [dialog.cb_control.itemText(i) for i in range(dialog.cb_control.count())] )
            #self.cb_test.addItems( [dialog.cb_test.itemText(i) for i in range(dialog.cb_test.count())] )

            #if dialog.le_timecourseRegExp.text() != '':
            #    self.experiment['timecourse'] = dialog.le_timecourseRegExp.text()
            #elif 'timecourse' in self.experiment:
            #    del(self.experiment['timecourse'])

            # Update the toolbar dropdown to match
            self.toolbars['experiment'].cb_control.setCurrentIndex(self.cb_control.findText(self.experiment['control']))
            self.toolbars['experiment'].cb_test.setCurrentIndex(self.cb_test.findText(self.experiment['test']))
            self.generate()

    def generate(self, input):
        dso = input
        # Get config (convenience)
        _experiment_test = self.config.get('experiment_test')
        _experiment_control = self.config.get('experiment_control')
        _use_baseline_minima = self.config.get('use_baseline_minima')


        # Get the dso filtered by class if we're not doing a global match
        if _experiment_test != "*":
            dso = dso.as_filtered(dim=0, classes=[_experiment_control, _experiment_test])

        # Replace zero values with minima (if setting)
        if _use_baseline_minima:
            #minima = np.min( dso.data[ dso.data > 0 ] ) / 2 # Half the smallest value by default
            #dsoc.data[ dsoc.data <= 0] = minima
            #print 'Fold change minima', np.min(dsoc.data)

            # Get all columns where at least 1 row != 0
            #nzmask = (dsoc.data > 0).sum(0)
            #mdata = dsoc.data[ :, nzmask != 0] # Get all non-zero columns
            # Get copy, set zeros to Nan
            #dso.data[dso.data==0] = np.nan
            dmin = np.ma.masked_less_equal(dso.data, 0).min(0) / 2
            inds = np.where(np.logical_and(dso.data == 0, np.logical_not(np.ma.getmask(dmin))))
            dso.data[inds] = np.take(dmin, inds[1])

            #minima = np.amin( dso.data[ dso.data > 0 ], axis=0 ) / 2 # Half the smallest value (in each column) by default


        # Compress to extract the two rows identified by class control and test
        dso = dso.as_summary(dim=0, match_attribs=['classes'])

        # We have a dso with two rows, one for each class
        # Process by calculating the fold change from row 1 to row 2
        # Output: delta log2, deltalog10, fold change (optionally calculate)
        data = copy(dso.data)
        ci = dso.classes[0].index(_experiment_control)
        if _experiment_test == "*":  # Do all comparisons vs. control
            tests = sorted([t for t in dso.classes[0] if t != _experiment_control])
        else:
            tests = [_experiment_test]

        for n, test in enumerate(tests):
            self.logger.debug(dso.classes[0])
            ti = dso.classes[0].index(test)

            self.logger.info('Indices for fold change: %s,%s' % (ci, ti))
            # Fold change is performed to give negative values for reductions
            # May make this optional in future?
            # i.e. t > c  fc =  t/c;   t < c    fc = -c/t

            c = data[ci, :]
            t = data[ti, :]

            dso.data[n, t > c] = np.array(t / c)[t > c]
            dso.data[n, t < c] = -np.array(c / t)[t < c]
            dso.data[n, c == t] = 0
        #dsoc.data[0,:] = data[ci,:] / data[ti,:]

        final_shape = list(dso.data.shape)
        final_shape[0] = len(tests)  # 1 dimensional (final change value)

        for n, test in enumerate(tests):
            dso.labels[0][n] = 'fc %s:%s' % (_experiment_control, test)
            dso.entities[0][n] = None
            dso.classes[0][n] = 'fc %s:%s' % (_experiment_control, test)

        dso.crop(final_shape)

        return {'output': dso}

    def url_handler(self, url):

        kind, id, action = url.split('/')  # FIXME: Can use split here once stop using pathwaynames           

        # url is Qurl kind
        # Add an object to the current view
        if kind == "_readme":

        # FIXME: Hacky test of an idea
            if action == 'add' and id == 'data_source':
                # Add the pathway and regenerate
                self.onSelectDataSource()


class FoldChange(AnalysisPlugin):

    def __init__(self, **kwargs):
        super(FoldChange, self).__init__(**kwargs)
        FoldChangeApp.plugin = self
        self.register_app_launcher(FoldChangeApp)
