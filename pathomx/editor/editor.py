import os 
import utils
# Import PyQt5 classes
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWebKit import *
from PyQt5.QtNetwork import *
from PyQt5.QtWidgets import *
from PyQt5.QtWebKitWidgets import *
from PyQt5.QtPrintSupport import *

from items import *

class WorkspaceEditor(QGraphicsView):
    def __init__( self, parent = None ):
        super(WorkspaceEditor, self).__init__(parent)

        self.m = parent
        
        self.setRenderHint(QPainter.Antialiasing, True)
        self.setRenderHint(QPainter.SmoothPixmapTransform, True)
        
        self.scene = QGraphicsScene(self)
        
        self.setScene(self.scene)
        self._scene_extreme_rect = self.scene.addRect( QRectF(self.mapToScene( QPoint(0, 0) ), self.mapToScene( QPoint(self.width(), self.height()) ) ), pen=QPen(Qt.NoPen), brush=QBrush(Qt.NoBrush) )
        self.objs = []
        
        self.setAcceptDrops(True)
        
        image = QImage( os.path.join( utils.scriptdir,'icons','grid.png' ) )
        self.setBackgroundBrush(QBrush(image))
        
    def resizeEvent(self,e):
        self._scene_extreme_rect.setRect( QRectF(
                self.mapToScene( QPoint(0, 0) ), 
                self.mapToScene( QPoint(self.width(), self.height()) )
                ) )


        #self.image = QImage(self.scene.sceneRect().size().toSize(), QImage.Format_ARGB32)
        #self.image.fill(Qt.transparent)
        #painter = QPainter(self.image)
        #self.scene.render(painter)
        #self.image.save('/Users/mxf793/Desktop/workspace-view.png')

    def addApp(self, app, position=None):
        i = ToolItem(self.scene, app, position=position)
        self.scene.addItem(i)
        return i
        
    def removeApp(self, app):
        i = app.editorItem
        i.hide()
        self.scene.removeItem(i)
        app.editorItem = None
        
    def dragEnterEvent(self, e):
        if e.mimeData().hasFormat('application/x-pathomx-app') or e.mimeData().hasFormat('text/uri-list'):
            e.accept()
        else:
            e.ignore() 
            
    def dragMoveEvent(self, e):
        e.accept()            

    def dropEvent(self, e):
        scenePos = self.mapToScene( e.pos() ) - QPointF(32,32)

        if e.mimeData().hasFormat('application/x-pathomx-app'):
        
            app_id = str( e.mimeData().data('application/x-pathomx-app') )
        
            a = self.m.app_launchers[ app_id ](position=scenePos, auto_focus=False)
            self.centerOn(a.editorItem)
            e.accept()            
        
        elif e.mimeData().hasFormat('text/uri-list'):
            for ufn in e.mimeData().urls():
                fn = ufn.path()
                fnn, ext = os.path.splitext( fn )
                ext = ext.strip('.')
                if ext in self.m.file_handlers:    
                    a = self.m.file_handlers[ ext ](position=scenePos, auto_focus=False, filename=fn )
                    self.centerOn(a.editorItem)
                    e.accept() 

        
        
        
        
