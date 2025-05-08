from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QFileDialog, QMessageBox, QLabel, QComboBox,
    QProgressBar, QApplication
)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal, QThread
from GridManager import GridManager
from GridWidget import GridWidget
from constants import GRID_SIZE, EMPTY, OBSTACLE, CELL_SIZE
from CoppeliaSimController import CoppeliaSimController
import os
import asyncio

class CoppeliaSimWorker(QThread):
    connection_status = pyqtSignal(bool)
    progress_update = pyqtSignal(int)
    operation_result = pyqtSignal(bool, str)  # Para informar sobre resultados de operaciones
    cube_created = pyqtSignal(int, int, int)  # Nueva señal: (row, col, handle)

    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.operation = None
        self.params = {}
        self.loop = asyncio.new_event_loop()

    def set_task(self, operation, **params):
        self.operation = operation
        self.params = params

    async def connect_task(self):
        result = await self.controller.connect()
        self.connection_status.emit(result)
        return result

    async def disconnect_task(self):
        result = await self.controller.disconnect()
        self.connection_status.emit(not result)
        return result

    async def test_connection_task(self):
        result = await self.controller.test_connection()
        self.connection_status.emit(result)
        return result

    async def create_cuboid_task(self):
        position = self.params.get('position', [0, 0, 0.05])
        size = self.params.get('size', [0.1, 0.1, 0.1])
        color = self.params.get('color', [1, 0, 0])
        row = self.params.get('row')
        col = self.params.get('col')

        # Intentar crear el objeto en el floor (-1 es el parent por defecto, 0 para el floor)
        result = await self.controller.create_cuboid(size, position, color, parent_handle=0)
        
        if result is not None:
            # Emitir señal con fila, columna y handle del cubo creado
            self.cube_created.emit(row, col, result)
            self.operation_result.emit(True, f"Cubo creado con éxito (handle: {result})")
        else:
            self.operation_result.emit(False, "No se pudo crear el cubo")
        
        return result
    
    async def remove_cuboid_task(self):
        handle = self.params.get('handle')
        row = self.params.get('row', None)
        col = self.params.get('col', None)
        
        if handle is None:
            self.operation_result.emit(False, "Handle no proporcionado")
            return False
        
        result = await self.controller.eliminar_cubo_por_handle(handle)
        
        # Si hay información de fila y columna, emitir señal para actualizar el registro
        if row is not None and col is not None:
            self.operation_result.emit(result, f"Cubo en ({row}, {col}) {'eliminado' if result else 'no eliminado'}")
        else:
            self.operation_result.emit(result, f"Cubo {handle} {'eliminado' if result else 'no eliminado'}")
        
        return result

    async def remove_all_cuboids_task(self):
        result = await self.controller.eliminar_cubos()
        message = "Cubos eliminados exitosamente" if result else "No se pudieron eliminar todos los cubos"
        self.operation_result.emit(result, message)
        return result

    def run(self):
        if self.operation is None:
            return

        asyncio.set_event_loop(self.loop)

        try:
            self.progress_update.emit(25)  # Inicio de la operación
            
            if self.operation == 'connect':
                self.loop.run_until_complete(self.connect_task())
            elif self.operation == 'disconnect':
                self.loop.run_until_complete(self.disconnect_task())
            elif self.operation == 'test':
                self.loop.run_until_complete(self.test_connection_task())
            elif self.operation == 'create_cuboid':
                self.loop.run_until_complete(self.create_cuboid_task())
            elif self.operation == 'start_sim':
                self.loop.run_until_complete(self.controller.start_simulation())
            elif self.operation == 'pause_sim':
                self.loop.run_until_complete(self.controller.send_request("sim.pauseSimulation"))
            elif self.operation == 'stop_sim':
                self.loop.run_until_complete(self.controller.stop_simulation())
            elif self.operation == 'remove_cuboid':
                self.loop.run_until_complete(self.remove_cuboid_task())
            elif self.operation == 'remove_all_cuboids':
                self.loop.run_until_complete(self.remove_all_cuboids_task())
            
            self.progress_update.emit(100)  # Operación completada
        except Exception as e:
            print(f"❌ Error en operación '{self.operation}': {e}")
            self.operation_result.emit(False, f"Error en operación: {str(e)}")
            self.progress_update.emit(0)  # Indicar error


