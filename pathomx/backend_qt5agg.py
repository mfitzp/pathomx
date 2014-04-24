"""
Render to qt from agg
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
import logging
logging.debug('Loading backend_qt5agg.py')

import sys
import ctypes

import matplotlib
from matplotlib.figure import Figure

from matplotlib.backends.backend_agg import FigureCanvasAgg
from .qt import *
from .backend_qt5 import FigureManagerQT
from .backend_qt5 import FigureCanvasQT
from .backend_qt5 import NavigationToolbar2QT
from .backend_qt5 import show
from .backend_qt5 import draw_if_interactive

DEBUG = False

_decref = ctypes.pythonapi.Py_DecRef
_decref.argtypes = [ctypes.py_object]
_decref.restype = None


def new_figure_manager(num, *args, **kwargs):
    """
    Create a new figure manager instance
    """
    if DEBUG:
        print('backend_qtagg.new_figure_manager')
    FigureClass = kwargs.pop('FigureClass', Figure)
    thisFig = FigureClass(*args, **kwargs)
    return new_figure_manager_given_figure(num, thisFig)


def new_figure_manager_given_figure(num, figure):
    """
    Create a new figure manager instance for the given figure.
    """
    canvas = FigureCanvasQTAgg(figure)
    return FigureManagerQT(canvas, num)


class NavigationToolbar2QTAgg(NavigationToolbar2QT):
    def _get_canvas(self, fig):
        return FigureCanvasQTAgg(fig)


class FigureManagerQTAgg(FigureManagerQT):
    def _get_toolbar(self, canvas, parent):
        # must be inited after the window, drawingArea and figure
        # attrs are set
        if matplotlib.rcParams['toolbar'] == 'toolbar2':
            toolbar = NavigationToolbar2QTAgg(canvas, parent)
        else:
            toolbar = None
        return toolbar


class FigureCanvasQTAgg(FigureCanvasQT, FigureCanvasAgg):
    """
    The canvas the figure renders into.  Calls the draw and print fig
    methods, creates the renderers, etc...

    Public attribute

      figure - A Figure instance
    """

    def __init__(self, figure):
        if DEBUG:
            print('FigureCanvasQtAgg: ', figure)
        super(FigureCanvasQTAgg, self).__init__(figure=figure)
        self.drawRect = False
        self.rect = []
        self.blitbox = None
        self.setAttribute(Qt.WA_OpaquePaintEvent)

    def drawRectangle(self, rect):
        self.rect = rect
        self.drawRect = True
        self.repaint()

    def paintEvent(self, e):
        """
        Copy the image from the Agg canvas to the qt.drawable.
        In Qt, all drawing should be done inside of here when a widget is
        shown onscreen.
        """

        #FigureCanvasQT.paintEvent(self, e)
        if DEBUG:
            print('FigureCanvasQtAgg.paintEvent: ', self,
                  self.get_width_height())

        if self.blitbox is None:
            # matplotlib is in rgba byte order.  QImage wants to put the bytes
            # into argb format and is in a 4 byte unsigned int.  Little endian
            # system is LSB first and expects the bytes in reverse order
            # (bgra).
            if QSysInfo.ByteOrder == QSysInfo.LittleEndian:
                stringBuffer = self.renderer._renderer.tostring_bgra()
            else:
                stringBuffer = self.renderer._renderer.tostring_argb()

            refcnt = sys.getrefcount(stringBuffer)

            qImage = QImage(stringBuffer, self.renderer.width,
                                  self.renderer.height,
                                  QImage.Format_ARGB32)
            p = QPainter(self)
            p.drawPixmap(QPoint(0, 0), QPixmap.fromImage(qImage))

            # draw the zoom rectangle to the QPainter
            if self.drawRect:
                p.setPen(QPen(Qt.black, 1, Qt.DotLine))
                p.drawRect(self.rect[0], self.rect[1],
                           self.rect[2], self.rect[3])
            p.end()

            # This works around a bug in PySide 1.1.2 on Python 3.x,
            # where the reference count of stringBuffer is incremented
            # but never decremented by QImage.
            # TODO: revert PR #1323 once the issue is fixed in PySide.
            del qImage
            if refcnt != sys.getrefcount(stringBuffer):
                _decref(stringBuffer)
        else:
            bbox = self.blitbox
            l, b, r, t = bbox.extents
            w = int(r) - int(l)
            h = int(t) - int(b)
            t = int(b) + h
            reg = self.copy_from_bbox(bbox)
            stringBuffer = reg.to_string_argb()
            qImage = QImage(stringBuffer, w, h,
                                  QImage.Format_ARGB32)
            pixmap = QPixmap.fromImage(qImage)
            p = QPainter(self)
            p.drawPixmap(QPoint(l, self.renderer.height - t), pixmap)
            p.end()
            self.blitbox = None
        self.drawRect = False

    def draw(self):
        """
        Draw the figure with Agg, and queue a request
        for a Qt draw.
        """
        # The Agg draw is done here; delaying it until the paintEvent
        # causes problems with code that uses the result of the
        # draw() to update plot elements.
        FigureCanvasAgg.draw(self)
        self.update()

    def blit(self, bbox=None):
        """
        Blit the region in bbox
        """
        self.blitbox = bbox
        l, b, w, h = bbox.bounds
        t = b + h
        self.repaint(l, self.renderer.height - t, w, h)

    def print_figure(self, *args, **kwargs):
        FigureCanvasAgg.print_figure(self, *args, **kwargs)
        self.draw()
