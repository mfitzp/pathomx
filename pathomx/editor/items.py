import os
import copy
import math
from .. import utils

# Import PyQt5 classes
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWebKit import *
from PyQt5.QtNetwork import *
from PyQt5.QtWidgets import *
from PyQt5.QtWebKitWidgets import *
from PyQt5.QtPrintSupport import *

TEXT_COLOR = "#000000"
SHADOW_COLOR = QColor(63, 63, 63, 180)
BORDER_COLOR = "#888888"

INTERFACE_COLOR_INPUT = "orange"
INTERFACE_COLOR_INPUT_BORDER = BORDER_COLOR  # "darkorange"
INTERFACE_COLOR_OUTPUT = "yellow"
INTERFACE_COLOR_VIEW = "blue"

CONNECTOR_COLOR = "#aaaaaa"

INTERFACE_ACTIVE_COLOR = {
    True: 'blue',  # Light Tango green
    False: '#aaaaaa',
}

STATUS_COLORS = {
    'active': 'green',
    'error': 'red',
    'waiting': 'yellow',
    'paused': 'white',
    'render': 'purple',
    'done': 'blue'
}


class BaseGroup(QGraphicsItemGroup):

    def __init__(self, parent=None):
        super(BaseGroup, self).__init__()

        self.setFlag(QGraphicsItem.ItemSendsScenePositionChanges, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)

        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setAcceptHoverEvents(True)

    @property
    def width(self):
        return self.boundingRect().width()

    @property
    def height(self):
        return self.boundingRect().height()


class BaseItem(QGraphicsItem):

    def __init__(self, parent=None):
        super(BaseItem, self).__init__(parent=parent)
        self.setParentItem(parent)

        self.setFlag(QGraphicsItem.ItemSendsScenePositionChanges, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)

    @property
    def width(self):
        return self.size.width()

    @property
    def height(self):
        return self.size.height()

    def boundingRect(self):
        return QRectF(0, 0, self.size.width(), self.size.height())


class BaseInteractiveItem(BaseItem):

    def __init__(self, parent=None):
        super(BaseInteractiveItem, self).__init__(parent=parent)
        self.setAcceptHoverEvents(True)

        self.shadow = QGraphicsDropShadowEffect(
            blurRadius=10,
            color=QColor(SHADOW_COLOR),
            offset=QPointF(0, 0),
            )

        self.shadow.setEnabled(False)
        self.setGraphicsEffect(self.shadow)

    def hoverEnterEvent(self, e):
        self.graphicsEffect().setEnabled(True)

    def hoverLeaveEvent(self, e):
        self.graphicsEffect().setEnabled(False)


