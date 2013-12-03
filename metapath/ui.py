#!/usr/bin/env python
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

from collections import defaultdict

import os, urllib, urllib2, copy, re, json, importlib

# MetaPath classes
import utils

import numpy as np

import data, config

# Translation (@default context)
from translate import tr

# GENERIC CONFIGURATION AND OPTION HANDLING

# Generic configuration dialog handling class
class genericDialog(QDialog):
    def __init__(self, parent, buttons = ['ok','cancel'], **kwargs):
        super(genericDialog, self).__init__(parent, **kwargs)        

        self.sizer = QVBoxLayout()
        self.layout = QVBoxLayout()
        
        QButtons = {
            'ok':QDialogButtonBox.Ok,
            'cancel':QDialogButtonBox.Cancel,
        }
        Qbtn = 0
        for k in buttons:
            Qbtn = Qbtn | QButtons[k]
        
        # Setup default button configurations etc.
        self.buttonBox = QDialogButtonBox(Qbtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
                
    def dialogFinalise(self):
        self.sizer.addLayout(self.layout)
        self.sizer.addWidget(self.buttonBox)
    
        # Set dialog layout
        self.setLayout(self.sizer)

    def setListControl(self, control, list, checked):
        # Automatically set List control checked based on current options list
        items = control.GetItems()
        try:
            idxs = [items.index(e) for e in list]
            for idx in idxs:
                if checked:
                    control.Select(idx)
                else:
                    control.Deselect(idx)
        except:
            pass
        
# Web views

BLANK_DEFAULT_HTML = '''
<html>
<style>
    * {
        width:100%;
        height:100%;
        margin:0;
        background-color: #f5f5f5;
    }
</style>
<body>&nbsp;</body></html>
'''

class ExportImageDialog(genericDialog):
    
    print_u = { # Qt uses pixels/meter as it's default resolution so measure relative to meters
        'in':39.3701,
        'mm':1000,
        'cm':100,
        'm':1,
        }
    
    print_p = { # Spinbox parameters dp, increment
        'in': (3, 1, 0.01, 1000),
        'mm': (2, 1, 0.1, 100000),
        'cm': (3, 1, 0.01, 10000),
        'm': (5, 1, 0.0001, 100),
    }
        
    resolution_u = { # Qt uses pixels/meter as it's default resolution so scale to that
                    'dpi':39.3701,
                    'px/mm':1000,
                    'px/cm':100,
                    'px/m':1,
                    }
                    
    def __init__(self, parent, size=QSize(800,600), dpm=11811, **kwargs):
        super(ExportImageDialog, self).__init__(parent, **kwargs)        
        
        self.setWindowTitle( tr("Export Image") )

        # Handle measurements internally as pixels, convert to/from
        self._w = size.width()
        self._h = size.height()
        self.default_print_units = 'cm'
        self.default_resolution_units = 'dpi'

        self._updating = False

        r = 0
        w = QGridLayout()

        w.addWidget( QLabel('<b>Image Size</b>'), r, 0 )
        r += 1
        
        self.width = QSpinBox()
        self.width.setRange( 1, 100000)
        w.addWidget( QLabel('Width'), r, 0 )        
        w.addWidget( self.width, r, 1 )        
        r += 1

        self.height = QSpinBox()
        self.height.setRange( 1, 100000)
        w.addWidget( QLabel('Height'), r, 0 )        
        w.addWidget( self.height, r, 1 )        
        r += 1
        w.addItem( QSpacerItem(1,10), r, 0 )
        r += 1

        w.addWidget( QLabel('<b>Print Size</b>'), r, 0 )    
        r += 1

        self.width_p = QDoubleSpinBox()
        self.width_p.setRange( 0.0001, 10000)
        w.addWidget( QLabel('Width'), r, 0 )        
        w.addWidget( self.width_p, r, 1 )        
        r += 1

        self.height_p = QDoubleSpinBox()
        self.height_p.setRange( 0.0001, 10000)
        w.addWidget( QLabel('Height'), r, 0 )        
        w.addWidget( self.height_p, r, 1 )     
        
        self.print_units = QComboBox()
        self.print_units.addItems(self.print_u.keys())
        self.print_units.setCurrentText( self.default_print_units )

        w.addWidget( self.print_units, r, 2 )        
        r += 1

        self.resolution = QDoubleSpinBox()
        self.resolution.setRange( 1, 1000000)
        self.resolution.setValue( 300)
        self.resolution.setDecimals( 2 )

        self.resolution_units = QComboBox()
        self.resolution_units.addItems(self.resolution_u.keys())
        self.resolution_units.setCurrentText( self.default_resolution_units )

        w.addWidget( QLabel('Resolution'), r, 0 )        
        w.addWidget( self.resolution, r, 1 )        
        w.addWidget( self.resolution_units, r, 2 )        
        r += 1
        w.addItem( QSpacerItem(1,10), r, 0 )
        r += 1

        w.addWidget( QLabel('<b>Scaling</b>'), r, 0 )        
        r += 1
        self.scaling = QComboBox()
        self.scaling.addItems(['Resample', 'Resize'])
        self.scaling.setCurrentText( 'Resample' )
        w.addWidget( QLabel('Scaling method'), r, 0 )        
        w.addWidget( self.scaling, r, 1 )        
        r += 1
        w.addItem( QSpacerItem(1,20), r, 0 )

        # Set values
        self.width.setValue(self._w)
        self.height.setValue(self._h)
        self.update_print_dimensions()

        # Set event handlers (here so not triggered while setting up)
        self.width.valueChanged.connect( self.changed_image_dimensions )
        self.height.valueChanged.connect( self.changed_image_dimensions )
        self.width_p.valueChanged.connect( self.changed_print_dimensions )
        self.height_p.valueChanged.connect( self.changed_print_dimensions )
        self.resolution_units.currentIndexChanged.connect(self.changed_resolution_units)
        self.resolution.valueChanged.connect( self.changed_print_resolution )
        self.print_units.currentIndexChanged.connect(self.changed_print_units)


        self.layout.addLayout(w)
        
        self.setMinimumSize( QSize(300,150) )
        self.layout.setSizeConstraint(QLayout.SetMinimumSize)

        self._current_dimension = self.print_units.currentText()
        self._current_resolution = self.resolution.value()
        self._current_resolution_units = self.resolution_units.currentText()
                
        # Build dialog layout
        self.dialogFinalise()
        
    def changed_image_dimensions(self):
        if not self._updating:
            self._updating = True
            self.update_print_dimensions()
        self._updating = False
        
        # Keep internal data synced
        self._w = self.width.value()
        self._h = self.height.value()
        
    def changed_print_dimensions(self):
        if not self._updating:
            self._updating = True
            self.update_image_dimensions()
        self._updating = False
        
    def changed_print_resolution(self):
        w_p = self.width_p.value()
        h_p = self.height_p.value()
            
        new_resolution = self.resolution.value()
        self.width_p.setValue(  ( w_p / self._current_resolution ) * new_resolution )
        self.height_p.setValue(  ( h_p / self._current_resolution ) * new_resolution ) 
        self._current_resolution = self.resolution.value()
        

    def changed_print_units(self):
        dimension_t = self.print_units.currentText()
        for o in [self.height_p, self.width_p]:
            o.setDecimals( self.print_p[dimension_t][0] )
            o.setSingleStep( self.print_p[dimension_t][1] )
            o.setRange( self.print_p[dimension_t][2], self.print_p[dimension_t][3])

        if dimension_t != self._current_dimension:
            # We've had a change, so convert
            self.width_p.setValue( self.get_converted_measurement( self.width_p.value(), self._current_dimension, dimension_t ) )
            self.height_p.setValue( self.get_converted_measurement( self.height_p.value(), self._current_dimension, dimension_t ) )

        self._current_dimension = dimension_t
        
    def changed_resolution_units(self):
        ru = self.resolution_units.currentText()    
        self.resolution.setValue( self.resolution.value() * self.resolution_u[self._current_resolution_units] / float(self.resolution_u[ru]) )
        self._current_resolution_units = ru
        
    # Update print dimensions using the image dimensions and resolutions
    def update_print_dimensions(self):
        self._w = self.width.value()
        self._h = self.height.value()
        
        print_units = self.print_units.currentText()
    
        w_p = self.get_print_size( self._w, print_units )
        h_p = self.get_print_size( self._h, print_units )
        
        self.width_p.setValue( w_p )
        self.height_p.setValue( h_p )
        
    def get_print_size(self, s, u):
        ps = self.resolution.value()
        ps_u = self.resolution_units.currentText()
        s = s / (ps * self.resolution_u[ ps_u ]) # Get size in metres
        return self.get_converted_measurement( s, 'm', u ) # Return converted value    

    # Update image dimensions using the print dimensions and resolutions
    def update_image_dimensions(self):
        w_p = self.width_p.value()
        h_p = self.height_p.value()
        
        print_units = self.print_units.currentText()
        resolution = self.resolution.value()
        resolution_units = self.resolution_units.currentText()
    
        self._w = self.get_pixel_size( w_p, print_units, resolution, resolution_units )
        self._h = self.get_pixel_size( h_p, print_units, resolution, resolution_units )

        self.width.setValue( self._w )
        self.height.setValue( self._h )

    def get_pixel_size(self, s, pu, r, ru):
        s = s / self.print_u[ pu ] # Convert to metres
        rm = r * self.resolution_u[ ru ] # Dots per metre
        return s * rm
       
    def get_converted_measurement(self, x, f, t):
        # Convert measurement from f to t 
        f = self.print_u[f]
        t = self.print_u[t]
        return (float(x)/float(f)) * t

    def get_pixel_dimensions(self):
        return QSize( self._w, self._h)
    
    def get_dots_per_meter(self):
        return self.resolution.value() * self.resolution_u[ self.resolution_units.currentText() ] 
    
    def get_resample(self):
        return self.scaling.currentText() == 'Resample' 


class QWebPageJSLog(QWebPage):
    """
    Makes it possible to use a Python logger to print javascript console messages
    """
    def __init__(self, parent=None, **kwargs):
        super(QWebPageJSLog, self).__init__(parent, **kwargs)

    def javaScriptConsoleMessage(self, msg, lineNumber, sourceID):
        print "JsConsole(%s:%d): %s" % (sourceID, lineNumber, msg)
     

class RenderPageToFile(QWebPage): 
    def __init__(self, wv, fn, size=None, dpm=11811, resample=True): # 11811 == 300dpi
        super(RenderPageToFile, self).__init__()

        self.mainFrame().setScrollBarPolicy(Qt.Vertical, Qt.ScrollBarAlwaysOff)
        self.mainFrame().setScrollBarPolicy(Qt.Horizontal, Qt.ScrollBarAlwaysOff)

        #self.settings().setAttribute( QWebSettings.JavascriptEnabled,False)

        self.finished = False
            
        self.size = size if size != None else wv.size() 
        self.dpm = dpm
        self.resample = resample

        self.setViewportSize(self.size)
        self.loadFinished.connect(self._loadFinished)
        self.fn = fn
        
        c = wv.page().mainFrame().toHtml()
        c = c.replace('<html><head></head><body>','')
        c = c.replace('</body></html>','')
        print c[:1000]
        if self.resample: # Remove drawn graph; we'll regenerate
            c = re.sub( '\<g.*\/g\>', '', c,  re.MULTILINE)
        else:
            # Keep graph but apply sizing; using svg viewport scaling
            # this is a bit hacky; rewriting the svg width/height parameters using regex
            c = re.sub( '(\<svg.*width=")([^"]*)(".*\>)', '\g<1>%d\g<3>' % self.size.width(), c)
            c = re.sub( '(\<svg.*height=")([^"]*)(".*\>)', '\g<1>%d\g<3>' % self.size.height(), c)
            
        print 'RESULT:'
        print c[:1000]
        self.mainFrame().setHtml( c )
    
    def _loadFinished(self, ok):

        frame = self.mainFrame()
        if self.resample: # If resampling we need to regenerate the graph
            frame.evaluateJavaScript( "_metapath_render_trigger(); console.log('done');" )

        #self.size = frame.contentsSize()#        self.setViewportSize(self.size)
        image = QImage(self.size, QImage.Format_ARGB32)
        image.setDotsPerMeterX(self.dpm)
        image.setDotsPerMeterY(self.dpm)
        painter = QPainter(image)
        frame.render(painter)
        painter.end()

        image.save(self.fn)
        self.finished = True

class QWebPageExtend(QWebPage):
    def shouldInterruptJavascript():
        return False


class QWebViewExtend(QWebView):

    def __init__(self, parent, onNavEvent=None, **kwargs):
        super(QWebViewExtend, self).__init__(parent, **kwargs)        
        
        self.w = parent
        self.setPage( QWebPageExtend(self.w) )
        self.setHtml(BLANK_DEFAULT_HTML,QUrl("~"))
        
        self.page().setContentEditable(False)
        self.page().setLinkDelegationPolicy( QWebPage.DelegateExternalLinks )
        self.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding )
        self.loadFinished.connect(self._loadFinished)
        self._is_svg_with_js = False
        #self._svg_graph_dimensions = None
        
        # Override links for internal link cleverness
        if onNavEvent:
            self.onNavEvent = onNavEvent
            self.linkClicked.connect( self.onNavEvent )

        self.setContextMenuPolicy(Qt.CustomContextMenu) # Disable right-click
    
    def sizeHint(self):
        if self.w:
            return self.w.size()
        else:
            return super(QWebViewExtend, self).sizeHint()        

    def setSVG(self, svg):
        self._is_svg_with_js = True
        super(QWebViewExtend, self).setHtml(svg, QUrl('~') )             
        #super(QWebViewExtend, self).setContent(svg, "image/svg+xml") <- this would be preferable but has encoding issues
        
    def _loadFinished(self, ok):
        sizer = self.sizeHint()   
        self.page().currentFrame().addToJavaScriptWindowObject("QtWebView", self)
        if self._is_svg_with_js:
            self.page().currentFrame().evaluateJavaScript( "QtViewportSize={'x':%s,'y':%s};" % ( sizer.width()-30, sizer.height()-80 ) ) #-magic number for scrollbars (ugh)        
            self.page().currentFrame().evaluateJavaScript( "_metapath_render_trigger();" )
            #self.page().currentFrame().evaluateJavaScript( "_metapath_store_graph_dimensions();" ) # get the inner dimensions of the g#graph element (minus margins)
            #print self._svg_graph_dimensions
            
    @pyqtSlot(str)
    def delegateLink(self, url):
        self.onNavEvent( QUrl(url) )
        return True

    #@pyqtSlot(int, int)
    #def storeGraphDimensions(self, width, height):
    #    self._svg_graph_dimensions = (width, height)
    #    print self._svg_graph_dimensions
    #    return True
        
    def saveAsImage(self, size=(800,600), dpm=11811, resample=True): # Size, dots per metre (for print), resample (redraw) image
        filename, _ = QFileDialog.getSaveFileName(self, 'Save current figure', '',  "Tagged Image File Format (*.tif);;\
                                                                                     Portable Network Graphics (*.png)")
        if filename:
            r = RenderPageToFile(self, filename, size, dpm, resample ) 
            while r.finished != True:
                QCoreApplication.processEvents()
                

