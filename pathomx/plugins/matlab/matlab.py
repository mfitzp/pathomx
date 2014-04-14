# -*- coding: utf-8 -*-

import os
import copy

import numpy as np
import scipy as sp
import mlabwrap

import pathomx.ui as ui
import pathomx.db as db
import pathomx.utils as utils
import pathomx.threads as threads

from pathomx.plugins import ImportPlugin
from pathomx.ui import ImportDataApp, ExportDataApp, CodeEditorTool
from pathomx.data import DataSet, DataDefinition
from pathomx.views import D3SpectraView, D3DifferenceView, MplSpectraView, MplDifferenceView
from pathomx.qt import *
from pathomx.custom_exceptions import PathomxExternalResourceTimeoutException
from pathomx.resources import matlab, MATLABLock

class MATLABTool(MATLABLock, ui.DataApp):
    def __init__(self, **kwargs):
        super(MATLABTool, self).__init__(**kwargs)

        self.addDataToolBar()
        self.addFigureToolBar()

        self.data.add_input('input')  # Add input slot
        self.data.add_output('output')
        self.table.setModel(self.data.o['output'].as_table)

        self.views.addTab(MplSpectraView(self), 'View')

        self.matlab = matlab.init()

        # Setup data consumer options
        self.data.consumer_defs.append(
            DataDefinition('input', {
            'labels_n': ('>1', None),
            'entities_t': (None, None),
            'scales_t': (None, ['float']),
            })
        )

        self.config.set_defaults({
            'bin_size': 0.01,
            'bin_offset': 0,
        })

    def __exit__(self, ext_type, exc_value, traceback):
        self.matlab.stop()


class MATLABInputTool(ImportDataApp):
    name = "MATLAB"

    def __init__(self, **kwargs):
        super(MATLABInputTool, self).__init__(**kwargs)

        self.config.set_defaults({
        })

        self.finalise()

    def generate(self, input):
        pass


class MATLABOutputTool(ExportDataApp):
    name = "MATLAB"
    export_type = "MATLAB"
    export_description = "Export data to MATLAB® format file"
    export_filename_filter = "MATLAB files (*.mat);;All files (*.*)"

    def __init__(self, **kwargs):
        super(MATLABOutputTool, self).__init__(**kwargs)
        self.data.add_input('input')  # Add input slot
        self.data.consumer_defs.append(
            DataDefinition('input', {
            })
        )

        self.config.set_defaults({
            'filename': None,
        })

        self.finalise()

    def save_datafile(self, filename, dso):
        # Build a dict representing the data to be written to disk
        mdict = {
            'data': dso.data,
            #'labels':
            #'entities': [str(x) if x != None else '' for x in dso.entities],
            #'scales': [x if x != None else np.nan for x in dso.scales],
            #'classes': [str(x) if x != None else '' for x in dso.classes],
        }

        for n, _ in enumerate(dso.scales):
            l = len(dso.scales[n])
            r = np.zeros((l, ), dtype=('(%d,)f8, (%d,)a20, (%d,)a20, (%d,)a20' % (l, l, l, l)))

            mdict['scales_%d' % n] = np.array([x if x != None else np.nan for x in dso.scales[n]])
            mdict['classes_%d' % n] = [x if x != None else ''  for x in dso.classes[n]]
            mdict['labels_%d' % n] = [x if x != None else ''  for x in dso.labels[n]]
            mdict['entities_%d' % n] = [str(x) if x != None else '' for x in dso.entities[n]]

            #l = len( dso.scales[n] )
            #dt = np.dtype('(%d,)f8, (%d,)a20, (%d,)a20, (%d,)a20' % (l,l,l,l) )
            #dt.names = (b'scales',b'classes',b'labels',b'entities' )
            #r = np.zeros((l,), dt )
            #r[:] = (
            #    np.array([ x if x != None else np.nan for x in dso.scales[n] ]),
            #    np.array([ x if x != None else ''  for x in dso.classes[n] ]),
            #    np.array([ x if x != None else ''  for x in dso.labels[n] ]),
            #    np.array([ str(x) if x != None else '' for x in dso.entities[n] ]),
            #    )
            #mdict['axis_%d' % n] = r


        # Write the file to disk using Numpy IO for Matlab
        sp.io.savemat(filename, mdict)
        return {'complete': True}

        
class HighlightingRule():
    def __init__(self, pattern, format):
        self.pattern = pattern
        self.format = format