class ToolItem(BaseItem):
    """
    A tool item constructed as an item group containing an icon and with 
    additional visual elements. Treated as a single entity by Scene
    """

    def __init__(self, scene=None, app=None, position=None):
        super(ToolItem, self).__init__()
        self.scene = scene
        self.app = app
        app.editorItem = self
        #self.viewertest = ToolViewItem(self, 'View')

        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setFlag(QGraphicsItem.ItemIsFocusable)

        self.app.data.consumed.connect(self.addDataLink)
        self.app.data.unconsumed.connect(self.removeDataLink)

        self._links = {}

        self.size = QSize(64, 64)

        self.label = QGraphicsTextItem(parent=self)
        self.label.setDefaultTextColor(QColor(TEXT_COLOR))
        self.label.setTextInteractionFlags(Qt.TextEditable)
        self.label.setTextWidth(100)
        opt = QTextOption(Qt.AlignHCenter)
        opt.setWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        self.label.document().setDefaultTextOption(opt)

        self.getName()
        self.label.document().contentsChanged.connect(self.setName)
        self.app.nameChanged.connect(self.getName)

        transform = QTransform()
        transform.translate(32 - self.label.boundingRect().width() / 2, 64)
        self.label.setTransform(transform)

        self.input = ToolInterfaceHandler(app, interface_type='input', parent=self)
        self.output = ToolInterfaceHandler(app, interface_type='output', parent=self)
        self.icon = ToolIcon(parent=self)

        self.progressBar = ToolProgressItem(parent=self)

        self.app.progress.connect(self.progressBar.updateProgress)
        self.app.status.connect(self.progressBar.updateStatus)
        self.app.status.connect(self.updateTip)

        if position:
            self.setPos(position)

    @property
    def name(self):
        if self.app:
            return self.app.name
        else:
            return "Untitled"

    def centerSelf(self):
        for v in self.scene.views():
            v.centerOn(self)

    def updateTip(self, status):
        if status == 'error':
            self.setToolTip('Error: %s' % self.app._latest_exception)
        else:
            self.setToolTip('')

    def getName(self):
        # FIXME: This feels a bit hacky
        if self.label.toPlainText() != self.name:  # Prevent infinite loop get/set
            self.label.setPlainText(self.name)

    def setName(self):
        self.app.set_name(self.label.toPlainText())

    def paint(self, painter, option, widget):
        pass

    def addDataLink(self, datao, datai):

        o = datao[0].v.editorItem.output.interface_items[datao[1]]
        i = datai[0].v.editorItem.input.interface_items[datai[1]]
        # (data.manager, data.manager_interface), (self, interface)

        linker = LinkItem(o, i)  # , o.output.settings[1], i.input.settings[1])
        linker.dso = datao[0].o[datao[1]]  # Get the dso from the interface
        linker.updateLine()

        self.scene.addItem(linker)

        o._links.append(linker)
        i._links.append(linker)

        self._links[datai] = linker
        print("LINKS", self._links)

    def removeDataLink(self, datao, datai):
        # (data_manager, interface)

        o = datao[0].v.editorItem.output.interface_items[datao[1]]
        i = datai[0].v.editorItem.input.interface_items[datai[1]]

        print(datai, "LINKS", self._links)
        if datai in self._links:

            linker = self._links[datai]
            self.scene.removeItem(linker)

            linker.source._links.remove(linker)
            linker.sink._links.remove(linker)

            del self._links[datai]

    def mouseDoubleClickEvent(self, e):
        self.onShow()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Backspace and e.modifiers() == Qt.ControlModifier:
            self.app.delete()

    def contextMenuEvent(self, e):

        o = self.scene.parent()
        menu = QMenu(o)

        show_action = QAction('&Show', o)
        show_action.triggered.connect(self.onShow)
        menu.addAction(show_action)

        delete_action = QAction('&Delete', o)
        delete_action.triggered.connect(self.onDelete)
        menu.addAction(delete_action)

        vmenu = menu.addMenu('&Views')
        vc = {}
        for wid in range(self.app.views.count()):
            if self.app.views.widget(wid).is_floatable_view:
                def make_callback(i):
                    return lambda n: self.onAddView(n, i)

                ve = QAction(self.app.views.tabText(wid), o)
                ve.triggered.connect(make_callback(wid))
                vmenu.addAction(ve)

        menu.exec_(e.screenPos())

    def onDelete(self):
        self.app.delete()

    def onShow(self, v=None):
        if v:
            self.app.views.setCurrentWidget(v)
        self.app.show()
        self.app.raise_()

    def onAddView(self, e, wid):
        self.viewertest = ToolViewItem(self, self.app.views.widget(wid))

        
class ToolIcon(BaseInteractiveItem):
    """
    A tool item constructed as an item group containing an icon and with 
    additional visual elements. Treated as a single entity by Scene
    """

    def __init__(self, parent=None):
        super(ToolIcon, self).__init__(parent)

        self.size = QSize(64, 64)

    def paint(self, painter, option, widget):
        """
        Paint the tool object
        """
        pen = Qt.NoPen  # ()
        #pen.setColor(QColor(BORDER_COLOR))
        #pen.setCapStyle(Qt.RoundCap)
        #pen.setWidth(0)
        painter.setPen(pen)
        painter.setBrush(QBrush(self.parentItem().app.plugin.icon.pixmap(self.size)))
        painter.drawRect(QRect(0, 0, self.size.width(), self.size.height()))
        #painter.drawEllipse( QRect(0,0,self.size.width(), self.size.height()) )
        #painter.drawRoundedRect( QRect(0,0,self.size.width(), self.size.height()), 5.0, 5.0 )