class QWebViewScrollFix(QWebViewExtend):
    
    def __init__(self, parent, onNavEvent=None, **kwargs):
        super(QWebViewScrollFix, self).__init__(parent, onNavEvent=onNavEvent, **kwargs)        

        

# View Dialogs

# Source data selection dialog
# Present a list of widgets (drop-downs) for each of the interfaces available on this plugin
# in each list show the data sources that can potentially file that slot. 
# Select the currently used 
class DialogDataSource(genericDialog):
    def __init__(self, parent=None, view=None, **kwargs):
        super(DialogDataSource, self).__init__(parent, **kwargs)        
        
        self.v = view
        self.m = view.m
        
        self.setWindowTitle( tr("Select Data Source(s)") )

        # Build a list of dicts containing the widget
        # with target data in there
        self.lw_consumeri = list()
        for n,cd in enumerate(self.v.data.consumer_defs):
            
            self.lw_consumeri.append( QComboBox() )
            cdw = self.lw_consumeri[n] # Shorthand
            datasets = self.v.data.can_consume_which_of(self.m.datasets, [cd])
            
            cdw.addItem('No input')
            
            for nd, dataset in enumerate(datasets):

                e = set()
                for el in dataset.entities_t:
                    e |= set(el) # Add entities to the set
                e = e - {'NoneType'} # Remove if it's in there
            
                entities = ', '.join( e )
                dimensions = 'x'.join( [str(s) for s in dataset.shape ] )

                cdw.addItem( QIcon(dataset.manager.v.plugin.workspace_icon),'%s %s %s (%s)' % (dataset.name, dataset.manager.v.name, entities, dimensions) )

                # If this is the currently used data source for this interface, set it active
                if cd.target in self.v.data.i and dataset == self.v.data.i[cd.target]:
                    cdw.setCurrentIndex(nd+1) #nd+1 because of the None we've inserted at the front

            cdw.consumer_def = cd
            cdw.datasets = [None] + datasets
            
            self.layout.addWidget( QLabel( "%s:" % cd.title  ) )
            self.layout.addWidget(cdw)
            
        self.setMinimumSize( QSize(600,100) )
        self.layout.setSizeConstraint(QLayout.SetMinimumSize)
        
        # Build dialog layout
        self.dialogFinalise()
        
        

