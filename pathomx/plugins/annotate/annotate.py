# -*- coding: utf-8 -*-
import os

import csv
import xml.etree.cElementTree as et
from collections import defaultdict

import numpy as np

import pathomx.utils as utils
import pathomx.ui as ui
import pathomx.db as db

from pathomx.data import DataSet, DataDefinition
from pathomx.plugins import ProcessingPlugin
from pathomx.qt import *


# Source data selection dialog
# Present a list of widgets (drop-downs) for each of the interfaces available on this plugin
# in each list show the data sources that can potentially file that slot.
# Select the currently used
class DialogAnnotationTargets(ui.GenericDialog):
    def __init__(self, parent=None, view=None, auto_consume_data=True, **kwargs):
        super(DialogAnnotationTargets, self).__init__(parent, **kwargs)

        self.v = view
        self.m = view.m

        self.setWindowTitle("Select annotation targets(s)")

        # Build a list of dicts containing the widget
        # with target data in there
        self.lw_annotatei = list()
        dsi = self.v.data.get('input')

        for k, a in list(self.v._annotations.items()):

            self.lw_annotatei.append(QComboBox())
            cdw = self.lw_annotatei[k]  # Shorthand
            cdw.addItem('Ignore')

            for n, i in enumerate(dsi.scales):
                print(len(i), len(a))
                if len(i) == len(a):
                    for target in ['labels', 'classes', 'scales']:
                        cdw.addItem('%s/%s' % (n, target))

            self.layout.addWidget(QLabel("Source column %s [%s...]" % (k, ','.join(a[0:3]))))
            self.layout.addWidget(cdw)
            # If this is the currently used data source for this interface, set it active
            #if cd.target in self.v.data.i and dataset == self.v.data.i[cd.target]:
            #    cdw.setCurrentIndex(nd+1) #nd+1 because of the None we've inserted at the front

            cdw.annotation_column = k

        self.setMinimumSize(QSize(600, 100))
        self.layout.setSizeConstraint(QLayout.SetMinimumSize)

        # Build dialog layout
        self.dialogFinalise()

        
class AnnotateApp(ui.DataApp):

    import_name = "Annotations"
    import_filename_filter = "All compatible files (*.csv *.txt *.tsv);;Comma Separated Values (*.csv);;Plain Text Files (*.txt);;Tab Separated Values (*.tsv);;All files (*.*)"
    import_description = "Import data annotations (classes, labels, scales) for current dataset"

    def __init__(self, **kwargs):
        super(AnnotateApp, self).__init__(**kwargs)
        # Annotations is a list of dicts; each list a distinct annotation
        # Targets is their mapping to the data; e.g. ('scales', 1) for scales[1]
        self._annotations = defaultdict(list)
        self._annotations_targets = dict()

        # Source object for the data
        self.addDataToolBar()

        self._field_transforms = {'scales': float, 'labels': self.str_or_none, 'classes': self.str_or_none}

        self.data.add_input('input')  # Add input slot
        self.data.add_output('output')  # Add output slot
        self.table.setModel(self.data.o['output'].as_table)

        t = self.getCreatedToolbar('Annotations', 'external-data')

        import_dataAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'disk--arrow.png')), 'Load annotations from file\\u2026', self.m)
        import_dataAction.setStatusTip('Load annotations from .csv. file')
        import_dataAction.triggered.connect(self.onLoadAnnotations)
        t.addAction(import_dataAction)

        self.addExternalDataToolbar()  # Add standard source data options

        annotations_dataAction = QAction(QIcon(os.path.join(utils.scriptdir, 'icons', 'pencil-field.png')), 'Edit annotation settings\\u2026', self.m)
        annotations_dataAction.setStatusTip('Import additional annotations for a dataset including classes, labels, scales')
        annotations_dataAction.triggered.connect(self.onEditAnnotationsSettings)
        t.addAction(annotations_dataAction)

        # We need an input filter for this type; accepting *anything*
        self.data.consumer_defs.append(
            DataDefinition('input', {
                'labels_n': ('>0', '>0')
            
            })
        )

        self.finalise()

    def onLoadAnnotations(self):
        """ Open a annotations file"""
        filename, _ = QFileDialog.getOpenFileName(self.m, self.import_description, '', self.import_filename_filter)
        if filename:
            self.load_annotations(filename)
            self.onEditAnnotationsSettings()
            self.autogenerate()
            self.file_watcher.addPath(filename)

            self.workspace_item.setText(0, os.path.basename(filename))

        return False

    def onEditAnnotationsSettings(self):
        """ Open a data file"""
        dialog = DialogAnnotationTargets(parent=self, view=self)
        ok = dialog.exec_()
        if ok:
            # Extract the settings and store in the _annotations_targets settings
            # then run the annotation process
            self._annotations_targets = dict()
            # dict of source = (target, axis)

            for n, cb in enumerate(dialog.lw_annotatei):  # Get list of comboboxes
                txt = cb.currentText()
                if txt != 'Ignore':
                    axis, field = txt.split('/')
                    axis = int(axis)  # index to apply
                    source = n
                    target = field
                    self._annotations_targets[source] = (target, axis)

    def generate(self, input):
        dso = input
        print('Applying annotations...')

        for source, (target, index) in list(self._annotations_targets.items()):
            annotation = self._annotations[source]
            print(':', source, target, index)
            if len(annotation) == len(dso.__dict__[target][index]):
                print('Applying annotation %s to %s' % (source, target))
                dso.__dict__[target][index] = [self._field_transforms[target](a) for a in annotation]

        return {'output': dso}

    def load_datafile(self, filename):
        self.load_annotations(filename)

    def load_annotations(self, filename):
        # Load the annotation file and attempt to apply it in the most logical way possible
        reader = csv.reader(open(filename, 'rU'), delimiter=',', dialect='excel')
        self._annotations = defaultdict(list)

        for row in reader:
            if type(row) != list:
                row = [row]  # So we accept multiple columns below
            for c, r in enumerate(row):
                self._annotations[c].append(r)

    def str_or_none(self, x):
        if x == '':
            return None
        else:
            return str(x)


class Annotate(ProcessingPlugin):

    def __init__(self, **kwargs):
        super(Annotate, self).__init__(**kwargs)
        AnnotateApp.plugin = self
        self.register_app_launcher(AnnotateApp)