class MATLABHighlighter(QSyntaxHighlighter):

    def __init__(self, parent):
        QSyntaxHighlighter.__init__(self, parent)
        self.parent = parent
        self.highlightingRules = []

        keyword = QTextCharFormat()
        keyword.setForeground(Qt.darkBlue)
        keyword.setFontWeight(QFont.Bold)
        keywords = ['break', 'case', 'catch', 'continue', 'else', 'elseif', 'end', 'for', 'function', 'global', 'if', 'otherwise', 'persistent', 'return', 'switch', 'try', 'while']
        for word in keywords:
            pattern = QRegExp("\\b" + word + "\\b")
            rule = HighlightingRule(pattern, keyword)
            self.highlightingRules.append(rule)

        reservedClasses = QTextCharFormat()
        reservedClasses.setForeground(Qt.darkRed)
        reservedClasses.setFontWeight(QFont.Bold)
        keywords = ["array", "character", "complex",
                                  "data.frame", "double", "factor",
                                  "function", "integer", "list",
                                  "logical", "matrix", "numeric",
                                  "vector"]
        for word in keywords:
            pattern = QRegExp("\\b" + word + "\\b")
            rule = HighlightingRule(pattern, reservedClasses)
            self.highlightingRules.append(rule)

        assignmentOperator = QTextCharFormat()
        pattern = QRegExp("(<){1,2}-")
        assignmentOperator.setForeground(Qt.green)
        assignmentOperator.setFontWeight(QFont.Bold)
        rule = HighlightingRule(pattern, assignmentOperator)
        self.highlightingRules.append(rule)
        number = QTextCharFormat()
        pattern = QRegExp("[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?")
        pattern.setMinimal(True)
        number.setForeground(Qt.blue)
        rule = HighlightingRule(pattern, number)
        self.highlightingRules.append(rule)

        self.comments = QTextCharFormat()
        self.comments.setFontWeight(QFont.Normal)
        self.comments.setForeground(Qt.darkYellow)

    def highlightBlock(self, text):

        for rule in self.highlightingRules:
            expression = QRegExp(rule.pattern)
            index = expression.indexIn(text)
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat(index, length, rule.format)
                try:
                    index = text.index(str(expression), index + length)
                except:
                    break

        if '%' in text:
            i = text.index('%')
            self.setFormat(i, len(text) - i, self.comments)

        self.setCurrentBlockState(0)


class MATLABScriptTool(MATLABLock, CodeEditorTool):

    def __init__(self, **kwargs):
        super(MATLABScriptTool, self).__init__(**kwargs)

        self.addDataToolBar()
        self.addCodeEditorToolbar()

        self.data.add_input('input')  # Add input slot
        self.data.add_output('output')  # Add output slot
        # We need an input filter for this type; accepting *anything*
        self.data.consumer_defs.append(
            DataDefinition('input', {
            })
        )

        self.config.set_defaults({
            'source': '''
% %%%%% MATLAB Scripting for Pathomx %%%%
% 
% Source data from input ports is available as same-named variables in the MATLAB
% workspace (default input). The data matrix is therefore available under input.data
% Put your modified data output into the variable output.
% For more information on the Pathomx Dataset object structure see:
% http://docs.pathomx.org/en/latest/
%
% Have fun!

output_data=input_data
'''
        })

        self.editor = ui.CodeEditor()
        self.config.add_handler('source', self.editor)
        highlighter = MATLABHighlighter(self.editor.document())
        self.views.addView(self.editor, 'Editor')

        self.matlab = mlabwrap.init()

        self.finalise()

    def generate(self, input):
        self.status.emit('active')
        self.matlab._set("input_data", input.data)
        #self.matlab._set("pmx_classes", input.classes)
        #self.matlab._set("pmx_scales", input.scales)
        self.progress.emit(0.25)
        self.matlab._do(self.editor.document().toPlainText(), nout=0)
        self.progress.emit(0.50)
        input.data = self.matlab.output_data.reshape(input.data.shape)
        self.progress.emit(0.75)
        return {'output': input}

        
class MATLAB(ImportPlugin):

    def __init__(self, **kwargs):
        super(MATLAB, self).__init__(**kwargs)
        #self.register_app_launcher( MATLABInputApp, 'Import' )
        self.register_app_launcher(MATLABOutputTool, 'Export')
        self.register_app_launcher(MATLABScriptTool, 'Scripting')