class DialogDataOutput(genericDialog):
    def __init__(self, parent=None, view=None, **kwargs):
        super(DialogDataOutput, self).__init__(parent, buttons=['ok'], **kwargs)        
        
        self.v = view
        self.m = view.m

        self.setWindowTitle("Data Output(s)")

        self.lw_sources = QTreeWidget() # Use TreeWidget but flat; for multiple column view
        self.lw_sources.setColumnCount(5)
        self.lw_sources.setHeaderLabels(['','Source','Data','Entities', 'Size']) #,'#'])
        self.lw_sources.setUniformRowHeights(True)
        self.lw_sources.rootIsDecorated()
        self.lw_sources.hideColumn(0)                
        
        datasets = self.m.datasets # Get a list of dataset objects to test
        self.datasets = []
        
        for k,dataset in self.v.data.o.items():
            
            #QListWidgetItem(dataset.name, self.lw_sources)
            tw = QTreeWidgetItem()

            tw.setText(0, str( len(self.datasets)-1) ) # Store index
            tw.setText(1, dataset.manager.v.name )
            if dataset.manager.v.plugin.workspace_icon:
                tw.setIcon(1, dataset.manager.v.plugin.workspace_icon )

            tw.setText(2, dataset.name)
            e = set()
            for el in dataset.entities_t:
                e |= set(el) # Add entities to the set
            e = e - {'NoneType'} # Remove if it's in there
            
            tw.setText(3, ', '.join( e ) )

            tw.setText(4, 'x'.join( [str(s) for s in dataset.shape ] ) )
            
            self.lw_sources.addTopLevelItem(tw) 

        for c in range(5):
            self.lw_sources.resizeColumnToContents(c)
        
        self.layout.addWidget(self.lw_sources)
        self.setMinimumSize( QSize(600,100) )
        self.layout.setSizeConstraint(QLayout.SetMinimumSize)
        
        # Build dialog layout
        self.dialogFinalise()        


# Overload this to provide some better size hinting to the inside tabs
class QTabWidgetExtend( QTabWidget ):

    auto_unfocus_tabs = ['?']

    def __init__(self, parent, **kwargs):
        super(QTabWidgetExtend, self).__init__(parent, **kwargs)
        self.w = parent
        self.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding )
            
        self._unfocus_tabs_enabled = True
    
    def sizeHint(self):
        return self.w.size()
    
    # A few wrappers to 
    def addTab(self, widget, name, focused=True, unfocus_on_refresh=False, **kwargs):
        widget.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding )
        # Automagically unfocus the help (+any other equivalent) tabs if were' refreshing a more interesting one
        widget._unfocus_on_refresh = unfocus_on_refresh
        t = super(QTabWidgetExtend, self).addTab(widget, name, **kwargs)
        
        return t
    
    def autoSelect(self):
        if self._unfocus_tabs_enabled:
            cw = self.currentWidget()
            if cw._unfocus_on_refresh:
                for w in range(0, self.count()):
                    uf = self.widget(w)._unfocus_on_refresh
                    if not uf and self.widget(w).isEnabled():
                        self.setCurrentIndex( w )
                        self._unfocus_tabs_enabled = False # Don't do this again (so user can select whatever they want)
                        break
        


