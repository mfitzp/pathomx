# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
logging.debug('Loading views.py')


# Import PyQt5 classes
from .qt import *

import os, re, sys, logging
from collections import OrderedDict

# Pathomx classes
from . import utils
from . import db

import numpy as np
import pandas as pd

from .globals import styles

# Translation (@default context)
from .translate import tr

from .qt import USE_QT_PY, PYQT4, PYQT5

ON_RTD = os.environ.get('READTHEDOCS', None) == 'True'

if ON_RTD or USE_QT_PY == PYQT5:
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
elif USE_QT_PY == PYQT4:
    from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas

if sys.version_info >= (3,0):
    unicode = str

from matplotlib.backend_bases import NavigationToolbar2
from matplotlib.figure import Figure
from matplotlib.path import Path
from matplotlib.patches import BoxStyle, Ellipse

import matplotlib.cm as cm

from IPython.nbconvert.exporters import export as IPyexport
from IPython.nbconvert.exporters.export import exporter_map as IPyexporter_map

progname = os.path.basename(sys.argv[0])
progversion = "0.1"

        
# Web views default HTML
BLANK_DEFAULT_HTML = """
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
"""

# Handler for the views available for each app. Extended implementation of the QTabWidget
# to provide extra features, e.g. refresh handling, auto focus-un-focus, status color-hinting
class ViewManager( QTabWidget ):
    """ 
    Manager class for the tool views.
    
    Inherits from QTabWidget to focusing tabs on add and unfocus-on-refresh. The QTabWidget method
    is overridden to wrap addView. All other QTabWidget methods and attributes are available.
    """
    
    auto_unfocus_tabs = ['?']
    # Signals
    source_data_updated = pyqtSignal()
    style_updated = pyqtSignal()
    updated = pyqtSignal()

    def __init__(self, parent, auto_unfocus_tabs = True, auto_delete_on_no_data = True, **kwargs):
        super(ViewManager, self).__init__()
        
        self.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding )
            
        self.setDocumentMode(True)
        self.setTabsClosable(False)
        self.setTabPosition( QTabWidget.South )
        #self.setMovable(True)
            
        self._auto_unfocus_tabs = auto_unfocus_tabs
        self._auto_delete_on_no_data = auto_delete_on_no_data
        
        self.data = dict() # Stores data from which figures are rendered
        self.views = {}
        
        self._refresh_later = set() # Indexes of views to update at some future point
    
        self.source_data_updated.connect(self.onRefreshAll)
        self.style_updated.connect(self.onRefreshAll)
    
    # A few wrappers to 
    def addView(self, widget, name, color=None, createargs=[], focused=True, unfocus_on_refresh=False, **kwargs):
        """
        Add a view to this view manager.

        Adds the specified widget to the ViewManager under a named tab.

        :param widget: The widget to add as a view.
        :type widget: object inherited from QWidget or views.BaseView
        :param name: The name of the widget, will be shown on the tab and used as a data-redirector selector.
        :type name: str
        :rtype: int tab/view index     
        """
        
        widget.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding )
        # Automagically unfocus the help (+any other equivalent) tabs if we're refreshing a more interesting one
        widget._unfocus_on_refresh = unfocus_on_refresh
        widget.vm = self
        widget.name = name

        if name in self.views:
            # Already exists; we check if of the same type before calling this
            # so here we just replace
            t = self.indexOf( self.views[name] )
            self.widget(t).deleteLater()
            self.removeTab(t)
            self.insertTab(t, widget, name, **kwargs)
        else:
            t = super(ViewManager, self).addTab(widget, name, **kwargs)
        self.views[name] = widget
        
        if color:
            self.tabBar().setTabTextColor(t, color)
            
        return t
    
    def get_type(self, name):
        """ Return the type of a current view (by name) used to check whether to re-add/replace widget """
        if name in self.views:
            return type(self.views[name])
        else:
            return None
    
    def onRefreshAll(self): #, to_refresh=None):
        to_delete = []
        
        #if to_refresh is None:
        #    others = set( range(self.count()) )
        #    others.discard(self.currentIndex())
        #    self._refresh_later.update( others )
        #    self.postponed_refresh.emit()
        #    to_refresh = [self.currentIndex()]
        
        for n in range(self.count()): #to_refresh:

            if hasattr(self.widget(n),'autogenerate') and self.widget(n).autogenerate:
                try:
                    self.widget(n).autogenerate()
                except Exception as e:
                    logging.error(e)
                    # Failure; disable the tab or delete
                    if self._auto_delete_on_no_data:
                        to_delete.append( self.widget(n) )
                    else:
                        self.setTabEnabled( n, False)
                else:
                    # Success; enable the tab
                    self.setTabEnabled( n, True)

        # Do after so don't upset ordering on loop
        for w in to_delete:
            k = self.views.keys()[ list( self.views.values() ).index( w ) ]
            del self.views[k]
            w.deleteLater()
            self.removeTab( self.indexOf(w) )


        self.updated.emit()
        
    #def onRefreshLater(self):
    #    self.onRefreshAll( to_refresh=self._refresh_later )
    #    self._refresh_later.clear()
        
    def addTab(self, widget, name, **kwargs):
        """
        Overridden to redirect addTab calls to addView method. Do not use.
        """
        self.addView(widget, name, **kwargs)
    
    def autoSelect(self):
        """
        Autoselect one of the current views.

        Iterates through all current views and selects the first that is not flagged `_unfocus_on_refresh`. 
        This is used primarily to unfocus the help tabs following successful data calculation.
        """    
        if self._auto_unfocus_tabs:
            cw = self.currentWidget()
            if cw._unfocus_on_refresh:
                for w in range(0, self.count()):
                    uf = self.widget(w)._unfocus_on_refresh
                    if not uf and self.widget(w).isEnabled():
                        self.setCurrentIndex( w )
                        self._unfocus_tabs_enabled = False # Don't do this again (so user can select whatever they want)
                        break

