# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
logging.debug('Loading styles.py')

import sys
import re

from matplotlib import markers
from matplotlib.markers import TICKLEFT, TICKRIGHT, TICKUP, TICKDOWN, CARETLEFT, CARETRIGHT, CARETUP, CARETDOWN

try:
    import xml.etree.cElementTree as et
except ImportError:
    import xml.etree.ElementTree as et

MARKERS = ['o', 's', '^', 'v', '<', '>', '.', '1', '2', '3', '4', '8',
            'p', '*', 'h', 'H', '+', 'x', 'D', 'd', '|', '_', ]
            #TICKLEFT, TICKRIGHT, TICKUP, TICKDOWN, CARETLEFT, CARETRIGHT,
            #CARETUP, CARETDOWN ]

LINESTYLES = ['-', '--', '-.', ':']

FILLSTYLES = ['full', 'left', 'right', 'bottom', 'top', 'none']

HATCHSTYLES = ['-', '|', '||', '|||', '/', '//', '///', '\\', '\\\\', '\\\\\\', '+', 'x', '*', 'o', 'O', '.']

COLORS_RDBU9 = [0, '#b2182b', '#d6604d', '#f4a582', '#fddbc7', '#cccccc', '#d1e5f0', '#92c5de', '#4393c3', '#2166ac']
COLORS_RDBU9C = [0, '#ffffff', '#000000', '#000000', '#000000', '#000000', '#000000', '#000000', '#ffffff', '#ffffff']
COLORS_CATEGORY10 = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
COLORS_MATPLOTLIB = ['b', 'g', 'r', 'c', 'm', 'y', 'k', 'w']

MATCH_EXACT = 1
MATCH_CONTAINS = 2
MATCH_START = 3
MATCH_END = 4
MATCH_REGEXP = 5

from . import utils

class StyleHandler(object):
    '''
    Interface to return a marker and colour combination for a given classifier
    
    Holds a number of ClassMatch objects that are run against each request, applying 
    a given set of attributes (color, marker, etc.) for each one.
    
    Returns a CategoryMarker object that describes the complete style set.
    '''

    def __init__(self):
        self.matchdefs = []  # User defined match definitions
        self.automatchdefs = []  # Automatic match definitions (applied after, non-static but consistent)
    
    def add_match_definition(self):
        cm_def = ClassMatchDefinition()
        # Get unique marker definition (algo)
        # def = self.get_unique_marker_definition()
        ls_def = StyleDefinition()

    def get_style_for_class(self, classname):
        '''
        Run through each match and definition in turn, applying any non-None value to 
        a cumulative marker definition. Return the result for use to assign a color.
        
        If we reach the end without a single hit, means we've got an unmatched class and
        need to assign a generic, unique, colour/label set to it. This must be stored
        (as an auto-assignment) to ensure the same class still receives the same label in future. 
        '''
        is_matched = False
        ls_def = StyleDefinition()

        for cm_def, ls_definition in self.matchdefs:
            if cm_def.is_match_for_class(classname):
                # We have a match, extract and apply the set
                is_matched = True
                ls_def.import_from(ls_definition)

        if is_matched:
            # If we've previously generated an automatch marker for this we need to remove it
            self.automatchdefs = [(cm, ls) for cm, ls in self.automatchdefs if cm.match_str != classname]
            return ls_def

        else:
            # No custom match, only automatch definitions to test now
            for cm_def, ls_definition in self.automatchdefs:
                if cm_def.is_match_for_class(classname):
                    # We have a match, set it
                    return ls_definition
            # If we're here, means we've still not matched
            # We need to generate a unique marker and provide a default marker def (unique match)
            # to ensure class receives the same marker in future
            cm_def = ClassMatchDefinition(classname, MATCH_EXACT, is_auto=True)
            ls_def = self.get_unique_style_definition()
            self.automatchdefs.append((cm_def, ls_def))

            return ls_def

    def get_unique_style_definition(self):
        '''
        Assign a unique marker definition using standard progression set
        Note: this is only guaranteed to be unique at the point of assignment,
        subsequent filters/assignments may give identical output
        FIXME: Watch for clashes and fix, then refresh
        '''

        # Get a list of all StyleDefinitions currently in use
        currently_in_use = [ls_def for cm_def, ls_def in self.matchdefs + self.automatchdefs]
        for m in MARKERS:
            for l in LINESTYLES:
                for c in COLORS_CATEGORY10:
                    ls_def = StyleDefinition(marker=m, linestyle=l, linewidth=1, color=c, markerfacecolor=c, markersize=4.5, fillstyle='full')
                    if ls_def not in currently_in_use:
                        return ls_def

        return None
        
    def getXMLMatchDefinitionsStyles(self, root):
    
        # Iterate over the entire set (in order) creating a XML representation of the MatchDef and Style
        for cm, ls in self.matchdefs + self.automatchdefs:
            
            cmls = et.SubElement(root, "ClassMatchStyle")
            if cm.is_auto:
                cmls.set('is_auto', 'true')
            
            cme = et.SubElement(cmls, "ClassMatch")
            cme.set("match_str", cm.match_str)
            cme.set("match_type", str(cm.match_type) )

            lse = et.SubElement(cmls, "Style")
            
            for attr in ls.attr:
                value = ls.__dict__[attr]
                if value != None: # We can skip None values (default anyway)
                    lse.set(attr, str(value))

        return root
        
    def setXMLMatchDefinitionsStyles(self, root):

        self.automatchdefs = []
        self.matchdefs = []

        for cmls in root.findall('ClassMatchStyle'):
            
            cm = ClassMatchDefinition()
            ls = StyleDefinition()
            
            cme = cmls.find('ClassMatch')
            cm.match_str = cme.get('match_str')
            cm.match_type = int( cme.get('match_type') )

            lse = cmls.find('Style')
            for attr in ls.attr:
                ls.__dict__[attr] = lse.get(attr, None)
                
            # Fix types
            ls.linewidth = float( ls.linewidth )
            if cmls.get('is_auto', False):
                cm.is_auto = True
                self.automatchdefs.append( ( cm, ls ) )
            else:
                self.matchdefs.append( ( cm, ls ) )


