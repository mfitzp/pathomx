import os

import math
from .. import utils
from ..globals import settings
from ..qt import *

from pyqtconfig import ConfigManager

TEXT_COLOR = "#000000"
SHADOW_COLOR = QColor(63, 63, 63, 100)
BORDER_COLOR = "#888888"
SELECT_COLOR = QColor(63, 63, 255, 127)

INTERFACE_COLOR_INPUT = "orange"
INTERFACE_COLOR_INPUT_BORDER = BORDER_COLOR  # "darkorange"
INTERFACE_COLOR_OUTPUT = "yellow"
INTERFACE_COLOR_VIEW = "blue"

CAN_CONSUME_COLOR = QColor(0, 200, 0, 127)
CANNOT_CONSUME_COLOR = QColor(200, 0, 0, 127)

CONNECTOR_COLOR = QColor(100, 100, 100, 127)  # Grey

INTERFACE_ACTIVE_COLOR = {
    True: QColor(0, 0, 255, 127),  # Grey-blue
    False: CONNECTOR_COLOR,
}

STATUS_COLORS = {
    'active': 'green',
    'error': 'red',
    'waiting': 'yellow',
    'paused': 'white',
    'render': 'purple',
    'done': 'blue'
}

ANNOTATION_MINIMUM_SIZE = 50
ANNOTATION_MINIMUM_QSIZE = QSize(ANNOTATION_MINIMUM_SIZE, ANNOTATION_MINIMUM_SIZE)

RESIZE_HANDLE_SIZE = 8

RESIZE_TOPLEFT = 1
RESIZE_TOP = 2
RESIZE_TOPRIGHT = 3
RESIZE_RIGHT = 4
RESIZE_BOTTOMRIGHT = 5
RESIZE_BOTTOM = 6
RESIZE_BOTTOMLEFT = 7
RESIZE_LEFT = 8


def minimalQRect(r, min):
    if r.width() < min.width():
        r.setWidth(min.width())

    if r.height() < min.height():
        r.setHeight(min.height())

    return r


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

        self._effects_locked = False

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

    def hoverEnterEvent(self, e):
        if not self._effects_locked:
            shadow = QGraphicsDropShadowEffect(
                blurRadius=10,
                color=QColor(SHADOW_COLOR),
                offset=QPointF(0, 0),
                )
            self.setGraphicsEffect(shadow)
            self.prepareGeometryChange()
            self.graphicsEffect().setEnabled(True)

    def hoverLeaveEvent(self, e):
        if not self._effects_locked:
            self.graphicsEffect().setEnabled(False)