#### View Object Prototypes (Data, Assignment, Processing, Analysis, Visualisation) e.g. used by plugins
class GenericView( QMainWindow ):

    help_tab_html_filename = None
    status = pyqtSignal(str)

    def __init__(self, plugin, parent, **kwargs):
        super(GenericView, self).__init__(parent, **kwargs)
    
        self.id = str( id( self ) )

        self.plugin = plugin
        self.m = parent
        self.m.views.append( self )
        
        self._floating = False
        self._pause_analysis_flag = False
        
        self.data = data.DataManager(self.m, self)
        self.name = self.m.plugin_names[ id( self.plugin ) ]

        self.thread = None

        self.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding )
        
        #self.w = QMainWindow()
        self.tabs = QTabWidgetExtend(self)
        self.tabs.setDocumentMode(True)
        self.tabs.setTabsClosable(False)
        self.tabs.setTabPosition( QTabWidget.South )
        self.tabs.setMovable(True)
        
        self.file_watcher = QFileSystemWatcher()            
        self.file_watcher.fileChanged.connect( self.onFileChanged )

        if self.plugin.help_tab_html_filename:
            self.help = QWebViewExtend(self, self.m.onBrowserNav) # Watch browser for external nav
            self.tabs.addTab(self.help, '?', unfocus_on_refresh=True)            
            template = self.plugin.templateEngine.get_template(self.plugin.help_tab_html_filename)
            self.help.setHtml( template.render( {
                        'htmlbase': os.path.join( utils.scriptdir,'html'),
                        'pluginbase': self.plugin.path,
                        'view': self,                        
                        } ), QUrl("~") 
                        )
        
        self.toolbars = {}
        self.addSelfToolBar() # Everything has one
        
        self.controls = defaultdict( dict ) # Store accessible controls
        
        self.register_url_handler( self.default_url_handler )

        self.setCentralWidget(self.tabs)
        
        self.status.connect( self.setWorkspaceStatus )
        
        self.config = config.ConfigManager() # Configuration manager object; handle all get/setting, defaults etc.
        
        self.workspace_item = self.m.addWorkspaceItem(self, self.plugin.default_workspace_category, self.name, is_selected=True, icon=self.plugin.workspace_icon) #, icon = None)

    def register_url_handler(self, url_handler):
        self.m.register_url_handler( self.id, url_handler ) 

    def render(self, metadata):
        return
        
    def delete(self):
        self.m.removeWorkspaceItem(self)
        # Tear down the config and data objects
        self.data.reset()
        self.config.reset()
        # Delete all threads (remove references)
        # FIXME: Wait for nice cleanup
        self.thread = None
        # Close the window obj
        self.m.views.remove( self )
        # Trigger notification for state change
        self.m.workspace_updated.emit()
        self.close()

    
    def autogenerate(self, *args, **kwargs):
        if self._pause_analysis_flag:
            self.setWorkspaceStatus('paused')
            return False
        
        self.tabs.autoSelect() # Unfocus the help file if we've done something here
        self.generate(*args, **kwargs)
    
    def generate(self):
        return
    
    # Callback function for threaded generators; see _worker_result_callback and start_worker_thread
    def generated(self, **kwargs):
        return
        
    def _worker_result_callback(self, kwargs_dict):
        self.status.emit('render')
        self.generated(**kwargs_dict)  
        self.status.emit('done')

    def _worker_error_callback(self):
        self.status.emit('error')

    def _worker_status_callback(self, s):
        self.setWorkspaceStatus(s)
        
    def _thread_finished_callback(self):
        self.thread = None
        
    def start_worker_thread(self, worker, callback=None):
        if callback == None:
            callback = self._worker_result_callback

        if self.thread != None: # Handle nicer; wait or similar
            return False
            
        thread = QThread()
        self.thread = thread #(thread, worker)
        #print "%s thread stack @%d" % (self.name, len(self.threads) )
         
        worker.result.connect( self._worker_result_callback )

        worker.error.connect( self._worker_error_callback )
        worker.error.connect( worker.deleteLater )
        worker.error.connect( thread.quit )

        worker.finished.connect( worker.deleteLater )
        worker.finished.connect( thread.quit )

        thread.finished.connect( thread.deleteLater )
        thread.finished.connect( self._thread_finished_callback )
        
        #worker.status.connect( self.setWorkspaceStatus )

        thread.worker = worker
        thread.started.connect( worker.run )
        worker.moveToThread(thread)
        self.status.emit('active')
        thread.start()
        
        
    def set_name(self, name):
        self.name = name
        try:
            self.workspace_item.setText(0, name)
        except:
            pass

        try: # Notify the mainview of the workspace change
            self.m.workspace_updated.emit()            
        except:
            pass

    def setWorkspaceStatus(self, status):
        self.m.setWorkspaceStatus( self.workspace_item, status)

    def clearWorkspaceStatus(self):
        self.m.clearWorkspaceStatus( self.workspace_item )

    def onDelete(self):
        self.delete()
            
    def onPopOutToggle(self, status):
        if status and not self._floating: # Only pop out if in
            # Pop us out
            #stack_index = self.m.stack.addWidget( self )
            self._parent = self.parent()
            self._floating = True
            self._placeholder = QWidget()
            self.m.stack.insertWidget(self.m.stack.currentIndex(), self._placeholder ) # Keep space in the stack prevent flow-over
            self.setParent(self.m, Qt.Window)
            self.show()
        elif self._floating: # Only pop in if out
            # Pop us in
            self._floating = False
            self.m.stack.addWidget(self)
            self.m.stack.removeWidget(self._placeholder)
            #self.setParent(self._parent, Qt.Window)

    def addSelfToolBar(self):            
        t = self.addToolBar('App')
        t.setIconSize( QSize(16,16) )

        delete_selfAction = QAction( QIcon( os.path.join(  utils.scriptdir, 'icons', 'cross.png' ) ), tr('Delete this app…'), self.m)
        delete_selfAction.setStatusTip('Delete this app')
        delete_selfAction.triggered.connect(self.onDelete)
        t.addAction(delete_selfAction)

        popout_selfAction = QAction( QIcon( os.path.join(  utils.scriptdir, 'icons', 'applications-blue.png' ) ), tr('Move to new window'), self.m)
        popout_selfAction.setStatusTip('Open this app in a separate window')
        popout_selfAction.setCheckable(True)
        popout_selfAction.setChecked(False)
        popout_selfAction.toggled.connect(self.onPopOutToggle)
        t.addAction(popout_selfAction)
        
        self.toolbars['self'] = t        

    def addDataToolBar(self, default_pause_analysis=False):            
        t = self.addToolBar('Data')
        t.setIconSize( QSize(16,16) )

        select_dataAction = QAction( QIcon( os.path.join(  utils.scriptdir, 'icons', 'data-source.png' ) ), tr('Select a data source…'), self.m)
        select_dataAction.setStatusTip('Select a compatible data source')
        select_dataAction.triggered.connect(self.onSelectDataSource)
        t.addAction(select_dataAction)

        select_dataAction = QAction( QIcon( os.path.join(  utils.scriptdir, 'icons', 'arrow-circle-double.png' ) ), tr('Recalculate'), self.m)
        select_dataAction.setStatusTip('Recalculate')
        select_dataAction.triggered.connect(self.onRecalculate)
        t.addAction(select_dataAction)
        
        pause_analysisAction = QAction( QIcon( os.path.join(  utils.scriptdir, 'icons', 'control-pause.png' ) ), tr('Pause automatic analysis'), self.m)
        pause_analysisAction.setStatusTip('Do not automatically refresh analysis when source data updates')
        pause_analysisAction.setCheckable(True)
        pause_analysisAction.setChecked(default_pause_analysis)
        pause_analysisAction.toggled.connect(self.onAutoAnalysisToggle)
        t.addAction(pause_analysisAction)        
        self._pause_analysis_flag = default_pause_analysis

        select_dataAction = QAction( QIcon( os.path.join(  utils.scriptdir, 'icons', 'data-output.png' ) ), tr('View resulting data…'), self.m)
        select_dataAction.setStatusTip('View resulting data output from this plugin')
        select_dataAction.triggered.connect(self.onViewDataOutput)
        t.addAction(select_dataAction)
        
        self.toolbars['image'] = t        

        
    def onSelectDataSource(self):
        # Basic add data source dialog. Extend later for multiple data sources etc.
        """ Open the mining setup dialog to define conditions, ranges, class-comparisons, etc. """
        dialog = DialogDataSource(parent=self, view=self)
        ok = dialog.exec_()
        if ok:
            for cb in dialog.lw_consumeri: # Get list of comboboxes
                i = cb.currentIndex() # Get selected item
                consumer_def = cb.consumer_def
                print consumer_def.target, i, len(cb.datasets)
                if i > 0: # Something in the list (-1) and not 'No data'
                    dso = cb.datasets[i]
                    self.data.consume_with(dso, consumer_def)  
                    
                else: # Stop consuming through this interface
                    self.data.stop_consuming( consumer_def.target )
             
            # Trigger notification for data source change; re-render inheritance map        
            #self.m.onDataInheritanceChanged()
            
            #self.generate() automatic
            
    def onViewDataOutput(self):
        # Basic add data source dialog. Extend later for multiple data sources etc.
        """ Open the mining setup dialog to define conditions, ranges, class-comparisons, etc. """
        dialog = DialogDataOutput(parent=self, view=self)        
        dialog.exec_()

    def closeEvent(self, event):
        self.onPopOutToggle(False)
        event.ignore()

    def getCreatedToolbar(self, name, id):
        if id not in self.toolbars:       
            self.toolbars[id] = self.addToolBar(name)
            self.toolbars[id].setIconSize( QSize(16,16) )

        return self.toolbars[id] 

    def addFigureToolBar(self):            
        t = self.getCreatedToolbar(tr('Figures'),'figure')

        export_imageAction = QAction( QIcon( os.path.join(  utils.scriptdir, 'icons', 'image-export.png' ) ), tr('Export current figure as image…'), self.m)
        export_imageAction.setStatusTip( tr('Export figure to image') )
        export_imageAction.triggered.connect(self.onSaveImage)
        t.addAction(export_imageAction)

        printAction = QAction(QIcon.fromTheme("document-print", QIcon( os.path.join( utils.scriptdir, 'icons', 'printer.png') )), tr('&Print…'), self)
        printAction.setShortcut('Ctrl+P')
        printAction.setStatusTip( tr('Print current figure') )
        #printAction.triggered.connect(self.onPrint)
        t.addAction(printAction)        
                        
        zoominAction = QAction(QIcon.fromTheme("zoom-in", QIcon( os.path.join( utils.scriptdir,'icons', 'zoom-in.png') )), tr('&Zoom in'), self)
        zoominAction.setShortcut('Ctrl++')
        zoominAction.setStatusTip( tr('Zoom in') )
        #zoominAction.triggered.connect(self.onZoomIn)
        t.addAction(zoominAction)

        zoomoutAction = QAction(QIcon.fromTheme("zoom-out", QIcon( os.path.join( utils.scriptdir,'icons', 'zoom-out.png') )), tr('&Zoom out'), self)
        zoomoutAction.setShortcut('Ctrl+-')
        zoomoutAction.setStatusTip( tr('Zoom out') )
        #zoomoutAction.triggered.connect(self.onZoomOut)
        t.addAction(zoomoutAction)


    def addExternalDataToolbar(self):     
        t = self.getCreatedToolbar( tr('External Data'),'external-data')
        
        watch_fileAction = QAction( QIcon( os.path.join(  utils.scriptdir, 'icons', 'eye--exclamation.png' ) ), tr('Watch data file(s) for changes…'), self.m)
        watch_fileAction.setStatusTip( tr('Watch external data file(s) for changes and automatically refresh') )
        watch_fileAction.triggered.connect(self.onWatchSourceDataToggle)
        watch_fileAction.setCheckable(True)
        watch_fileAction.setChecked(False)
        t.addAction(watch_fileAction)
        self._autoload_source_files_on_change = False


    
    def onWatchSourceDataToggle(self, checked):
        self._autoload_source_files_on_change = checked

    def onAutoAnalysisToggle(self, checked):
        self._pause_analysis_flag = checked
        
    def onFileChanged(self, file):
        if self._autoload_source_files_on_change:
            self.load_datafile( file )

    
    def onSaveImage(self):
        # Get currently selected webview
        cw = self.tabs.currentWidget()
        
        # Load dialog for image export dimensions and resolution
        # TODO: dialog!
        sizedialog = ExportImageDialog(self, size=cw.size() )
        ok = sizedialog.exec_()
        if ok:
            size = sizedialog.get_pixel_dimensions()
            dpm =  sizedialog.get_dots_per_meter()
            resample =  sizedialog.get_resample()
        
            cw.saveAsImage(size, dpm, resample)        


    def onRecalculate(self):
        self.generate()

    # Url handler for all default plugin-related actions; making these accessible to all plugins
    # from a predefined url structure: metapath://<view.id>/default_actions/data_source/add
    def default_url_handler(self, url):

        kind, id, action = url.split('/') # FIXME: Can use split here once stop using pathwaynames           
        
        # url is Qurl kind
        # Add an object to the current view
        if kind == "default_actions":
            
            if action == 'add' and id == 'data_source':
                # Add the pathway and regenerate
                self.onSelectDataSource()        

        
    def _build_entity_cmp(self,s,e,l):
        return e == None

    def _build_label_cmp(self,s,e,l):
        return e != None or l == None or str(s) == l

    def build_markers(self, zo, i, cmp_fn):
        accumulator = []
        last_v = None
        no = 0
        for n, (s,e,l) in enumerate(zo):
            v = zo[n][i]
            if cmp_fn(s, e, l):
                last_v = None
                continue
            no += 1
            if last_v == None or v != accumulator[-1][2]:
                accumulator.append( [s,s,v] )
            else:
                accumulator[-1][1] = s
            
            last_v = v
        
        print "%s reduced to %s" % ( no, len(accumulator) ) 
        return accumulator

