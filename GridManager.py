import csv
from constants import CELL_SIZE, GRID_SIZE, EMPTY, START, END, PATH, OBSTACLE

class GridManager:
    def __init__(self):
        self.grid = [[EMPTY for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        self.start_set = False
        self.end_set = False
        self.history = []  # Historial de cambios para deshacer

    def clear_type(self, cell_type):
        """Limpiar celdas de un tipo específico y guardar la acción"""
        positions = []
        for row in range(GRID_SIZE):
            for col in range(GRID_SIZE):
                if self.grid[row][col] == cell_type:
                    self.grid[row][col] = EMPTY
                    positions.append((row, col))  # Guardar la posición de la celda limpiada
        self.history.append(('clear', cell_type, positions))  # Guardar la acción para deshacer

    def set_start(self, row, col):
        """Establecer el punto de inicio y guardar la acción"""
        if not self.start_set:
            self.clear_type(START)
            self.grid[row][col] = START
            self.start_set = True
            self.history.append(('set_start', (row, col)))

    def set_end(self, row, col):
        """Establecer el punto de fin y guardar la acción"""
        if not self.end_set:
            self.clear_type(END)
            self.grid[row][col] = END
            self.end_set = True
            self.history.append(('set_end', (row, col)))

    def add_path(self, row, col):
        """Agregar un camino y guardar la acción"""
        if self.grid[row][col] == EMPTY:
            self.grid[row][col] = PATH
            self.history.append(('add_path', (row, col)))

    def add_obstacle(self, row, col):
        """Agregar un obstáculo y guardar la acción"""
        if self.grid[row][col] == EMPTY:
            self.grid[row][col] = OBSTACLE
            self.history.append(('add_obstacle', (row, col)))

    def export_to_csv(self, filename):
        """Exportar el recorrido a un archivo CSV"""
        with open(filename, mode='w', newline='') as file:
            writer = csv.writer(file)
            for row in self.grid:
                writer.writerow(row)

