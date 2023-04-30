import os, sys
from PyQt5.Qt import QPainterPath
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QFileDialog, QGraphicsView, QGraphicsScene, QLineEdit, QMessageBox
from PyQt5.QtGui import QPixmap, QImage, QPainter, QPen, QColor, QPainterPath, QPainterPathStroker
from PyQt5.QtCore import Qt, QPoint, QRect

import cv2

class CustomQGraphicsView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.start = QPoint()
        self.end = QPoint()
        self.segmentation_layer = QImage()
        self.grid_size = 20
        self.pixmap = QPixmap()
        self.grid_pixmap = QPixmap()
        self.fill_color = QColor(0, 0, 0, 64)
        self.filled_cells = {}
        self.lasso_path = QPainterPath()
        self.mode = "original"
    
    def change_mode(self, mode):
        self.mode = mode

    def toggle_grid_cell(self, x, y, operation):
        grid_x = x // self.grid_size * self.grid_size
        grid_y = y // self.grid_size * self.grid_size

        cell_key = (grid_x, grid_y)

        painter = QPainter(self.pixmap)

        if operation == "color" and cell_key not in self.filled_cells:
            # Store the original content of the cell
            cell_image = self.pixmap.copy(grid_x, grid_y, self.grid_size, self.grid_size)
            self.filled_cells[cell_key] = cell_image

            painter.setBrush(self.fill_color)
            painter.setPen(QPen(self.fill_color, 1, Qt.SolidLine))
            painter.drawRect(grid_x, grid_y, self.grid_size, self.grid_size)
        elif operation == "decolor" and cell_key in self.filled_cells:
            # Restore the original content of the cell
            painter.drawPixmap(grid_x, grid_y, self.filled_cells[cell_key])
            del self.filled_cells[cell_key]

        painter.end()
        self.draw_grid()


    def mousePressEvent(self, event):
        self.start = self.mapToScene(event.pos()).toPoint()
        if not self.pixmap.isNull():
            if self.mode == "original":
                grid_x = self.start.x() // self.grid_size * self.grid_size
                grid_y = self.start.y() // self.grid_size * self.grid_size
                cell_key = (grid_x, grid_y)

                self.operation = "decolor" if cell_key in self.filled_cells else "color"
                self.toggle_grid_cell(self.start.x(), self.start.y(), self.operation)
            elif self.mode == "lasso":
                pos = self.mapToScene(event.pos()).toPoint()
                self.start = pos
                self.lasso_path = QPainterPath()
                self.lasso_path.moveTo(self.start)  # Add this line
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:  # Check if the left mouse button is being pressed
            pos = self.mapToScene(event.pos()).toPoint()
            if not self.pixmap.isNull():
                if self.mode == "original":
                    self.toggle_grid_cell(pos.x(), pos.y(), self.operation)
                elif self.mode == "lasso":
                    self.lasso_path.lineTo(pos)  # Change this line
                    self.draw_lasso()
            else:
                super().mouseMoveEvent(event)

                
    def mouseReleaseEvent(self, event):
        self.end = QPoint()
        if not self.pixmap.isNull():
            if self.mode == "original":
                pass
            elif self.mode == "lasso":
                self.fill_enclosed_area()
                self.lasso_path = QPainterPath()  # Change this line
                self.draw_grid()
        else:
            super().mouseReleaseEvent(event)

    def set_image(self, q_image):
        self.segmentation_layer = QImage(q_image.size(), QImage.Format_ARGB32)
        self.segmentation_layer.fill(Qt.transparent)
        self.pixmap = QPixmap.fromImage(q_image)
        self.filled_cells = {}  # Add this line to clear the filled_cells dictionary


    def set_grid_size(self, size):
        self.grid_size = size

    def draw_grid(self):
        if not self.pixmap.isNull():
            self.grid_pixmap = self.pixmap.copy()
            
            # Clear and redraw filled cells with the new grid size
            painter = QPainter(self.grid_pixmap)
            for cell_key, cell_image in self.filled_cells.items():
                grid_x, grid_y = cell_key
                painter.drawPixmap(grid_x, grid_y, cell_image)
                painter.setBrush(self.fill_color)
                painter.setPen(QPen(self.fill_color, 1, Qt.SolidLine))
                painter.drawRect(grid_x, grid_y, self.grid_size, self.grid_size)
            painter.end()
            
            grid_painter = QPainter(self.grid_pixmap)
            grid_painter.setPen(QPen(Qt.black, 1, Qt.DotLine))

            for x in range(0, self.grid_pixmap.width(), self.grid_size):
                grid_painter.drawLine(x, 0, x, self.grid_pixmap.height())

            for y in range(0, self.grid_pixmap.height(), self.grid_size):
                grid_painter.drawLine(0, y, self.grid_pixmap.width(), y)

            grid_painter.end()
            self.scene().clear()
            self.scene().addPixmap(self.grid_pixmap)


    def set_fill_color(self, color):
        self.fill_color = color

    
    def get_binary_mask(self):
        if self.pixmap.isNull():
            return QImage()

        binary_mask = QImage(self.pixmap.size(), QImage.Format_ARGB32)
        binary_mask.fill(Qt.transparent)
        mask_painter = QPainter(binary_mask)

        for cell_key, _ in self.filled_cells.items():
            grid_x, grid_y = cell_key
            mask_painter.fillRect(grid_x, grid_y, self.grid_size, self.grid_size, Qt.black)

        mask_painter.end()
        return binary_mask
    
    def color_all_cells(self):
        if not self.pixmap.isNull():
            for x in range(0, self.pixmap.width(), self.grid_size):
                for y in range(0, self.pixmap.height(), self.grid_size):
                    self.toggle_grid_cell(x, y, "color")

    def decolor_all_cells(self):
        if not self.pixmap.isNull():
            for x in range(0, self.pixmap.width(), self.grid_size):
                for y in range(0, self.pixmap.height(), self.grid_size):
                    self.toggle_grid_cell(x, y, "decolor")

    def draw_lasso(self):
        self.lasso_pixmap = self.grid_pixmap.copy()
        lasso_painter = QPainter(self.lasso_pixmap)
        lasso_painter.setPen(QPen(Qt.red, 1, Qt.SolidLine))
        lasso_painter.drawPath(self.lasso_path)
        lasso_painter.end()

        self.scene().clear()
        self.scene().addPixmap(self.lasso_pixmap)

    def fill_enclosed_area(self):
        self.lasso_path.closeSubpath()  # Close the lasso path to create an enclosed area

        for x in range(0, self.pixmap.width(), self.grid_size):
            for y in range(0, self.pixmap.height(), self.grid_size):
                center_point = QPoint(x + self.grid_size // 2, y + self.grid_size // 2)
                if self.lasso_path.contains(center_point):
                    self.toggle_grid_cell(x, y, "color")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.opened_image_file_name = None
        self.initUI()

    def initUI(self):
        # Set main window properties
        self.setWindowTitle('Image Segmentation Tool')
        self.setGeometry(100, 100, 1000, 700)

        # Add "Open" button
        open_button = QPushButton('Open', self)
        open_button.clicked.connect(self.open_image)
        open_button.move(10, 10)

        # Add "Save" button
        save_button = QPushButton('Save', self)
        save_button.clicked.connect(self.save_image)
        save_button.move(100, 10)

        # Add a QLineEdit to control the grid size
        self.grid_input = QLineEdit(self)
        self.grid_input.setText("20")
        self.grid_input.move(400, 10)
        self.grid_input.setFixedWidth(100)
        self.grid_input.textChanged.connect(self.change_grid_size)

        # Add "Grid Size" label
        self.grid_label = QLabel('Grid Size', self)
        self.grid_label.move(520, 10)

        # Add grid height and width labels
        self.grid_width_label = QLabel(self)
        self.grid_height_label = QLabel(self)
        self.grid_width_label.move(600, 10)
        self.grid_height_label.move(700, 10)
        
        # Add QGraphicsView for displaying and annotating the image
        self.graphics_view = CustomQGraphicsView(self)
        self.graphics_view.setGeometry(10, 50, 900, 600)
        self.scene = QGraphicsScene()
        self.graphics_view.setScene(self.scene)

        self.change_grid_size(self.grid_input.text())

        # Add "Color All" button
        color_all_button = QPushButton('Color All', self)
        color_all_button.clicked.connect(self.graphics_view.color_all_cells)
        color_all_button.move(190, 10)

        # Add "Decolor All" button
        decolor_all_button = QPushButton('Decolor All', self)
        decolor_all_button.clicked.connect(self.graphics_view.decolor_all_cells)
        decolor_all_button.move(280, 10)

        self.toggle_mode_button = QPushButton('Original', self)
        self.toggle_mode_button.clicked.connect(self.toggle_mode)
        self.toggle_mode_button.move(800, 10)


    def open_image(self):
        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getOpenFileName(self, "Open Image", "", "Images (*.png *.jpg *.jpeg *.bmp)", options=options)
        self.opened_image_file_name = file_name
        if file_name:
            self.image = cv2.imread(file_name)
            height, width, channel = self.image.shape
            bytes_per_line = 3 * width
            q_image = QImage(self.image.data, width, height, bytes_per_line, QImage.Format_RGB888).rgbSwapped()

            self.graphics_view.set_image(q_image)
            self.scene.clear()
            self.scene.addPixmap(self.graphics_view.pixmap)
            self.graphics_view.draw_grid()
            self.graphics_view.setScene(self.scene)
            self.graphics_view.set_image(q_image)
            self.graphics_view.draw_grid()


    def change_grid_size(self, value):
        try:
            int_value = int(value)
        except ValueError:
            return
        
        int_value = max(1, int_value)

        self.graphics_view.set_grid_size(int_value)

        # Recalculate the filled_cells based on the new grid size
        new_filled_cells = {}
        for (old_grid_x, old_grid_y), cell_image in self.graphics_view.filled_cells.items():
            new_grid_x = old_grid_x // int_value * int_value
            new_grid_y = old_grid_y // int_value * int_value
            new_cell_key = (new_grid_x, new_grid_y)
            if new_cell_key not in new_filled_cells:
                new_filled_cells[new_cell_key] = cell_image

        self.graphics_view.filled_cells = new_filled_cells

        if not self.graphics_view.pixmap.isNull():
            self.graphics_view.draw_grid()
        self.update_grid_info()


    def update_grid_info(self):
        if self.graphics_view.pixmap.isNull():  # Check if an image is loaded
            return

        grid_width = self.graphics_view.pixmap.width() // self.graphics_view.grid_size
        grid_height = self.graphics_view.pixmap.height() // self.graphics_view.grid_size

        self.grid_width_label.setText(f"Grid Width: {grid_width}")
        self.grid_height_label.setText(f"Grid Height: {grid_height}")

    def save_image(self):
        if self.graphics_view.pixmap.isNull() or self.opened_image_file_name is None:
            QMessageBox.warning(self, "Warning", "No image loaded.")
            return

        base_name, _ = os.path.splitext(os.path.basename(self.opened_image_file_name))
        grid_width = self.graphics_view.pixmap.width() // self.graphics_view.grid_size
        grid_height = self.graphics_view.pixmap.height() // self.graphics_view.grid_size
        default_save_name = f"{base_name}_grid_{grid_height}x{grid_width}.png"

        options = QFileDialog.Options()
        file_name, _ = QFileDialog.getSaveFileName(self, "Save Image", default_save_name, "PNG Files (*.png)", options=options)

        if file_name:
            if not file_name.lower().endswith(".png"):
                file_name += ".png"

            binary_mask = self.graphics_view.get_binary_mask()
            binary_mask.save(file_name, "PNG")

    def toggle_mode(self):
        if self.graphics_view.mode == "original":
            self.graphics_view.change_mode("lasso")
            self.toggle_mode_button.setText("Lasso")
        else:
            self.graphics_view.change_mode("original")
            self.toggle_mode_button.setText("Original")




if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