class BaseView(object):
    """
    Base View prototype with stubs and data-handling functions that are generically useful.
    Sub-class from this if you want to create a new type of view, e.g. supporting an alternative
    graph rendering engine. If you just want to create a new graph-type you should sub-class
    from one of the backend specific stubs, e.g. MplView or D3View.
    """
     
    _offers_rerender_on_save = False
    is_floatable_view = False
    is_mpl_toolbar_enabled = False
    
    @property
    def data(self):
        return self.vm.data[ self.name ] 
        
    def autogenerate(self):
        self.generate( **self.vm.data[ self.name ] )
        
    def _build_entity_cmp(self,s,e,l):
        return e is None

    def _build_label_cmp(self,s,e,l):
        return e is not None or l is None or str(s) == l

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
            if last_v is None or v != accumulator[-1][2]:
                accumulator.append( [s,s,v] )
            else:
                accumulator[-1][1] = s
            
            last_v = v
        
        print("%s reduced to %s" % ( no, len(accumulator) )) 
        return accumulator

# Views for Svg/HTML based views (inc d3)
class RenderPageToFile(QWebPage): 
    def __init__(self, wv, fn, settings): # 11811 == 300dpi
        super(RenderPageToFile, self).__init__()

        self.mainFrame().setScrollBarPolicy(Qt.Vertical, Qt.ScrollBarAlwaysOff)
        self.mainFrame().setScrollBarPolicy(Qt.Horizontal, Qt.ScrollBarAlwaysOff)

        #self.settings().setAttribute( QWebSettings.JavascriptEnabled,False)

        self.finished = False
            
        self.size = settings.get_pixel_dimensions()
        self.dpm = settings.get_dots_per_meter()
        self.resample = settings.get_resample()

        self.setViewportSize(self.size)
        self.loadFinished.connect(self._loadFinished)
        self.fn = fn
        
        c = wv.page().mainFrame().toHtml()
        c = c.replace('<html><head></head><body>','')
        c = c.replace('</body></html>','')
        if self.resample: # Remove drawn graph; we'll regenerate
            c = re.sub( '\<g.*\/g\>', '', c,  re.MULTILINE)
        else:
            # Keep graph but apply sizing; using svg viewport scaling
            # this is a bit hacky; rewriting the svg width/height parameters using regex
            c = re.sub( '(\<svg.*width=")([^"]*)(".*\>)', '\g<1>%d\g<3>' % self.size.width(), c)
            c = re.sub( '(\<svg.*height=")([^"]*)(".*\>)', '\g<1>%d\g<3>' % self.size.height(), c)
            
        self.mainFrame().setHtml( c )
    
    def _loadFinished(self, ok):

        frame = self.mainFrame()
        if self.resample: # If resampling we need to regenerate the graph
            frame.evaluateJavaScript( "_pathomx_render_trigger();" )

        image = QImage(self.size, QImage.Format_ARGB32)
        image.setDotsPerMeterX(self.dpm)
        image.setDotsPerMeterY(self.dpm)
        painter = QPainter(image)
        frame.render(painter)
        painter.end()

        image.save(self.fn)
        self.finished = True