class ToolItem(BaseItem):
    """
    A tool item constructed as an item group containing an icon and with 
    additional visual elements. Treated as a single entity by Scene
    """

    def __init__(self, app, position=None):
        super(ToolItem, self).__init__()
        self.app = app
        app.editorItem = self
        #self.viewertest = ToolViewItem(self, 'View')

        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setFlag(QGraphicsItem.ItemIsFocusable)

        self.app.data.consumed.connect(self.addDataLink)
        self.app.data.unconsumed.connect(self.removeDataLink)

        self.app.pause_status_changed.connect(self.onPauseChange)

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

        self.status_icon = QGraphicsPixmapItem(self)
        self.status_icon.setPos(48, 48)

        if position:
            self.setPos(position)

        self.app.deleted.connect(self.delete)

    @property
    def name(self):
        if self.app:
            return self.app.name
        else:
            return "Untitled"

    def centerSelf(self):
        for v in self.scene().views():
            v.centerOn(self)

    def getName(self):
        # FIXME: This feels a bit hacky
        if self.label.toPlainText() != self.name:  # Prevent infinite loop get/set
            self.label.prepareGeometryChange()
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
        linker.data = (datao[0], datao[1])  # Get the dso from the interface
        linker.updateLine()

        self.prepareGeometryChange()
        self.scene().addItem(linker)

        o._links.append(linker)
        i._links.append(linker)

        self._links[datai] = linker

        datao[0].v.editorItem.auto_position_children()


    def removeDataLink(self, datao, datai):
        # (data_manager, interface)
        o = datao[0].v.editorItem.output.interface_items[datao[1]]
        i = datai[0].v.editorItem.input.interface_items[datai[1]]

        self.prepareGeometryChange()
        if datai in self._links:

            linker = self._links[datai]
            self.scene().removeItem(linker)

            linker.source._links.remove(linker)
            linker.sink._links.remove(linker)

            del self._links[datai]

        datao[0].v.editorItem.auto_position_children()


    def auto_position_children(self):
        if settings.get('Editor/Auto_position'):
            # Iterate over the child data tools and distribute at least +200 in x, and evenly in y
            items = []
            for _, cs in self.app.data.watchers.items():
                for c in cs:
                    item = c.v.editorItem # Blimey
                    items.append(item)

            n = len(items)
            center_y = float(n-1) * 200 / 2

            for n, i in enumerate(items):
                i.setPos( i.calculate_auto_position_x(), self.y() + (n * 200) - center_y )
                i.auto_position_children()

    def calculate_auto_position_x(self):
        """
        Auto position at furthest x of parent +200
        """
        x = []
        for _, cs in self.app.data.i.items():
            if cs:
                cm, ci = cs
                x.append( cm.v.editorItem.x() )

        if max:
            return max(x) + 200
        else:
            return self.x()


    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Backspace and e.modifiers() == Qt.ControlModifier:
            self.app.delete()
        else:
            return super(ToolItem, self).keyPressEvent(e)

    def contextMenuEvent(self, e):
        e.accept()

        o = self.scene().parent()
        menu = QMenu(o)

        run_action = QAction('&Run', o)
        run_action.triggered.connect(self.app.onRecalculate)
        menu.addAction(run_action)

        pause_action = QAction('&Pause', o)
        pause_action.setCheckable(True)
        pause_action.setChecked(self.app.pause_analysisAction.isChecked())
        pause_action.toggled.connect(self.app.pause_analysisAction.setChecked)
        menu.addAction(pause_action)

        show_action = QAction('&Show', o)
        show_action.triggered.connect(self.onShow)
        menu.addAction(show_action)

        delete_action = QAction('&Delete', o)
        delete_action.triggered.connect(self.app.delete)
        menu.addAction(delete_action)

        vmenu = menu.addMenu('&Views')
        vc = {}
        for wid in range(self.app.views.count()):
            if hasattr(self.app.views.widget(wid), 'is_floatable_view') and \
               self.app.views.widget(wid).is_floatable_view:
                def make_callback(i):
                    return lambda n: self.onAddView(n, i)

                ve = QAction(self.app.views.tabText(wid), o)
                ve.triggered.connect(make_callback(wid))
                vmenu.addAction(ve)

        menu.exec_(e.screenPos())

    def delete(self):
        self.app = None
        self.scene().removeItem(self)

    def onShow(self):
        self.app.show()
        self.app.raise_()

    def onHide(self):
        self.app.hide()

    def onRun(self):
        self.app.onRecalculate()

    def onAddView(self, e, wid):
        self.viewertest = ToolViewItem(self, self.app.views.widget(wid))

    def itemChange(self, change, value):
        # Snap to grid in QGraphicsView (if enabled)

        if change == QGraphicsItem.ItemPositionChange:
            self.auto_position_children()
            if settings.get('Editor/Snap_to_grid'):
                newPos = value  # .toPointF()
                snap = 100
                snapPos = QPointF(snap / 2 + (newPos.x() // snap) * snap, snap / 2 + (newPos.y() // snap) * snap)
                return snapPos


        elif change == QGraphicsItem.ItemSelectedChange:
            if value:
                selected_shadow = QGraphicsColorizeEffect(
                    color=QColor(SELECT_COLOR),
                    strength=1,
                    )
                self.icon.setGraphicsEffect(selected_shadow)
                self.icon.prepareGeometryChange()
                self.icon.graphicsEffect().setEnabled(True)
                self.onShow()
                self.icon._effects_locked = True
            else:
                self.icon.graphicsEffect().setEnabled(False)
                self.onHide()
                self.icon._effects_locked = False

            return value

        return super(ToolItem, self).itemChange(change, value)

    def onPauseChange(self, is_paused):
        if is_paused:
            self.status_icon.setPixmap(QIcon(os.path.join(utils.scriptdir, 'icons', 'control-pause.png')).pixmap(QSize(16, 16)))
        else:
            self.status_icon.setPixmap(QPixmap())


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
        painter.setBrush(QBrush(self.parentItem().app.get_icon.pixmap(self.size)))
        painter.drawRect(QRect(0, 0, self.size.width(), self.size.height()))
        #painter.drawEllipse( QRect(0,0,self.size.width(), self.size.height()) )
        #painter.drawRoundedRect( QRect(0,0,self.size.width(), self.size.height()), 5.0, 5.0 )


class ToolInterfaceHandler(BaseItem):

    def __init__(self, app=None, interface_type='input', parent=None):
        super(ToolInterfaceHandler, self).__init__(parent=parent)

        self.app = app
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

        self.setup = self.defaults[interface_type]
        self.interface_type = interface_type

        self.interfaces = {'input': app.data.i, 'output': app.data.o, 'views': app.views}[interface_type]
        self.interface_items = dict()

        app.data.source_updated.connect(self.update_interface_status)
        app.data.output_updated.connect(self.update_interface_status)
        app.data.interfaces_changed.connect(self.update_interfaces)

        transform = QTransform()
        transform.translate(*self.setup[2])
        self.setTransform(transform)

        self._linkInProgress = None

    def delete(self):
        self.prepareGeometryChange()
        for interface in self.interfaces.keys():
            self.interface_items[interface].prepareGeometryChange()
            self.scene().removeItem(self.interface_items[interface])
            del self.interface_items[interface]

        self.interfaces = {}
        self.scene().removeItem(self)

    def update_interfaces(self):

        x0, y0 = self.setup[3], 44
        r = 44

        items = len(self.interfaces.keys())

        angle_increment = 15.
        angle_start = self.setup[0] - (items - 1) * (angle_increment / 2)

        self.prepareGeometryChange()
        for n, interface in enumerate(sorted(self.interfaces.keys())):
            angle = angle_start + (n * angle_increment)
            x = x0 + r * math.cos(2 * math.pi * (angle / 360.)) - 4
            y = y0 + r * math.sin(2 * math.pi * (angle / 360.))
            if interface not in self.interface_items:
                # Creating
                self.interface_items[interface] = ToolInterface(self.app, self.interfaces[interface], interface, self.interface_type, self)
                self.interface_items[interface].setPos(x, y)
                t = QTransform()
                t.rotate(n * angle_increment)
                self.interface_items[interface].prepareGeometryChange()
                self.interface_items[interface].setTransform(t)
            else:
                # Updating
                self.interface_items[interface].interface = self.interfaces[interface]
                self.interface_items[interface].prepareGeometryChange()
                self.interface_items[interface].setPos(x, y)

    def update_interface_status(self, i):
        if i in self.interface_items.keys():
            self.interface_items[i].update_interface_color()  # Redraw

            for l in self.interface_items[i]._links:  # Redraw links
                l.updateLine()

    def paint(self, painter, option, widget):
        pass


class ToolInterface(BaseInteractiveItem):  # QGraphicsPolygonItem):

    def __init__(self, app=None, interface=None, interface_name='', interface_type='input', parent=None):
        super(ToolInterface, self).__init__(parent=parent)
        #self.setAcceptHoverEvents(True)
        #self.setFlag(QGraphicsItem.ItemSendsScenePositionChanges, True)
        #self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)

        self.app = app

        self.interface = interface
        self.interface_name = interface_name
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

        self.update_interface_color()
        #self.updateShape( len(interface_name) * 8)

    def update_interface_color(self, color=None):
        if color:
            self.color = color
        else:
            self.color = INTERFACE_ACTIVE_COLOR[self.get_interface_status()]

        self.update()

    def get_interface_status(self):
        if self.interface_type == 'input':
            return (self.app.data.i[self.interface_name] is not None) and \
                   (self.app.data.get(self.interface_name) is not None)

        elif self.interface_type == 'output':
            return not self.app.data.o[self.interface_name] is None

    def updateShape(self, l):
        ''' Update polygon shape to the specified length (to match inner text) '''
        w = 5
        points = [QPoint(0, 0), QPoint(w * 2, -w), QPoint(l, -w),
        QPoint(l - w, 0),
        QPoint(l, w), QPoint(w * 2, w), QPoint(0, 0)]
        self.setPolygon(QPolygonF(points))

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemScenePositionHasChanged:
            for i in self._links:
                i.updateLine()

        return super(ToolInterface, self).itemChange(change, value)

    def mouseMoveEvent(self, event):

        if self._linkInProgress is None:
            if self.interface_type == 'output':
                self._linkInProgress = LinkItem(self, event)  # source_offset=self.scenePos())
                self.scene().addItem(self._linkInProgress)
                # Highlight all targets that are acceptable
                for i in self.scene().items():
                    if isinstance(i, ToolInterface) and i.interface_type == 'input':  # and \
                        # i.app.data.i[i.interface_name] is None:

                        source_manager = self._linkInProgress.source.app.data
                        source_interface = self._linkInProgress.source.interface_name
                        dest_manager = i.app.data
                        dest_interface = i.interface_name

                        if dest_manager.can_consume(source_manager, source_interface, interface=dest_interface):
                            i.update_interface_color(CAN_CONSUME_COLOR)

                        else:
                            i.update_interface_color(CANNOT_CONSUME_COLOR)

                self.grabMouse()
        else:
            self._linkInProgress.sink = event
            self._linkInProgress.updateLine()

    def mouseReleaseEvent(self, event):
        if self._linkInProgress:
            self.ungrabMouse()

            # Reset apperance
            for i in self.scene().items():
                if isinstance(i, ToolInterface) and i.interface_type == 'input':
                    i.update_interface_color()

            targets = [x for x in self.scene().items(event.scenePos()) if isinstance(x, ToolInterface) and x.interface_type == 'input']
            if targets:
                target = targets[0]

                source_manager = self._linkInProgress.source.app.data
                source_interface = self._linkInProgress.source.interface_name

                dest_manager = target.app.data
                dest_interface = target.interface_name

                logging.debug("Data link: %s %s %s %s " % (source_manager, source_interface, dest_manager, dest_interface))

                if dest_manager.can_consume(source_manager, source_interface, interface=dest_interface) or \
                    event.modifiers() == Qt.ControlModifier:  # force connection with modifier key

                # FIXME: This is horrible; simplify the data manager
                    c = dest_manager._consume_action(source_manager, source_interface, dest_interface)
                    dest_manager.source_updated.emit(dest_interface)

            self.scene().removeItem(self._linkInProgress)
            self._linkInProgress = None

    def paint(self, painter, option, widget):
        """
        Paint the tool object; pass first to default then over-write
        """
        #super(ToolInterface, self).paint(painter, option, widget)

        #self.color = INTERFACE_ACTIVE_COLOR[ self.get_interface_status() ]  # INTERFACE_ACTIVE_COLOR[not (self.interface is None or self.interface.is_empty) ]

        brush = QBrush(QColor(self.color))
        painter.setBrush(brush)
        painter.setPen(Qt.NoPen)

        painter.drawEllipse(QRect(0, 0, 8, 8))


class LinkItem(QGraphicsPathItem):
    def __init__(self, source=None, sink=None):
        super(LinkItem, self).__init__()

        # DataSet carried by this link (if any)
        self.data = None
        self.setLineColor(CONNECTOR_COLOR)

        self.textLabelItem = QGraphicsTextItem(self)
        self.textLabelItem.setPlainText('')
        font = QFont()
        font.setPointSize(8)
        self.textLabelItem.setFont(font)

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

        pi = abs(sourcePoint.x() - sinkPoint.x()) / 2
        if pi > 100:
            pi = 100

        p1 = sourcePoint + QPointF(pi, 0)
        p2 = sinkPoint - QPointF(pi, 0)

        bezierPath.cubicTo(p1, p2, sinkPoint)
        self.bezierPath = bezierPath

        self.prepareGeometryChange()
        self.setPath(bezierPath)  # source.x(), source.y(), self.sink.x(), self.sink.y() )

        self.updateText()
        self.setLineColor(INTERFACE_ACTIVE_COLOR[self.source.get_interface_status()])

    def updateText(self):
        self.textLabelItem.prepareGeometryChange()

        if self.data is not None:
        # Determine maximum length of text by horribly kludge
            max_length = self.bezierPath.length() / 10
            source_manager, source_interface = self.data
            dataobj = source_manager.o[source_interface]
            if dataobj is not None:
                strs = [source_interface]
                if hasattr(dataobj, 'shape'):
                    strs.append("(%s)" % "x".join([str(x) for x in dataobj.shape]))
                else:
                    try:
                        obj_len = len(dataobj)
                    except:
                        pass
                    else:
                        strs.append("(%s)" % obj_len)

                text = ''
                for s in strs:
                    if len(text + s) < max_length:
                        text += ' ' + s
            else:
                text = "empty"

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

    def setLineColor(self, color):
        pen = QPen()
        pen.setColor(QColor(color))
        pen.setCapStyle(Qt.RoundCap)
        pen.setWidth(4)
        self.pen = pen
        self.setPen(self.pen)

    def contextMenuEvent(self, e):
        e.accept()

        o = self.scene().parent()
        menu = QMenu(o)

        delete_action = QAction('&Delete', o)
        delete_action.triggered.connect(self.onDelete)
        menu.addAction(delete_action)

        menu.exec_(e.screenPos())

    def onDelete(self):
        if self.sink:
            self.sink.app.data.unget(self.sink.interface_name)


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
        self.prepareGeometryChange()

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
        else:
            return super(ToolViewItem, self).keyPressEvent(e)

    def mouseDoubleClickEvent(self, e):
        if self.view:
            self.parentItem().onShow(self.view)


class FigureItem(BaseItem):
    """
    Render a figure from the given app directly to the workflow viewer 
    """
    pass

    
class ResizableGraphicsItem(QGraphicsItem):

    def __init__(self, *args, **kwargs):
        super(ResizableGraphicsItem, self).__init__(*args, **kwargs)
        self._resizeMode = None

        self.setAcceptHoverEvents(True)
        self.updateResizeHandles()

    def hoverEnterEvent(self, event):
        self.updateResizeHandles()

    def hoverMoveEvent(self, event):
        if self.topLeft.contains(event.pos()) or self.bottomRight.contains(event.pos()):
            self.setCursor(Qt.SizeFDiagCursor)
        elif self.topRight.contains(event.pos()) or self.bottomLeft.contains(event.pos()):
            self.setCursor(Qt.SizeBDiagCursor)
        else:
            self.setCursor(Qt.SizeAllCursor)

    def mousePressEvent(self, event):
        """
        Capture mouse press events and find where the mosue was pressed on the object
        """
        # Top left corner
        if self.topLeft.contains(event.pos()):
            self._resizeMode = RESIZE_TOPLEFT
        # top right corner
        elif self.topRight.contains(event.pos()):
            self._resizeMode = RESIZE_TOPRIGHT
        #  bottom left corner
        elif self.bottomLeft.contains(event.pos()):
            self._resizeMode = RESIZE_BOTTOMLEFT
        # bottom right corner
        elif self.bottomRight.contains(event.pos()):
            self._resizeMode = RESIZE_BOTTOMRIGHT
        # entire rectangle
        else:
            self._resizeMode = None

        super(ResizableGraphicsItem, self).mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        self.prepareGeometryChange()
        self.updateResizeHandles()
        super(ResizableGraphicsItem, self).mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        if self._resizeMode:
            r = self.rect()

            # Move top left corner
            if self._resizeMode == RESIZE_TOPLEFT:
                r.setTopLeft(event.pos())

            # Move top right corner
            elif self._resizeMode == RESIZE_TOPRIGHT:
                r.setTopRight(event.pos())

            # Move bottom left corner
            elif self._resizeMode == RESIZE_BOTTOMLEFT:
                r.setBottomLeft(event.pos())

            # Move bottom right corner
            elif  self._resizeMode == RESIZE_BOTTOMRIGHT:
                r.setBottomRight(event.pos())

            r = minimalQRect(r, self.minSize)

            self.prepareGeometryChange()
            self.setRect(r)
            self.updateResizeHandles()
        else:
            super(ResizableGraphicsItem, self).mouseMoveEvent(event)

    def updateResizeHandles(self):
        """
        Update bounding rectangle and resize handles
        """
        r = self.rect()
        s = QSizeF(RESIZE_HANDLE_SIZE, RESIZE_HANDLE_SIZE)
        self.topLeft = QRectF(r.topLeft(), s)
        self.topRight = QRectF(QPointF(r.topRight().x() - RESIZE_HANDLE_SIZE, r.topRight().y()), s)

        self.bottomLeft = QRectF(QPointF(r.bottomLeft().x(), r.bottomLeft().y() - RESIZE_HANDLE_SIZE), s)
        self.bottomRight = QRectF(QPointF(r.bottomRight().x() - RESIZE_HANDLE_SIZE, r.bottomRight().y() - RESIZE_HANDLE_SIZE), s)

    def paintResizeHandles(self, painter):
        """
        Paint Widget
        """
        # If mouse is over, draw handles
        # if rect selected, fill in handles
        if self.isSelected():
            p, b = painter.pen(), painter.brush()
            painter.setBrush(QColor(0, 0, 0))
            painter.setPen(QPen(Qt.NoPen))

            painter.drawRect(self.topLeft)
            painter.drawRect(self.topRight)
            painter.drawRect(self.bottomLeft)
            painter.drawRect(self.bottomRight)

                       
class BaseAnnotationItem(ResizableGraphicsItem):

    handler_cache = {}
    styles = ['font-family', 'font-size', 'text-bold', 'text-italic', 'text-underline', 'text-color', 'color-border', 'color-background']

    minSize = ANNOTATION_MINIMUM_QSIZE

    def __init__(self, position=None, *args, **kwargs):
        super(BaseAnnotationItem, self).__init__(*args, **kwargs)
        # Config for each annotation item, holding the settings (styles, etc)
        # update-control via the toolbar using add_handler linking
        self.config = ConfigManager()
        self.config.updated.connect(self.applyStyleConfig)

        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setFlag(QGraphicsItem.ItemIsFocusable)

        if position:
            self.setPos(position)

        self.setZValue(-1)

    def delete(self):
        self.prepareGeometryChange()
        self.scene().annotations.remove(self)
        self.scene().removeItem(self)
        self.removeHandlers()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Backspace and e.modifiers() == Qt.ControlModifier:
            self.delete()
        else:
            return super(BaseAnnotationItem, self).keyPressEvent(e)

    def importStyleConfig(self, config):
        for k in self.styles:
            self.config.set(k, config.get(k))

    def addHandlers(self):
        m = self.scene().views()[0].m  # Hack; need to switch to importing this
        for k in self.styles:
            self.config.add_handler(k, m.styletoolbarwidgets[k])

    def removeHandlers(self):
        for k in self.styles:
            self.config.remove_handler(k)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemSelectedChange:
            if not value:
                self.removeHandlers()

        elif change == QGraphicsItem.ItemSelectedHasChanged:
            if value:
                self.addHandlers()

        return super(BaseAnnotationItem, self).itemChange(change, value)


class QGraphicsTextItemExtend(QGraphicsTextItem):

    def focusInEvent(self, e):
        # Deselect other objects; set the parent selected
        for i in self.scene().selectedItems():
            if i != self.parentItem():
                i.setSelected(False)

        self.parentItem().setSelected(True)
        super(QGraphicsTextItemExtend, self).focusInEvent(e)

    def hoverMoveEvent(self, e):
        self.setCursor(Qt.IBeamCursor)
        e.accept()

        #super(QGraphicsTextItemExtend, self).hoverMoveEvent(e)

class AnnotationTextItem(QGraphicsRectItem, BaseAnnotationItem):

    def __init__(self, *args, **kwargs):
        super(AnnotationTextItem, self).__init__(*args, **kwargs)

        self.text = QGraphicsTextItemExtend(parent=self)
        self.text.setTextInteractionFlags(Qt.TextEditable | Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        self.text.setAcceptHoverEvents(True)
        self.text.setPlainText('Your text here')
        self.text.setParentItem(self)

        self.setFocusProxy(self.text)

    def delete(self):
        self.setFocusProxy(None)
        super(AnnotationTextItem, self).delete()

    def applyStyleConfig(self):

        font = QFont()
        font.setFamily(self.config.get('font-family'))
        font.setPointSizeF(float(self.config.get('font-size')))
        font.setBold(self.config.get('text-bold'))
        font.setItalic(self.config.get('text-italic'))
        font.setUnderline(self.config.get('text-underline'))

        self.text.setFont(font)
        self.text.setDefaultTextColor(QColor(self.config.get('text-color')))

        if self.config.get('color-border'):
            c = QColor(self.config.get('color-border'))
            self.setPen(c)
        else:
            self.setPen(QPen(Qt.NoPen))

        if self.config.get('color-background'):
            c = QColor(self.config.get('color-background'))
            c.setAlpha(25)
            self.setBrush(c)
        else:
            self.setBrush(QBrush(Qt.NoBrush))

    def setRect(self, r):

        self.text.setTextWidth(r.width() - RESIZE_HANDLE_SIZE * 2)
        # Add size padding
        tr = self.text.boundingRect()
        nr = QRect(0, 0, tr.width() + RESIZE_HANDLE_SIZE * 2, tr.height() + RESIZE_HANDLE_SIZE * 2)
        super(AnnotationTextItem, self).setRect(minimalQRect(r, nr))
        self.text.setPos(QPointF(RESIZE_HANDLE_SIZE, RESIZE_HANDLE_SIZE) + QPointF(self.rect().x(), self.rect().y()))

    def _createFromMousePressEvent(self, e):
        r = QRectF(QPointF(0, 0), QPointF(ANNOTATION_MINIMUM_SIZE, ANNOTATION_MINIMUM_SIZE))
        self.setPos(e.scenePos())
        self.prepareGeometryChange()
        self.setRect(r)
        self.importStyleConfig(self.config)
        self.updateResizeHandles()

    def _resizeFromMouseMoveEvent(self, e):
        r = self.rect()
        r.setBottomRight(e.scenePos() - self.pos())  # self.mapToScene(e.pos()) ) #- self.mode_current_object.pos() )
        r = minimalQRect(r, self.minSize)
        self.prepareGeometryChange()
        self.setRect(r)
        self.updateResizeHandles()

    def paint(self, painter, option, widget):
        super(AnnotationTextItem, self).paint(painter, option, widget)
        self.paintResizeHandles(painter)


class AnnotationRegionItem(QGraphicsRectItem, BaseAnnotationItem):

    def __init__(self, *args, **kwargs):
        super(AnnotationRegionItem, self).__init__(*args, **kwargs)

    def applyStyleConfig(self):

        if self.config.get('color-border'):
            c = QColor(self.config.get('color-border'))
            self.setPen(c)
        else:
            self.setPen(QPen(Qt.NoPen))
        if self.config.get('color-background'):
            c = QColor(self.config.get('color-background'))
            c.setAlpha(25)
            self.setBrush(c)
        else:
            self.setBrush(QBrush(Qt.NoBrush))

    def _createFromMousePressEvent(self, e):
        self.prepareGeometryChange()
        self.setRect(QRectF(QPointF(0, 0), QPointF(ANNOTATION_MINIMUM_SIZE, ANNOTATION_MINIMUM_SIZE)))
        self.updateResizeHandles()

    def _resizeFromMouseMoveEvent(self, e):
        r = self.rect()
        r.setBottomRight(e.scenePos() - self.pos())  # self.mapToScene(e.pos()) ) #- self.mode_current_object.pos() )
        r = minimalQRect(r, self.minSize)
        self.prepareGeometryChange()
        self.setRect(r)
        self.updateResizeHandles()

    def paint(self, painter, option, widget):
        super(AnnotationRegionItem, self).paint(painter, option, widget)
        self.paintResizeHandles(painter)