# Workspace overview (Home) class

class HomeView( GenericView ):

    def __init__(self, parent, **kwargs):
        super(GenericView, self).__init__(parent, **kwargs) # We're overriding all of the GenericView Init, so super it
    
        self.plugin = None
        self.m = parent
        
        self._floating = False
    
        self.id = 'home' #str( id( self ) )
        self.name = "Home"

        self.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding )
        
        #self.w = QMainWindow()
        self.tabs = QTabWidgetExtend(self)
        self.tabs.setDocumentMode(True)
        self.tabs.setTabsClosable(False)
        self.tabs.setTabPosition( QTabWidget.South )
        self.tabs.setMovable(True)
        
        # Display welcome file
        self.help = QWebViewExtend(self, self.m.onBrowserNav) # Watch browser for external nav
        self.tabs.addTab(self.help,'?', unfocus_on_refresh=True)            
        template = self.m.templateEngine.get_template('welcome.html')
        self.help.setHtml( template.render( {
                    'htmlbase': os.path.join( utils.scriptdir,'html'),
                    } ), QUrl("~") 
                    )

        self.workspace = QWebViewExtend( self, onNavEvent=self.m.onBrowserNav )
        self.tabs.addTab(self.workspace,'Workspace')

        self.toolbars = {}
        self.addSelfToolBar() # Everything has one
        self.controls = defaultdict( dict ) # Store accessible controls
        
        self.register_url_handler( self.workspace_url_handler )
        self.setCentralWidget(self.tabs)
        
        self.config = QSettings()
        
        self.addFigureToolBar()
        
        self.workspace_item = self.m.addWorkspaceItem(self, None, self.name, is_selected=True, icon=QIcon( os.path.join( utils.scriptdir,'icons','home.png' )) )#, icon = None)

    def render(self):
        objects = []
        for v in self.m.views:
            objects.append( (v.id, v) )

        inheritance = [] # Inter datasetmanager links; used for view hierarchy
        for v in self.m.views:
            # v.id = origin
            for i,ws in v.data.watchers.items():
                for w in ws:
                    inheritance.append( (v.id, w.v.id) ) # watcher->view->id
                    
        links = [] # Links inputs -> outputs (dso links)
        

        template = self.m.templateEngine.get_template('d3/workspace.svg')
        self.workspace.setSVG(template.render( {'htmlbase': os.path.join( utils.scriptdir,'html'), 'objects':objects, 'inheritance':inheritance} )) 

        self.tabs.autoSelect()
        
        
    # Url handler for all default plugin-related actions; making these accessible to all plugins
    # from a predefined url structure: metapath://<view.id>/default_actions/data_source/add
    def workspace_url_handler(self, url):

        kind, id, action = url.split('/') # FIXME: Can use split here once stop using pathwaynames           
        print "Workspace handler: %s" % url
        # url is Qurl kind
        # Add an object to the current view
        if kind == "view":
            if action == 'view':
                for v in self.m.views:
                    if v.id == id:
                        # We've got the view object; find index in the stack
                        si = self.m.stack.indexOf(v)
                        if si:
                            self.m.stack.setCurrentIndex(si)
                            # Find the tree item and select it
                            self.m.workspace.setCurrentItem( v._workspace_tree_widget )
                        break      

            elif action == "connect":
                #"metapath://home/view/4545179728:scores,4545247392:input/connect"                          
                #id = origin:int,dest:int
                origin, dest = [o.split(':') for o in id.split(',')]
                #o/d[0] == view, [1] == interface
                # We have the view ids; so find the real things
                for v in self.m.views:
                    if v.id == origin[0]:
                        origin[0] = v
                        break

                for v in self.m.views:
                    if v.id == dest[0]:
                        dest[0] = v
                        break
                
                # Get the origin data
                source_data = origin[0].data.o[origin[1]]
                
                # We now have the two views
                for d in dest[0].data.consumer_defs:
                    if d.target == dest[1]:
                        dest[0].data.consume_with(source_data, d)
                        break
                                    