class WebPageJSLog(QWebPage):
    """
    Redirects Javascript errors to the console (STDOUT) for debugging.
    """

    def __init__(self, parent=None, **kwargs):
        super(WebPageJSLog, self).__init__(parent, **kwargs)

    def javaScriptConsoleMessage(self, msg, lineNumber, sourceID):
        logging.debug("JsConsole(%s:%d): %s" % (sourceID, lineNumber, msg))

class QWebPageExtend(QWebPage):
    def shouldInterruptJavascript():
        return False


        
class TableView(QTableView):
    """
    Modified QTableView with additional metadata for internal use.
    """
    is_floatable_view = False
    is_mpl_toolbar_enabled = False
    
    def copy(self):
        selection = self.selectionModel()
        indexes = selection.selectedIndexes()
        model = self.model()
        
        if len(indexes) < 1:
            return

        previous = indexes[0]
        indexes = indexes[1:]
        
        selected_text = ''

        for current in indexes:
            data = model.data(previous, Qt.DisplayRole)
            text = str(data)
            selected_text += text
            if current.row() != previous.row():
                selected_text += '\n'
            else:
                selected_text += '\t'
            previous = current

        selected_text += str( model.data(current, Qt.DisplayRole) )
        selected_text += '\n'
        qApp.clipboard().setText(selected_text)

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.Copy):
            self.copy()
        else:
            return super(TableView, self).keyPressEvent(event)        


class WebView(QWebView, BaseView):
    """
    Modified QWebView with internal navigation handling, loadfinished-resize triggers
    for SVG, HTML, etc.
    """

    def __init__(self, parent, **kwargs):
        super(WebView, self).__init__(None, **kwargs)        
        
        #self.setPage( WebPageJSLog(parent) )
        self.setHtml(BLANK_DEFAULT_HTML,QUrl("~"))

        self.page().setContentEditable(False)
        self.page().setLinkDelegationPolicy( QWebPage.DelegateExternalLinks )
        # self.page().settings().setAttribute( QWebSettings.JavascriptEnabled,False)

        self.setSizePolicy( QSizePolicy.Expanding, QSizePolicy.Expanding )
        #self.loadFinished.connect(self._loadFinished)
        
        # Override links for internal link cleverness
        #if hasattr(self.w,'onBrowserNav'):
        #    self.onNavEvent = self.w.onBrowserNav
        #    self.linkClicked.connect( self.delegateUrlWrapper )

        self.setContextMenuPolicy(Qt.CustomContextMenu) # Disable right-click

    
    def delegateUrlWrapper(self, url):
        if url.isRelative() and url.hasFragment(): # Fugly; use JQuery to scroll to anchors (Qt is broken if using setHtml)
            self.page().currentFrame().evaluateJavaScript("$('html,body').scrollTop( $(\"a[name='%s']\").offset().top );" % url.fragment()) 
        else:
            self.onNavEvent(url)
        
       
    def _loadFinished(self, ok):
        # FIXME for ref to parent; will need to pass something as obj parent
        """
        sizer = self.w.views.size()
        self.page().currentFrame().addToJavaScriptWindowObject("QtWebView", self)
        self.page().currentFrame().evaluateJavaScript( "QtViewportSize={'x':%s,'y':%s};" % ( sizer.width()-30, sizer.height()-80 ) ) #-magic number for scrollbars (ugh)        
        self.page().currentFrame().evaluateJavaScript( "_pathomx_render_trigger();" )
        """
 
    def saveAsImage(self,settings): # Size, dots per metre (for print), resample (redraw) image
        filename, _ = QFileDialog.getSaveFileName(self, 'Save current figure', '',  "Tagged Image File Format (*.tif);;\
                                                                                     Portable Network Graphics (*.png)")
        if filename:
            r = RenderPageToFile(self, filename, settings ) 
            while r.finished != True:
                QCoreApplication.processEvents()
    
    def getSize(self):
        if self.w.size() == QSize(100,30):
            return self.w.sizeHint()
        else:
            return self.w.size()
                
    def sizeHint(self):
        return QSize(600,400)
            
    @pyqtSlot(str)
    def delegateLink(self, url):
        self.onNavEvent( QUrl(url) )
        return True
        
    def generate(self):
        pass
        
    