class ToolInterfaceHandler(BaseItem):

    def __init__(self, app=None, interface_type='input', parent=None):
        super(ToolInterfaceHandler, self).__init__(parent=parent)

        self.app = app

        self.parent = parent
        self.size = QSize(50, 100)

        self._links = []

        #self.setFlag(QGraphicsItem.ItemIsMovable)
        #self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setFlag(QGraphicsItem.ItemStacksBehindParent)

        self.setAcceptDrops(True)

        self.defaults = {
            'input': (180, QPointF(0, 44), (-18, -12), 50),
            'output': (0, QPointF(44, 44), (+32, -12), 0),
        }

        self.settings = self.defaults[interface_type]
        self.interface_type = interface_type

        self.interfaces = {'input': app.data.i, 'output': app.data.o, 'views': app.views}[interface_type]
        self.interface_items = dict()

        app.data.interfaces_changed.connect(self.update_interfaces)

        transform = QTransform()
        transform.translate(*self.settings[2])
        self.setTransform(transform)

        self._linkInProgress = None

    def update_interfaces(self):

        x0, y0 = self.settings[3], 44
        r = 44

        items = len(self.interfaces.keys())

        angle_increment = 15.
        angle_start = self.settings[0] - (items - 1) * (angle_increment / 2)

        for n, interface in enumerate(self.interfaces.keys()):
            angle = angle_start + (n * angle_increment)
            x = x0 + r * math.cos(2 * math.pi * (angle / 360.)) - 4
            y = y0 + r * math.sin(2 * math.pi * (angle / 360.))
            if interface not in self.interface_items:
                # Creating
                self.interface_items[interface] = ToolInterface(self.app, self.interfaces[interface], interface, self.interface_type, self)
                self.interface_items[interface].setPos(x, y)
            else:
                # Updating
                self.interface_items[interface].interface = self.interfaces[interface]
                self.interface_items[interface].setPos(x, y)

    def paint(self, painter, option, widget):
        pass


class ToolInterface(BaseInteractiveItem):

    def __init__(self, app=None, interface=None, interface_name='', interface_type='input', parent=None):
        super(ToolInterface, self).__init__(parent=parent)

        self.app = app

        self.interface = interface

        self.parent = parent
        self.size = QSize(8, 8)

        self.interface_type = interface_type

        self.setToolTip(interface_name)

        self._links = []

        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setFlag(QGraphicsItem.ItemStacksBehindParent)

        self.setAcceptDrops(True)
        self._linkInProgress = None
        self._offset = QPointF(4, 4)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemScenePositionHasChanged:
            for i in self._links:
                i.updateLine()

        return super(ToolInterface, self).itemChange(change, value)

    def mouseMoveEvent(self, event):

        if self._linkInProgress == None:
            self._linkInProgress = LinkItem(self, event)  # source_offset=self.scenePos())
            self.scene().addItem(self._linkInProgress)

            self.grabMouse()
        else:
            self._linkInProgress.sink = event
            self._linkInProgress.updateLine()

    def mouseReleaseEvent(self, event):
        if self._linkInProgress:
            self.ungrabMouse()
            targets = [x for x in self.scene().items(event.scenePos()) if isinstance(x, ToolInterface) and x.interface_type == 'input']
            if targets:
                target = targets[0]

                source = self._linkInProgress.source.app
                dest = target.app
                c = dest.data.consume_any_of(list(source.data.o.values()))

            self.scene().removeItem(self._linkInProgress)
            self._linkInProgress = None

    def paint(self, painter, option, widget):
        """
        Paint the tool object
        """
        self.color = CONNECTOR_COLOR  # INTERFACE_ACTIVE_COLOR[not (self.interface == None or self.interface.is_empty) ]
        brush = QBrush(QColor(self.color))
        #pen.setWidth(4)
        painter.setBrush(brush)
        painter.setPen(Qt.NoPen)

        painter.drawEllipse(QRect(0, 0, 8, 8))