# Data view prototypes

class DataView(GenericView):
    def __init__(self, plugin, parent, **kwargs):
        super(DataView, self).__init__(plugin, parent, **kwargs)

        self.summary = QWebViewExtend(self)
        self.table = QTableView()
        self.viewer = QWebViewExtend(self, onNavEvent=self.m.onBrowserNav) # Optional viewer; activate only if there is scale data

        self.tabs.addTab(self.table, tr('Table'), unfocus_on_refresh=True )
        self.viewer_tab_index = self.tabs.addTab(self.viewer, tr('View'))
        self.tabs.setTabEnabled( self.viewer_tab_index, False)
        #self.tabs.addTab(self.summary, 'Summary')

    def render(self, metadata={}):
        # If we have scale data, enable and render the Viewer tab
        #FIXME: Must be along the top axis 
        if 'output' in self.data.o:
            dso = self.data.o['output']

            if float in [type(t) for t in dso.scales[1]]:
                self.tabs.setTabEnabled( self.viewer_tab_index, True)
            
                print "Scale data up top; make a spectra view"
                metadata['htmlbase'] = os.path.join( utils.scriptdir,'html')
            
                dso_z = zip( dso.scales[1], dso.entities[1], dso.labels[1] )

                # Compress data along the 0-dimensions by class (reduce the number of data series; too large)                
                dsot = dso.as_summary(dim=0, match_attribs=['classes'])

                # Copy to sort without affecting original
                scale = np.array(dso.scales[1])
                data = np.array(dsot.data)
                
                # Sort along x axis
                sp = np.argsort( scale )
                scale = scale[sp]
                data = data[:,sp]
                
                metadata['figure'] = {
                    'data':zip( scale, data.T ), # (ppm, [data,data,data])
                    'compounds': self.build_markers( dso_z, 1, self._build_entity_cmp ),
                    'labels': self.build_markers( dso_z, 2, self._build_label_cmp ),
                }

                template = self.m.templateEngine.get_template('d3/spectra.svg')
                self.viewer.setSVG(template.render( metadata ))
                
                f = open('/Users/mxf793/Desktop/test3.svg','w')
                f.write( template.render( metadata ) )
                f.close()

        return
        

# Import Data viewer

class ImportDataView( DataView ):

    import_type = tr('Data')
    import_filename_filter = tr("All Files") + " (*.*);;"
    import_description =  tr("Open experimental data from file")
    
    def __init__(self, plugin, parent, **kwargs):
        super(ImportDataView, self).__init__(plugin, parent, **kwargs)
    
        self.data.add_output('output') # Add output slot
        self.table.setModel(self.data.o['output'].as_table)
        
        self.addImportDataToolbar()
        
        #fn = self.onImportData()

    def onImportData(self):
        """ Open a data file"""
        filename, _ = QFileDialog.getOpenFileName(self.m, self.import_description, '', self.import_filename_filter)
        if filename:
            self.load_datafile( filename )

            self.file_watcher = QFileSystemWatcher()            
            self.file_watcher.fileChanged.connect( self.onFileChanged )
            self.file_watcher.addPath( filename )
            
            self.workspace_item.setText(0, os.path.basename(filename))
            
        return False

    def onFileChanged(self, file):
        pass
        #self.load_datafile( file )

    def addImportDataToolbar(self):   
        t = self.getCreatedToolbar( tr('External Data'),'external-data')
        
        import_dataAction = QAction( QIcon( os.path.join(  utils.scriptdir, 'icons', 'disk--arrow.png' ) ), 'Import %s file…' % self.import_type, self.m)
        import_dataAction.setStatusTip(self.import_description)
        import_dataAction.triggered.connect(self.onImportData)
        t.addAction(import_dataAction)
    
        self.addExternalDataToolbar()



# Analysis/Visualisation view prototypes