class StyleDefinition(object):
    '''
    
    '''
    line_attr = ['linestyle', 'color', 'linewidth']
    marker_attr = ['marker', 'markersize', 'markeredgecolor', 'markerfacecolor', 'fillstyle']
    hatch_attr = ['hatch']
    attr = line_attr + marker_attr + hatch_attr

    def __eq__(self, other):
        for attr in self.attr:
            if other.__dict__[attr] != self.__dict__[attr]:
                return False
        return True

    def __repr__(self):
        return "StyleDefinition(%s)" % self.__unicode__()

    def __unicode__(self):
        return ', '.join(['%s=%s' % (attr, self.__dict__[attr]) for attr in self.attr])

    def __init__(self, marker=None, markersize=None, markeredgecolor=None, markerfacecolor=None, fillstyle=None, linewidth=None, linestyle=None, color=None, hatch=None):

        self.marker = marker
        self.markersize = markersize
        self.markeredgecolor = markeredgecolor
        self.markerfacecolor = markerfacecolor
        self.fillstyle = fillstyle
        self.linestyle = linestyle
        self.linewidth = linewidth
        self.color = color
        self.hatch = hatch

    def import_from(self, ls_def):
        '''
        Apply any non-none components of the specified linestyle definition to this one
        producing a composite linestyle definition
        '''
        for attr in self.attr:
            if ls_def.__dict__[attr] != None:
                self.__dict__[attr] = ls_def.__dict__[attr]

    @property
    def kwargs(self):
        '''
        Return the style definition as a list of kwargs (where set)
        can be applied directly to the plot command
        '''
        return {attr: self.__dict__[attr] for attr in self.attr if self.__dict__[attr] != None}

    @property
    def line_kwargs(self):
        '''
        Return the line style definition as a list of kwargs (where set)
        can be applied directly to the plot command
        '''
        return {attr: self.__dict__[attr] for attr in self.line_attr if self.__dict__[attr] != None}

    @property
    def marker_kwargs(self):
        '''
        Return the marker style definition as a list of kwargs (where set)
        can be applied directly to the plot command
        '''
        return {attr: self.__dict__[attr] for attr in self.marker_attr if self.__dict__[attr] != None}

    @property
    def bar_kwargs(self):
        kw_attr = {'fc': 'markerfacecolor', 'ec': 'markeredgecolor', 'lw': 'linewidth', 'ecolor': 'markeredgecolor', 'hatch': 'hatch'}
        return {kw: self.__dict__[attr] for kw, attr in kw_attr.items() if self.__dict__[attr] != None}


class ClassMatchDefinition(object):
    '''
    '''

    def __init__(self, match_str='', match_type=MATCH_EXACT, is_auto=False):
        self.match_str = match_str
        self.match_type = match_type
        self.is_auto = is_auto

    def is_match_for_class(self, class_str):
        if self.match_type == MATCH_EXACT:
            return class_str == self.match_str

        elif self.match_type == MATCH_CONTAINS:
            return self.match_str in class_str

        elif self.match_type == MATCH_START:
            return class_str.startswith(self.match_str)

        elif self.match_type == MATCH_END:
            return class_str.endswith(self.match_str)

        elif self.match_type == MATCH_REGEXP:
            m = re.search(self.match_str, class_str) 
            if m:
                return True
            else:
                return False

styles = StyleHandler()