class LinkItem(QGraphicsPathItem):
    def __init__(self, source=None, sink=None):
        super(LinkItem, self).__init__()

        # DataSet carried by this link (if any)
        self.dso = None

        pen = QPen()
        pen.setColor(QColor(CONNECTOR_COLOR))
        pen.setCapStyle(Qt.RoundCap)
        pen.setWidth(4)
        self.pen = pen
        self.setPen(self.pen)
        self._LINE_PEN = pen
        self._TEXT_PEN = QPen(QColor(TEXT_COLOR))

        self.textLabelItem = QGraphicsTextItem(self)
        self.textLabelItem.setPlainText('')
        font = QFont()
        font.setPointSize(8)
        self.textLabelItem.setFont(font)
        #self.scene().addItem( self.textLabelItem )

        self.bezierPath = None

        self.source = source
        self.sink = sink

        if source and sink:
            self.updateLine()

    def updateLine(self):
        sourcePoint = self.source.scenePos() + self.source._offset
        sinkPoint = self.sink.scenePos() + self.sink._offset if hasattr(self.sink, '_offset') else self.sink.scenePos()
        bezierPath = QPainterPath()
        bezierPath.moveTo(sourcePoint)

        p1 = sourcePoint + QPointF(100, 0)
        p2 = sinkPoint - QPointF(100, 0)

        # Shrink the horizontal port extension if we're too close
        if p1.x() > p2.x():
            pi = (p1.x() + p2.x()) / 2
            p1 = QPointF(pi, p1.y())
            p2 = QPointF(pi, p2.y())

        bezierPath.cubicTo(p1, p2, sinkPoint)
        self.bezierPath = bezierPath
        self.setPath(bezierPath)  # source.x(), source.y(), self.sink.x(), self.sink.y() )

        self.updateText()

    def updateText(self):
        self.textLabelItem.prepareGeometryChange()
        if self.dso:
            # Determine maximum length of text by horribly kludge
            max_length = self.bezierPath.length() / 10
            strs = [
                self.dso.manager_interface,
                "(%s)" % "x".join([str(x) for x in self.dso.shape]),
                self.dso.name,
                ]

            text = ''
            for s in strs:
                if len(text + s) < max_length:
                    text += ' ' + s

            self.textLabelItem.setPlainText(text)

        path = self.bezierPath
        if path and not path.isEmpty():

            center = path.pointAtPercent(0.5)
            angle = path.angleAtPercent(0.5)

            brect = self.textLabelItem.boundingRect()

            # Center the item and position it on path
            transform = QTransform()
            transform.translate(center.x(), center.y())
            transform.rotate(-angle)

            transform.translate(-brect.width() / 2, -brect.height())

            self.textLabelItem.setTransform(transform)


class ToolProgressItem(BaseItem):
    """
    Progress bar for tool calculation (individual)
    """

    def __init__(self, parent=None):
        super(ToolProgressItem, self).__init__(parent=parent)

        self.progress = None
        self.status = None
        self.thick = 6
        self.size = QSize(64, self.thick)
        transform = QTransform()
        transform.translate(0, 64 - self.thick)
        self.setTransform(transform)

        self.setOpacity(0.5)

    def updateProgress(self, progress):
        self.progress = progress
        self.update()

    def updateStatus(self, status):
        self.status = status
        self.update()

    def paint(self, painter, option, widget):
        """
        Paint the tool object
        """
        painter.setPen(QPen(Qt.NoPen))
        if self.progress:  # Only paint if there is 'progress' (i.e. active)
            progressSize = self.size.width() * self.progress  # 0-1.
            brush = QBrush(QColor(STATUS_COLORS[self.status])) if self.status in STATUS_COLORS else QBrush(Qt.NoBrush)
            #pen.setWidth(self.thick)
            painter.setBrush(brush)
            painter.drawRect(0, 0, progressSize, self.thick)
            #painter.drawArc( QRect(0,0,64-self.thick,64-self.thick), 90*16, -self.progress * 5760)

        #else:
        #    painter.setBrush( QBrush( QColor( Qt.gray ) ) )
        #    painter.drawRect(0,0,*self.size)


class ToolViewItem(BaseInteractiveItem):
    """
    Display a view of the contents of a view
    """

    def __init__(self, parent, view):
        super(ToolViewItem, self).__init__(parent)
        self.pixmap = None
        self.size = QSize(225, 150)

        self.app = parent.app

        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setFlag(QGraphicsItem.ItemIsFocusable)

        self.view = view  # self.app.views.widget(viewid)
        self.app.views.updated.connect(self.refreshView)

        transform = QTransform()
        transform.translate(-100 + 32, -200)
        self.setTransform(transform)

    def refreshView(self):
        #self.view = self.app.views.widget(1)
        if self.view:
            self.pixmap = self.view.grab().scaled(self.size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.size = self.pixmap.size()
            self.update()

    def paint(self, painter, option, widget):
        """
        Paint the view
        """
        if not self.pixmap:
            self.refreshView()

        if self.pixmap:
            pen = QPen()
            pen.setColor(QColor(BORDER_COLOR))
            pen.setCapStyle(Qt.RoundCap)
            pen.setWidth(0)
            painter.setPen(pen)
            painter.setBrush(QBrush(self.pixmap))
            painter.drawRect(QRect(0, 0, self.size.width(), self.size.height()))

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Backspace and e.modifiers() == Qt.ControlModifier:
            self.parentItem().scene.removeItem(self)

    def mouseDoubleClickEvent(self, e):
        if self.view:
            self.parentItem().onShow(self.view)


class FigureItem(BaseItem):
    """
    Render a figure from the given app directly to the workflow viewer 
    """
    pass