class D3View(WebView):

    """
    Modified QWebView (via WebView) with d3 generated SVG image saving handler.
    
    Use this as a basis for any custom d3-based rendering views.
    """

    d3_template = 'd3/figure.svg'
    _offers_rerender_on_save = True

    def setSVG(self, svg):
        super(D3View, self).setHtml(svg, QUrl('file:///') )             


    def generate_d3(self, metadata):
        metadata['htmlbase'] = os.path.join( utils.scriptdir,'html')

# D3 legacy figure views (single js/svg; needs extracting)
class D3LegacyView(D3View):

    d3_template = 'figure.svg'

    def generate(self, metadata):
        metadata['htmlbase'] = os.path.join( utils.scriptdir,'html')


class HTMLView(WebView):
    """
    Convenience wrapper for WebView for HTML viewing.
    """
    def __init__(self, parent, html=None, **kwargs):
        super(HTMLView, self).__init__(parent, **kwargs)        
        if html:
            self.generate(html)
    
    def generate(self, html):
        self.setHtml(unicode(html), QUrl('file:///')) 

class NotebookView(QWebView, BaseView):
    def __init__(self, parent, notebook, **kwargs):
        super(NotebookView, self).__init__(None, **kwargs)        

        self.page().setContentEditable(False)
        self.page().setLinkDelegationPolicy( QWebPage.DelegateExternalLinks )
        # self.page().settings().setAttribute( QWebSettings.JavascriptEnabled,False)

        if notebook:
            self.generate(notebook)
            
    autogenerate = False

    def generate(self, notebook):
        html, resources = IPyexport(IPyexporter_map['html'], notebook)  
        self.setHtml(unicode(html), QUrl('file:///')) 

        
class StaticHTMLView(HTMLView):
    """
    Convenience wrapper for WebView for HTML viewing of non-dynamic content.
    
    This is used for tool help files which do not need to refresh on data update.
    """
    def __init__(self, parent, html=None, **kwargs):
        super(StaticHTMLView, self).__init__(parent, html, **kwargs)        

        self.page().setContentEditable(False)
        self.page().settings().setAttribute( QWebSettings.JavascriptEnabled,False)
    
    
    autogenerate = False


class SVGView(D3View):
    
    def generate(self, svg):
        self.setSVG( svg.data )

class WheezyView(WebView):
    
    def generate(self, template, metadata={}):
        metadata['htmlbase'] = os.path.join( utils.scriptdir,'html')
        self.setHtml(template.render( metadata ),QUrl("~")) 


