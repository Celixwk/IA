from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPainter, QColor
from PyQt5.QtCore import QRect, pyqtSignal
from constants import CELL_SIZE, GRID_SIZE, EMPTY, START, END, PATH, OBSTACLE

class GridWidget(QWidget):
    # Señal para informar cuando se ha añadido un obstáculo
    obstacle_added = pyqtSignal(int, int)
    
    def __init__(self, grid_manager):
        super().__init__()
        self.grid_manager = grid_manager
        self.mode = 'start'
        self.setFixedSize(CELL_SIZE * GRID_SIZE, CELL_SIZE * GRID_SIZE)

    def mousePressEvent(self, event):
        col = event.x() // CELL_SIZE
        row = event.y() // CELL_SIZE

        if 0 <= row < GRID_SIZE and 0 <= col < GRID_SIZE:
            if self.mode == 'start':
                self.grid_manager.set_start(row, col)
            elif self.mode == 'end':
                self.grid_manager.set_end(row, col)
            elif self.mode == 'path':
                self.grid_manager.grid[row][col] = PATH
            elif self.mode == 'obstacle':
                self.grid_manager.grid[row][col] = OBSTACLE
                # 🔔 Emitir señal para que MainWindow cree cubo en CoppeliaSim
                self.obstacle_added.emit(row, col)

            self.update()


    def paintEvent(self, event):
        qp = QPainter(self)
        for row in range(GRID_SIZE):
            for col in range(GRID_SIZE):
                rect = QRect(col * CELL_SIZE, row * CELL_SIZE, CELL_SIZE, CELL_SIZE)
                cell_state = self.grid_manager.grid[row][col]
                if cell_state == EMPTY:
                    qp.setBrush(QColor(255, 255, 255))
                elif cell_state == START:
                    qp.setBrush(QColor(0, 255, 0))
                elif cell_state == END:
                    qp.setBrush(QColor(255, 0, 0))
                elif cell_state == PATH:
                    qp.setBrush(QColor(255, 255, 0))
                elif cell_state == OBSTACLE:
                    qp.setBrush(QColor(50, 50, 50))
                qp.drawRect(rect)
        
        # Dibujar líneas de la cuadrícula
        qp.setPen(QColor(200, 200, 200))
        for i in range(GRID_SIZE + 1):
            # Líneas horizontales
            qp.drawLine(0, i * CELL_SIZE, GRID_SIZE * CELL_SIZE, i * CELL_SIZE)
            # Líneas verticales
            qp.drawLine(i * CELL_SIZE, 0, i * CELL_SIZE, GRID_SIZE * CELL_SIZE)

    # Nota: La implementación de mousePressEvent se delega a MainWindow
    # a través de custom_mouse_press_event para poder manejar la creación
    # de obstáculos tanto en la interfaz como en CoppeliaSim