# Class for analysis views, using graph-based visualisations of defined datasets
# associated layout and/or analysis
class AnalysisView(GenericView):
    def __init__(self, plugin, parent, **kwargs):
        super(AnalysisView, self).__init__(plugin, parent, **kwargs)

        self.browser = QWebViewExtend( self, onNavEvent=parent.onBrowserNav )
        self.tabs.addTab(self.browser, tr('View') )
    
    def render(self, metadata, template='d3/figure.svg', target=None):
        if target == None:
            target = self.browser
            
        metadata['htmlbase'] = os.path.join( utils.scriptdir,'html')

        template = self.m.templateEngine.get_template(template)
        target.setSVG(template.render( metadata ))
                
        f = open("/Users/mxf793/Desktop/test.svg","w")
        f.write(template.render( metadata ))
        f.close()                
        
        
    # Build change table 
    def build_change_table_of_classes(self, dso, objs, classes):
        
        # Reduce dimensionality; combine all class/entity objects via np.mean()
        dso = dso.as_summary()
        
        #FIXME: Need to allow entities to be passed in and use entity / labels
        #entities = []
        #for o in objs:
        #    entities.extend( [ self.m.db.index[id] for id in o if id in self.m.db.index] )
         
           
        # Filter for the things we're displaying
        dso = dso.as_filtered( labels=objs)

        #data = data.as_class_grouped(classes=classes)
        data = np.zeros( (len(objs), len(classes)) )

        for y,l in enumerate(objs): #[u'PYRUVATE', u'PHOSPHO-ENOL-PYRUVATE']
            for x,c in enumerate(classes):
                try:
                    #e = self.m.db.index[o] # Get entity for lookup
                    data[y,x] = dso.data[ dso.classes[0].index(c), dso.labels[1].index(l) ]
                except: # Can't find it
                    pass
                
        return data
  
  
    def build_change_table_of_entitytypes(self, dso, objs, entityt):
        
        # Reduce dimensionality; combine all class/entity objects via np.mean()
        dso = dso.as_summary()
        
        entities = []
        for o in objs:
            entities.extend( [ self.m.db.index[id] for id in o if id in self.m.db.index] )
        # Filter for the things we're displaying
        dso = dso.as_filtered( entities=entities)

        #data = data.as_class_grouped(classes=classes)
        data = np.zeros( (len(objs), len(entityt)) )

        for y,obj in enumerate(objs): #[u'PYRUVATE', u'PHOSPHO-ENOL-PYRUVATE']
            for x,o in enumerate(obj):
                try:
                    e = self.m.db.index[o] # Get entity for lookup
                    data[y,x] = dso.data[ 0, dso.entities[1].index(e) ]
                except: # Can't find it
                    pass
                
        return data
  

    def build_log2_change_control_vs_multi(self, objs, classes):
        data = np.zeros( (len(objs), len(classes)) )
        for x,xl in enumerate(classes):
            for y,yl in enumerate(objs):
                data[y,x] = self.parent.data.get_log2(yl,xl) - self.parent.data.get_log2( yl , self.parent.experiment['control'] )
    
        return data


    def build_raw_change_control_vs_multi(self, objs, classes):
        data = np.zeros( (len(objs), len(classes)) )
        for x,xl in enumerate(classes):
            for y,yl in enumerate(objs):
                data[y,x] = np.mean( self.parent.data.quantities[yl][xl] ) - np.mean( self.parent.data.quantities[ yl ][ self.parent.experiment['control'] ] )
    
        return data

    def get_fig_tempfile(self, fig):
        tf = QTemporaryFile()
        tf.open()
        fig.savefig(tf.fileName(), format='png', bbox_inches='tight')
        return tf

    def addExperimentToolBar(self):

        t = self.addToolBar( tr('Experiment') )
        t.setIconSize( QSize(16,16) )

        # DATA MENU
        define_experimentAction = QAction( QIcon( os.path.join( utils.scriptdir,'icons','layout-design.png') ), tr('Define experiment…'), self)
        define_experimentAction.setShortcut('Ctrl+Q')
        define_experimentAction.setStatusTip( tr('Define experiment control, test and timecourse settings') )
        define_experimentAction.triggered.connect(self.onDefineExperiment)

        t.addAction(define_experimentAction)
        
        t.cb_control = QComboBox()
        t.cb_control.addItems(['Control'])
        self.config.add_handler('experiment_control', t.cb_control )

        t.cb_test = QComboBox()
        t.cb_test.addItems(['Test'])
        self.config.add_handler('experiment_test', t.cb_test )

        t.addWidget(t.cb_control)
        t.addWidget(t.cb_test)
    
        self.toolbars['experiment'] = t
        
        self.data.source_updated.connect( self.repopulate_experiment_classes ) # Update the classes if data source changes        

    def repopulate_experiment_classes(self):
        _control = self.config.get('experiment_control')
        _test = self.config.get('experiment_test')

        classes = self.data.i['input'].classes_l[0]

        if _control not in classes or _test not in classes:
            # Block signals so no trigger of update
            self.toolbars['experiment'].cb_control.blockSignals(True)
            self.toolbars['experiment'].cb_test.blockSignals(True)
            # Empty the toolbar controls
            self.toolbars['experiment'].cb_control.clear()
            self.toolbars['experiment'].cb_test.clear()
            # Data source change; update the experimental control with the data input source
            self.toolbars['experiment'].cb_control.addItems( [i for i in self.data.i['input'].classes_l[0]] )
            self.toolbars['experiment'].cb_test.addItem("*")
            self.toolbars['experiment'].cb_test.addItems( [i for i in self.data.i['input'].classes_l[0]] )
            # Reset to previous values (-if possible)
            self.toolbars['experiment'].cb_control.setCurrentText(_control)
            self.toolbars['experiment'].cb_test.setCurrentText(_test)
            # Unblock
            self.toolbars['experiment'].cb_control.blockSignals(False)
            self.toolbars['experiment'].cb_test.blockSignals(False)
            # If previously nothing set; now set it to something
            _control = _control if _control in self.data.i['input'].classes_l[0] else self.data.i['input'].classes_l[0][0]
            _test = _test if _test in self.data.i['input'].classes_l[0] else '*'

            self.config.set_many({
                'experiment_control': _control,
                'experiment_test': _test,
            })
        
        
    def onDataChanged(self):
        self.repopulate_experiment_classes()
        
    def onDefineExperiment(self):
        pass

    def onModifyExperiment(self):
        """ Update the experimental settings for analysis then regenerate """    
        self._experiment_control = self.toolbars['experiment'].cb_control.currentText()
        self._experiment_test = self.toolbars['experiment'].cb_test.currentText()
        self.generate()
    
# Class for analysis views, using graph-based visualisations of defined datasets
# associated layout and/or analysis
class AnalysisD3View(AnalysisView):
        
    def render(self, metadata, debug=False, template_name='figure'):
        metadata['htmlbase'] = os.path.join( utils.scriptdir,'html')
        
        
        template = self.m.templateEngine.get_template('d3/%s.svg' % template_name)
        self.browser.setSVG(template.render( metadata ))

        self.m.workspace_updated.emit()
                
        f = open("/Users/mxf793/Desktop/test.svg","w")
        f.write(template.render( metadata ))
        f.close()                
        