class MplNavigationHandler(NavigationToolbar2):
    def _init_toolbar(self):
        pass
        
    def draw_rubberband(self, event, x0, y0, x1, y1):
        height = self.canvas.figure.bbox.height
        y1 = height - y1
        y0 = height - y0

        w = abs(x1 - x0)
        h = abs(y1 - y0)

        rect = [int(val)for val in (min(x0, x1), min(y0, y1), w, h)]
        self.canvas.drawRectangle(rect)

    def select_region(self, *args):
        """Activate zoom to rect mode"""
        if self._active == 'REGION':
            self._active = None
        else:
            self._active = 'REGION'

        if self._idPress is not None:
            self._idPress = self.canvas.mpl_disconnect(self._idPress)
            self.mode = ''

        if self._idRelease is not None:
            self._idRelease = self.canvas.mpl_disconnect(self._idRelease)
            self.mode = ''

        if self._active:
            self._idPress = self.canvas.mpl_connect('button_press_event',
                                                    self.press_region)
            self._idRelease = self.canvas.mpl_connect('button_release_event',
                                                      self.release_region)
            self.mode = 'region rect'
            self.canvas.widgetlock(self)
        else:
            self.canvas.widgetlock.release(self)

        for a in self.canvas.figure.get_axes():
            a.set_navigate_mode(self._active)

        self.set_message(self.mode)

    def press_region(self, event):
        """the press mouse button in zoom to rect mode callback"""
        # If we're already in the middle of a zoom, pressing another
        # button works to "cancel"
        if self._ids_zoom != []:
            for zoom_id in self._ids_zoom:
                self.canvas.mpl_disconnect(zoom_id)
            self.release(event)
            self.draw()
            self._xypress = None
            self._button_pressed = None
            self._ids_zoom = []
            return

        if event.button == 1:
            self._button_pressed = 1
        elif event.button == 3:
            self._button_pressed = 3
        else:
            self._button_pressed = None
            return

        x, y = event.x, event.y

        # push the current view to define home if stack is empty
        if self._views.empty():
            self.push_current()

        self._xypress = []
        for i, a in enumerate(self.canvas.figure.get_axes()):
            if (x is not None and y is not None and a.in_axes(event) and
                    a.get_navigate() and a.can_zoom()):
                self._xypress.append((x, y, a, i, a.viewLim.frozen(),
                                      a.transData.frozen()))

        id1 = self.canvas.mpl_connect('motion_notify_event', self.drag_region)
        id2 = self.canvas.mpl_connect('key_press_event',
                                      self._switch_on_zoom_mode)
        id3 = self.canvas.mpl_connect('key_release_event',
                                      self._switch_off_zoom_mode)

        self._ids_zoom = id1, id2, id3
        self._zoom_mode = event.key

        self.press(event)

    def release_region(self, event):
        """the release mouse button callback in select region mode"""
        if not self._xypress:
            return

        last_a = []

        for cur_xypress in self._xypress:
            x, y = event.x, event.y
            lastx, lasty, a, ind, lim, trans = cur_xypress
            # ignore singular clicks - 5 pixels is a threshold
            if abs(x - lastx) < 5 or abs(y - lasty) < 5:
                self._xypress = None
                self.release(event)
                self.draw()
                return

            x0, y0, x1, y1 = lim.extents

            # zoom to rect
            inverse = a.transData.inverted()
            lastx, lasty = inverse.transform_point((lastx, lasty))
            x, y = inverse.transform_point((x, y))
            Xmin, Xmax = a.get_xlim()
            Ymin, Ymax = a.get_ylim()

            # detect twinx,y axes and avoid double zooming
            twinx, twiny = False, False
            if last_a:
                for la in last_a:
                    if a.get_shared_x_axes().joined(a, la):
                        twinx = True
                    if a.get_shared_y_axes().joined(a, la):
                        twiny = True
            last_a.append(a)

            if twinx:
                x0, x1 = Xmin, Xmax
            else:
                if Xmin < Xmax:
                    if x < lastx:
                        x0, x1 = x, lastx
                    else:
                        x0, x1 = lastx, x
                    if x0 < Xmin:
                        x0 = Xmin
                    if x1 > Xmax:
                        x1 = Xmax
                else:
                    if x > lastx:
                        x0, x1 = x, lastx
                    else:
                        x0, x1 = lastx, x
                    if x0 > Xmin:
                        x0 = Xmin
                    if x1 < Xmax:
                        x1 = Xmax

            if twiny:
                y0, y1 = Ymin, Ymax
            else:
                if Ymin < Ymax:
                    if y < lasty:
                        y0, y1 = y, lasty
                    else:
                        y0, y1 = lasty, y
                    if y0 < Ymin:
                        y0 = Ymin
                    if y1 > Ymax:
                        y1 = Ymax
                else:
                    if y > lasty:
                        y0, y1 = y, lasty
                    else:
                        y0, y1 = lasty, y
                    if y0 > Ymin:
                        y0 = Ymin
                    if y1 < Ymax:
                        y1 = Ymax

        self.add_region_callback(x0, y0, x1, y1)

        self._xypress = None
        self._button_pressed = None

        self._zoom_mode = None

        self.push_current()
        self.release(event)


    def drag_region(self, event):
        """the drag callback in zoom mode"""

        if self._xypress:
            x, y = event.x, event.y
            lastx, lasty, a, ind, lim, trans = self._xypress[0]

            # adjust x, last, y, last
            x1, y1, x2, y2 = a.bbox.extents
            x, lastx = max(min(x, lastx), x1), min(max(x, lastx), x2)
            y, lasty = max(min(y, lasty), y1), min(max(y, lasty), y2)

            if self._zoom_mode == "x":
                x1, y1, x2, y2 = a.bbox.extents
                y, lasty = y1, y2
            elif self._zoom_mode == "y":
                x1, y1, x2, y2 = a.bbox.extents
                x, lastx = x1, x2

            self.draw_rubberband(event, x, y, lastx, lasty)


