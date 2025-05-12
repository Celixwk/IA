from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QFileDialog, QMessageBox, QLabel, QComboBox,
    QProgressBar, QApplication
)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal
from GridManager import GridManager
from GridWidget import GridWidget
from constants import GRID_SIZE, EMPTY, OBSTACLE, CELL_SIZE
from CoppeliaSimController import CoppeliaSimController
from CoppeliaSimWorker import CoppeliaSimWorker
import os

class MainWindow(QWidget):
    progress_update = pyqtSignal(int)
    connection_status_update = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Diseñador de Recorridos - Robot con CoppeliaSim (ZeroMQ)")

        self.grid_manager = GridManager()
        self.grid_widget = GridWidget(self.grid_manager)
        self.grid_widget.obstacle_added.connect(self.agregar_cubo_en_posicion)
        self.last_saved_path = None
        self.robot_handle = None
        self.robot_position = None
        self.is_connected = False
        self.is_resetting = False  # Nueva bandera para controlar el proceso de restablecimiento

        # Usar el controlador con ZeroMQ
        self.sim_controller = CoppeliaSimController(host="localhost", port=23000)
        self.sim_worker = CoppeliaSimWorker(self.sim_controller)
        self.sim_worker.connection_status.connect(self.update_connection_status_ui)
        self.sim_worker.progress_update.connect(self.update_progress_bar)
        self.sim_worker.operation_result.connect(self.handle_operation_result)
        self.sim_worker.operation_complete.connect(self.handle_operation_complete)  # Conectar nueva señal

        self.progress_update.connect(self.update_progress_bar)
        self.connection_status_update.connect(self.update_connection_status_ui)

        self.setup_ui()
        self.cube_handles = {}
        self.connect_signals()
        
        # Timer para verificar la conexión periódicamente
        self.check_timer = QTimer(self)
        self.check_timer.timeout.connect(self.check_connection)
        self.check_timer.start(5000)  # Verificar cada 5 segundos

    def check_connection(self):
        """Verifica periódicamente el estado de la conexión"""
        if self.is_connected:
            self.sim_worker.set_task('test')
            self.sim_worker.start()

    def handle_operation_result(self, success, message):
        """Maneja los resultados de operaciones asíncronas de CoppeliaSim"""
        self.progress_bar.setVisible(False)
        if success:
            print(f"✅ Operación exitosa: {message}")
        else:
            print(f"❌ Error en operación: {message}")
            # Solo mostrar mensaje de error si no estamos en proceso de restablecimiento
            if not self.is_resetting:
                QMessageBox.warning(self, "Error en operación", message)

    def handle_operation_complete(self, operation, result):
        """Maneja la finalización de operaciones específicas"""
        if operation == 'create_cuboid' and isinstance(result, dict):
            # Guardar el handle del cubo creado junto con su posición
            handle = result.get('handle')
            row = result.get('row')
            col = result.get('col')
            if handle is not None and row is not None and col is not None:
                self.cube_handles[(row, col)] = handle
                print(f"✅ Cubo registrado en posición ({row}, {col}) con handle {handle}")
                
                # Asegurar que el estado de la cuadrícula refleje el cambio
                self.grid_manager.add_obstacle(row, col)
                self.grid_widget.update()
        
        elif operation == 'create_robot' and isinstance(result, dict):
            # Manejar la creación del robot
            handle = result.get('handle')
            robot_type = result.get('robot_type')
            row = result.get('row')
            col = result.get('col')
            
            if handle is not None and row is not None and col is not None:
                # Guardar el handle y posición del robot
                self.robot_handle = handle
                self.robot_position = (row, col)
                print(f"✅ Robot {robot_type} registrado en posición ({row}, {col}) con handle {handle}")
                
                # Actualizar solo la representación visual del robot, no toda la cuadrícula
                self.grid_widget.update()
        
        elif operation == 'remove_cuboid' and isinstance(result, dict):
            # Manejar la eliminación de un cubo individual
            row = result.get('row')
            col = result.get('col')
            success = result.get('success', False)
            
            if success and row is not None and col is not None:
                # Eliminar del registro de handles
                if (row, col) in self.cube_handles:
                    del self.cube_handles[(row, col)]
                    print(f"✅ Handle eliminado para posición ({row}, {col})")
                
                # Actualizar el estado de la cuadrícula
                self.grid_manager.grid[row][col] = EMPTY
                self.grid_widget.update()
        
        elif operation == 'remove_robot' and isinstance(result, dict):
            # Manejar la eliminación del robot
            success = result.get('success', False)
            
            if success:
                self.robot_handle = None
                self.robot_position = None
                print("✅ Robot eliminado correctamente")
                self.grid_widget.update()
        
        elif operation == 'remove_all_cuboids':
            # Finalizar el proceso de restablecimiento si estamos en ese modo
            if self.is_resetting:
                self.is_resetting = False
                self.cube_handles = {}  # Limpiar todos los handles guardados
                print("✅ Proceso de restablecimiento completado")

    def setup_ui(self):
        layout = QVBoxLayout()

        header = QHBoxLayout()
        title = QLabel("Diseñador de Recorridos - Robot con CoppeliaSim (ZeroMQ)")
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
        self.robot_button = QPushButton("Colocar Robot")
        self.save_button = QPushButton("Guardar Recorrido")
        self.reset_button = QPushButton("Restablecer")

        for btn in [self.start_button, self.end_button, self.path_button,
                    self.obstacle_button, self.robot_button, self.save_button, self.reset_button]:
            grid_buttons.addWidget(btn)

        layout.addLayout(grid_buttons)

        config = QHBoxLayout()
        self.scale_combo = QComboBox()
        self.scale_combo.addItems(["0.25", "0.5"])
        self.scale_combo.setCurrentText("0.5")

        self.robot_combo = QComboBox()
        self.robot_combo.addItems(["/PioneerP3DX"])

        self.delay_combo = QComboBox()
        self.delay_combo.addItems(["0.5", "1.0", "1.5", "2.0"])
        self.delay_combo.setCurrentText("1.5")

        config.addWidget(QLabel("Escala (m):"))
        config.addWidget(self.scale_combo)
        config.addWidget(QLabel("Robot:"))
        config.addWidget(self.robot_combo)
        config.addWidget(QLabel("Retardo (s):"))
        config.addWidget(self.delay_combo)

        # Agregar configuración para ZeroMQ
        self.zmq_port = QComboBox()
        self.zmq_port.addItems(["23000", "23001", "23002"])
        self.zmq_port.setCurrentText("23000")
        self.zmq_port.setEditable(True)
        config.addWidget(QLabel("Puerto ZeroMQ:"))
        config.addWidget(self.zmq_port)

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
        self.robot_button.clicked.connect(lambda: self.set_mode('robot'))

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
        4. Asegúrese de que el puerto ZeroMQ coincida con el configurado en CoppeliaSim.
        """)
        layout.addWidget(instructions)

        self.setLayout(layout)
        self.resize(600, 700)

    # Agrega ambos métodos a tu MainWindow.py

    def agregar_robot_en_posicion(self, row, col):
        """
        Agrega un robot en la posición especificada.
        Solo permite un robot a la vez en la escena.
        """
        if not self.is_connected:
            QMessageBox.warning(self, "No conectado", "Conéctate a CoppeliaSim antes de colocar el robot.")
            return
            
        # Si ya existe un robot, mostrar mensaje y no hacer nada
        if self.robot_handle is not None:
            QMessageBox.information(self, "Robot ya existe", 
                                "Ya existe un robot en la escena. Restablece la cuadrícula para colocar otro.")
            return
            
        # Obtener el tipo de robot seleccionado - quitar la barra inicial si existe
        robot_type = self.robot_combo.currentText()
        if robot_type.startswith("/"):
            robot_type = robot_type[1:]  # Eliminar la barra inicial si existe
        
        # Usar la misma escala de referencia que para los cubos para consistencia
        reference_scale = 0.5
        
        # Calcular posición igual que para los cubos
        x = (col - GRID_SIZE/2 + 0.5) * reference_scale
        y = (GRID_SIZE/2 - row - 0.5) * reference_scale
        z = 0.05  # Ligeramente sobre el suelo para visualizarlo mejor
        
        position = [x, y, z]
        
        print(f"🤖 Colocando robot {robot_type} en fila {row}, columna {col} → Posición: {position}")
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(25)
        
        # Guardar temporalmente la posición deseada del robot
        self.temp_robot_position = (row, col)
        
        # Crear el robot usando el worker
        self.sim_worker.set_task('create_robot', 
                            robot_type=robot_type, 
                            position=position, 
                            row=row, 
                            col=col)
        self.sim_worker.start()

    def agregar_cubo_en_posicion(self, row, col):
        """
        Agrega un cubo en la posición especificada, manteniendo posiciones
        constantes independientemente de la escala seleccionada
        """
        if not self.is_connected:
            QMessageBox.warning(self, "No conectado", "Conéctate a CoppeliaSim antes de agregar obstáculos.")
            return

        # IMPORTANTE: Usar una escala de referencia fija para calcular posiciones
        # Esto hará que los cubos aparezcan en las mismas posiciones sin importar la escala seleccionada
        reference_scale = 0.5  # Escala de referencia fija para posicionamiento
        
        # Obtenemos la escala actual solo para el tamaño del cubo
        current_scale = float(self.scale_combo.currentText())
        
        # MAPEO FIJO: Usamos una escala de referencia para todas las posiciones
        # Calcular posición ajustada al tablero de CoppeliaSim (que está centrado)
        x = (col - GRID_SIZE/2 + 0.5) * reference_scale
        y = (GRID_SIZE/2 - row - 0.5) * reference_scale
        z = 0.05  # Altura ligeramente sobre el suelo
        
        position = [x, y, z]
        
        # El TAMAÑO SÍ varía según la escala seleccionada
        cube_size = current_scale * 0.8  # Factor 0.8 para que no ocupe toda la celda
        size = [cube_size, cube_size, 0.1]  # 10cm de altura
        
        # Color para obstáculos (gris oscuro)
        color = [0.2, 0.2, 0.2]  # RGB (0-1)
        
        print(f"📊 Creando cubo en fila {row}, columna {col} → Posición CoppeliaSim: {position}, Tamaño: {size}")
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(25)
        
        # Verificar si ya existe un cubo en esta posición
        if (row, col) in self.cube_handles:
            old_handle = self.cube_handles[(row, col)]
            print(f"⚠️ Ya existe un cubo en ({row}, {col}) con handle {old_handle}, eliminándolo primero")
            
            # Eliminar el cubo existente
            self.sim_worker.set_task('remove_cuboid', handle=old_handle, row=row, col=col)
            self.sim_worker.start()
            
            # Esperar un momento antes de crear el nuevo cubo
            QTimer.singleShot(300, lambda: self.crear_cubo_delayed(position, size, color, row, col))
        else:
            # Crear el cubo directamente
            self.crear_cubo_delayed(position, size, color, row, col)

    def crear_cubo_delayed(self, position, size, color, row, col):
        """Crea un cubo con un pequeño retraso (utilizado después de eliminar un cubo existente)"""
        self.sim_worker.set_task('create_cuboid', position=position, size=size, color=color, row=row, col=col)
        self.sim_worker.start()

    def agregar_obstaculo_coppelia(self):
            self.set_mode("obstacle")

    def connect_signals(self):
        self.connect_button.clicked.connect(self.toggle_connection)
        self.test_button.clicked.connect(self.test_connection)
        self.obstacle_button.clicked.connect(self.agregar_obstaculo_coppelia)
        self.robot_button.clicked.connect(lambda: self.set_mode('robot'))
        self.start_button.clicked.connect(self.set_start_mode)
        self.end_button.clicked.connect(self.set_end_mode)
        self.path_button.clicked.connect(self.set_path_mode)
        self.reset_button.clicked.connect(self.reset_grid)
        self.save_button.clicked.connect(self.save_grid)
        self.zmq_port.currentTextChanged.connect(self.update_zmq_port)
        self.grid_widget.mousePressEvent = self.custom_mouse_press_event
    
    def update_zmq_port(self):
        """Actualiza el puerto ZeroMQ en el controlador"""
        try:
            port = int(self.zmq_port.currentText())
            self.sim_controller.port = port
            print(f"Puerto ZeroMQ actualizado a: {port}")
        except ValueError:
            print("El puerto debe ser un número entero")

    def update_progress_bar(self, value):
        self.progress_bar.setValue(value)
        QApplication.processEvents()  # Procesar eventos para actualizar la UI

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
        # Actualizar el puerto ZeroMQ antes de conectar
        try:
            port = int(self.zmq_port.currentText())
            self.sim_controller.port = port
        except ValueError:
            QMessageBox.warning(self, "Error", "El puerto ZeroMQ debe ser un número entero")
            return
            
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
            'obstacle': self.obstacle_button,
            'robot': self.robot_button
        }.items():
            button.setStyleSheet("background-color: #a0e0a0;" if btn_mode == mode else "")

    def set_start_mode(self):
        self.set_mode('start')

    def set_end_mode(self):
        self.set_mode('end')

    def set_path_mode(self):
        self.set_mode('path')

    def reset_grid(self):
        try:
            # Primero resetear la cuadrícula en la interfaz
            self.grid_manager = GridManager()
            self.grid_widget.grid_manager = self.grid_manager
            self.grid_widget.update()
            
            # Resetear el estado del robot
            self.robot_handle = None
            self.robot_position = None
            
            # Luego, si estamos conectados a CoppeliaSim, eliminar los cubos y el robot
            if self.is_connected:
                self.is_resetting = True  # Indicar que estamos en proceso de restablecimiento
                self.eliminar_cubos_en_coppelia()
                
                # Si había un robot, incluirlo en la eliminación (esto se manejaría en el controlador)
                if hasattr(self, 'robot_handle') and self.robot_handle is not None:
                    self.sim_worker.set_task('remove_robot', handle=self.robot_handle)
                    self.sim_worker.start()
            else:
                # Si no estamos conectados, simplemente limpiar el registro de handles
                self.cube_handles = {}
        except Exception as e:
            print(f"❌ Error al restablecer la cuadrícula: {e}")
            QMessageBox.warning(self, "Error", f"Error al restablecer: {str(e)}")

    def save_grid(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Guardar Recorrido", "", "CSV Files (*.csv)")
        if filename:
            self.grid_manager.export_to_csv(filename)
            self.last_saved_path = filename
            QMessageBox.information(self, "Éxito", f"Recorrido guardado en {filename}")
            self.execute_button.setEnabled(self.is_connected)

    def custom_mouse_press_event(self, event):
        """Maneja el evento de clic en la cuadrícula"""
        col = event.x() // CELL_SIZE
        row = event.y() // CELL_SIZE

        if 0 <= row < GRID_SIZE and 0 <= col < GRID_SIZE:
            mode = self.grid_widget.mode
            
            if mode == 'start':
                self.grid_manager.set_start(row, col)
            elif mode == 'end':
                self.grid_manager.set_end(row, col)
            elif mode == 'path':
                self.grid_manager.add_path(row, col)
            elif mode == 'obstacle':
                # Si ya hay obstáculo, eliminarlo
                if self.grid_manager.grid[row][col] == OBSTACLE:
                    # Eliminar el cubo en CoppeliaSim si estamos conectados
                    if self.is_connected:
                        self.eliminar_cubo_en_posicion(row, col)
                    else:
                        # Si no estamos conectados, solo actualizar la cuadrícula
                        self.grid_manager.grid[row][col] = EMPTY
                        self.grid_widget.update()
                else:
                    # Si no hay obstáculo, agregarlo
                    self.grid_manager.grid[row][col] = OBSTACLE
                    
                    # Crear el cubo en CoppeliaSim si estamos conectados
                    if self.is_connected:
                        self.agregar_cubo_en_posicion(row, col)
            elif mode == 'robot':
                # Colocar robot en la posición seleccionada
                if self.is_connected:
                    self.agregar_robot_en_posicion(row, col)

            self.grid_widget.update()


    def eliminar_cubos_en_coppelia(self):
        """Elimina todos los cubos de la escena de CoppeliaSim"""
        if not self.is_connected:
            QMessageBox.warning(self, "No conectado", "Conéctate a CoppeliaSim antes de eliminar obstáculos.")
            return

        try:
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(25)
            
            # Iniciar el proceso de eliminación de cubos
            self.sim_worker.set_task('remove_all_cuboids')
            self.sim_worker.start()
            
            print("🧹 Iniciando eliminación de cubos en CoppeliaSim...")
        except Exception as e:
            self.is_resetting = False
            print(f"❌ Error al iniciar la eliminación de cubos: {e}")
            QMessageBox.warning(self, "Error", f"Error al eliminar cubos: {str(e)}")

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
        self.sim_worker.set_task('remove_cuboid', handle=handle)
        self.sim_worker.start()
        
        # Eliminar el handle del registro cuando se elimina el cubo específico
        if (row, col) in self.cube_handles:
            del self.cube_handles[(row, col)]