# Class for analysis views, using graph-based visualisations of defined datasets
# associated layout and/or analysis
class D3View(AnalysisView):
    def __init__(self, plugin, parent, **kwargs):
        super(D3View, self).__init__(plugin, parent, **kwargs)        
    
        self.parent = parent
        self.browser = QWebViewExtend( self.tabs, onNavEvent=parent.onBrowserNav )
    
    def generate(self):
        current_pathways = [self.parent.db.pathways[p] for p in self.parent.config.value('/Pathways/Show').split(',') if p in self.parent.db.pathways]
        # Iterate pathways and get a list of all metabolites (list, for index)
        metabolites = []
        reactions = []
        metabolite_pathway_groups = {}
        for p in current_pathways:

            for r in p.reactions:
                ms = r.mtins + r.mtouts
                for m in ms:
                    if m not in metabolites:
                        metabolites.append(m)

                for m in ms:
                    metabolite_pathway_groups[m] = current_pathways.index(p)

                for mi in r.mtins:
                    for mo in r.mtouts:
                        reactions.append( [ metabolites.index(mi), metabolites.index(mo) ] )
                
        
        # Get list of all reactions
        # In template:
        # Loop metabolites (nodes; plus their groups)
    
    
        metadata = { 'htmlbase': os.path.join( utils.scriptdir,'html'),
                     'pathways':[self.parent.db.pathways[p] for p in self.parent.config.value('/Pathways/Show').split(',')],
                     'metabolites':metabolites,
                     'metabolite_pathway_groups':metabolite_pathway_groups, 
                     'reactions':reactions,
                     }
        template = self.parent.templateEngine.get_template('d3/force.svg')

        self.browser.setSVG(template.render( metadata ))

          

# Class for analysis views, using graph-based visualisations of defined datasets
# associated layout and/or analysis
class AnalysisHeatmapView(AnalysisD3View):

    #self.build_heatmap_buckets( labelsX, labelsY, self.build_log2_change_table_of_classtypes( self.phosphate, labelsX ), remove_empty_rows=True, sort_data=True  )
    def build_heatmap_buckets(self, labelsX, labelsY, data, remove_empty_rows=False, remove_incomplete_rows=False, sort_data=False):
        buckets = []

        if remove_empty_rows:
            mask = ~np.isnan(data).all(axis=1)
            data = data[mask]
            labelsY = [l for l,m in zip(labelsY,mask) if m]

        elif remove_incomplete_rows:
            mask = ~np.isnan(data).any(axis=1)
            data = data[mask]
            labelsY = [l for l,m in zip(labelsY,mask) if m]


        # Broken, fix if needed
        #if remove_empty_cols:
        #    mask = ~np.isnan(data).all(axis=0)
        #    data = data.T[mask.T]
        #    labelsX = [l for l,m in zip(labelsX,mask) if m]

        if sort_data:
            # Preferable would be to sort by the total for each row
            # can then use that to sort the labels list also
            totals = np.ma.masked_invalid(data).sum(1).data # Get sum for rows, ignoring NaNs
            si = totals.argsort()[::-1]
            data = data[si] # Sort
            labelsY = list( np.array( labelsY )[si] ) # Sort Ylabels via numpy array.
        
        for x, xL in enumerate(labelsX):
            for y, yL in enumerate(labelsY):  

                if data[y][x] != np.nan:
                    buckets.append([ xL, yL, data[y][x] ] )

        return buckets    



class AnalysisCircosView(AnalysisD3View):
    def __init__(self, plugin, parent, **kwargs):
        super(AnalysisCircosView, self).__init__(plugin, parent, **kwargs)        
        self.parent = parent
        self.browser = QWebViewExtend( self, onNavEvent=parent.onBrowserNav )

    def build_matrix(self, targets, target_links):

        data = []
        for mx in targets:
            row = []
            for my in targets:
                n = len( list( target_links[my] & target_links[mx] ) )
                row.append( n )
    
            data.append( row )
        return data, targets







class AnalysisCircosPathwayView(AnalysisHeatmapView):
    def __init__(self, plugin, parent, **kwargs):
        super(AnalysisCircosPathwayView, self).__init__(plugin, parent, **kwargs)        

        self.parent = parent
        self.browser = QWebViewExtend( self, onNavEvent=parent.onBrowserNav )


    def build_matrix(self, targets, target_links):

        data = []
        for mx in targets:
            row = []
            for my in targets:
                n = len( list( target_links[my] & target_links[mx] ) )
                row.append( n )
    
            data.append( row )
        return data, targets


    def generate(self):
        pathways = self.parent.db.pathways.keys()
        pathway_metabolites = dict()
        
        for k,p in self.parent.db.pathways.items():
            pathway_metabolites[p.id] = set( [m for m in p.metabolites] )

        data_m, labels_m = self.build_matrix(pathways, pathway_metabolites)

        pathway_reactions = dict()
        
        for k,p in self.parent.db.pathways.items():
            pathway_reactions[p.id] = set( [m for m in p.reactions] )

        data_r, labels_r = self.build_matrix(pathways, pathway_reactions)


        pathway_active_reactions = dict()
        pathway_active_metabolites = dict()
        active_pathways = [self.parent.db.pathways[p] for p in self.parent.config.value('/Pathways/Show').split(',')]
        active_pathways_id = []
        
        for p in active_pathways:
            pathway_active_reactions[p.id] = set( [r for r in p.reactions] )
            pathway_active_metabolites[p.id] = set( [r for r in p.metabolites] )
            active_pathways_id.append(p.id)
    

        data_ar, labels_ar = self.build_matrix(active_pathways_id, pathway_active_reactions)
        data_am, labels_am = self.build_matrix(active_pathways_id, pathway_active_metabolites)


        self.render( {
            'htmlbase': os.path.join( utils.scriptdir,'html'),
            'figures': [[
                        {
                            'type':'circos',
                            'data': data_ar,
                            'labels': labels_ar,
                            'n':1,  
                            'legend':('Metabolic pathway reaction interconnections','Links between pathways indicate proportions of shared reactions between the two pathways in MetaCyc database')                             
                        },
                        {
                            'type':'circos',
                            'data': data_am,
                            'labels': labels_am,
                            'n':2,  
                            'legend':('Metabolic pathway metabolite interconnections','Links between pathways indicate proportions of shared metabolites between the two pathways in MetaCyc database')
                        },                                             
                    ]],
                    }, debug=True)


class remoteQueryDialog(genericDialog):

    def parse(self, data):
        # Parse incoming data and return a dict mapping the displayed values to the internal value
        l = data.split('\n')
        return dict( zip( l, l ) )

    def do_query(self):
        f = urllib2.urlopen(self.query_target % urllib.quote( self.textbox.text() ) )
        query_result = f.read()
        f.close()
        
        self.data = self.parse( query_result ) 
        self.select.clear()
        self.select.addItems( self.data.keys() )

    def __init__(self, parent, query_target=None, **kwargs):
        super(remoteQueryDialog, self).__init__(parent, **kwargs)        

        self.textbox = QLineEdit()
        querybutton = QPushButton('↺')
        querybutton.clicked.connect( self.do_query )

        queryboxh = QHBoxLayout()
        queryboxh.addWidget( self.textbox )        
        queryboxh.addWidget( querybutton )        
        
        self.data = None # Deprecated
        
        self.select = QListWidget()
        self.query_target = query_target
        
        self.layout.addLayout( queryboxh )
        self.layout.addWidget( self.select )
        
        self.dialogFinalise()



    

    