# Matplotlib-based views handler. Extend render call for update/refresh(?)
class MplView(FigureCanvas, BaseView):
    """
    Base class for matplotlib based views. This handles graph canvas setup, toolbar initialisation
    and figure save options.
    """
    is_floatable_view = True
    is_mpl_toolbar_enabled = True

    """Ultimately, this is a QWidget (as well as a FigureCanvasAgg, etc.)."""
    def __init__(self, parent, width=5, height=4, dpi=100, **kwargs):

        self.v = parent

        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.ax = self.fig.add_subplot(111)
        
        self.ax.plot([1, 2, 3, 4])

        self.ax.spines['top'].set_visible(False)
        self.ax.spines['right'].set_visible(False)
        self.ax.get_xaxis().tick_bottom()
        self.ax.get_yaxis().tick_left()

        FigureCanvas.__init__(self, self.fig)

        self.setParent(parent.views)

        FigureCanvas.setSizePolicy(self,
                                   QSizePolicy.Expanding,
                                   QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)
        
        # Install navigation handler; we need to provide a Qt interface that can handle multiple 
        # plots in a window under separate tabs
        self.navigation = MplNavigationHandler(self)

        self._current_axis_bounds = None

    def generate(self):
        pass

    def saveAsImage(self, settings): # Size, dots per metre (for print), resample (redraw) image
        filename, _ = QFileDialog.getSaveFileName(self, 'Save current figure', '',  "Tagged Image File Format (*.tif);;\
                                                                                     Portable Document File (*.pdf);;\
                                                                                     Encapsulated Postscript File (*.eps);;\
                                                                                     Scalable Vector Graphics (*.svg);;\
                                                                                     Portable Network Graphics (*.png)")

        if filename:
            size = settings.get_print_size('in')
            dpi = settings.get_dots_per_inch()
            prev_size = self.fig.get_size_inches()
            self.fig.set_size_inches(*size)
            
            self.fig.savefig(filename, dpi=dpi)
            self.fig.set_size_inches(*prev_size)
            self.redraw()
            
    def redraw(self):
        #FIXME: Ugly hack to refresh the canvas
        self.resize( self.size() - QSize(1,1) )
        self.resize( self.size() + QSize(1,1) )
        
    def resizeEvent(self,e):
        FigureCanvas.resizeEvent(self,e)
        

    def get_text_bbox_screen_coords(self, t):
        bbox = t.get_window_extent(self.get_renderer())        
        return bbox.get_points()

    def get_text_bbox_data_coords(self, t):
        bbox = t.get_window_extent(self.get_renderer())        
        axbox = bbox.transformed(self.ax.transData.inverted())
        return axbox.get_points()
        
    def extend_limits(self, a, b):
        # Extend a to meet b where applicable
        ax, ay = list(a[0]), list(a[1])
        bx, by = b[:, 0], b[:, 1]
   
        ax[0] = bx[0] if bx[0] < ax[0] else ax[0]
        ax[1] = bx[1] if bx[1] > ax[1] else ax[1]

        ay[0] = by[0] if by[0] < ay[0] else ay[0]
        ay[1] = by[1] if by[1] > ay[1] else ay[1]
                
        return [ax,ay]
 
 
class IPyMplView(MplView):
    """Ultimately, this is a QWidget (as well as a FigureCanvasAgg, etc.)."""
    def generate(self, fig=None):

        if fig is None:
            return
        
        fc = fig.get_facecolor()
        if fc == (1, 1, 1, 0): # Default non-background
            fig.set_facecolor('white')

        fig.set_dpi(100)

        lims = []
        bounds = []
        pos = []

        # Reset the xlim and ylim to the previous figure
        for a in self.fig.get_axes():
            xmin, xmax = a.get_xlim()
            ymin, ymax = a.get_ylim()

            lims.append((xmin, xmax, ymin, ymax))
            pos.append(a.get_position().frozen())


        self.ax = None
        del self.fig
        del self.figure

        self.fig = fig
        self.figure = fig
        self.fig.set_canvas(self)

        boundsl = []
        for i, a in enumerate(self.fig.get_axes()):
            xmin, xmax, ymin, ymax = lims[i]
            bounds = (a.get_xbound(), a.get_ybound())
            if self._current_axis_bounds and self._current_axis_bounds[i] == bounds:
                    a.set_xlim((xmin, xmax))
                    a.set_ylim((ymin, ymax))
                    a.set_position(pos[i], 'active')

            else:
                # Reset the view if we've gone too far
                a.set_position(a.get_position().frozen(), 'original')

            boundsl.append(bounds)

        self._current_axis_bounds = boundsl


        self.redraw()
        self.draw()

        self.is_blank = False

