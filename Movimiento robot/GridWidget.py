from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPainter, QColor, QPen
from PyQt5.QtCore import QRect, pyqtSignal, Qt
from constants import CELL_SIZE, GRID_SIZE, EMPTY, START, END, PATH, OBSTACLE, ROBOT

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
        """Dibuja la cuadrícula con todos sus elementos, incluyendo el robot si existe"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        qp = QPainter(self)
        
        # Dibujar todas las celdas
        for row in range(GRID_SIZE):
            for col in range(GRID_SIZE):
                rect = QRect(col * CELL_SIZE, row * CELL_SIZE, CELL_SIZE, CELL_SIZE)
                cell_state = self.grid_manager.grid[row][col]
                
                # Determinar color de la celda según su estado
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
                elif cell_state == ROBOT:
                     qp.setBrush(QColor(0, 0, 255))  # Azul para el robot
                
                qp.drawRect(rect)
        
        # Dibujar el robot si existe (accediendo directamente a MainWindow)
        # Podemos obtener la ventana principal desde el widget
        parent_widget = self.parent()
        while parent_widget and not hasattr(parent_widget, 'robot_position'):
            parent_widget = parent_widget.parent()
        
        # Si encontramos la ventana principal y tiene un robot
        if parent_widget and hasattr(parent_widget, 'robot_position') and parent_widget.robot_position:
            row, col = parent_widget.robot_position
            
            # Dibujar un círculo azul para el robot
            robot_rect = QRect(col * CELL_SIZE + 5, row * CELL_SIZE + 5, 
                            CELL_SIZE - 10, CELL_SIZE - 10)  # Ligeramente más pequeño que la celda
            qp.setBrush(QColor(0, 100, 255))  # Azul para el robot
            qp.setPen(QColor(0, 0, 0))  # Borde negro
            qp.drawEllipse(robot_rect)
            
            # Opcional: dibujar un ícono o texto para identificar el robot
            qp.setPen(QColor(255, 255, 255))  # Texto blanco
            qp.drawText(robot_rect, Qt.AlignCenter, "R")
        
        if hasattr(self.parent(), 'robot_position') and self.parent().robot_position is not None:
            row, col = self.parent().robot_position
            x = col * CELL_SIZE
            y = row * CELL_SIZE
            
            robot_color = QColor(0, 128, 255)  # Azul para el robot
            painter.fillRect(x, y, CELL_SIZE, CELL_SIZE, robot_color)
            
            # Dibujar un círculo para representar el robot de manera más clara
            painter.setPen(QPen(QColor(255, 255, 255), 2))  # Borde blanco
            painter.drawEllipse(x + CELL_SIZE//4, y + CELL_SIZE//4, CELL_SIZE//2, CELL_SIZE//2)
            
            # Opcional: Dibujar un símbolo de dirección (como una flecha)
            painter.setPen(QPen(QColor(255, 255, 255), 2))
            painter.drawLine(x + CELL_SIZE//2, y + CELL_SIZE//2, x + 3*CELL_SIZE//4, y + CELL_SIZE//2)
            painter.drawLine(x + 3*CELL_SIZE//4, y + CELL_SIZE//2, x + 2*CELL_SIZE//3, y + CELL_SIZE//3)
            painter.drawLine(x + 3*CELL_SIZE//4, y + CELL_SIZE//2, x + 2*CELL_SIZE//3, y + 2*CELL_SIZE//3)

        # Dibujar líneas de la cuadrícula
        painter.setPen(QColor(200, 200, 200))
        for i in range(GRID_SIZE + 1):
            # Líneas horizontales
            painter.drawLine(0, i * CELL_SIZE, GRID_SIZE * CELL_SIZE, i * CELL_SIZE)
            # Líneas verticales
            painter.drawLine(i * CELL_SIZE, 0, i * CELL_SIZE, GRID_SIZE * CELL_SIZE)

    # Nota: La implementación de mousePressEvent se delega a MainWindow
    # a través de custom_mouse_press_event para poder manejar la creación
    # de obstáculos tanto en la interfaz como en CoppeliaSim