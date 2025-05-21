from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush
from PyQt5.QtCore import QRect, pyqtSignal, Qt
from constants import CELL_SIZE, GRID_SIZE, EMPTY, START, END, PATH, OBSTACLE, ROBOT

class GridWidget(QWidget):
    # Señal para informar cuando se ha añadido un obstáculo
    obstacle_added = pyqtSignal(int, int)
    
    def __init__(self, grid_manager):
        super().__init__()
        self.grid_manager = grid_manager
        self.mode = 'select'  # Modo por defecto
        self.setFixedSize(CELL_SIZE * GRID_SIZE, CELL_SIZE * GRID_SIZE)
        
        # Guardar referencias a posiciones
        self.robot_pos = None
        self.meta_pos = None
        self.obstacles = []

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
        """Dibuja la cuadrícula y los objetos"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Dibujar fondo de la cuadrícula
        for row in range(GRID_SIZE):
            for col in range(GRID_SIZE):
                rect = QRect(col * CELL_SIZE, row * CELL_SIZE, CELL_SIZE, CELL_SIZE)
                
                # Color base: blanco
                painter.setBrush(QColor(255, 255, 255))
                painter.setPen(QColor(200, 200, 200))
                painter.drawRect(rect)
        
        # Dibujar líneas de la cuadrícula
        painter.setPen(QColor(200, 200, 200))
        for i in range(GRID_SIZE + 1):
            # Líneas horizontales
            painter.drawLine(0, i * CELL_SIZE, GRID_SIZE * CELL_SIZE, i * CELL_SIZE)
            # Líneas verticales
            painter.drawLine(i * CELL_SIZE, 0, i * CELL_SIZE, GRID_SIZE * CELL_SIZE)
        
        # --- PASO 1: DIBUJAR META (PUNTO ROJO) ---
        # Buscar el punto meta en el grid_manager
        meta_row, meta_col = None, None
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                if self.grid_manager.grid[r][c] == END:
                    meta_row, meta_col = r, c
                    break
            if meta_row is not None:
                break
        
        # Si no encontramos la meta en grid_manager, usar la referencia guardada
        if meta_row is None and hasattr(self, 'meta_pos') and self.meta_pos:
            meta_row, meta_col = self.meta_pos
        
        # Buscar en el padre como último recurso
        if meta_row is None:
            parent = self.parent()
            if parent and hasattr(parent, 'goal_position') and parent.goal_position:
                meta_row, meta_col = parent.goal_position
        
        # Dibujar la meta si tenemos su posición
        if meta_row is not None and meta_col is not None:
            meta_rect = QRect(meta_col * CELL_SIZE, meta_row * CELL_SIZE, CELL_SIZE, CELL_SIZE)
            
            # Relleno rojo
            painter.setBrush(QColor(255, 0, 0))
            painter.setPen(Qt.NoPen)
            painter.drawRect(meta_rect)
            
            # Bordes más claros
            painter.setPen(QColor(255, 200, 200))
            painter.drawRect(meta_rect)
        
        # --- PASO 2: DIBUJAR OBSTÁCULOS (GRIS) ---
        # Primero dibujar obstáculos del grid_manager
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                if self.grid_manager.grid[r][c] == OBSTACLE:
                    obs_rect = QRect(c * CELL_SIZE, r * CELL_SIZE, CELL_SIZE, CELL_SIZE)
                    
                    # Relleno gris
                    painter.setBrush(QColor(100, 100, 100))
                    painter.setPen(Qt.NoPen)
                    painter.drawRect(obs_rect)
                    
                    # Bordes más claros
                    painter.setPen(QColor(150, 150, 150))
                    painter.drawRect(obs_rect)
        
        # Luego dibujar obstáculos adicionales desde la lista
        if hasattr(self, 'obstacles') and self.obstacles:
            for r, c in self.obstacles:
                # Solo si no está ya marcado en el grid_manager
                if 0 <= r < GRID_SIZE and 0 <= c < GRID_SIZE and self.grid_manager.grid[r][c] != OBSTACLE:
                    obs_rect = QRect(c * CELL_SIZE, r * CELL_SIZE, CELL_SIZE, CELL_SIZE)
                    
                    # Relleno gris
                    painter.setBrush(QColor(100, 100, 100))
                    painter.setPen(Qt.NoPen)
                    painter.drawRect(obs_rect)
                    
                    # Bordes más claros
                    painter.setPen(QColor(150, 150, 150))
                    painter.drawRect(obs_rect)
        
        # --- PASO 3: DIBUJAR ROBOT (CÍRCULO AZUL) ---
        # Buscar el robot en el grid_manager
        robot_row, robot_col = None, None
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                if self.grid_manager.grid[r][c] == ROBOT:
                    robot_row, robot_col = r, c
                    break
            if robot_row is not None:
                break
        
        # Si no encontramos el robot en grid_manager, usar la referencia guardada
        if robot_row is None and hasattr(self, 'robot_pos') and self.robot_pos:
            robot_row, robot_col = self.robot_pos
        
        # Buscar en el padre como último recurso
        if robot_row is None:
            parent = self.parent()
            if parent and hasattr(parent, 'robot_position') and parent.robot_position:
                robot_row, robot_col = parent.robot_position
        
        # Dibujar el robot si tenemos su posición
        if robot_row is not None and robot_col is not None:
            # Círculo azul con margen
            margin = 4
            robot_rect = QRect(
                robot_col * CELL_SIZE + margin, 
                robot_row * CELL_SIZE + margin, 
                CELL_SIZE - 2*margin, 
                CELL_SIZE - 2*margin
            )
            
            # Fondo azul
            painter.setBrush(QColor(0, 120, 255))
            painter.setPen(QColor(0, 0, 0))
            painter.drawEllipse(robot_rect)
            
            # Círculo interior blanco para el centro
            center_x = robot_col * CELL_SIZE + CELL_SIZE/2
            center_y = robot_row * CELL_SIZE + CELL_SIZE/2
            
            painter.setBrush(QColor(255, 255, 255))
            painter.drawEllipse(int(center_x-5), int(center_y-5), 10, 10)
        
        # --- PASO 4: DIBUJAR SELECCIÓN (BORDE NARANJA) ---
        parent = self.parent()
        if parent and hasattr(parent, 'selected_position') and parent.selected_position:
            sel_row, sel_col = parent.selected_position
            if 0 <= sel_row < GRID_SIZE and 0 <= sel_col < GRID_SIZE:
                select_rect = QRect(
                    sel_col * CELL_SIZE, 
                    sel_row * CELL_SIZE, 
                    CELL_SIZE, 
                    CELL_SIZE
                )
                
                # Borde naranja más grueso
                pen = QPen(QColor(255, 165, 0), 3)
                painter.setPen(pen)
                painter.setBrush(Qt.NoBrush)
                painter.drawRect(select_rect)