class DataFrameModel(QAbstractTableModel):
    """ data model for a DataFrame class """
    def __init__(self):
        super(DataFrameModel, self).__init__()
        self.df = pd.DataFrame()

    def setDataFrame(self, dataFrame):
        self.df = dataFrame

    def signalUpdate(self):
        """ tell viewers to update their data (this is full update, not
        efficient)"""
        self.layoutChanged.emit()

    #------------- table display functions -----------------
    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None #QVariant()

        if orientation == Qt.Horizontal:
            try:
                return self.df.columns.tolist()[section]
            except (IndexError, ):
                return None #QVariant()
        elif orientation == Qt.Vertical:
            try:
                # return self.df.index.tolist()
                return self.df.index.tolist()[section]
            except (IndexError, ):
                return None #QVariant()

    def data(self, index, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None #QVariant()

        if not index.isValid():
            return None #QVariant()

        return str(self.df.iloc[index.row(), index.column()])

    def flags(self, index):
            flags = super(DataFrameModel, self).flags(index)
            flags |= Qt.ItemIsEditable
            return flags

    def rowCount(self, index=QModelIndex()):
        return self.df.shape[0]

    def columnCount(self, index=QModelIndex()):
        return self.df.shape[1]


class DataFrameWidget(QWidget, BaseView):
    """ a simple widget for using DataFrames in a gui """
    def __init__(self, dataFrame, parent=None):
        super(DataFrameWidget, self).__init__(parent.w)

        self.dataModel = DataFrameModel()
        self.dataTable = QTableView()
        self.dataTable.setModel(self.dataModel)

        layout = QVBoxLayout()
        layout.addWidget(self.dataTable)
        self.setLayout(layout)
        # Set DataFrame
        self.setDataFrame(dataFrame)

    def setDataFrame(self, dataFrame):
        self.dataModel.setDataFrame(dataFrame)
        self.dataModel.signalUpdate()
        #self.dataTable.resizeColumnsToContents()

    def generate(self, data=None):
        if data is not None:
            self.setDataFrame(data)

    
class D3PrerenderedView(D3View):
    
    def generate(self, metadata, template):
        self.d3_template = template
        self.generate_d3( metadata )
    

class D3ForceView(D3View):


    def generate(self):
        current_pathways = [db.dbm.pathway(p) for p in self.parent.config.value('/Pathways/Show').split(',') if db.dbm.pathway(p) is not None]
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
                     'pathways':[db.dbm.pathway(p) for p in self.parent.config.value('/Pathways/Show').split(',')],
                     'metabolites':metabolites,
                     'metabolite_pathway_groups':metabolite_pathway_groups, 
                     'reactions':reactions,
                     }


# D3 Based bargraph view
class D3SpectraView(D3View):

    d3_template = 'd3/spectra.svg'

    def generate(self, dso=None):
        if dso is None or not float in [type(t) for t in dso.scales[1]]:   
            assert False # Can't continue
            
        # If we have scale data, enable and render the Viewer tab
        #FIXME: Must be along the top axis 
        print("Scale data up top; make a spectra view")
        metadata = {'htmlbase': os.path.join( utils.scriptdir,'html')}
    
        dso_z = list(zip( dso.scales[1], dso.entities[1], dso.labels[1] ))

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
            'data':list(zip( scale, data.T )), # (ppm, [data,data,data])
            'compounds': self.build_markers( dso_z, 1, self._build_entity_cmp ),
            'labels': self.build_markers( dso_z, 2, self._build_label_cmp ),
        }

        
        
class EntityBoxStyle(BoxStyle._Base):
    """
    A simple box.
    """

    def __init__(self, pad=0.1):
        """
        The arguments need to be floating numbers and need to have
        default values.

         *pad*
            amount of padding
        """

        self.pad = pad
        super(EntityBoxStyle, self).__init__()

    def transmute(self, x0, y0, width, height, mutation_size):
        """
        Given the location and size of the box, return the path of
        the box around it.

         - *x0*, *y0*, *width*, *height* : location and size of the box
         - *mutation_size* : a reference scale for the mutation.

        Often, the *mutation_size* is the font size of the text.
        You don't need to worry about the rotation as it is
        automatically taken care of.
        """

        # padding
        pad = mutation_size * self.pad

        # width and height with padding added.
        width, height = width + 2.*pad, \
                        height + 2.*pad,

        # boundary of the padded box
        x0, y0 = x0-pad, y0-pad,
        x1, y1 = x0+width, y0 + height

        cp = [(x0, y0),
              (x1, y0), (x1, y1), (x0, y1),
              (x0-pad, (y0+y1)/2.), (x0, y0),
              (x0, y0)]

        com = [Path.MOVETO,
               Path.LINETO, Path.LINETO, Path.LINETO,
               Path.LINETO, Path.LINETO,
               Path.CLOSEPOLY]

        path = Path(cp, com)

        return path


