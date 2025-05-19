from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QFileDialog, QMessageBox, QLabel, QComboBox,
    QProgressBar, QApplication
)
from PyQt5.QtCore import QTimer
from GridManager import GridManager
from GridWidget import GridWidget
from constants import GRID_SIZE, EMPTY, OBSTACLE, CELL_SIZE, START, END, ROBOT
from CoppeliaSimController import CoppeliaSimController
from CoppeliaSimWorker import CoppeliaSimWorker
import time

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Diseñador de Recorridos - Robot con CoppeliaSim (ZeroMQ)")

        self.grid_manager = GridManager()
        self.grid_widget = GridWidget(self.grid_manager)
        self.grid_widget.obstacle_added.connect(self.agregar_cubo_en_posicion)
        self.robot_handle = None
        self.robot_position = None
        self.is_connected = False

        # Inicializar el controlador con ZeroMQ
        self.sim_controller = CoppeliaSimController(host="localhost", port=23000)
        self.sim_worker = CoppeliaSimWorker(self.sim_controller)
        self.sim_worker.connection_status.connect(self.update_connection_status_ui)
        self.sim_worker.progress_update.connect(self.update_progress_bar)
        self.sim_worker.operation_result.connect(self.handle_operation_result)
        self.sim_worker.operation_complete.connect(self.handle_operation_complete)

        self.setup_ui()
        self.cube_handles = {}
        self.connect_signals()

    def handle_operation_result(self, success, message):
        """Maneja los resultados de operaciones asíncronas de CoppeliaSim"""
        self.progress_bar.setVisible(False)
        if success:
            print(f"✅ Operación exitosa: {message}")
        else:
            print(f"❌ Error en operación: {message}")
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
            row = result.get('row')
            col = result.get('col')
            
            if handle is not None and row is not None and col is not None:
                # Guardar el handle y posición del robot
                self.robot_handle = handle
                self.robot_position = (row, col)
                print(f"✅ Robot registrado en posición ({row}, {col}) con handle {handle}")
                
                # Actualizar la representación visual del robot
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
            # Limpiar todos los handles guardados
            self.cube_handles = {}
            print("✅ Handles de cubos eliminados")

    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Header con título y estado de conexión
        header = QHBoxLayout()
        title = QLabel("Diseñador de Recorridos - Robot con CoppeliaSim (ZeroMQ)")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.status_label = QLabel("Estado: No conectado")
        self.status_label.setStyleSheet("color: red;")
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.status_label)
        layout.addLayout(header)

        # Botones de control de la cuadrícula
        grid_buttons = QHBoxLayout()
        self.end_button = QPushButton("Marcar Meta (B)")
        self.obstacle_button = QPushButton("Agregar Obstáculo")
        self.robot_button = QPushButton("Colocar Robot")
        self.save_button = QPushButton("Guardar Recorrido")
        self.reset_button = QPushButton("Restablecer")

        for btn in [self.end_button, self.obstacle_button, self.robot_button, 
                    self.save_button, self.reset_button]:
            grid_buttons.addWidget(btn)

        layout.addLayout(grid_buttons)

        # Configuración
        config = QHBoxLayout()
        self.scale_combo = QComboBox()
        self.scale_combo.addItems(["0.25", "0.5"])
        self.scale_combo.setCurrentText("0.5")

        self.robot_combo = QComboBox()
        self.robot_combo.addItems(["/PioneerP3DX"])

        self.zmq_port = QComboBox()
        self.zmq_port.addItems(["23000", "23001", "23002"])
        self.zmq_port.setCurrentText("23000")
        self.zmq_port.setEditable(True)

        config.addWidget(QLabel("Escala (m):"))
        config.addWidget(self.scale_combo)
        config.addWidget(QLabel("Robot:"))
        config.addWidget(self.robot_combo)
        config.addWidget(QLabel("Puerto ZeroMQ:"))
        config.addWidget(self.zmq_port)

        layout.addLayout(config)

        # Botones de conexión y ejecución
        sim_buttons = QHBoxLayout()
        self.connect_button = QPushButton("Conectar a CoppeliaSim")
        self.test_button = QPushButton("Probar Conexión")
        self.execute_button = QPushButton("Ejecutar Ruta en CoppeliaSim")
        self.execute_button.setEnabled(False)  # Se habilitará cuando esté conectado

        sim_buttons.addWidget(self.connect_button)
        sim_buttons.addWidget(self.test_button)
        sim_buttons.addWidget(self.execute_button)
        layout.addLayout(sim_buttons)

        # Botones de control de simulación
        sim_control_buttons = QHBoxLayout()
        self.play_button = QPushButton("▶️ Iniciar Simulación")
        self.pause_button = QPushButton("⏸️ Pausar Simulación")
        self.stop_button = QPushButton("⏹️ Detener Simulación")

        sim_control_buttons.addWidget(self.play_button)
        sim_control_buttons.addWidget(self.pause_button)
        sim_control_buttons.addWidget(self.stop_button)
        layout.addLayout(sim_control_buttons)

        # Barra de progreso
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Cuadrícula
        layout.addWidget(self.grid_widget)

        # Instrucciones
        instructions = QLabel("""
        Instrucciones:
        1. Conecte con CoppeliaSim usando el botón "Conectar a CoppeliaSim".
        2. Coloque el robot en cualquier posición (será el punto de inicio).
        3. Marque el punto B como destino.
        4. Si desea, agregue obstáculos.
        5. Presione "Ejecutar Ruta en CoppeliaSim" para que el robot se mueva al punto B.
        """)
        layout.addWidget(instructions)

        self.setLayout(layout)
        self.resize(600, 700)

    def agregar_robot_en_posicion(self, row, col):
        """Agrega un robot en la posición especificada"""
        if not self.is_connected:
            QMessageBox.warning(self, "No conectado", "Conéctate a CoppeliaSim antes de colocar el robot.")
            return
            
        # Si ya existe un robot, mostrar mensaje
        if self.robot_handle is not None:
            QMessageBox.information(self, "Robot ya existe", 
                                "Ya existe un robot en la escena. Restablece la cuadrícula para colocar otro.")
            return
            
        # Obtener el tipo de robot seleccionado
        robot_type = self.robot_combo.currentText()
        
        # Calcular posición en CoppeliaSim
        reference_scale = 0.5
        x = (col - GRID_SIZE/2 + 0.5) * reference_scale
        y = (GRID_SIZE/2 - row - 0.5) * reference_scale
        z = 0.15  # Ligeramente sobre el suelo
        
        position = [x, y, z]
        
        print(f"🤖 Colocando robot {robot_type} en fila {row}, columna {col} → Posición: {position}")
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(25)
        
        # Actualizar la UI inmediatamente
        self.robot_position = (row, col)
        self.grid_widget.update()
        
        # Crear el robot usando el worker
        self.sim_worker.set_task('create_robot', 
                            robot_type=robot_type, 
                            position=position, 
                            row=row, 
                            col=col)
        self.sim_worker.start()

    def agregar_cubo_en_posicion(self, row, col):
        """Agrega un cubo/obstáculo en la posición especificada"""
        if not self.is_connected:
            QMessageBox.warning(self, "No conectado", "Conéctate a CoppeliaSim antes de agregar obstáculos.")
            return

        # Calcular posición en CoppeliaSim
        reference_scale = 0.5
        x = (col - GRID_SIZE/2 + 0.5) * reference_scale
        y = (GRID_SIZE/2 - row - 0.5) * reference_scale
        z = 0.0  # Se ajustará automáticamente
        
        position = [x, y, z]
        
        # Definir el tamaño según la escala seleccionada
        cube_size = float(self.scale_combo.currentText()) * 0.8  # Factor 0.8 para que no ocupe toda la celda
        size = [cube_size, cube_size, cube_size]  # Cubo regular
        
        # Color gris para obstáculos
        color = [0.2, 0.2, 0.2]  # RGB (0-1)
        
        print(f"📊 Creando cubo en fila {row}, columna {col} → Posición: {position}, Tamaño: {size}")
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(25)
        
        # Verificar si ya existe un objeto en esta posición
        if (row, col) in self.cube_handles:
            old_handle = self.cube_handles[(row, col)]
            print(f"⚠️ Ya existe un objeto en ({row}, {col}), eliminándolo")
            
            try:
                self.sim_controller.sim.removeObjects([old_handle])
                del self.cube_handles[(row, col)]
                print(f"✅ Objeto anterior eliminado")
            except Exception as e:
                print(f"❌ Error al eliminar objeto anterior: {e}")
        
        # Crear el cubo
        handle = self.sim_controller.cargar_muro_personalizado(size, position, color)
        
        if handle is not None:
            self.cube_handles[(row, col)] = handle
            self.grid_manager.grid[row][col] = OBSTACLE
            self.grid_widget.update()
            print(f"✅ Cubo agregado en ({row}, {col}) con handle {handle}")
        else:
            print(f"❌ Error al crear cubo en posición ({row}, {col})")
        
        self.progress_bar.setValue(100)
        self.progress_bar.setVisible(False)

    def connect_signals(self):
        """Conecta todas las señales de la interfaz"""
        self.connect_button.clicked.connect(self.toggle_connection)
        self.test_button.clicked.connect(self.test_connection)
        self.obstacle_button.clicked.connect(lambda: self.set_mode('obstacle'))
        self.robot_button.clicked.connect(lambda: self.set_mode('robot'))
        self.end_button.clicked.connect(lambda: self.set_mode('end'))
        self.reset_button.clicked.connect(self.reset_grid)
        self.save_button.clicked.connect(self.save_grid)
        self.zmq_port.currentTextChanged.connect(self.update_zmq_port)
        
        # Configurar grid_widget para usar nuestro handler de eventos de mouse
        self.grid_widget.mousePressEvent = self.custom_mouse_press_event
        
        # Conectar los botones de control de simulación
        self.play_button.clicked.connect(lambda: self.sim_worker.set_task('start_sim') or self.sim_worker.start())
        self.pause_button.clicked.connect(lambda: self.sim_worker.set_task('pause_sim') or self.sim_worker.start())
        self.stop_button.clicked.connect(lambda: self.sim_worker.set_task('stop_sim') or self.sim_worker.start())
        
        # Conectar el botón de ejecutar ruta
        self.execute_button.clicked.connect(self.execute_route)
    
    def update_zmq_port(self):
        """Actualiza el puerto ZeroMQ en el controlador"""
        try:
            port = int(self.zmq_port.currentText())
            self.sim_controller.port = port
            print(f"Puerto ZeroMQ actualizado a: {port}")
        except ValueError:
            print("El puerto debe ser un número entero")

    def update_progress_bar(self, value):
        """Actualiza la barra de progreso"""
        self.progress_bar.setValue(value)
        QApplication.processEvents()  # Procesar eventos para actualizar la UI

    def update_connection_status_ui(self, is_connected):
        """Actualiza el estado de conexión en la UI"""
        self.is_connected = is_connected
        self.status_label.setText("Estado: Conectado" if is_connected else "Estado: No conectado")
        self.status_label.setStyleSheet("color: green;" if is_connected else "color: red;")
        self.connect_button.setText("Desconectar" if is_connected else "Conectar a CoppeliaSim")
        self.execute_button.setEnabled(is_connected)

    def toggle_connection(self):
        """Alterna entre conectar y desconectar"""
        if not self.is_connected:
            self.connect_to_coppelia()
        else:
            self.disconnect_from_coppelia()

    def connect_to_coppelia(self):
        """Conecta con CoppeliaSim"""
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
        """Desconecta de CoppeliaSim"""
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(50)
        self.sim_worker.set_task('disconnect')
        self.sim_worker.start()

    def test_connection(self):
        """Prueba la conexión con CoppeliaSim"""
        if not self.is_connected:
            QMessageBox.warning(self, "Advertencia", "No hay conexión con CoppeliaSim. Conéctese primero.")
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(50)
        self.sim_worker.set_task('test')
        self.sim_worker.start()

    def set_mode(self, mode):
        """Establece el modo de interacción con la cuadrícula"""
        self.grid_widget.mode = mode
        # Actualizar la apariencia de los botones según el modo seleccionado
        for btn_mode, button in {
            'end': self.end_button,
            'obstacle': self.obstacle_button,
            'robot': self.robot_button
        }.items():
            button.setStyleSheet("background-color: #a0e0a0;" if btn_mode == mode else "")

    def reset_grid(self):
        """Restablece la cuadrícula y elimina todos los objetos"""
        try:
            print("Iniciando restablecimiento de la cuadrícula...")
            
            # Resetear la cuadrícula en la interfaz
            self.grid_manager = GridManager()
            self.grid_widget.grid_manager = self.grid_manager
            self.grid_widget.update()
            
            # Si estamos conectados a CoppeliaSim, eliminar objetos
            if self.is_connected:
                # Detener la simulación primero
                try:
                    self.sim_controller.stop_simulation()
                    time.sleep(0.5)  # Esperar a que se detenga
                except Exception as e:
                    print(f"Advertencia al detener simulación: {e}")
                
                # Eliminar cubos
                print("Eliminando cubos...")
                positions = list(self.cube_handles.keys())
                for pos in positions:
                    try:
                        handle = self.cube_handles[pos]
                        try:
                            self.sim_controller.sim.getObjectPosition(handle, -1)
                            self.sim_controller.sim.removeObject(handle)
                            print(f"✅ Cubo en posición {pos} eliminado")
                        except:
                            print(f"Objeto {handle} en posición {pos} ya no existe")
                        
                        del self.cube_handles[pos]
                    except Exception as e:
                        print(f"Error al eliminar cubo en posición {pos}: {e}")
                
                # Eliminar el robot
                if self.robot_handle is not None:
                    try:
                        try:
                            self.sim_controller.sim.getObjectPosition(self.robot_handle, -1)
                            self.sim_controller.sim.removeObject(self.robot_handle)
                            print(f"✅ Robot eliminado (handle: {self.robot_handle})")
                        except:
                            print(f"Robot (handle: {self.robot_handle}) ya no existe")
                        
                        self.robot_handle = None
                        self.robot_position = None
                    except Exception as e:
                        print(f"Error al eliminar robot: {e}")
                
                print("✅ Proceso de restablecimiento completado")
            
            return True
                
        except Exception as e:
            print(f"❌ Error al restablecer la cuadrícula: {e}")
            return False

    def save_grid(self):
        """Guarda la configuración actual de la cuadrícula en un archivo CSV"""
        filename, _ = QFileDialog.getSaveFileName(self, "Guardar Recorrido", "", "CSV Files (*.csv)")
        if filename:
            self.grid_manager.export_to_csv(filename)
            QMessageBox.information(self, "Éxito", f"Recorrido guardado en {filename}")

    def custom_mouse_press_event(self, event):
        """Maneja el evento de clic en la cuadrícula"""
        col = event.x() // CELL_SIZE
        row = event.y() // CELL_SIZE

        if 0 <= row < GRID_SIZE and 0 <= col < GRID_SIZE:
            mode = self.grid_widget.mode
            
            if mode == 'end':
                # Establecer punto B (meta)
                self.grid_manager.clear_type(END)
                self.grid_manager.grid[row][col] = END
                self.grid_manager.end_set = True
                print(f"✅ Punto B (meta) establecido en ({row}, {col})")
            elif mode == 'obstacle':
                # Gestionar obstáculos
                if self.grid_manager.grid[row][col] == OBSTACLE:
                    # Eliminar obstáculo
                    if self.is_connected:
                        self.eliminar_cubo_en_posicion(row, col)
                    else:
                        self.grid_manager.grid[row][col] = EMPTY
                        self.grid_widget.update()
                else:
                    # Agregar obstáculo
                    self.grid_manager.grid[row][col] = OBSTACLE
                    
                    if self.is_connected:
                        self.agregar_cubo_en_posicion(row, col)
            elif mode == 'robot':
                # Colocar robot
                if self.is_connected:
                    # Verificar si la posición está disponible
                    if self.grid_manager.grid[row][col] != EMPTY and self.grid_manager.grid[row][col] != END:
                        QMessageBox.warning(self, "Posición ocupada", 
                                        "No se puede colocar el robot en una posición ocupada.")
                        return
                        
                    self.agregar_robot_en_posicion(row, col)

            self.grid_widget.update()

    def eliminar_cubo_en_posicion(self, row, col):
        """Elimina un cubo específico por su posición"""
        if not self.is_connected:
            QMessageBox.warning(self, "No conectado", "Conéctate a CoppeliaSim antes de eliminar obstáculos.")
            return
        
        handle = self.cube_handles.get((row, col))
        if handle is None:
            print(f"⚠️ No se encontró handle para la posición ({row}, {col})")
            return
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(25)
        
        try:
            self.sim_controller.sim.removeObject(handle)
            del self.cube_handles[(row, col)]
            self.grid_manager.grid[row][col] = EMPTY
            self.grid_widget.update()
            print(f"✅ Cubo en posición ({row}, {col}) eliminado")
        except Exception as e:
            print(f"❌ Error al eliminar cubo: {e}")
        
        self.progress_bar.setValue(100)
        self.progress_bar.setVisible(False)

    def execute_route(self):
        """Ejecuta el recorrido desde la posición del robot hasta el punto B"""
        if not self.is_connected:
            QMessageBox.warning(self, "No conectado", "Conéctate a CoppeliaSim primero.")
            return
        
        # Verificar que tenemos un robot 
        if self.robot_handle is None or self.robot_position is None:
            QMessageBox.warning(self, "Falta robot", "Coloca un robot en la escena primero.")
            return
        
        # Obtener el punto de destino (B)
        end_pos = None
        obstacles = []
        
        for row in range(GRID_SIZE):
            for col in range(GRID_SIZE):
                cell_value = self.grid_manager.grid[row][col]
                
                if cell_value == END:
                    end_pos = (row, col)
                elif cell_value == OBSTACLE:
                    obstacles.append((row, col))
        
        if end_pos is None:
            QMessageBox.warning(self, "Falta meta", "Marca un punto meta (B) primero.")
            return
        
        # Usar la posición actual del robot como punto de inicio
        start_pos = self.robot_position
        
        # Mostrar información del recorrido
        print(f"🚀 Iniciando recorrido desde el robot en {start_pos} hasta el punto B en {end_pos}")
        print(f"Evitando {len(obstacles)} obstáculos")
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(25)
        
        # Iniciar la simulación si no está en ejecución
        try:
            sim_state = self.sim_controller.sim.getSimulationState()
            if sim_state != 1:  # 1 = simulación en ejecución
                print("Iniciando simulación automáticamente...")
                self.sim_controller.sim.startSimulation()
                QApplication.processEvents()
                time.sleep(0.5)
        except Exception as e:
            print(f"Error al iniciar simulación: {e}")
        
        self.progress_bar.setValue(50)
        
        # Ejecutar el recorrido usando el método de ejecución de ruta disponible
        # en lugar de navigate_to_target que aún no existe
        success = self.sim_controller.execute_path(start_pos, end_pos, obstacles)
        
        self.progress_bar.setValue(100)
        self.progress_bar.setVisible(False)
        
        if success:
            QMessageBox.information(self, "Éxito", "Recorrido iniciado. El robot está en movimiento hacia el punto B.")
        else:
            QMessageBox.warning(self, "Error", "No se pudo iniciar el recorrido. Verifica la consola para más detalles.")