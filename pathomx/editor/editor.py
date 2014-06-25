import os
from .. import utils
from ..qt import *

from .items import *
from ..globals import settings, app_launchers, file_handlers
from pyqtconfig import ConfigManager

try:
    import xml.etree.cElementTree as et
except ImportError:
    import xml.etree.ElementTree as et

EDITOR_MODE_NORMAL = 0
EDITOR_MODE_TEXT = 1
EDITOR_MODE_REGION = 2
EDITOR_MODE_ARROW = 3


class QGraphicsSceneExtend(QGraphicsScene):

    def __init__(self, parent, *args, **kwargs):
        super(QGraphicsSceneExtend, self).__init__(parent, *args, **kwargs)

        self.m = parent.m

        self.config = ConfigManager()
        # These config settings are transient (ie. not stored between sessions)
        self.config.set_defaults({
            'mode': EDITOR_MODE_NORMAL,
            'font-family': 'Arial',
            'font-size': '12',
            'text-bold': False,
            'text-italic': False,
            'text-underline': False,
            'text-color': '#000000',
            'color-border': None,  # '#000000',
            'color-background': None,
        })

        # Pre-set these values (will be used by default)
        self.config.set('color-background', '#5555ff')

        self.background_image = QImage(os.path.join(utils.scriptdir, 'icons', 'grid100.png'))
        if settings.get('Editor/Show_grid'):
            self.showGrid()
        else:
            self.hideGrid()

        self.mode = EDITOR_MODE_NORMAL
        self.mode_current_object = None

        self.annotations = []

    def mousePressEvent(self, e):
        if self.config.get('mode') != EDITOR_MODE_NORMAL:

            for i in self.selectedItems():
                i.setSelected(False)

            if self.config.get('mode') == EDITOR_MODE_TEXT:
                tw = AnnotationTextItem(position=e.scenePos())

            elif self.config.get('mode') == EDITOR_MODE_REGION:
                tw = AnnotationRegionItem(position=e.scenePos())

            elif self.config.get('mode') == EDITOR_MODE_ARROW:
                tw = AnnotationRegionItem(position=e.scenePos())

            self.addItem(tw)
            self.mode_current_object = tw
            tw._createFromMousePressEvent(e)
            tw.importStyleConfig(self.config)

            self.annotations.append(tw)

        else:
            super(QGraphicsSceneExtend, self).mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self.config.get('mode') == EDITOR_MODE_TEXT and self.mode_current_object:
            self.mode_current_object._resizeFromMouseMoveEvent(e)

        elif self.config.get('mode') == EDITOR_MODE_REGION and self.mode_current_object:
            self.mode_current_object._resizeFromMouseMoveEvent(e)

        else:
            super(QGraphicsSceneExtend, self).mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if self.config.get('mode'):
            self.mode_current_object.setSelected(True)
            self.mode_current_object.setFocus()

            self.config.set('mode', EDITOR_MODE_NORMAL)
            self.mode_current_object = None

        super(QGraphicsSceneExtend, self).mouseReleaseEvent(e)

    def showGrid(self):
        self.setBackgroundBrush(QBrush(self.background_image))

    def hideGrid(self):
        self.setBackgroundBrush(QBrush(None))

    def onSaveAsImage(self):
        filename, _ = QFileDialog.getSaveFileName(self.m, 'Save current figure', '', "Tagged Image File Format (*.tif);;\
                                                                                     Portable Network Graphics (*.png)")
        if filename:
            self.saveAsImage(filename)

    def saveAsImage(self, f):
        self.image = QImage(self.sceneRect().size().toSize(), QImage.Format_ARGB32)
        self.image.fill(Qt.white)
        painter = QPainter(self.image)
        self.render(painter)
        self.image.save(f)

    def addApp(self, app, position=None):
        i = ToolItem(self, app, position=position)
        self.addItem(i)
        return i

    def removeApp(self, app):
        i = app.editorItem
        i.hide()
        self.removeItem(i)
        app.editorItem = None

    def dragEnterEvent(self, e):
        if e.mimeData().hasFormat('application/x-pathomx-app') or e.mimeData().hasFormat('text/uri-list'):
            e.accept()
        else:
            e.ignore()

    def dragMoveEvent(self, e):
        e.accept()

    def dropEvent(self, e):
        scenePos = e.scenePos() - QPointF(32, 32)

        if e.mimeData().hasFormat('application/x-pathomx-app'):
            try:
                app_id = str(e.mimeData().data('application/x-pathomx-app'), 'utf-8')  # Python 3 
            except:
                app_id = str(e.mimeData().data('application/x-pathomx-app'))  # Python 2

            e.setDropAction(Qt.CopyAction)
            a = app_launchers[app_id](self.m, position=scenePos, auto_focus=False)
            #self.centerOn(a.editorItem)
            e.accept()

        elif e.mimeData().hasFormat('text/uri-list'):
            for ufn in e.mimeData().urls():
                fn = ufn.path()
                fnn, ext = os.path.splitext(fn)
                ext = ext.strip('.')
                if ext in file_handlers:
                    a = file_handlers[ext](position=scenePos, auto_focus=False, filename=fn)
                    self.centerOn(a.editorItem)
                    e.accept()

    def getXMLAnnotations(self, root):

    # Iterate over the entire set (in order) creating a XML representation of the MatchDef and Style
        for annotation in self.annotations:

            ase = et.SubElement(root, "Annotation")
            ase.set('type', type(annotation).__name__)

            ase.set('x', str(annotation.x()))
            ase.set('y', str(annotation.y()))
            ase.set('width', str(annotation.rect().width()))
            ase.set('height', str(annotation.rect().height()))

            if hasattr(annotation, 'text'):
                text = et.SubElement(ase, "Text")
                text.text = annotation.text.toPlainText()

            ase = annotation.config.getXMLConfig(ase)

        return root

    def setXMLAnnotations(self, root):

        ANNOTATION_TYPES = {
            'AnnotationTextItem': AnnotationTextItem,
            'AnnotationRegionItem': AnnotationRegionItem,
        }

        for ase in root.findall('Annotation'):

            # Validate the class definition before creating it
            if ase.get('type') in ANNOTATION_TYPES:

                pos = QPointF(float(ase.get('x')), float(ase.get('y')))
                aobj = ANNOTATION_TYPES[ase.get('type')](position=pos)
                aobj.setRect(QRectF(0, 0, float(ase.get('width')), float(ase.get('height'))))

                to = ase.find('Text')
                if to is not None:
                    aobj.text.setPlainText(to.text)

                self.addItem(aobj)
                self.annotations.append(aobj)
                aobj.config.setXMLConfig(ase)
                aobj.applyStyleConfig()


class WorkspaceEditorView(QGraphicsView):
    def __init__(self, parent=None):
        super(WorkspaceEditorView, self).__init__(parent)

        self.m = parent

        self.setRenderHint(QPainter.Antialiasing, True)
        self.setRenderHint(QPainter.SmoothPixmapTransform, True)
        self.setAcceptDrops(True)

        self.scene = QGraphicsSceneExtend(self)
        self.setScene(self.scene)

        self.resetScene()

    def resetScene(self):
        self.scene.clear()
        r = QRectF(self.mapToScene(QPoint(0, 0)), self.mapToScene(QPoint(self.width(), self.height())))
        self._scene_extreme_rect = self.scene.addRect(r, pen=QPen(Qt.NoPen), brush=QBrush(Qt.NoBrush))

    def resizeEvent(self, e):
        self._scene_extreme_rect.setRect(QRectF(
                self.mapToScene(QPoint(0, 0)),
                self.mapToScene(QPoint(self.width(), self.height()))
                ))