# register the custom style
BoxStyle._style_list["entity-tip"] = EntityBoxStyle

        
        
        
class D3DifferenceView(D3View):
    """
    A matplotlib-based difference-lineplot viewer.
    
    Takes two inputs - line A and B and plots both, highlighting the regions where they differ.
    """
    
    d3_template = 'd3/difference.svg'
    
    def generate(self, dso_a, dso_b):
        metadata = {'htmlbase': os.path.join( utils.scriptdir,'html')}
        
        # Get common scales
        datai = np.mean( dso_a.data, 0) # Mean flatten
        datao = np.mean( dso_b.data, 0) # Mean flatten
        
        # Interpolate the data for shorter set
        if len(datao) < len(datai):
            datao = np.interp( dso_a.scales[1], dso_b.scales[1], datao)

        metadata['figure'] = {
            'data':list(zip( dso_a.scales[1], datai.T, datao.T )), # (ppm, [dataa,datab])
        }
        


# Class for analysis views, using graph-based visualisations of defined datasets
# associated layout and/or analysis
class AnalysisHeatmapView(D3LegacyView):

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







# D3 Based bargraph view
class D3CircosView(D3View):

    d3_template = 'd3/circos.svg'

    def generate(self, dso=None):
        print(dso)

        self.generate_d3( {
            'figure': {
                            'type':'circos',
                            'data': dso.data,
                            'labels': dso.labels[1],
                            'n':1,  
                            'legend':('Metabolic pathway reaction interconnections','Links between pathways indicate proportions of shared reactions between the two pathways in MetaCyc database')                             
                        },
                    })
        


class AnalysisCircosPathwayView(D3LegacyView):

    def generate(self):
        pathways = [k for k,v in db.dbm.get_pathways()]
        pathway_metabolites = dict()
        
        for k,p in db.dbm.pathways():
            pathway_metabolites[p.id] = set( [m for m in p.metabolites] )

        data_m, labels_m = self.build_matrix(pathways, pathway_metabolites)

        pathway_reactions = dict()
        
        for k,p in db.dbm.pathways():
            pathway_reactions[p.id] = set( [m for m in p.reactions] )

        data_r, labels_r = self.build_matrix(pathways, pathway_reactions)


        pathway_active_reactions = dict()
        pathway_active_metabolites = dict()
        active_pathways = [db.dbm.pathway(p) for p in self.parent.config.value('/Pathways/Show').split(',')]
        active_pathways_id = []
        
        for p in active_pathways:
            pathway_active_reactions[p.id] = set( [r for r in p.reactions] )
            pathway_active_metabolites[p.id] = set( [r for r in p.metabolites] )
            active_pathways_id.append(p.id)
    

        data_ar, labels_ar = self.build_matrix(active_pathways_id, pathway_active_reactions)
        data_am, labels_am = self.build_matrix(active_pathways_id, pathway_active_metabolites)

    
class AppView(HTMLView):
    pass
    
    
    


# D3 Based bargraph view
class D3BarView(D3View):

    d3_template = 'd3/bar.svg'

    def generate(self, dso): 
        fd = np.mean( dso.data, axis=0 )

        fdm = list(zip( dso.labels[1], fd ))
        sms = sorted(fdm,key=lambda x: abs(x[1]), reverse=True )
        metabolites = [m for m,s in sms]

        # Get mean version of dataset (or alternative; +/- error)
        # Requires compressing dataset >1 for each alternative information set

        dso_mean = dso.as_summary( fn=np.mean, dim=0, match_attribs=['classes']) # Get mean dataset/ Classes only
        dso_std = dso.as_summary( fn=np.std, dim=0, match_attribs=['classes']) # Get std_dev/ Classes only
        
        classes = dso_mean.classes[0]
        groups = metabolites[:10]

        data = []
        for g in groups:
            
            data.append(
                ( g, 
                    {c: dso_mean.data[n, dso_mean.labels[1].index(g)] for n,c in enumerate(classes)},
                    {c: dso_std.data[n, dso_std.labels[1].index(g)] for n,c in enumerate(classes)} #2sd?
                     )
            )
    
        self.generate_d3( {
            'figure':  {
                            'type':'bar',
                            'data': data,
                        },                        
        })
