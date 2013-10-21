# -*- coding: utf-8 -*-

import os

from plugins import ProcessingPlugin

# Import PyQt5 classes
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWebKit import *
from PyQt5.QtNetwork import *
from PyQt5.QtWidgets import *
from PyQt5.QtWebKitWidgets import *
from PyQt5.QtPrintSupport import *

import ui
from data import DataSet, DataDefinition

class HighlightingRule():
  def __init__( self, pattern, format ):
    self.pattern = pattern
    self.format = format

class PythonHighlighter( QSyntaxHighlighter ):
    def __init__( self, parent ):
        QSyntaxHighlighter.__init__( self, parent )
        self.parent = parent
        self.highlightingRules = []

        keyword = QTextCharFormat()
        keyword.setForeground( Qt.darkBlue )
        keyword.setFontWeight( QFont.Bold )
        keywords = [ "break", "else", "for", "if", "in",
                                  "next", "repeat", "return", "switch",
                                  "try", "while" ]
        for word in keywords:
            pattern = QRegExp("\\b" + word + "\\b")
            rule = HighlightingRule( pattern, keyword )
            self.highlightingRules.append( rule )

        reservedClasses = QTextCharFormat()
        reservedClasses.setForeground( Qt.darkRed )
        reservedClasses.setFontWeight( QFont.Bold )
        keywords = [ "array", "character", "complex",
                                  "data.frame", "double", "factor",
                                  "function", "integer", "list",
                                  "logical", "matrix", "numeric",
                                  "vector" ]
        for word in keywords:
            pattern = QRegExp("\\b" + word + "\\b")
            rule = HighlightingRule( pattern, reservedClasses )
            self.highlightingRules.append( rule )
        
        assignmentOperator = QTextCharFormat()
        pattern = QRegExp( "(<){1,2}-" )
        assignmentOperator.setForeground( Qt.green )
        assignmentOperator.setFontWeight( QFont.Bold )
        rule = HighlightingRule( pattern, assignmentOperator )
        self.highlightingRules.append( rule )
        number = QTextCharFormat()
        pattern = QRegExp( "[-+]?[0-9]*\.?[0-9]+([eE][-+]?[0-9]+)?" )
        pattern.setMinimal( True )
        number.setForeground( Qt.blue )
        rule = HighlightingRule( pattern, number )
        self.highlightingRules.append( rule )

    def highlightBlock( self, text ):
        for rule in self.highlightingRules:
            expression = QRegExp( rule.pattern )
            index = expression.indexIn( text )
            while index >= 0:
                length = expression.matchedLength()
                self.setFormat( index, length, rule.format )
                try:
                    index = text.index( str(expression), index + length )
                except:
                    break
                    
        self.setCurrentBlockState( 0 )


class PythonView( ui.GenericView ):

    def __init__(self, plugin, parent, **kwargs):
        super(PythonView, self).__init__(plugin, parent, **kwargs)

        self.addDataToolBar()

        self.data.add_interface('output') # Add output slot
        # We need an input filter for this type; accepting *anything*
        self.data.consumer_defs.append( 
            DataDefinition('input', {
            })
        )
        
        self.editor = QTextEdit()
        highlighter = PythonHighlighter( self.editor )
        self.tabs.addTab( self.editor, 'Editor' )
        self.setWindowTitle( "Syntax Highlighter Example" )
        
        self.data.source_updated.connect( self.autogenerate ) # Auto-regenerate if the source data is modified
        self.data.consume_any_of( self.m.datasets[::-1] ) # Try consume any dataset; work backwards

        
    def generate(self):
        self.setWorkspaceStatus('active')
    
        dso = self.data.get('input')
        print self.editor.document().toPlainText() 
        # Handy imports
        import numpy as np
        import scipy as sp
        
        exec( self.editor.document().toPlainText() )
        self.data.put('output',dso)

        self.setWorkspaceStatus('done')
        self.clearWorkspaceStatus()                


class Python(ProcessingPlugin):

    def __init__(self, **kwargs):
        super(Python, self).__init__(**kwargs)
        self.register_app_launcher( self.app_launcher )

    def app_launcher(self):
        #self.load_data_file()
        self.instances.append( PythonView( self, self.m ) )
