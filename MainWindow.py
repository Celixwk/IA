from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLabel, QFileDialog, QMessageBox, QComboBox, 
                            QProgressBar, QApplication)
from PyQt5.QtCore import Qt, QPoint, QTimer, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QBrush, QPen
from GridManager import GridManager
from GridWidget import GridWidget
from CoppeliaSimController import CoppeliaSimController
from CoppeliaSimWorker import CoppeliaSimWorker
from constants import CELL_SIZE, GRID_SIZE, EMPTY, START, END, PATH, OBSTACLE, ROBOT
import time

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Diseñador de Recorridos - Robot con CoppeliaSim (ZeroMQ)")
        
        # Inicializar variables para la gestión de objetos
        self.grid_manager = GridManager()
        self.grid_widget = GridWidget(self.grid_manager)
        self.selected_object = None
        self.selected_position = None
        self.robot_handle = None
        self.robot_position = None
        self.goal_handle = None
        self.goal_position = None
        self.objects = {}  # Diccionario para mapear posiciones (row, col) a handles de objetos
        
        # Inicializar el controlador con ZeroMQ
        self.sim_controller = CoppeliaSimController(host="localhost", port=23000)
        self.sim_worker = CoppeliaSimWorker(self.sim_controller)
        self.sim_worker.connection_status.connect(self.update_connection_status)
        
        # Configurar la interfaz de usuario
        self.setup_ui()
        self.connect_signals()

    def setup_ui(self):
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        
        # Sección de título
        title_layout = QHBoxLayout()
        title = QLabel("Diseñador de Recorridos - Robot con CoppeliaSim (ZeroMQ)")
        self.connection_status = QLabel("Estado: No conectado")
        self.connection_status.setStyleSheet("color: red;")
        title_layout.addWidget(title)
        title_layout.addStretch()
        title_layout.addWidget(self.connection_status)
        main_layout.addLayout(title_layout)
        
        # Controles principales
        controls_layout = QHBoxLayout()
        self.add_obstacle_button = QPushButton("Agregar Obstáculo")
        self.select_button = QPushButton("Seleccionar Objeto")
        self.delete_button = QPushButton("Eliminar Selección")  # Este es el botón que faltaba
        self.save_button = QPushButton("Guardar Recorrido")
        self.reset_button = QPushButton("Restablecer")
        self.detect_button = QPushButton("Detectar Objetos")
        
        for btn in [self.add_obstacle_button, self.delete_button, 
                    self.select_button, self.save_button, 
                    self.reset_button, self.detect_button]:
            controls_layout.addWidget(btn)
        
        main_layout.addLayout(controls_layout)
        
        # Configuración
        config_layout = QHBoxLayout()
        self.scale_combo = QComboBox()
        self.scale_combo.addItems(["0.25", "0.5", "1.0"])
        self.scale_combo.setCurrentText("0.5")
        
        config_layout.addWidget(QLabel("Escala (m):"))
        config_layout.addWidget(self.scale_combo)
        
        # Puerto ZeroMQ
        config_layout.addWidget(QLabel("Puerto ZeroMQ:"))
        self.port_combo = QComboBox()
        self.port_combo.addItems(["23000", "23001"])
        self.port_combo.setEditable(True)
        config_layout.addWidget(self.port_combo)
        
        main_layout.addLayout(config_layout)
        
        # Conexión y Simulación
        conn_layout = QHBoxLayout()
        self.connect_button = QPushButton("Conectar a CoppeliaSim")
        self.execute_button = QPushButton("Ejecutar Ruta en CoppeliaSim")
        
        conn_layout.addWidget(self.connect_button)
        conn_layout.addWidget(self.execute_button)
        
        main_layout.addLayout(conn_layout)
        
        # Controles de simulación
        sim_layout = QHBoxLayout()
        self.start_sim_button = QPushButton("▶️ Iniciar Simulación")
        self.pause_sim_button = QPushButton("⏸️ Pausar Simulación")
        self.stop_sim_button = QPushButton("⏹️ Detener Simulación")
        
        sim_layout.addWidget(self.start_sim_button)
        sim_layout.addWidget(self.pause_sim_button)
        sim_layout.addWidget(self.stop_sim_button)
        
        main_layout.addLayout(sim_layout)
        
        # Barra de progreso
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
           
        
        # Grid Widget (visualización de la cuadrícula)
        main_layout.addWidget(self.grid_widget)
        
        # Instrucciones
        instructions = QLabel("""
        Instrucciones:
        1. Conecte con CoppeliaSim usando el botón "Conectar a CoppeliaSim".
        2. Use "Detectar Objetos" para encontrar los elementos existentes en la escena.
        3. Use "Seleccionar Objeto" para elegir y mover elementos en la escena.
        4. Marque la Meta (B) para establecer el destino.
        5. Presione "Ejecutar Ruta en CoppeliaSim" para que el robot se mueva al destino.
        """)
        main_layout.addWidget(instructions)
        
        self.setLayout(main_layout)
        self.resize(800, 700)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("border-top: 1px solid #999; padding: 3px;")
        main_layout.addWidget(self.status_label) 
        
        
    def connect_signals(self):
        # Botones de acción
        self.connect_button.clicked.connect(self.toggle_connection)
        self.add_obstacle_button.clicked.connect(lambda: self.set_mode('obstacle'))
        self.select_button.clicked.connect(lambda: self.set_mode('select'))
        self.delete_button.clicked.connect(self.remove_selected_object)
        self.reset_button.clicked.connect(self.reset_grid)
        self.save_button.clicked.connect(self.save_grid)
        self.detect_button.clicked.connect(self.detect_scene_objects)
        
        # Botones de simulación
        self.start_sim_button.clicked.connect(self.start_simulation)
        self.pause_sim_button.clicked.connect(self.pause_simulation)
        self.stop_sim_button.clicked.connect(self.stop_simulation)
        
        # Custom mouse press event para el grid widget
        self.grid_widget.mousePressEvent = self.custom_mouse_press_event
        
    def update_connection_status(self, connected):
        """Actualiza el estado de la conexión en la interfaz"""
        self.is_connected = connected
        self.connection_status.setText("Estado: Conectado" if connected else "Estado: No conectado")
        self.connection_status.setStyleSheet("color: green;" if connected else "color: red;")
        self.connect_button.setText("Desconectar" if connected else "Conectar a CoppeliaSim")
        
        if connected:
            # Si acabamos de conectar, detectar objetos en la escena
            QTimer.singleShot(500, self.detect_scene_objects)
    
    def toggle_connection(self):
        """Alterna entre conectar y desconectar de CoppeliaSim"""
        if not hasattr(self, 'is_connected') or not self.is_connected:
            self.connect_to_coppelia()
        else:
            self.disconnect_from_coppelia()
    
    def connect_to_coppelia(self):
        """Establece conexión con CoppeliaSim"""
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(20)
        QApplication.processEvents()
        
        try:
            # Actualizar el puerto según la selección actual
            port = int(self.port_combo.currentText())
            self.sim_controller.port = port
            
            # Intentar conectar
            success = self.sim_controller.connect()
            
            if success:
                self.is_connected = True
                self.update_connection_status(True)
                self.execute_button.setEnabled(True)
                
                # Detectar objetos automáticamente
                self.detect_scene_objects()
            else:
                self.is_connected = False
                self.update_connection_status(False)
                QMessageBox.warning(self, "Error de conexión", 
                                   "No se pudo conectar a CoppeliaSim. Verifica que el simulador esté en ejecución.")
        
        except Exception as e:
            self.is_connected = False
            self.update_connection_status(False)
            QMessageBox.warning(self, "Error de conexión", str(e))
        
        finally:
            self.progress_bar.setValue(100)
            self.progress_bar.setVisible(False)
    
    def disconnect_from_coppelia(self):
        """Cierra la conexión con CoppeliaSim"""
        if hasattr(self, 'is_connected') and self.is_connected:
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(20)
            QApplication.processEvents()
            
            try:
                success = self.sim_controller.disconnect()
                
                if success:
                    self.is_connected = False
                    self.update_connection_status(False)
                    self.execute_button.setEnabled(False)
                else:
                    QMessageBox.warning(self, "Error", "No se pudo desconectar correctamente de CoppeliaSim.")
            
            except Exception as e:
                QMessageBox.warning(self, "Error de desconexión", str(e))
            
            finally:
                self.progress_bar.setValue(100)
                self.progress_bar.setVisible(False)
    
    def clean_interface(self):
        """Limpia la representación de obstáculos en la interfaz sin tocar el robot ni la meta"""
        # Limpiar objetos que no son robot ni meta
        positions_to_remove = []
        
        for position, handle in self.objects.items():
            # Si no es robot ni meta, eliminar
            if (hasattr(self, 'robot_handle') and handle == self.robot_handle) or \
            (hasattr(self, 'goal_handle') and handle == self.goal_handle):
                continue
            
            positions_to_remove.append(position)
        
        # Eliminar posiciones
        for position in positions_to_remove:
            row, col = position
            # Limpiar cuadrícula
            if self.grid_manager.grid[row][col] == OBSTACLE:
                self.grid_manager.grid[row][col] = EMPTY
            # Eliminar del diccionario
            del self.objects[position]
        
        # Limpiar obstáculos en grid_widget
        if hasattr(self.grid_widget, 'obstacles'):
            self.grid_widget.obstacles = []
        
        # Actualizar visualización
        self.grid_widget.update()
        
        print(f"Interfaz limpiada: {len(positions_to_remove)} obstáculos eliminados de la representación")

    def get_all_scene_objects(self):
        """Obtiene todos los objetos visibles en la escena de CoppeliaSim"""
        if not self.is_connected:
            return []
        
        try:
            scene_objects = []
            
            # Método 1: Usar funciones específicas para obtener diferentes tipos de objetos
            try:
                # Obtener handles de distintos tipos de objetos
                shape_objects = self.sim_controller.sim.getShapes()
                joint_objects = self.sim_controller.sim.getJoints()
                dummy_objects = self.sim_controller.sim.getDummies()
                
                # Combinar todos los handles
                scene_objects = shape_objects + joint_objects + dummy_objects
                print(f"Método 1: Encontrados {len(scene_objects)} objetos")
            except Exception as e:
                print(f"Error en método 1: {e}")
                scene_objects = []
            
            # Si no funcionó, probar con otro método
            if not scene_objects:
                try:
                    # Método 2: Usar getObjects con diferentes filtros
                    for i in range(100):  # Límite razonable
                        try:
                            obj = self.sim_controller.sim.getObject(".", i)
                            if obj != -1:
                                scene_objects.append(obj)
                        except:
                            pass
                    
                    print(f"Método 2: Encontrados {len(scene_objects)} objetos")
                except Exception as e:
                    print(f"Error en método 2: {e}")
            
            # Si aún no tenemos nada, intentar con nombres específicos
            if not scene_objects:
                print("Buscando por nombres específicos")
                
                # Lista de nombres comunes en la escena mobileRobotPathPlanning
                specific_objects = [
                    "/mobileRobot", "mobileRobot",
                    "/goalDummy", "goalDummy",
                    "/Obstacle", "Obstacle",
                    "/Cuboid", "Cuboid",
                    "/Floor", "Floor"
                ]
                
                for name in specific_objects:
                    try:
                        obj = self.sim_controller.sim.getObject(name)
                        if obj != -1 and obj not in scene_objects:
                            scene_objects.append(obj)
                            print(f"Objeto encontrado por nombre: {name}")
                    except:
                        pass
            
            return scene_objects
            
        except Exception as e:
            print(f"Error al obtener objetos de la escena: {e}")
            return []

    def detect_scene_objects(self):
        """Detecta todos los objetos de la escena de CoppeliaSim en un solo paso"""
        if not self.is_connected:
            print("No hay conexión con CoppeliaSim. Conéctate primero.")
            return
        
        print("Detectando TODOS los objetos en la escena...")
        
        try:
            # Limpiar la interfaz primero
            self.clean_interface()
            
            # Variables para conteo
            robot_detected = False
            goal_detected = False
            obstacles_found = 0
            
            # Obtener TODOS los objetos visibles en la escena
            all_objects = []
            
            # Método 1: Obtener todos los objetos con handleSerialization
            try:
                # Primero intentar con getObjects para obtener todos los objetos
                all_objects = []
                i = 0
                while True:
                    try:
                        handle = self.sim_controller.sim.getObjects(i)
                        if handle != -1:
                            all_objects.append(handle)
                            i += 1
                        else:
                            break
                    except:
                        break
                        
                if not all_objects:
                    # Si no funcionó, intentar otro método
                    try:
                        # Obtener handles por tipo
                        shapes = self.sim_controller.sim.getShapes()
                        joints = self.sim_controller.sim.getJoints()
                        dummies = self.sim_controller.sim.getDummies()
                        
                        # Combinar todos los handles
                        all_objects = shapes + joints + dummies
                    except:
                        pass
            except Exception as e:
                print(f"Error al obtener objetos con método 1: {e}")
            
            # Si aún no hay objetos, probar con nombres específicos conocidos
            if not all_objects:
                print("Probando búsqueda directa por nombres conocidos...")
                
                # Lista de patrones de nombres a buscar
                name_patterns = [
                    "/mobileRobot", "mobileRobot",
                    "/goalDummy", "goalDummy",
                    "/Obstacle", "Obstacle", 
                    "/Cylinder", "Cylinder",
                    "/Cuboid", "Cuboid",
                    "/Box", "Box",
                    "/Wall", "Wall"
                ]
                
                # Para obstáculos numerados
                for base_name in ["Cuboid", "Obstacle", "Box", "Wall"]:
                    for i in range(10):  # Buscar hasta 10 instancias numeradas
                        name_patterns.append(f"/{base_name}{i}")
                        name_patterns.append(f"{base_name}{i}")
                
                # Buscar objetos con estos nombres
                for name in name_patterns:
                    try:
                        handle = self.sim_controller.sim.getObject(name)
                        if handle != -1 and handle not in all_objects:
                            all_objects.append(handle)
                            print(f"Objeto encontrado por nombre: {name}")
                    except:
                        pass
            
            print(f"Se encontraron {len(all_objects)} objetos en total")
            
            # Si aún no hay objetos, algo está mal
            if not all_objects:
                print("⚠️ No se pudieron detectar objetos en la escena.")
                return
            
            # Procesar todos los objetos encontrados
            for obj in all_objects:
                try:
                    # Obtener nombre, tipo y posición
                    obj_name = self.sim_controller.sim.getObjectAlias(obj, 1)
                    obj_type = self.sim_controller.sim.getObjectType(obj)
                    obj_pos = self.sim_controller.sim.getObjectPosition(obj, -1)
                    
                    # Convertir posición a coordenadas de cuadrícula
                    reference_scale = float(self.scale_combo.currentText())
                    col = int((obj_pos[0] / reference_scale) + GRID_SIZE/2 - 0.5)
                    row = int(GRID_SIZE/2 - (obj_pos[1] / reference_scale) - 0.5)
                    
                    # Asegurar que está dentro de los límites
                    if not (0 <= row < GRID_SIZE and 0 <= col < GRID_SIZE):
                        # Está fuera de los límites de la cuadrícula
                        continue
                    
                    print(f"Procesando objeto: {obj_name}, tipo: {obj_type}, posición: ({row}, {col})")
                    
                    # Clasificar el objeto según su nombre y tipo
                    obj_name_lower = obj_name.lower()
                    
                    # 1. Detectar ROBOT
                    if not robot_detected and ('robot' in obj_name_lower or 'mobile' in obj_name_lower):
                        self.robot_handle = obj
                        self.robot_position = (row, col)
                        self.objects[(row, col)] = obj
                        if hasattr(self.grid_widget, 'robot_pos'):
                            self.grid_widget.robot_pos = (row, col)
                        print(f"Robot detectado: {obj_name} en ({row}, {col})")
                        robot_detected = True
                        continue
                    
                    # 2. Detectar META
                    if not goal_detected and ('goal' in obj_name_lower or 'dummy' in obj_name_lower or 'target' in obj_name_lower):
                        self.goal_handle = obj
                        self.goal_position = (row, col)
                        self.grid_manager.clear_type(END)
                        self.grid_manager.grid[row][col] = END
                        self.grid_manager.end_set = True
                        self.objects[(row, col)] = obj
                        if hasattr(self.grid_widget, 'meta_pos'):
                            self.grid_widget.meta_pos = (row, col)
                        print(f"Meta detectada: {obj_name} en ({row}, {col})")
                        goal_detected = True
                        continue
                    
                    # 3. Detectar OBSTÁCULOS
                    # Primero, verificar si la celda ya está ocupada
                    if self.grid_manager.grid[row][col] != EMPTY:
                        continue
                    
                    # Considerar como obstáculo si:
                    # - Es una forma (type = 3)
                    # - O su nombre indica que es un obstáculo
                    is_obstacle = False
                    
                    if obj_type == 3:  # Shape (forma)
                        is_obstacle = True
                    elif any(name in obj_name_lower for name in ['cuboid', 'obstacle', 'box', 'wall', 'muro']):
                        is_obstacle = True
                    
                    if is_obstacle:
                        # Marcar como obstáculo en el grid_manager
                        self.grid_manager.grid[row][col] = OBSTACLE
                        self.objects[(row, col)] = obj
                        
                        # Añadir a la lista de obstáculos del grid_widget
                        if not hasattr(self.grid_widget, 'obstacles'):
                            self.grid_widget.obstacles = []
                        if (row, col) not in self.grid_widget.obstacles:
                            self.grid_widget.obstacles.append((row, col))
                        
                        obstacles_found += 1
                        print(f"Obstáculo detectado: {obj_name} en ({row}, {col})")
                
                except Exception as e:
                    print(f"Error al procesar objeto {obj}: {e}")
            
            # Si no se ha detectado el robot o la meta, pero teníamos referencias anteriores, mantenerlas
            if not robot_detected and hasattr(self, 'robot_handle') and self.robot_handle is not None:
                try:
                    # Verificar si sigue existiendo
                    self.sim_controller.sim.getObjectPosition(self.robot_handle, -1)
                    print("Se mantiene la referencia al robot anterior")
                    robot_detected = True
                except:
                    self.robot_handle = None
                    self.robot_position = None
                    print("La referencia anterior al robot ya no es válida")
            
            if not goal_detected and hasattr(self, 'goal_handle') and self.goal_handle is not None:
                try:
                    # Verificar si sigue existiendo
                    self.sim_controller.sim.getObjectPosition(self.goal_handle, -1)
                    print("Se mantiene la referencia a la meta anterior")
                    goal_detected = True
                except:
                    self.goal_handle = None
                    self.goal_position = None
                    self.grid_manager.clear_type(END)
                    self.grid_manager.end_set = False
                    print("La referencia anterior a la meta ya no es válida")
            
            # Actualizar directamente la visualización del grid_widget
            if hasattr(self, 'robot_position') and self.robot_position:
                self.grid_widget.robot_pos = self.robot_position
            
            if hasattr(self, 'goal_position') and self.goal_position:
                self.grid_widget.meta_pos = self.goal_position
            
            # Actualizar los obstáculos
            self.grid_widget.obstacles = []
            for position, handle in self.objects.items():
                if (hasattr(self, 'robot_handle') and handle == self.robot_handle) or \
                (hasattr(self, 'goal_handle') and handle == self.goal_handle):
                    continue
                self.grid_widget.obstacles.append(position)
            
            # Forzar actualización visual
            self.grid_widget.update()
            
            # Mostrar resumen
            if not robot_detected and not goal_detected:
                print("⚠️ No se detectaron el robot ni la meta en la escena.")
            elif not robot_detected:
                print("⚠️ No se detectó el robot en la escena.")
            elif not goal_detected:
                print("⚠️ No se detectó la meta en la escena.")
            else:
                print(f"✅ Detección completada: Robot, Meta y {obstacles_found} obstáculos encontrados.")
            
        except Exception as e:
            print(f"Error general al detectar objetos: {e}")
            import traceback
            traceback.print_exc()

    def update_grid_visualization(self):
        """Actualiza la visualización de la cuadrícula para mostrar correctamente todos los objetos"""
        # 1. Actualizar el robot
        if hasattr(self, 'robot_position') and self.robot_position:
            self.grid_widget.robot_pos = self.robot_position
        
        # 2. Actualizar la meta
        if hasattr(self, 'goal_position') and self.goal_position:
            row, col = self.goal_position
            self.grid_manager.clear_type(END)
            self.grid_manager.grid[row][col] = END
            self.grid_manager.end_set = True
            self.grid_widget.meta_pos = self.goal_position
        
        # 3. Actualizar obstáculos
        self.grid_widget.obstacles = []
        for position, handle in self.objects.items():
            if handle != self.robot_handle and handle != self.goal_handle:
                row, col = position
                self.grid_manager.grid[row][col] = OBSTACLE
                if position not in self.grid_widget.obstacles:
                    self.grid_widget.obstacles.append(position)
        
        # 4. Forzar redibujado
        self.grid_widget.update()
    
    def set_mode(self, mode):
        """Establece el modo de interacción con la cuadrícula"""
        # Guardar el modo anterior para poder restaurarlo si es necesario
        old_mode = self.grid_widget.mode
        
        # Establecer el nuevo modo
        self.grid_widget.mode = mode
        
        # Actualizar la apariencia de los botones (solo los que existen)
        buttons = {
            'obstacle': self.add_obstacle_button,
            'select': self.select_button
        }
        
        for btn_mode, button in buttons.items():
            button.setStyleSheet("background-color: #aaffaa;" if btn_mode == mode else "")
        
        # Limpiar la selección actual si cambiamos de modo
        if mode != 'move' and mode != old_mode:
            self.selected_object = None
            self.selected_position = None
        
        # Mostrar el modo actual
        mode_names = {
            'select': "Seleccionar objeto",
            'move': "Mover objeto",
            'obstacle': "Agregar obstáculo"
        }
        
        print(f"Modo: {mode_names.get(mode, mode)}")
    
    def custom_mouse_press_event(self, event):
        """Maneja eventos de clic de ratón según el modo activo"""
        col = event.x() // CELL_SIZE
        row = event.y() // CELL_SIZE
        
        if 0 <= row < GRID_SIZE and 0 <= col < GRID_SIZE:
            mode = self.grid_widget.mode
            
            # MODO SELECCIONAR
            if mode == 'select':
                # Intentar seleccionar un objeto en la posición del clic
                self.select_object_at_position(row, col)
            
            # MODO MOVER OBJETO SELECCIONADO
            elif mode == 'move' and hasattr(self, 'selected_object') and self.selected_object:
                # Mover el objeto seleccionado a la nueva posición
                self.move_selected_object(row, col)
                # Volver al modo seleccionar después de mover
                self.grid_widget.mode = 'select'
                self.select_button.setStyleSheet("background-color: #aaffaa;")
            
            # MODO MARCAR META
            elif mode == 'meta':
                # Establecer la meta en la posición del clic
                self.set_meta_point(row, col)
            
            # MODO AGREGAR OBSTÁCULO
            elif mode == 'obstacle':
                # Agregar obstáculo en la posición del clic
                self.add_obstacle(row, col)
            
            # MODO COLOCAR ROBOT
            elif mode == 'robot':
                # Colocar o mover el robot a la posición del clic
                self.place_robot(row, col)
            
            # Actualizar la visualización
            self.grid_widget.update()

    def select_object_at_position(self, row, col):
        """Selecciona un objeto en la posición de cuadrícula especificada"""
        if not self.is_connected:
            return
        
        found_object = False
        
        # Comprobar si hay robot en esta posición
        if hasattr(self, 'robot_position') and self.robot_position and self.robot_position == (row, col):
            self.selected_object = self.robot_handle
            self.selected_position = (row, col)
            found_object = True
            object_type = "Robot"
        
        # Comprobar si hay meta en esta posición
        elif self.grid_manager.grid[row][col] == END and hasattr(self, 'goal_handle') and self.goal_handle:
            self.selected_object = self.goal_handle
            self.selected_position = (row, col)
            found_object = True
            object_type = "Meta"
        
        # Comprobar si hay obstáculo en esta posición
        elif self.grid_manager.grid[row][col] == OBSTACLE:
            # Buscar el handle del obstáculo
            if (row, col) in self.objects:
                self.selected_object = self.objects[(row, col)]
                self.selected_position = (row, col)
                found_object = True
                object_type = "Obstáculo"
        
        # Si encontramos un objeto, mostrar información y cambiar a modo mover
        if found_object:
            # Cambiar al modo mover para permitir que el siguiente clic mueva el objeto
            self.grid_widget.mode = 'move'
            
            # Desactivar resaltado de todos los botones
            # NOTA: Solo usar los botones que existen
            self.select_button.setStyleSheet("")
            self.add_obstacle_button.setStyleSheet("")
            # No usar self.meta_button ni self.place_robot_button porque ya no existen
            
            # Mostrar información en consola
            print(f"Objeto seleccionado: {object_type}. Haz clic en otra posición para moverlo.")
            
            return True
        else:
            # No se encontró objeto, mostrar mensaje
            print("No hay objeto en esta posición")
            self.selected_object = None
            self.selected_position = None
            return False
    
    def set_meta_point(self, row, col):
        """Establece el punto meta (B) y mueve el cilindro blanco en CoppeliaSim"""
        # Marcar en la cuadrícula
        self.grid_manager.clear_type(END)
        self.grid_manager.grid[row][col] = END
        self.grid_manager.end_set = True
        
        # Si estamos conectados, mover también el objeto en CoppeliaSim
        if hasattr(self, 'is_connected') and self.is_connected and hasattr(self, 'goal_handle') and self.goal_handle is not None:
            try:
                # Convertir coordenadas de cuadrícula a CoppeliaSim
                reference_scale = float(self.scale_combo.currentText())
                x = (col - GRID_SIZE/2 + 0.5) * reference_scale
                y = (GRID_SIZE/2 - row - 0.5) * reference_scale
                
                # Mantener la altura Z original
                current_pos = self.sim_controller.sim.getObjectPosition(self.goal_handle, -1)
                z = current_pos[2]
                
                # Mover el objeto
                self.sim_controller.sim.setObjectPosition(self.goal_handle, -1, [x, y, z])
                
                # Actualizar la referencia
                self.goal_position = (row, col)
                self.objects[(row, col)] = self.goal_handle
                
                print(f"Meta movida a: {row}, {col} -> {[x, y, z]}")
            except Exception as e:
                print(f"Error al mover meta: {e}")
    
    def add_obstacle(self, row, col):
        """Agrega un obstáculo en la posición especificada"""
        # Solo permitir agregar obstáculos si estamos conectados
        if not hasattr(self, 'is_connected') or not self.is_connected:
            QMessageBox.warning(self, "No conectado", "Conecta a CoppeliaSim antes de agregar obstáculos.")
            return
        
        # Verificar si la celda está vacía
        if self.grid_manager.grid[row][col] != EMPTY:
            # Si ya hay un obstáculo, preguntar si quiere eliminarlo
            if self.grid_manager.grid[row][col] == OBSTACLE:
                reply = QMessageBox.question(self, "Eliminar obstáculo", 
                                           "Ya existe un obstáculo en esta posición. ¿Deseas eliminarlo?",
                                           QMessageBox.Yes | QMessageBox.No)
                if reply == QMessageBox.Yes:
                    # Eliminar el obstáculo existente
                    self.remove_obstacle(row, col)
            return
        
        try:
            # Convertir coordenadas de cuadrícula a CoppeliaSim
            reference_scale = float(self.scale_combo.currentText())
            x = (col - GRID_SIZE/2 + 0.5) * reference_scale
            y = (GRID_SIZE/2 - row - 0.5) * reference_scale
            z = 0.05  # Altura del obstáculo
            
            # Crear el obstáculo (cubo)
            size = [reference_scale * 0.8, reference_scale * 0.8, 0.1]  # Tamaño del obstáculo
            position = [x, y, z]
            color = [0.2, 0.2, 0.2]  # Gris
            
            # Crear el obstáculo en CoppeliaSim
            handle = self.sim_controller.cargar_muro_personalizado(size, position, color)
            
            if handle is not None:
                # Actualizar la cuadrícula
                self.grid_manager.grid[row][col] = OBSTACLE
                # Guardar la referencia
                self.objects[(row, col)] = handle
                
                print(f"Obstáculo creado en: {row}, {col} -> {position} con handle {handle}")
                self.grid_widget.update()
                
                return True
            else:
                print("Error al crear obstáculo")
                return False
            
        except Exception as e:
            print(f"Error al agregar obstáculo: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def remove_obstacle(self, row, col):
        """Elimina un obstáculo de la posición especificada"""
        if not hasattr(self, 'is_connected') or not self.is_connected:
            return
        
        if (row, col) in self.objects:
            handle = self.objects[(row, col)]
            try:
                # Eliminar el objeto en CoppeliaSim
                self.sim_controller.sim.removeObject(handle)
                # Actualizar la cuadrícula
                self.grid_manager.grid[row][col] = EMPTY
                # Eliminar la referencia
                del self.objects[(row, col)]
                
                print(f"Obstáculo eliminado: {row}, {col}")
                return True
            except Exception as e:
                print(f"Error al eliminar obstáculo: {e}")
                return False
        return False
    
    def place_robot(self, row, col):
        """Coloca o mueve el robot a la posición especificada"""
        if not hasattr(self, 'is_connected') or not self.is_connected:
            QMessageBox.warning(self, "No conectado", "Conecta a CoppeliaSim antes de colocar el robot.")
            return
        
        # Verificar si ya tenemos un robot
        if not hasattr(self, 'robot_handle') or self.robot_handle is None:
            QMessageBox.warning(self, "Robot no encontrado", 
                              "No se ha detectado un robot en la escena. Usa 'Detectar Objetos' primero.")
            return
        
        try:
            # Convertir coordenadas de cuadrícula a CoppeliaSim
            reference_scale = float(self.scale_combo.currentText())
            x = (col - GRID_SIZE/2 + 0.5) * reference_scale
            y = (GRID_SIZE/2 - row - 0.5) * reference_scale
            
            # Mantener la altura Z original
            current_pos = self.sim_controller.sim.getObjectPosition(self.robot_handle, -1)
            z = current_pos[2]
            
            # Mover el robot
            self.sim_controller.sim.setObjectPosition(self.robot_handle, -1, [x, y, z])
            
            # Actualizar la posición en la interfaz
            if hasattr(self, 'robot_position') and self.robot_position is not None:
                old_row, old_col = self.robot_position
                # Limpiar la posición anterior si es necesario
                if (old_row, old_col) in self.objects and self.objects[(old_row, old_col)] == self.robot_handle:
                    del self.objects[(old_row, old_col)]
            
            # Guardar la nueva posición
            self.robot_position = (row, col)
            self.objects[(row, col)] = self.robot_handle
            
            print(f"Robot movido a: {row}, {col} -> {[x, y, z]}")
            self.grid_widget.update()
            
            return True
            
        except Exception as e:
            print(f"Error al colocar robot: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def select_object(self, row, col):
        """Selecciona un objeto en la posición indicada"""
        # Verificar si hay un objeto en esta posición
        if (row, col) in self.objects:
            handle = self.objects[(row, col)]
            
            try:
                # Guardar la selección
                self.selected_object = handle
                self.selected_position = (row, col)
                
                # Identificar qué tipo de objeto es
                obj_type = "desconocido"
                if handle == self.robot_handle:
                    obj_type = "Robot"
                elif handle == self.goal_handle:
                    obj_type = "Meta"
                elif self.grid_manager.grid[row][col] == OBSTACLE:
                    obj_type = "Obstáculo"
                
                # Mostrar información
                position = self.sim_controller.sim.getObjectPosition(handle, -1)
                QMessageBox.information(self, "Objeto seleccionado", 
                                      f"Tipo: {obj_type}\nPosición: {position}\n\n"
                                      f"Puedes mover este objeto haciendo clic en otra celda.")
                
                # Cambiar al modo de movimiento
                self.grid_widget.mode = 'move'
                
                return True
            except Exception as e:
                print(f"Error al seleccionar objeto: {e}")
        else:
            # Comprobar si hay un objeto cercano a esta posición
            reference_scale = float(self.scale_combo.currentText())
            x = (col - GRID_SIZE/2 + 0.5) * reference_scale
            y = (GRID_SIZE/2 - row - 0.5) * reference_scale
            
            nearest_handle = None
            min_distance = float('inf')
            
            # Buscar el objeto más cercano
            for (r, c), handle in self.objects.items():
                try:
                    obj_pos = self.sim_controller.sim.getObjectPosition(handle, -1)
                    dist = ((obj_pos[0] - x)**2 + (obj_pos[1] - y)**2)**0.5
                    
                    if dist < min_distance:
                        min_distance = dist
                        nearest_handle = handle
                        nearest_pos = (r, c)
                except:
                    pass
            
            # Si encontramos un objeto cercano, seleccionarlo
            if nearest_handle is not None and min_distance < 0.5 * reference_scale:
                self.selected_object = nearest_handle
                self.selected_position = nearest_pos
                
                # Identificar qué tipo de objeto es
                obj_type = "desconocido"
                if nearest_handle == self.robot_handle:
                    obj_type = "Robot"
                elif nearest_handle == self.goal_handle:
                    obj_type = "Meta"
                else:
                    obj_type = "Obstáculo"
                
                # Mostrar información
                QMessageBox.information(self, "Objeto seleccionado", 
                                      f"Tipo: {obj_type}\n\n"
                                      f"Puedes mover este objeto haciendo clic en otra celda.")
                
                # Cambiar al modo de movimiento
                self.grid_widget.mode = 'move'
                
                return True
            else:
                QMessageBox.information(self, "Selección", "No hay objetos en esta posición.")
                
                # Limpiar la selección actual
                self.selected_object = None
                self.selected_position = None
        
        return False
    
    def move_selected_object(self, row, col):
        """Mueve el objeto seleccionado a la nueva posición"""
        if not self.is_connected or not hasattr(self, 'selected_object') or not self.selected_object:
            return False
        
        # No permitir mover a una posición ocupada por otro objeto
        if self.grid_manager.grid[row][col] != EMPTY and (row, col) != self.selected_position:
            # Excepto si estamos reemplazando la meta o el robot
            allow_move = False
            
            # Si el objeto seleccionado es el robot, permitir moverlo a cualquier celda excepto a obstáculos
            if self.selected_object == self.robot_handle and self.grid_manager.grid[row][col] != OBSTACLE:
                allow_move = True
            
            # Si el objeto seleccionado es la meta, permitir moverla a cualquier celda excepto a obstáculos
            elif self.selected_object == self.goal_handle and self.grid_manager.grid[row][col] != OBSTACLE:
                allow_move = True
            
            if not allow_move:
                print("No se puede mover a una posición ocupada")
                return False
        
        try:
            # Convertir coordenadas de cuadrícula a CoppeliaSim
            reference_scale = float(self.scale_combo.currentText())
            x = (col - GRID_SIZE/2 + 0.5) * reference_scale
            y = (GRID_SIZE/2 - row - 0.5) * reference_scale
            
            # Mantener la altura Z original
            current_pos = self.sim_controller.sim.getObjectPosition(self.selected_object, -1)
            z = current_pos[2]
            
            # Mover el objeto en CoppeliaSim
            self.sim_controller.sim.setObjectPosition(self.selected_object, -1, [x, y, z])
            
            # Actualizar la cuadrícula según el tipo de objeto
            old_row, old_col = self.selected_position
            
            # Si es el robot
            if self.selected_object == self.robot_handle:
                # Actualizar la posición del robot
                self.robot_position = (row, col)
                
                # Actualizar referencias en el diccionario de objetos
                if (old_row, old_col) in self.objects:
                    del self.objects[(old_row, old_col)]
                self.objects[(row, col)] = self.robot_handle
                
                # Actualizar la visualización en el grid_widget
                self.grid_widget.robot_pos = (row, col)
            
            # Si es la meta
            elif self.selected_object == self.goal_handle:
                # Limpiar la meta anterior en el grid_manager
                self.grid_manager.clear_type(END)
                # Establecer la nueva posición de la meta
                self.grid_manager.grid[row][col] = END
                self.grid_manager.end_set = True
                self.goal_position = (row, col)
                
                # Actualizar referencias en el diccionario de objetos
                if (old_row, old_col) in self.objects:
                    del self.objects[(old_row, old_col)]
                self.objects[(row, col)] = self.goal_handle
                
                # Actualizar la visualización en el grid_widget
                self.grid_widget.meta_pos = (row, col)
            
            # Si es un obstáculo
            else:
                # Limpiar la posición anterior
                self.grid_manager.grid[old_row][old_col] = EMPTY
                # Establecer la nueva posición del obstáculo
                self.grid_manager.grid[row][col] = OBSTACLE
                
                # Actualizar referencias en el diccionario de objetos
                if (old_row, old_col) in self.objects:
                    del self.objects[(old_row, old_col)]
                self.objects[(row, col)] = self.selected_object
                
                # Actualizar la lista de obstáculos en el grid_widget
                if hasattr(self.grid_widget, 'obstacles') and (old_row, old_col) in self.grid_widget.obstacles:
                    self.grid_widget.obstacles.remove((old_row, old_col))
                if not hasattr(self.grid_widget, 'obstacles'):
                    self.grid_widget.obstacles = []
                self.grid_widget.obstacles.append((row, col))
            
            # Actualizar la posición seleccionada
            self.selected_position = (row, col)
            
            # Actualizar status
            print("Objeto movido a la posición ({row}, {col})")
            
            # Actualizar la visualización
            self.grid_widget.update()
            
            return True
        
        except Exception as e:
            print(f"Error al mover objeto: {e}")
            import traceback
            traceback.print_exc()
            print(f"Error al mover objeto: {str(e)}")
            return False
    
    def remove_selected_object(self):
        """Elimina el objeto seleccionado"""
        if not hasattr(self, 'selected_object') or self.selected_object is None:
            print("No hay objeto seleccionado para eliminar.")
            return False
        
        try:
            # No permitir eliminar el robot o la meta
            if self.selected_object == self.robot_handle:
                print("No se puede eliminar el robot principal.")
                return False
            
            if self.selected_object == self.goal_handle:
                print("No se puede eliminar el punto meta.")
                return False
            
            # Obtener la posición del objeto seleccionado
            row, col = self.selected_position
            
            # Intentar eliminar el objeto en CoppeliaSim
            try:
                # Verificar si el objeto existe
                self.sim_controller.sim.getObjectPosition(self.selected_object, -1)
                # Eliminarlo
                self.sim_controller.sim.removeObject(self.selected_object)
                print(f"Objeto eliminado de CoppeliaSim")
            except Exception as e:
                print(f"Error al eliminar objeto en CoppeliaSim: {e}")
                print("El objeto no existe en CoppeliaSim. Se eliminará solo de la interfaz.")
            
            # Actualizar la cuadrícula y las referencias
            # 1. Limpiar la celda en el grid_manager
            if self.grid_manager.grid[row][col] == OBSTACLE:
                self.grid_manager.grid[row][col] = EMPTY
            
            # 2. Eliminar la referencia en el diccionario de objetos
            if (row, col) in self.objects:
                del self.objects[(row, col)]
            
            # 3. Eliminar el obstáculo de la lista en grid_widget
            if hasattr(self.grid_widget, 'obstacles') and (row, col) in self.grid_widget.obstacles:
                self.grid_widget.obstacles.remove((row, col))
            
            # 4. Limpiar la selección
            self.selected_object = None
            self.selected_position = None
            
            # 5. Actualizar la visualización
            self.grid_widget.update()
            
            print("Objeto eliminado correctamente de la interfaz.")
            return True
            
        except Exception as e:
            print(f"Error al eliminar objeto: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def reset_grid(self):
        """Restablece la cuadrícula eliminando obstáculos pero manteniendo robot y meta"""
        reply = QMessageBox.question(self, "Confirmar reset", 
                                "¿Deseas restablecer la cuadrícula eliminando todos los obstáculos?",
                                QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.No:
            return
        
        try:
            # 1. Eliminar obstáculos en CoppeliaSim
            if self.is_connected:
                obstacles_to_remove = []
                
                # Identificar obstáculos
                for position, handle in self.objects.items():
                    # Si no es robot ni meta, es un obstáculo
                    if (hasattr(self, 'robot_handle') and handle == self.robot_handle) or \
                    (hasattr(self, 'goal_handle') and handle == self.goal_handle):
                        continue
                    
                    obstacles_to_remove.append((position, handle))
                
                # Eliminar obstáculos de CoppeliaSim
                for position, handle in obstacles_to_remove:
                    try:
                        # Verificar si el objeto existe
                        self.sim_controller.sim.getObjectPosition(handle, -1)
                        # Eliminarlo
                        self.sim_controller.sim.removeObject(handle)
                        print(f"Obstáculo eliminado de CoppeliaSim: {handle}")
                    except Exception as e:
                        print(f"Error al eliminar obstáculo {handle}: {e}")
            
            # 2. Limpiar la representación en la interfaz
            self.clean_interface()
            
            # 3. Actualizar la visualización
            self.grid_widget.update()
            
            print("✅ Obstáculos eliminados y cuadrícula restablecida")
            
        except Exception as e:
            print(f"Error al restablecer la cuadrícula: {e}")
            import traceback
            traceback.print_exc()
    
    def save_grid(self):
        """Guarda la cuadrícula en un archivo CSV"""
        filename, _ = QFileDialog.getSaveFileName(self, "Guardar recorrido", "", "CSV Files (*.csv)")
        if filename:
            self.grid_manager.export_to_csv(filename)
            QMessageBox.information(self, "Guardado exitoso", f"Recorrido guardado en {filename}")
    
    def start_simulation(self):
        """Inicia la simulación en CoppeliaSim"""
        if not hasattr(self, 'is_connected') or not self.is_connected:
            QMessageBox.warning(self, "No conectado", "Conecta a CoppeliaSim primero.")
            return
        
        try:
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(50)
            QApplication.processEvents()
            
            success = self.sim_controller.start_simulation()
            
            self.progress_bar.setValue(100)
            self.progress_bar.setVisible(False)
            
            if success:
                print("Simulación iniciada correctamente")
            else:
                QMessageBox.warning(self, "Error", "No se pudo iniciar la simulación.")
        
        except Exception as e:
            self.progress_bar.setVisible(False)
            print(f"Error al iniciar simulación: {e}")
            QMessageBox.warning(self, "Error", f"Error al iniciar simulación: {str(e)}")
    
    def pause_simulation(self):
        """Pausa la simulación en CoppeliaSim"""
        if not hasattr(self, 'is_connected') or not self.is_connected:
            QMessageBox.warning(self, "No conectado", "Conecta a CoppeliaSim primero.")
            return
        
        try:
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(50)
            QApplication.processEvents()
            
            success = self.sim_controller.suspend_simulation()
            
            self.progress_bar.setValue(100)
            self.progress_bar.setVisible(False)
            
            if success:
                print("Simulación pausada correctamente")
            else:
                QMessageBox.warning(self, "Error", "No se pudo pausar la simulación.")
        
        except Exception as e:
            self.progress_bar.setVisible(False)
            print(f"Error al pausar simulación: {e}")
            QMessageBox.warning(self, "Error", f"Error al pausar simulación: {str(e)}")
    
    def stop_simulation(self):
        """Detiene la simulación en CoppeliaSim"""
        if not hasattr(self, 'is_connected') or not self.is_connected:
            QMessageBox.warning(self, "No conectado", "Conecta a CoppeliaSim primero.")
            return
        
        try:
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(50)
            QApplication.processEvents()
            
            success = self.sim_controller.stop_simulation()
            
            self.progress_bar.setValue(100)
            self.progress_bar.setVisible(False)
            
            if success:
                print("Simulación detenida correctamente")
            else:
                QMessageBox.warning(self, "Error", "No se pudo detener la simulación.")
        
        except Exception as e:
            self.progress_bar.setVisible(False)
            print(f"Error al detener simulación: {e}")
            QMessageBox.warning(self, "Error", f"Error al detener simulación: {str(e)}")
    
    def execute_path(self):
        """Hace que el robot se mueva hacia el punto meta"""
        if not hasattr(self, 'is_connected') or not self.is_connected:
            QMessageBox.warning(self, "No conectado", "Conecta a CoppeliaSim primero.")
            return
        
        # Verificar que tenemos tanto el robot como la meta
        if not hasattr(self, 'robot_handle') or self.robot_handle is None:
            QMessageBox.warning(self, "Robot no encontrado", "No se ha detectado un robot en la escena.")
            return
        
        # Buscar el punto meta
        end_pos = None
        for row in range(GRID_SIZE):
            for col in range(GRID_SIZE):
                if self.grid_manager.grid[row][col] == END:
                    end_pos = (row, col)
                    break
            if end_pos:
                break
        
        if end_pos is None:
            QMessageBox.warning(self, "Meta no encontrada", "Establece primero un punto meta (B).")
            return
        
        try:
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(25)
            QApplication.processEvents()
            
            # Convertir coordenadas de cuadrícula a CoppeliaSim
            reference_scale = float(self.scale_combo.currentText())
            end_x = (end_pos[1] - GRID_SIZE/2 + 0.5) * reference_scale
            end_y = (GRID_SIZE/2 - end_pos[0] - 0.5) * reference_scale
            
            # Obtener altura original del objetivo
            if hasattr(self, 'goal_handle') and self.goal_handle is not None:
                goal_pos = self.sim_controller.sim.getObjectPosition(self.goal_handle, -1)
                end_z = goal_pos[2]
            else:
                end_z = 0.075  # Altura predeterminada para el objetivo
            
            target_position = [end_x, end_y, end_z]
            print(f"Enviando robot a posición: {target_position}")
            
            self.progress_bar.setValue(50)
            QApplication.processEvents()
            
            # Intentar varias estrategias para mover el robot
            success = False
            
            # Estrategia 1: Usar el método optimizado para la escena mobileRobotPathPlanning
            try:
                if hasattr(self.sim_controller, 'control_mobile_robot_path_planning'):
                    print("Usando control_mobile_robot_path_planning")
                    success = self.sim_controller.control_mobile_robot_path_planning(target_position)
                    if success:
                        print("✅ Recorrido iniciado con control_mobile_robot_path_planning")
            except Exception as e:
                print(f"Error en control_mobile_robot_path_planning: {e}")
            
            # Estrategia 2: Usar execute_path_for_mobile_robot como alternativa
            if not success:
                try:
                    if hasattr(self.sim_controller, 'execute_path_for_mobile_robot'):
                        print("Usando execute_path_for_mobile_robot")
                        success = self.sim_controller.execute_path_for_mobile_robot(None, end_pos)
                        if success:
                            print("✅ Recorrido iniciado con execute_path_for_mobile_robot")
                except Exception as e:
                    print(f"Error en execute_path_for_mobile_robot: {e}")
            
            # Estrategia 3: Ultimo recurso - mover directamente el goalDummy
            if not success and hasattr(self, 'goal_handle') and self.goal_handle is not None:
                try:
                    print("Moviendo goal_handle directamente")
                    self.sim_controller.sim.setObjectPosition(self.goal_handle, -1, target_position)
                    print("✅ goalDummy movido correctamente")
                    
                    # Verificar si necesitamos iniciar la simulación
                    try:
                        sim_state = self.sim_controller.sim.getSimulationState()
                        if sim_state != 1:  # 1 = simulación en ejecución
                            self.sim_controller.sim.startSimulation()
                            print("✅ Simulación iniciada")
                    except Exception as e:
                        print(f"Error al verificar estado de simulación: {e}")
                    
                    success = True
                except Exception as e:
                    print(f"Error al mover goalDummy: {e}")
            
            self.progress_bar.setValue(100)
            self.progress_bar.setVisible(False)
            
            if success:
                QMessageBox.information(self, "Recorrido iniciado", 
                                      "Se ha iniciado el recorrido del robot hacia el punto meta.")
            else:
                QMessageBox.warning(self, "Error", 
                                  "No se pudo iniciar el recorrido. Verifica la consola para más detalles.")
        
        except Exception as e:
            self.progress_bar.setVisible(False)
            print(f"Error al ejecutar recorrido: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.warning(self, "Error", f"Error al ejecutar recorrido: {str(e)}")