class MainWindow(QWidget):
    progress_update = pyqtSignal(int)
    connection_status_update = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Diseñador de Recorridos - Robot con CoppeliaSim")

        self.grid_manager = GridManager()
        self.grid_widget = GridWidget(self.grid_manager)
        self.grid_widget.obstacle_added.connect(self.agregar_cubo_en_posicion)
        self.last_saved_path = None
        self.is_connected = False

        self.sim_controller = CoppeliaSimController()
        self.sim_worker = CoppeliaSimWorker(self.sim_controller)
        self.sim_worker.connection_status.connect(self.update_connection_status_ui)
        self.sim_worker.progress_update.connect(self.update_progress_bar)
        self.sim_worker.operation_result.connect(self.handle_operation_result)
        # Conectar la señal de cubo creado para actualizar el handle
        self.sim_worker.cube_created.connect(self.update_cube_handle)

        self.progress_update.connect(self.update_progress_bar)
        self.connection_status_update.connect(self.update_connection_status_ui)

        self.setup_ui()
        self.cube_handles = {}  # Diccionario para asociar posiciones (row, col) con handles
        self.connect_signals()
    
    def handle_operation_result(self, success, message):
        """Maneja los resultados de operaciones asíncronas"""
        self.progress_bar.setVisible(False)
        if success:
            print(f"✅ {message}")
        else:
            print(f"❌ {message}")
            #QMessageBox.warning(self, "Error en operación", message)

    def update_cube_handle(self, row, col, handle):
        """Actualiza el diccionario de handles cuando se crea un cubo"""
        print(f"✅ Actualizando handle para cubo en ({row}, {col}): {handle}")
        self.cube_handles[(row, col)] = handle
        self.progress_bar.setVisible(False)

    def eliminar_cubo_en_posicion(self, row, col):
        """Elimina un cubo específico por su posición en la cuadrícula"""
        if not self.is_connected:
            QMessageBox.warning(self, "No conectado", "Conéctate a CoppeliaSim antes de eliminar obstáculos.")
            return
        
        handle = self.cube_handles.get((row, col))
        if handle is None:
            print(f"⚠️ No se encontró handle para la posición ({row}, {col})")
            return
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(25)
        self.sim_worker.set_task('remove_cuboid', handle=handle, row=row, col=col)
        self.sim_worker.start()
        
        # Eliminamos el handle después de que se complete la operación para evitar eliminar antes de tiempo
        # Esto se hará cuando la operación sea exitosa en el worker

    def update_cube_removal_status(self, row, col, success):
        """Actualiza el estado después de eliminar un cubo"""
        if success and (row, col) in self.cube_handles:
            del self.cube_handles[(row, col)]
            print(f"✅ Handle para cubo en ({row}, {col}) eliminado del registro")
        self.progress_bar.setVisible(False)

    def setup_ui(self):
        layout = QVBoxLayout()

        header = QHBoxLayout()
        title = QLabel("Diseñador de Recorridos - Robot con CoppeliaSim")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.status_label = QLabel("Estado: No conectado")
        self.status_label.setStyleSheet("color: red;")
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.status_label)
        layout.addLayout(header)

        grid_buttons = QHBoxLayout()
        self.start_button = QPushButton("Marcar Inicio (A)")
        self.end_button = QPushButton("Marcar Meta (B)")
        self.path_button = QPushButton("Trazo Manual")
        self.obstacle_button = QPushButton("Agregar Obstáculo")
        self.save_button = QPushButton("Guardar Recorrido")
        self.reset_button = QPushButton("Restablecer")

        for btn in [self.start_button, self.end_button, self.path_button,
                    self.obstacle_button, self.save_button, self.reset_button]:
            grid_buttons.addWidget(btn)

        layout.addLayout(grid_buttons)

        config = QHBoxLayout()
        self.scale_combo = QComboBox()
        self.scale_combo.addItems(["0.25", "0.5", "1.0", "2.0"])
        self.scale_combo.setCurrentText("0.5")

        self.robot_combo = QComboBox()
        self.robot_combo.addItems(["/PioneerP3DX", "/KukaRobot", "/youBot"])

        self.delay_combo = QComboBox()
        self.delay_combo.addItems(["0.5", "1.0", "1.5", "2.0"])
        self.delay_combo.setCurrentText("1.5")

        config.addWidget(QLabel("Escala (m):"))
        config.addWidget(self.scale_combo)
        config.addWidget(QLabel("Robot:"))
        config.addWidget(self.robot_combo)
        config.addWidget(QLabel("Retardo (s):"))
        config.addWidget(self.delay_combo)

        layout.addLayout(config)

        sim_buttons = QHBoxLayout()
        self.connect_button = QPushButton("Conectar a CoppeliaSim")
        self.test_button = QPushButton("Probar Conexión")
        self.execute_button = QPushButton("Ejecutar Ruta en CoppeliaSim")
        self.execute_button.setEnabled(False)

        sim_buttons.addWidget(self.connect_button)
        sim_buttons.addWidget(self.test_button)
        sim_buttons.addWidget(self.execute_button)
        layout.addLayout(sim_buttons)

        sim_control_buttons = QHBoxLayout()
        self.play_button = QPushButton("▶️ Iniciar Simulación")
        self.pause_button = QPushButton("⏸️ Pausar Simulación")
        self.stop_button = QPushButton("⏹️ Detener Simulación")

        self.play_button.clicked.connect(lambda: self.sim_worker.set_task('start_sim') or self.sim_worker.start())
        self.pause_button.clicked.connect(lambda: self.sim_worker.set_task('pause_sim') or self.sim_worker.start())
        self.stop_button.clicked.connect(lambda: self.sim_worker.set_task('stop_sim') or self.sim_worker.start())

        sim_control_buttons.addWidget(self.play_button)
        sim_control_buttons.addWidget(self.pause_button)
        sim_control_buttons.addWidget(self.stop_button)
        layout.addLayout(sim_control_buttons)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.grid_widget)

        instructions = QLabel("""
        Instrucciones:
        1. Diseñe su recorrido marcando inicio (A), meta (B), camino y obstáculos.
        2. Conecte con CoppeliaSim antes de agregar obstáculos en la simulación.
        3. Use el botón "Agregar Obstáculo" para crear cuboides en CoppeliaSim.
        """)
        layout.addWidget(instructions)

        self.setLayout(layout)
        self.resize(600, 700)

    def agregar_cubo_en_posicion(self, row, col):
        if not self.is_connected:
            QMessageBox.warning(self, "No conectado", "Conéctate a CoppeliaSim antes de agregar obstáculos.")
            return

        cell_size = float(self.scale_combo.currentText())
        x = col * cell_size
        y = -row * cell_size
        z = 0.05  # Altura reducida para que esté en el suelo

        size = [cell_size * 0.8, cell_size * 0.8, 0.1]
        position = [x, y, z]
        color = [0.2, 0.2, 0.2]

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(50)
        
        # Pasar fila y columna como parámetros para poder actualizar el handle después
        self.sim_worker.set_task('create_cuboid', position=position, size=size, color=color, row=row, col=col)
        self.sim_worker.start()

    def agregar_obstaculo_coppelia(self):
        self.set_mode("obstacle")

    def connect_signals(self):
        self.connect_button.clicked.connect(self.toggle_connection)
        self.test_button.clicked.connect(self.test_connection)
        self.obstacle_button.clicked.connect(self.agregar_obstaculo_coppelia)
        self.start_button.clicked.connect(self.set_start_mode)
        self.end_button.clicked.connect(self.set_end_mode)
        self.path_button.clicked.connect(self.set_path_mode)
        self.reset_button.clicked.connect(self.reset_grid)
        self.save_button.clicked.connect(self.save_grid)
        self.grid_widget.mousePressEvent = self.custom_mouse_press_event

    def update_progress_bar(self, value):
        self.progress_bar.setValue(value)
        QApplication.processEvents()

    def update_connection_status_ui(self, is_connected):
        self.is_connected = is_connected
        self.status_label.setText("Estado: Conectado" if is_connected else "Estado: No conectado")
        self.status_label.setStyleSheet("color: green;" if is_connected else "color: red;")
        self.connect_button.setText("Desconectar" if is_connected else "Conectar a CoppeliaSim")
        has_saved_path = self.last_saved_path is not None and os.path.exists(self.last_saved_path)
        self.execute_button.setEnabled(is_connected and has_saved_path)

    def toggle_connection(self):
        if not self.is_connected:
            self.connect_to_coppelia()
        else:
            self.disconnect_from_coppelia()

    def connect_to_coppelia(self):
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(50)
        self.sim_worker.set_task('connect')
        self.sim_worker.start()

    def disconnect_from_coppelia(self):
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(50)
        self.sim_worker.set_task('disconnect')
        self.sim_worker.start()

    def test_connection(self):
        if not self.is_connected:
            QMessageBox.warning(self, "Advertencia", "No hay conexión con CoppeliaSim. Conéctese primero.")
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(50)
        self.sim_worker.set_task('test')
        self.sim_worker.start()

    def set_mode(self, mode):
        self.grid_widget.mode = mode
        for btn_mode, button in {
            'start': self.start_button,
            'end': self.end_button,
            'path': self.path_button,
            'obstacle': self.obstacle_button
        }.items():
            button.setStyleSheet("background-color: #a0e0a0;" if btn_mode == mode else "")

    def set_start_mode(self):
        self.set_mode('start')

    def set_end_mode(self):
        self.set_mode('end')

    def set_path_mode(self):
        self.set_mode('path')

    def reset_grid(self):
        # Primero eliminar los cubos en CoppeliaSim si estamos conectados
        if self.is_connected and self.cube_handles:
            self.eliminar_cubos_en_coppelia()
        
        # Después resetear la cuadrícula
        self.grid_manager = GridManager()
        self.grid_widget.grid_manager = self.grid_manager
        self.grid_widget.update()

    def save_grid(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Guardar Recorrido", "", "CSV Files (*.csv)")
        if filename:
            self.grid_manager.export_to_csv(filename)
            self.last_saved_path = filename
            QMessageBox.information(self, "Éxito", f"Recorrido guardado en {filename}")
            self.execute_button.setEnabled(self.is_connected)

    def custom_mouse_press_event(self, event):
        col = event.x() // CELL_SIZE
        row = event.y() // CELL_SIZE

        if 0 <= row < GRID_SIZE and 0 <= col < GRID_SIZE:
            if self.grid_widget.mode == 'start':
                self.grid_manager.set_start(row, col)
            elif self.grid_widget.mode == 'end':
                self.grid_manager.set_end(row, col)
            elif self.grid_widget.mode == 'path':
                self.grid_manager.add_path(row, col)
            elif self.grid_widget.mode == 'obstacle':
                # Verificar si ya existe un obstáculo en esta posición
                if self.grid_manager.grid[row][col] == OBSTACLE:
                    # Si existe, eliminarlo
                    if (row, col) in self.cube_handles and self.is_connected:
                        self.eliminar_cubo_en_posicion(row, col)
                    self.grid_manager.grid[row][col] = EMPTY
                else:
                    # Si no existe, agregarlo
                    self.grid_manager.add_obstacle(row, col)
                    if self.is_connected:
                        self.agregar_cubo_en_posicion(row, col)

            self.grid_widget.update()

    def eliminar_cubos_en_coppelia(self):
        """Elimina todos los cubos de la escena de CoppeliaSim"""
        if not self.is_connected:
            QMessageBox.warning(self, "No conectado", "Conéctate a CoppeliaSim antes de eliminar obstáculos.")
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(25)
        self.sim_worker.set_task('remove_all_cuboids')
        self.sim_worker.start()

        # Limpiar el diccionario de handles
        self.cube_handles = {}