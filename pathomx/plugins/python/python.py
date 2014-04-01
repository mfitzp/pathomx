# -*- coding: utf-8 -*-

import os

from pathomx.plugins import ProcessingPlugin

import pathomx.ui as ui
from keyword import kwlist
from pathomx.data import DataSet, DataDefinition
from pathomx.qt import *


class HighlightingRule():
    def __init__(self, pattern, format):
        self.pattern = pattern
        self.format = format


class PythonHighlighter(QSyntaxHighlighter):
    def __init__(self, parent):
        QSyntaxHighlighter.__init__(self, parent)
        self.parent = parent
        self.highlightingRules = []

        keyword = QTextCharFormat()
        keyword.setForeground(Qt.blue)
        keyword.setFontWeight(QFont.Bold)

        for word in kwlist:
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

        if '#' in text:
            i = text.index('#')
            self.setFormat(i, len(text) - i, self.comments)

        self.setCurrentBlockState(0)


class PythonScriptTool(ui.CodeEditorTool):

    def __init__(self, **kwargs):
        super(PythonScriptTool, self).__init__(**kwargs)

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
# ##### Python Scripting for Pathomx ####
# 
# Source data from input ports is available as same-named variables in the current
# scope (default input). The data matrix is therefore available under input.data
# Put your modified data output into the variable output.
# For more information on the Pathomx Dataset object structure see:
# http://docs.pathomx.org/en/latest/
#
# Have fun!
'''
        })

        self.editor = ui.CodeEditor()
        self.config.add_handler('source', self.editor)
        highlighter = PythonHighlighter(self.editor.document())
        self.views.addView(self.editor, 'Editor')

        self.finalise()

    def generate(self, input):

    # Horribly insecure
        self.progress.emit(0.25)
        exec(self.editor.document().toPlainText())
        self.progress.emit(0.75)
        return {'output': output}


class Python(ProcessingPlugin):

    def __init__(self, **kwargs):
        super(Python, self).__init__(**kwargs)
        self.register_app_launcher(PythonScriptTool, 'Scripting')
