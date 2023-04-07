import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QFileDialog, QGraphicsView, QGraphicsScene
from PyQt5.QtGui import QPixmap, QImage, QPainter, QPen
from PyQt5.QtCore import Qt, QPoint
import cv2

class CustomQGraphicsView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.start = QPoint()
        self.end = QPoint()
        self.segmentation_layer = QImage()

    def mousePressEvent(self, event):
        self.start = self.mapToScene(event.pos()).toPoint()

    def mouseMoveEvent(self, event):
        self.end = self.mapToScene(event.pos()).toPoint()

        if not self.segmentation_layer.isNull():
            painter = QPainter(self.segmentation_layer)
            painter.setPen(QPen(Qt.red, 5, Qt.SolidLine))
            painter.drawLine(self.start, self.end)
            painter.end()

            pixmap = QPixmap.fromImage(self.segmentation_layer)
            self.scene().clear()
            self.scene().addPixmap(pixmap)

        self.start = self.end

    def mouseReleaseEvent(self, event):
        self.end = QPoint()

    def set_image(self, q_image):
        self.segmentation_layer = QImage(q_image.size(), QImage.Format_ARGB32)
        self.segmentation_layer.fill(Qt.transparent)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.initUI()

    def initUI(self):
        # Set main window properties
        self.setWindowTitle('Image Segmentation Tool')
        self.setGeometry(100, 100, 800, 600)

        # Add "Open" button
        open_button = QPushButton('Open', self)
        open_button.clicked.connect(self.open_image)
        open_button.move(10, 10)

        # Add QGraphicsView for displaying and annotating the image
        self.graphics_view = CustomQGraphicsView(self)
        self.graphics_view.setGeometry(10, 50, 780, 540)
        self.scene = QGraphicsScene()
        self.graphics_view.setScene(self.scene)

    def open_image(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "Open Image", "", "Images (*.png *.jpg *.jpeg *.bmp)", options=options)

        if file_name:
            self.image = cv2.imread(file_name)
            height, width, channel = self.image.shape
            bytes_per_line = 3 * width
            q_image = QImage(self.image.data, width, height, bytes_per_line, QImage.Format_RGB888).rgbSwapped()

            self.pixmap = QPixmap.fromImage(q_image)
            self.scene.clear()
            self.scene.addPixmap(self.pixmap)
            self.graphics_view.setScene(self.scene)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())