from coppeliasim_zmqremoteapi_client import RemoteAPIClient
import math
from heapq import heappush, heappop
from PyQt5.QtWidgets import (QMessageBox, QApplication)
from constants import GRID_SIZE, EMPTY, OBSTACLE, CELL_SIZE, START, END
from NavigationController import NavigationController

class CoppeliaSimController:
    def __init__(self, host="localhost", port=23000):
        self.host = host
        self.port = port
        self.client = None
        self.sim = None
        self.connected = False
        self.created_cubes = []  # Lista para rastrear los handles de cubos creados
    
    def connect(self):
        """Establece conexión con CoppeliaSim usando ZeroMQ"""
        try:
            # Usar el cliente de API remota ZeroMQ
            self.client = RemoteAPIClient(host=self.host, port=self.port)
            self.sim = self.client.getObject('sim')
            
            # Verificar que podemos acceder a CoppeliaSim obteniendo el estado de simulación
            state = self.sim.getSimulationState()
            self.connected = True
            print(f"Conectado a CoppeliaSim usando ZeroMQ. Estado de simulación: {state}")
            
            # Verificar comandos disponibles
            try:
                sim_time = self.sim.getSimulationTime()
                print(f"Tiempo de simulación actual: {sim_time}")
            except Exception as e:
                print(f"Advertencia: No se pudo verificar algunos comandos: {e}")
            
            # NUEVO: Listar métodos disponibles y tipos primitivos
            print("\n==== DIAGNÓSTICO DE API ====")
            self.list_available_methods()
            self.list_primitive_types()
            print("==== FIN DE DIAGNÓSTICO ====\n")
                
            return True
        except Exception as e:
            print(f"Error de conexión ZeroMQ: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """Cierra la conexión con CoppeliaSim"""
        if self.connected:
            try:
                # ZeroMQ no requiere cerrar la conexión explícitamente
                self.sim = None
                self.client = None
                self.connected = False
                print("Desconectado de CoppeliaSim")
                return True
            except Exception as e:
                print(f"Error al desconectar: {e}")
                return False
        return False
    
    def eliminar_cubos(self):
        """
        Elimina todos los cubos que fueron creados por esta instancia.
        Usando el método updateObjectSpecialProperty.
        """
        if not self.connected:
            print("❌ No se puede eliminar cubos: no hay conexión activa")
            return False
        
        if not self.created_cubes:
            print("ℹ️ No hay cubos registrados para eliminar")
            return True
        
        try:
            # Usar removeObjects (plural) en lugar de removeObject
            self.sim.removeObjects(self.created_cubes)
            count = len(self.created_cubes)
            self.created_cubes = []  # Limpiar la lista después de eliminar
            
            print(f"🧹 Se eliminaron {count} cubos correctamente")
            return True
        except Exception as e:
            print(f"❌ Error al eliminar cubos: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def eliminar_cubo_por_handle(self, handle):
        """Elimina un cubo específico por su handle"""
        if not self.connected:
            print("❌ No se puede eliminar el cubo: no hay conexión activa")
            return False

        try:
            print(f"Intentando eliminar cubo con handle: {handle}")
            self.sim.removeObject(handle)
            
            if handle in self.created_cubes:
                self.created_cubes.remove(handle)
            print(f"✅ Cubo con handle {handle} eliminado exitosamente")
            return True
        except Exception as e:
            print(f"❌ Excepción al eliminar cubo con handle {handle}: {e}")
            return False
    
    def get_available_methods(self):
        """Obtiene una lista aproximada de métodos disponibles en ZeroMQ API"""
        if not self.connected:
            print("No hay conexión activa")
            return []
        
        # ZeroMQ no proporciona un método para enumerar todos los métodos disponibles
        # Devolvemos una lista predefinida de métodos comunes como referencia
        common_methods = [
            "sim.startSimulation", 
            "sim.stopSimulation", 
            "sim.pauseSimulation",
            "sim.getSimulationState", 
            "sim.createPrimitiveShape",
            "sim.removeObject",
            "sim.setObjectPosition",
            "sim.setShapeColor"
        ]
        return common_methods
    
    def start_simulation(self):
        """Inicia la simulación en CoppeliaSim y recrea objetos si es necesario"""
        if not self.connected:
            print("No hay conexión activa. No se puede iniciar la simulación.")
            return False

        try:
            # Antes de iniciar, verificar si necesitamos recrear objetos
            need_recreate = False
            
            # Verificar si los cubos y robot existen
            if hasattr(self, 'created_cubes') and self.created_cubes:
                for handle in self.created_cubes:
                    try:
                        # Intentar obtener la posición para verificar si existe
                        self.sim.getObjectPosition(handle, -1)
                    except:
                        # El objeto no existe, necesitamos recrearlo
                        need_recreate = True
                        break
            
            # Si necesitamos recrear objetos, informar pero continuar
            if need_recreate:
                print("⚠️ Algunos objetos ya no existen y necesitan ser recreados")
                # Aquí podrías implementar lógica para recrear los objetos
                # basándote en la información guardada
            
            # Iniciar la simulación
            self.sim.startSimulation()
            print("✅ Simulación iniciada correctamente")
            return True
        except Exception as e:
            print(f"❌ Error al iniciar simulación: {e}")
            return False
        
    def suspend_simulation(self):
        """Pausa la simulación en CoppeliaSim sin detenerla por completo"""
        if not self.connected:
            print("❌ No se puede pausar: no hay conexión activa")
            return False

        try:
            # Intentar pausar la simulación usando pauseSimulation primero
            try:
                self.sim.pauseSimulation()
                print("✅ Simulación pausada usando pauseSimulation")
                return True
            except Exception as e:
                print(f"Error al usar pauseSimulation: {e}, intentando método alternativo...")
                
            # Si el método anterior falla, intentar obtener el estado actual y pausar basado en eso
            try:
                # Obtener el estado actual de la simulación
                sim_state = self.sim.getSimulationState()
                
                # Verificar si la simulación está en ejecución
                if sim_state == 0x01:  # simulation_running = 0x01 en muchas versiones
                    # Pausar la simulación estableciendo el estado a pausado
                    self.sim.setSimulationState(0x00)  # simulation_paused = 0x00 en muchas versiones
                    print("✅ Simulación pausada usando setSimulationState")
                    return True
                else:
                    print("⚠️ La simulación no está en ejecución, no se puede pausar")
                    return False
            except Exception as alt_e:
                print(f"Error en método alternativo: {alt_e}")
                
            # Si todos los métodos anteriores fallan, intentar detenerla (último recurso)
            print("⚠️ Intentando método de último recurso (detener)")
            self.sim.stopSimulation()
            print("⚠️ Simulación detenida como recurso alternativo")
            return True
            
        except Exception as e:
            print(f"❌ Error general al pausar simulación: {e}")
            return False
    
    def stop_simulation(self):
        """Detiene la simulación en CoppeliaSim"""
        try:
            self.sim.stopSimulation()
            print("✅ Simulación detenida correctamente")
            return True
        except Exception as e:
            print(f"❌ Error al detener simulación: {e}")
            return False
        
        # Añadimos esta función para reemplazar execute_path en CoppeliaSimController
    def execute_path(self, start_pos, end_pos, obstacles):
        """
        Controlador simplificado y agresivo para el robot Pioneer P3DX.
        Se enfoca únicamente en llegar al objetivo de manera directa.
        
        Args:
            start_pos: Tupla (row, col) con la posición inicial del robot
            end_pos: Tupla (row, col) con la posición final deseada
            obstacles: Lista de tuplas (row, col) con posiciones de obstáculos
        """
        if not self.connected:
            print("❌ No se puede ejecutar recorrido: no hay conexión activa")
            return False
                
        print(f"Ejecutando recorrido directo desde {start_pos} hasta {end_pos}")
        print(f"Evitando {len(obstacles)} obstáculos")
        
        try:
            # 1. Convertir coordenadas de cuadrícula a coordenadas CoppeliaSim
            reference_scale = 0.5
            
            # Calcular la posición objetivo
            end_x = (end_pos[1] - 5 + 0.5) * reference_scale
            end_y = (5 - end_pos[0] - 0.5) * reference_scale
            end_z = 0.1384  # Altura del Pioneer P3DX
            target_position = [end_x, end_y, end_z]
            
            print(f"Posición objetivo en coordenadas CoppeliaSim: {target_position}")
            
            # 2. Buscar los motores y el robot
            left_motor = None
            right_motor = None
            robot_handle = None
            
            # Obtener los motores (probando diferentes nombres)
            try:
                # Enfoque directo y específico para los motores
                print("Buscando motores con nombres específicos...")
                left_motor = self.sim.getObject("/PioneerP3DX/leftMotor")
                right_motor = self.sim.getObject("/PioneerP3DX/rightMotor")
            except:
                try:
                    left_motor = self.sim.getObject("Pioneer_p3dx_leftMotor")
                    right_motor = self.sim.getObject("Pioneer_p3dx_rightMotor")
                except Exception as e:
                    print(f"❌ Error al obtener motores: {e}")
                    return False
                    
            # Obtener handle del robot (probando diferentes nombres)
            try:
                # Enfoque directo y específico para el robot
                print("Buscando robot con nombres específicos...")
                robot_handle = self.sim.getObject("/PioneerP3DX")
            except:
                try:
                    robot_handle = self.sim.getObject("Pioneer_p3dx")
                except Exception as e:
                    print(f"❌ Error al obtener robot: {e}")
                    return False
            
            print(f"✅ Motores y robot encontrados")
            
            # 3. Crear un objetivo visual (esfera roja grande)
            try:
                # Intentar eliminar objetivo anterior si existe
                try:
                    old_target = self.sim.getObject("NavTarget")
                    self.sim.removeObject(old_target)
                except:
                    pass
                
                # Crear un nuevo objetivo visual (una esfera)
                target_size = 0.3  # Esfera muy grande para visualización
                # Usar nombre primitivo exacto para evitar errores
                target_handle = self.sim.createPrimitiveShape(1, [target_size, target_size, target_size])
                self.sim.setObjectPosition(target_handle, -1, target_position)
                
                # Intentar nombrar el objetivo
                try:
                    self.sim.setObjectAlias(target_handle, "NavTarget")
                except:
                    try:
                        self.sim.setObjectName(target_handle, "NavTarget")
                    except:
                        pass
                
                # Intentar cambiar el color a rojo brillante (con manejo de errores robusto)
                try:
                    print("Intentando establecer color rojo brillante para el objetivo...")
                    self.sim.setShapeColor(target_handle, 0, 0, [1, 0, 0])  # Intento simplificado
                except Exception as color_error:
                    try:
                        print(f"Primer intento fallido: {color_error}")
                        self.sim.setShapeColor(target_handle, 0, 16, [1, 0, 0])  # Intento alternativo
                    except:
                        print("No se pudo establecer el color, pero continuando...")
                    
                print(f"✅ Objetivo visual creado en: {target_position}")
            except Exception as e:
                print(f"⚠️ Error al crear objetivo visual: {e}")
                import traceback
                traceback.print_exc()
                # Continuar incluso sin el objetivo visual
            
            # 4. Iniciar navegación directa simplificada
            import threading
            import time
            import math
            import random
            
            # Variable de control
            self.navigation_active = True
            
            def direct_navigation_controller():
                """Controlador de navegación directa y agresiva"""
                print("🚀 Iniciando controlador de navegación directa y agresiva")
                
                # Parámetros con velocidades muy altas para movimiento agresivo
                max_velocity = 5.0       # Velocidad lineal máxima (m/s) - incrementada para movimiento más rápido
                turn_velocity = 2.0      # Velocidad de giro mucho más alta
                
                # Umbrales
                distance_threshold = 0.3  # Distancia para considerar llegada (m)
                
                # Control de maniobras de escape
                stuck_timer = 0
                escape_counter = 0
                
                # Registro de posición para detección de estancamiento
                prev_pos = None
                distances = []
                
                # Bucle principal
                try:
                    start_time = time.time()
                    
                    while self.navigation_active:
                        # 1. Obtener posición y orientación actual del robot
                        try:
                            robot_pos = self.sim.getObjectPosition(robot_handle, -1)
                            robot_orient = self.sim.getObjectOrientation(robot_handle, -1)
                            robot_angle = robot_orient[2]  # Yaw (rotación en Z)
                        except Exception as pos_error:
                            print(f"Error al obtener posición: {pos_error}")
                            time.sleep(0.1)
                            continue
                        
                        # 2. Calcular distancia y dirección al objetivo
                        dx = target_position[0] - robot_pos[0]
                        dy = target_position[1] - robot_pos[1]
                        distance = math.sqrt(dx*dx + dy*dy)
                        
                        # Registrar distancia para detección de estancamiento
                        distances.append(distance)
                        if len(distances) > 10:
                            distances.pop(0)
                        
                        print(f"Distancia al objetivo: {distance:.2f}m")
                        
                        # Si está muy cerca del objetivo, detenerse
                        if distance < distance_threshold:
                            self.sim.setJointTargetVelocity(left_motor, 0)
                            self.sim.setJointTargetVelocity(right_motor, 0)
                            print("🏁 ¡Objetivo alcanzado! Robot detenido.")
                            break
                        
                        # Verificar si estamos atascados
                        stuck = False
                        if len(distances) >= 10:
                            max_diff = max(distances) - min(distances)
                            if max_diff < 0.05:  # Si no hay progreso significativo
                                stuck = True
                                stuck_timer += 1
                            else:
                                stuck_timer = 0
                        
                        # Si estamos atascados por mucho tiempo o han pasado más de 30 segundos
                        if stuck_timer > 10 or (time.time() - start_time > 30 and distance > 1.0):
                            print("⚠️ Robot atascado o tomando demasiado tiempo, aplicando maniobra agresiva")
                            
                            # Maniobra agresiva aleatoria
                            escape_sequence = random.randint(1, 3)
                            
                            if escape_sequence == 1:
                                # Maniobra 1: Retroceder y girar
                                print("Maniobra de escape 1: Retroceder y girar")
                                self.sim.setJointTargetVelocity(left_motor, -3.0)
                                self.sim.setJointTargetVelocity(right_motor, -3.0)
                                time.sleep(1.0)
                                self.sim.setJointTargetVelocity(left_motor, 3.0)
                                self.sim.setJointTargetVelocity(right_motor, -3.0)
                                time.sleep(1.5)
                            
                            elif escape_sequence == 2:
                                # Maniobra 2: Giro completo
                                print("Maniobra de escape 2: Giro completo")
                                self.sim.setJointTargetVelocity(left_motor, 4.0)
                                self.sim.setJointTargetVelocity(right_motor, -4.0)
                                time.sleep(3.0)
                            
                            else:
                                # Maniobra 3: Zigzag
                                print("Maniobra de escape 3: Zigzag")
                                for _ in range(2):
                                    self.sim.setJointTargetVelocity(left_motor, 4.0)
                                    self.sim.setJointTargetVelocity(right_motor, 1.0)
                                    time.sleep(0.5)
                                    self.sim.setJointTargetVelocity(left_motor, 1.0)
                                    self.sim.setJointTargetVelocity(right_motor, 4.0)
                                    time.sleep(0.5)
                            
                            stuck_timer = 0
                            escape_counter += 1
                            distances = []  # Reiniciar registro de distancias
                            start_time = time.time()  # Reiniciar temporizador
                            
                            # Si hemos intentado demasiadas maniobras y seguimos lejos
                            if escape_counter > 5 and distance > 3.0:
                                print("⚠️ Demasiados intentos sin éxito, probando enfoque diferente")
                                # Movimiento agresivo directo
                                self.sim.setJointTargetVelocity(left_motor, 5.0)
                                self.sim.setJointTargetVelocity(right_motor, 5.0)
                                time.sleep(2.0)
                                escape_counter = 0
                            
                            continue  # Volver al inicio del bucle
                        
                        # 3. Calcular ángulo hacia el objetivo
                        target_angle = math.atan2(dy, dx)
                        
                        # 4. Calcular error de orientación
                        orientation_error = target_angle - robot_angle
                        
                        # Normalizar el error al rango (-pi, pi)
                        while orientation_error > math.pi:
                            orientation_error -= 2 * math.pi
                        while orientation_error < -math.pi:
                            orientation_error += 2 * math.pi
                            
                        print(f"Orientación actual: {robot_angle:.2f}, Objetivo: {target_angle:.2f}, Error: {orientation_error:.2f}")
                        
                        # 5. Enfoque simple pero efectivo para la navegación
                        left_velocity = 0
                        right_velocity = 0
                        
                        # Si el error de orientación es grande, girar agresivamente
                        if abs(orientation_error) > 0.3:  # ~17 grados
                            # Giro agresivo
                            turn_speed = turn_velocity
                            
                            if orientation_error > 0:  # Necesita girar a la izquierda
                                left_velocity = -turn_speed * 1.5  # Más agresivo
                                right_velocity = turn_speed * 1.5
                                print(f"Girando AGRESIVAMENTE a la IZQUIERDA: {turn_speed}")
                            else:  # Necesita girar a la derecha
                                left_velocity = turn_speed * 1.5
                                right_velocity = -turn_speed * 1.5
                                print(f"Girando AGRESIVAMENTE a la DERECHA: {turn_speed}")
                        else:
                            # Avanzar con corrección proporcional a la orientación
                            forward_speed = max_velocity
                            steering = orientation_error * 0.5
                            
                            left_velocity = forward_speed - steering
                            right_velocity = forward_speed + steering
                            
                            print(f"Avanzando rápido: Vel={forward_speed}")
                        
                        # 6. Aplicar velocidades a los motores
                        self.sim.setJointTargetVelocity(left_motor, left_velocity)
                        self.sim.setJointTargetVelocity(right_motor, right_velocity)
                        
                        # Pausa breve para no saturar la CPU
                        time.sleep(0.05)
                    
                    # Al finalizar, detener motores
                    try:
                        self.sim.setJointTargetVelocity(left_motor, 0)
                        self.sim.setJointTargetVelocity(right_motor, 0)
                        print("✅ Navegación finalizada")
                    except:
                        pass
                        
                except Exception as e:
                    print(f"❌ Error en bucle de navegación: {e}")
                    import traceback
                    traceback.print_exc()
                    # Intentar detener el robot si hay error
                    try:
                        self.sim.setJointTargetVelocity(left_motor, 0)
                        self.sim.setJointTargetVelocity(right_motor, 0)
                    except:
                        pass
                        
            # Iniciar el thread de navegación
            nav_thread = threading.Thread(target=direct_navigation_controller)
            nav_thread.daemon = True
            nav_thread.start()
            
            return True
            
        except Exception as e:
            print(f"❌ Error general al ejecutar recorrido: {e}")
            import traceback
            traceback.print_exc()
            self.navigation_active = False
            return False
        
    # Método para detener la navegación desde fuera
    def stop_navigation(self):
        """Detiene el proceso de navegación activo"""
        self.navigation_active = False
        print("Navegación detenida manualmente")
        return True
        
    def direct_robot_movement_to_target(self, target_position):
        """
        Mueve el robot directamente hacia una posición objetivo.
        
        Args:
            target_position: Lista [x, y, z] con la posición de destino
        """
        try:
            # Obtener los handles de los motores
            try:
                left_motor = self.sim.getObject("Pioneer_p3dx_leftMotor")
                right_motor = self.sim.getObject("Pioneer_p3dx_rightMotor")
            except:
                try:
                    left_motor = self.sim.getObject("/Pioneer_p3dx/leftMotor")
                    right_motor = self.sim.getObject("/Pioneer_p3dx/rightMotor")
                except Exception as e:
                    print(f"No se pudieron obtener los handles de los motores: {e}")
                    return False
            
            # Establecer velocidades para ambos motores
            self.sim.setJointTargetVelocity(left_motor, 2.0)
            self.sim.setJointTargetVelocity(right_motor, 2.0)
            
            print(f"✅ Robot en movimiento hacia objetivo: {target_position}")
            return True
        except Exception as e:
            print(f"❌ Error al mover el robot: {e}")
            return False

    def get_object_safely(self, object_name, alternatives=None):
        """
        Intenta obtener un objeto de CoppeliaSim por su nombre de manera segura,
        probando diferentes variantes del nombre y manejando errores.
        
        Args:
            object_name: Nombre principal del objeto a buscar
            alternatives: Lista opcional de nombres alternativos a probar
            
        Returns:
            El handle del objeto si se encuentra, None en caso contrario
        """
        if not self.connected:
            print(f"No se puede buscar '{object_name}': no hay conexión activa")
            return None
            
        # Lista de variantes de sintaxis a probar
        name_variants = [
            object_name,               # Nombre exacto
            f"/{object_name}",         # Con barra al inicio
            f"./{object_name}",        # Con ./ al inicio
            object_name.lower(),       # En minúsculas
            object_name.upper(),       # En mayúsculas
            # Variantes sin espacios
            object_name.replace(" ", ""),
            f"/{object_name.replace(' ', '')}",
            object_name.replace(" ", "").lower(),
            object_name.replace(" ", "").upper(),
            f"/{object_name.replace(' ', '')}".lower(),
            f"/{object_name.replace(' ', '')}".upper(),
            # Variante específica que vemos en la imagen
            "/PioneerP3DX",
            "PioneerP3DX",
            "/pioneerp3dx",
            "pioneerp3dx"
        ]
        
        # Agregar alternativas si se proporcionan
        if alternatives:
            for alt in alternatives:
                name_variants.append(alt)
                name_variants.append(f"/{alt}")
                name_variants.append(f"./{alt}")
                # También agregar variantes sin espacios
                name_variants.append(alt.replace(" ", ""))
                name_variants.append(f"/{alt.replace(' ', '')}")
        
        # Eliminar duplicados
        name_variants = list(set(name_variants))
        
        # Probar cada variante
        for name in name_variants:
            try:
                handle = self.sim.getObject(name)
                print(f"✅ Objeto '{name}' encontrado con handle: {handle}")
                return handle
            except Exception as e:
                # Falló esta variante, intentar la siguiente
                pass
        
        # Si llegamos aquí, no se encontró el objeto
        print(f"❌ No se pudo encontrar el objeto '{object_name}'")
        print("Nombres probados:")
        for name in name_variants:
            print(f"  - '{name}'")
        return None
    
    def find_path(self, start, end, obstacles):
        """
        Implementa el algoritmo A* para encontrar un camino óptimo desde start hasta end,
        evitando los obstacles.
        
        Args:
            start: Tupla (row, col) con la posición inicial
            end: Tupla (row, col) con la posición final
            obstacles: Lista de tuplas (row, col) con las posiciones de los obstáculos
        
        Returns:
            Lista de tuplas (row, col) con el camino encontrado, o lista vacía si no hay camino
        """
        from heapq import heappush, heappop
        import math
        
        print(f"Buscando camino desde {start} hasta {end}")
        print(f"Obstáculos: {obstacles}")
        
        # Convertir obstáculos a un set para búsqueda más rápida
        obstacles_set = set(obstacles)
        
        # Función heurística: distancia Manhattan
        def heuristic(a, b):
            return abs(a[0] - b[0]) + abs(a[1] - b[1])
        
        def get_neighbors(pos):
            row, col = pos
            neighbors = []
            
            # 4 direcciones: derecha, abajo, izquierda, arriba
            for dr, dc in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                new_row, new_col = row + dr, col + dc
                
                # Verificar límites de la cuadrícula y obstáculos
                if (0 <= new_row < 10 and 0 <= new_col < 10 and 
                    (new_row, new_col) not in obstacles_set):
                    neighbors.append((new_row, new_col))
                    
            return neighbors
        
        # Inicializar estructuras para A*
        open_set = []
        heappush(open_set, (0, start))  # (f_score, position)
        
        came_from = {start: None}  # Para reconstruir el camino
        g_score = {start: 0}  # Costo desde el inicio
        f_score = {start: heuristic(start, end)}  # Costo estimado total
        
        # Algoritmo A*
        while open_set:
            # Obtener el nodo con menor f_score
            _, current = heappop(open_set)
            
            # Si llegamos al destino, reconstruir el camino
            if current == end:
                path = []
                while current:
                    path.append(current)
                    current = came_from[current]
                path.reverse()  # El camino está en orden inverso
                return path
            
            # Explorar vecinos
            for neighbor in get_neighbors(current):
                # Costo tentativo desde el inicio hasta el vecino
                tentative_g = g_score[current] + 1  # 1 es el costo de moverse a un vecino
                
                # Si encontramos un camino mejor, actualizar
                if neighbor not in g_score or tentative_g < g_score[neighbor]:
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative_g
                    f_score[neighbor] = tentative_g + heuristic(neighbor, end)
                    
                    # Agregar a la cola de prioridad si no está ya
                    in_open_set = False
                    for _, pos in open_set:
                        if pos == neighbor:
                            in_open_set = True
                            break
                            
                    if not in_open_set:
                        heappush(open_set, (f_score[neighbor], neighbor))
        
        # Si llegamos aquí, no hay camino
        print("⚠️ No se encontró camino")
        return []
    
    def cargar_muro_personalizado(self, size=[0.1, 0.1, 0.1], position=[0, 0, 0], color=None):
        """
        Crea un cubo/muro personalizado con el tamaño especificado, asegurando 
        que tenga todas las propiedades correctas para ser detectado.
        """
        if not self.connected:
            print("❌ No se puede crear muro personalizado: no hay conexión activa")
            return None
        
        try:
            print(f"Creando muro personalizado en posición: {position}, tamaño: {size}")
            
            # Intentar método alternativo con createPureShape
            try:
                # Primero intenta con createPrimitiveShape (formato mejorado)
                wall_handle = self.sim.createPrimitiveShape(0, 18, size, 1.0)
            except Exception as e:
                print(f"Error con createPrimitiveShape: {e}, intentando método alternativo...")
                try:
                    # Intenta con createPureShape que podría tener parámetros diferentes
                    wall_handle = self.sim.createPureShape(0, 18, size, 1.0)
                except Exception as e2:
                    print(f"Error con createPureShape: {e2}, intentando método básico...")
                    try:
                        # Último intento con formato simplificado
                        options = 18  # 16 (static) + 2 (respondable)
                        wall_handle = self.sim.createPrimitiveShape(0, options, size)
                    except Exception as e3:
                        print(f"Todos los métodos de creación fallaron: {e3}")
                        return None
            
            if wall_handle == -1:
                print("❌ Error: Handle no válido (-1)")
                return None
            
            print(f"✅ Objeto creado con handle: {wall_handle}")
            
            # Posicionar el objeto
            position[2] = size[2]/2  # Centrar en Z según altura
            self.sim.setObjectPosition(wall_handle, -1, position)
            print(f"✅ Objeto posicionado en: {position}")
            
            # Establecer propiedades especiales para detectabilidad
            try:
                # Intentar con valor combinado
                detectable_value = self.sim.objectspecialproperty_detectable_all + self.sim.objectspecialproperty_collidable
                self.sim.setObjectSpecialProperty(wall_handle, detectable_value)
            except Exception as e:
                print(f"Error al establecer propiedades combinadas: {e}, intentando valores individuales...")
                try:
                    # Intentar agregar propiedades por separado
                    self.sim.setObjectSpecialProperty(wall_handle, self.sim.objectspecialproperty_detectable_all)
                    self.sim.setObjectSpecialProperty(wall_handle, self.sim.objectspecialproperty_collidable)
                except Exception as e2:
                    print(f"Error con propiedades individuales: {e2}, probando con valores numéricos fijos...")
                    try:
                        # Último intento con valores numéricos fijos
                        self.sim.setObjectSpecialProperty(wall_handle, 19)  # 16 + 2 + 1 (detectable + collidable + measurable)
                    except:
                        print("No se pudieron establecer propiedades especiales")
            
            print("✅ Intentado establecer propiedades especiales")
            
            # Intentar establecer parámetros adicionales
            try:
                self.sim.setObjectInt32Param(wall_handle, 3004, 1)  # sim.shapeintparam_respondable
            except:
                print("No se pudo establecer parámetro respondable")
            
            # Establecer color si se especifica
            if color:
                try:
                    self.sim.setShapeColor(wall_handle, None, 0, color)
                    print(f"✅ Color establecido: {color}")
                except Exception as e:
                    print(f"Error al establecer color: {e}")
            
            # Registrar el handle
            if hasattr(self, 'created_cubes'):
                self.created_cubes.append(wall_handle)
            else:
                self.created_cubes = [wall_handle]
            
            print(f"✅ Muro personalizado creado con handle: {wall_handle}")
            return wall_handle
            
        except Exception as e:
            print(f"❌ Error al crear muro personalizado: {e}")
            import traceback
            traceback.print_exc()
            return None

    def direct_robot_movement(self):
        """
        Método directo para mover el robot sin depender de algoritmos complejos.
        Este método garantiza que el robot se mueva.
        """
        try:
            # Obtener nombres exactos del entorno
            robot_name = "/PioneerP3DX"
            left_motor_name = "/PioneerP3DX/leftMotor"
            right_motor_name = "/PioneerP3DX/rightMotor"
            
            # Obtener handles
            robot_handle = self.sim_controller.sim.getObject(robot_name)
            left_motor = self.sim_controller.sim.getObject(left_motor_name)
            right_motor = self.sim_controller.sim.getObject(right_motor_name)
            
            print(f"Robot y motores localizados correctamente")
            print(f"Robot: {robot_handle}, Motor izquierdo: {left_motor}, Motor derecho: {right_motor}")
            
            # Aplicar velocidades directamente - valores simples pero efectivos
            left_speed = 2.0
            right_speed = 2.0
            
            # Intentar primero con velocidades iguales para avanzar en línea recta
            self.sim_controller.sim.setJointTargetVelocity(left_motor, left_speed)
            self.sim_controller.sim.setJointTargetVelocity(right_motor, right_speed)
            
            print(f"Velocidades aplicadas - Izquierda: {left_speed}, Derecha: {right_speed}")
            print("Robot en movimiento directo")
            
            return True
        except Exception as e:
            print(f"Error en movimiento directo: {e}")
            import traceback
            traceback.print_exc()
            return False

    def create_robot(self, robot_type, position, orientation=None):
        """
        Crea un robot en CoppeliaSim cargando un modelo predefinido.
        Versión mejorada con altura y nombre correctos.
        """
        if not self.connected:
            print("❌ No se puede crear robot: no hay conexión activa")
            return {"success": False, "error": "No hay conexión activa"}
        
        try:
            print(f"Intentando cargar el modelo del robot {robot_type} en posición {position}")
            
            # Cargar el modelo del robot
            robot_handle = None
            try:
                # Intentar cargar el modelo del robot
                robot_handle = self.sim.loadModel("models/robots/mobile/pioneer p3dx.ttm")
                print(f"Modelo cargado con handle: {robot_handle}")
            except Exception as e:
                print(f"Error al cargar el modelo: {e}")
                
                # Intentar rutas alternativas
                alternative_paths = [
                    "models/mobile/pioneer p3dx.ttm",
                    "models/robots/Pioneer_p3dx.ttm",
                    "Pioneer_p3dx.ttm",
                    "/models/robots/mobile/pioneer p3dx.ttm",
                    "./models/robots/mobile/pioneer p3dx.ttm",
                    "models/robots/mobile/PioneerP3DX.ttm"
                ]
                
                for path in alternative_paths:
                    try:
                        print(f"Intentando cargar desde ruta alternativa: {path}")
                        robot_handle = self.sim.loadModel(path)
                        print(f"Modelo cargado desde ruta alternativa con handle: {robot_handle}")
                        break
                    except Exception as alt_error:
                        print(f"Error con ruta alternativa {path}: {alt_error}")
            
            # Si no se pudo cargar el modelo, crear un objeto visual simple
            if robot_handle is None:
                try:
                    print("Creando objeto visual simple como sustituto...")
                    # Crear un cuboide para representar el robot (primitiva de tipo cuboide)
                    robot_handle = self.sim.createPrimitiveShape(0, 18, [0.3, 0.4, 0.2])
                    self.sim.setShapeColor(robot_handle, None, 0, [1, 0, 0])  # Color rojo
                    
                    # Intentar crear un par de ruedas/articulaciones para simular el movimiento
                    try:
                        # Crear articulación izquierda
                        left_joint = self.sim.createJoint(3, 2)  # Tipo revolución, modo cinemático
                        self.sim.setObjectParent(left_joint, robot_handle, True)
                        self.sim.setObjectPosition(left_joint, robot_handle, [-0.15, 0.1, -0.1])
                        self.sim.setObjectAlias(left_joint, "leftMotor")
                        
                        # Crear articulación derecha
                        right_joint = self.sim.createJoint(3, 2)  # Tipo revolución, modo cinemático
                        self.sim.setObjectParent(right_joint, robot_handle, True)
                        self.sim.setObjectPosition(right_joint, robot_handle, [-0.15, -0.1, -0.1])
                        self.sim.setObjectAlias(right_joint, "rightMotor")
                        
                        print("Articulaciones creadas exitosamente")
                    except Exception as joint_error:
                        print(f"Error al crear articulaciones: {joint_error}")
                    
                    print(f"Objeto visual creado con handle: {robot_handle}")
                except Exception as shape_error:
                    print(f"Error al crear forma visual: {shape_error}")
                    return {"success": False, "error": "No se pudo crear ninguna representación del robot"}
                    
            # Si llegamos aquí, tenemos un handle de robot. Posicionarlo.
            try:
                print(f"Estableciendo posición del robot a: {position}")
                
                # Asegurarse que la altura es correcta (Z)
                # La altura debe ser adecuada para que el robot no esté enterrado ni flotando
                position[2] = 0.1384  # Altura correcta para el Pioneer P3DX
                
                self.sim.setObjectPosition(robot_handle, -1, position)
                
                # Verificar si el posicionamiento funcionó
                current_pos = self.sim.getObjectPosition(robot_handle, -1)
                print(f"Posición actual del robot: {current_pos}")
                
                # Asignar un alias claro para facilitar la identificación
                try:
                    # Probamos varias formas de establecer el nombre según la versión de CoppeliaSim
                    try:
                        self.sim.setObjectAlias(robot_handle, "PioneerP3DX")
                    except:
                        try:
                            self.sim.setObjectName(robot_handle, "PioneerP3DX") 
                        except:
                            print("No se pudo establecer un nombre para el robot")
                except Exception as e:
                    print(f"Error al establecer nombre/alias: {e}")
                    # Continuar incluso si no se puede establecer el nombre
            except Exception as pos_error:
                print(f"Error al posicionar el robot: {pos_error}")
            
            print(f"✅ Robot cargado y posicionado con handle: {robot_handle}")
            return {
                "success": True,
                "handle": robot_handle
            }
        except Exception as e:
            print(f"❌ Error general al crear robot: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        
    def read_ultrasonic_sensors(self):
        """
        Lee los valores de los sensores ultrasónicos del robot Pioneer P3DX
        y devuelve las distancias detectadas
        """
        if not self.connected:
            print("❌ No se pueden leer sensores: no hay conexión activa")
            return None
            
        try:
            # Obtener las handles de los sensores ultrasónicos
            sensor_distances = []
            sensor_handles = []
            
            # Buscar todos los sensores ultrasónicos del robot
            for i in range(1, 17):  # El Pioneer P3DX tiene 16 sensores ultrasónicos
                try:
                    sensor_name = f"Pioneer_p3dx_ultrasonicSensor{i}"
                    _, sensor_handle = self.sim.simxGetObjectHandle(
                        self.clientID, 
                        sensor_name, 
                        self.sim.simx_opmode_blocking
                    )
                    sensor_handles.append(sensor_handle)
                    print(f"Sensor {sensor_name} encontrado con handle {sensor_handle}")
                except Exception as e:
                    print(f"No se pudo obtener handle para sensor {i}: {e}")
            
            # Leer los valores de los sensores
            for handle in sensor_handles:
                try:
                    # Leer el sensor de proximidad
                    ret, detection_state, detected_point, _, _ = self.sim.simxReadProximitySensor(
                        self.clientID,
                        handle,
                        self.sim.simx_opmode_blocking
                    )
                    
                    if ret == 0:  # Si la lectura fue exitosa
                        if detection_state:
                            # Calcular la distancia al punto detectado
                            import numpy as np
                            distance = np.linalg.norm(detected_point)
                            sensor_distances.append(distance)
                        else:
                            # No se detectó nada, usar valor máximo
                            sensor_distances.append(0.5)  # 0.5 metros como valor máximo
                    else:
                        print(f"Error al leer sensor {handle}")
                        sensor_distances.append(0.5)  # Valor por defecto
                except Exception as e:
                    print(f"Error al leer sensor {handle}: {e}")
                    sensor_distances.append(0.5)  # Valor por defecto
            
            return sensor_distances
        
        except Exception as e:
            print(f"❌ Error general al leer sensores: {e}")
            return None
        
    def configure_robot_sensors(self, robot_handle):
        """
        Configura específicamente los sensores del robot Pioneer P3DX para 
        que detecten correctamente los obstáculos.
        """
        if not self.connected or robot_handle is None:
            return False
        
        try:
            print(f"Configurando sensores del robot con handle: {robot_handle}")
            
            # Obtener todos los objetos en el árbol del robot
            children = self.sim.getObjectsInTree(robot_handle, 0, 0)
            
            # Parámetros para los sensores ultrasónicos
            sensor_count = 0
            
            # Buscar sensores y configurarlos
            for child in children:
                try:
                    # Verificar si es un sensor de proximidad
                    child_name = self.sim.getObjectName(child)
                    
                    if "ultrasonic" in child_name.lower() or "sensor" in child_name.lower():
                        # Es un sensor, configurarlo para detección óptima
                        
                        # 1. Aumentar el rango de detección
                        self.sim.setObjectFloatParam(
                            child, 
                            4001,  # sim_proxsensorfloatparam_far_clipping
                            0.5    # 50cm de detección
                        )
                        
                        # 2. Configurar qué entidades puede detectar (todo)
                        self.sim.setObjectInt32Param(
                            child,
                            4000,  # sim_proxintparam_entity_to_detect
                            1+2+4+8+16  # Todo tipo de entidades
                        )
                        
                        # 3. Aumentar el ángulo de apertura
                        try:
                            self.sim.setObjectFloatParam(
                                child,
                                4004,  # sim_proxsensorfloatparam_angle
                                0.5    # Ángulo de apertura más amplio
                            )
                        except:
                            pass
                        
                        sensor_count += 1
                        print(f"✅ Sensor {child_name} configurado")
                except:
                    continue
            
            print(f"Se configuraron {sensor_count} sensores para el robot")
            return sensor_count > 0
        
        except Exception as e:
            print(f"❌ Error al configurar sensores: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_connection(self):
        """Prueba la conexión enviando una solicitud simple"""
        if not self.connected:
            return False
            
        try:
            state = self.sim.getSimulationState()
            print(f"Conexión OK. Estado de simulación: {state}")
            return True
        except Exception as e:
            print(f"Error al probar conexión: {e}")
            self.connected = False
            return False
        
    def createDummy(self, size=0.01):
        """
        Crea un dummy (punto de referencia) en CoppeliaSim
        
        Args:
            size (float): Tamaño del dummy
        
        Returns:
            int o None: Handle del dummy creado o None si hay error
        """
        if not self.connected:
            print("❌ No se puede crear dummy: no hay conexión activa")
            return None
        
        try:
            # Intentar crear dummy
            dummy_handle = self.sim.createDummy(size)
            return dummy_handle
        except Exception as e:
            print(f"⚠️ Error al crear dummy: {e}")
            return None

    def setObjectAlias(self, handle, alias):
        """
        Establece un alias (nombre) para un objeto en CoppeliaSim
        
        Args:
            handle (int): Handle del objeto
            alias (str): Nombre a asignar
        
        Returns:
            bool: True si se pudo establecer el alias, False en caso contrario
        """
        if not self.connected:
            print("❌ No se puede establecer alias: no hay conexión activa")
            return False
        
        try:
            # Intentar establecer el alias/nombre
            # Nota: Algunas versiones de CoppeliaSim usan setObjectName en lugar de setObjectAlias
            try:
                self.sim.setObjectAlias(handle, alias)
            except:
                # Intentar con setObjectName si setObjectAlias no está disponible
                try:
                    self.sim.setObjectName(handle, alias)
                except:
                    print("⚠️ No se pudo establecer el nombre del objeto")
                    return False
            return True
        except Exception as e:
            print(f"⚠️ Error al establecer alias: {e}")
            return False

    def remove_robot(self, handle):
        """
        Elimina un robot de CoppeliaSim y todos sus componentes internos
        """
        if not self.connected:
            print("❌ No se puede eliminar robot: no hay conexión activa")
            return {
                "success": False,
                "error": "No hay conexión con CoppeliaSim"
            }
        
        try:
            print(f"Eliminando robot con handle: {handle}")
            
            # ENFOQUE MEJORADO: Remover por script más agresivo
            try:
                # Primero intentar eliminar el robot directamente con 'removeModel'
                try:
                    self.sim.removeModel(handle)
                    print("✅ Robot eliminado usando removeModel")
                    return {"success": True}
                except Exception as e:
                    print(f"No se pudo usar removeModel: {e}, intentando métodos alternativos...")
                
                # Obtener TODOS los objetos dependientes del robot, incluido el robot mismo
                children = []
                try:
                    children = self.sim.getObjectsInTree(handle, 0, 0)  # Todos los objetos en la jerarquía
                    print(f"Encontrados {len(children)} componentes internos")
                except Exception as tree_error:
                    print(f"Error al obtener objetos internos: {tree_error}")
                
                # Eliminar cada componente - empezando desde los hijos más profundos
                for child in reversed(children):
                    try:
                        self.sim.removeObject(child)
                        print(f"Componente interno eliminado: {child}")
                    except Exception as child_error:
                        print(f"Error al eliminar componente {child}: {child_error}")
                        
                # Después de eliminar todos los objetos específicos, realizar una limpieza general
                self.remove_all_robot_components()
                
                return {"success": True}
            
            except Exception as e:
                print(f"❌ Error general al eliminar robot: {e}")
                return {
                    "success": False,
                    "error": str(e)
                }
            
        except Exception as e:
            print(f"❌ Error general al eliminar robot: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def remove_all_robot_components(self):
        """
        Elimina TODOS los componentes del robot de la escena
        Versión compatible con la API detectada
        """
        if not self.connected:
            print("❌ No se puede realizar limpieza: no hay conexión activa")
            return {"success": False, "error": "No hay conexión con CoppeliaSim"}
        
        try:
            print("Iniciando limpieza completa de componentes...")
            
            # Lista de palabras clave para identificar componentes del robot
            robot_keywords = [
                "ultrasonic", "sensor", "pioneer", "p3dx", "motor", "left", "right", 
                "caster", "connection", "wheel", "joint", "visible", "Pioneer"
            ]
            
            # Usar getObjects() en lugar de getObjectsWithType()
            try:
                all_objects = self.sim.getObjects()
                print(f"Se encontraron {len(all_objects)} objetos en la escena")
                
                components_removed = 0
                
                # Procesamos todos los objetos
                for obj in all_objects:
                    try:
                        # Obtener el nombre del objeto
                        name = ""
                        try:
                            name = self.sim.getObjectName(obj)
                        except:
                            continue
                        
                        # Si es un objeto base, ignorarlo
                        if name.lower() in ["floor", "defaultlights", "defaultcamera"]:
                            continue
                        
                        # Comprobar si es un componente del robot
                        is_robot_part = False
                        name_lower = name.lower()
                        
                        for keyword in robot_keywords:
                            if keyword.lower() in name_lower:
                                is_robot_part = True
                                break
                        
                        # Eliminar si es parte del robot
                        if is_robot_part:
                            try:
                                self.sim.removeObject(obj)
                                components_removed += 1
                                print(f"✅ Componente eliminado: {name}")
                            except Exception as e:
                                print(f"❌ Error al eliminar {name}: {e}")
                        
                    except Exception as e:
                        print(f"❌ Error al procesar objeto: {e}")
                
                # También eliminar handles de cubos registrados
                for handle in self.created_cubes:
                    try:
                        self.sim.removeObject(handle)
                        components_removed += 1
                        print(f"✅ Cubo eliminado: {handle}")
                    except:
                        pass
                
                # Limpiar lista de cubos
                self.created_cubes = []
                
                return {
                    "success": True,
                    "components_removed": components_removed
                }
                
            except Exception as e:
                print(f"❌ Error al obtener objetos: {e}")
                return {"success": False, "error": f"Error al obtener objetos: {e}"}
                
        except Exception as e:
            print(f"❌ Error general al realizar limpieza: {e}")
            return {"success": False, "error": str(e)}
        
    def list_available_methods(self):
        """Lista los métodos disponibles en la API de CoppeliaSim"""
        if not self.connected:
            return []
            
        try:
            # Obtener todos los atributos del objeto sim
            all_attrs = dir(self.sim)
            
            # Filtrar para mostrar solo métodos relacionados con creación de objetos
            creation_methods = [attr for attr in all_attrs if "create" in attr.lower()]
            load_methods = [attr for attr in all_attrs if "load" in attr.lower()]
            object_methods = [attr for attr in all_attrs if "object" in attr.lower()]
            
            print("Métodos de creación disponibles:")
            for m in creation_methods:
                print(f"  - {m}")
                
            print("Métodos de carga disponibles:")
            for m in load_methods:
                print(f"  - {m}")
                
            print("Métodos de objeto disponibles:")
            for m in object_methods:
                print(f"  - {m}")
                
            return creation_methods + load_methods + object_methods
        except Exception as e:
            print(f"Error al listar métodos: {e}")
            return []
        
    def list_primitive_types(self):
        """Lista los tipos de primitivas disponibles en CoppeliaSim"""
        if not self.connected:
            return []
            
        try:
            # Buscar constantes relacionadas con primitivas
            sim_attrs = dir(self.sim)
            primitive_consts = [attr for attr in sim_attrs if "primitive" in attr.lower()]
            
            print("Constantes de primitivas disponibles:")
            for const in primitive_consts:
                try:
                    value = getattr(self.sim, const)
                    print(f"  - {const} = {value}")
                except:
                    pass
                    
            return primitive_consts
        except Exception as e:
            print(f"Error al listar primitivas: {e}")
            return []
        
    def send_command_to_coppelia(self, command):
        """
        Envía un comando al script principal en CoppeliaSim.
        
        Args:
            command: Diccionario con el comando a enviar
        
        Returns:
            bool: True si el comando se envió correctamente, False en caso contrario
        """
        if not self.connected:
            print("❌ No se puede enviar comando: no hay conexión activa")
            return False
        
        try:
            # Empaquetar y enviar el comando
            command_str = self.sim.packTable(command)
            self.sim.setStringSignal("CommandFromPython", command_str)
            
            print(f"✅ Comando enviado a CoppeliaSim: {command['action']}")
            return True
        except Exception as e:
            print(f"❌ Error al enviar comando: {e}")
            return False

    def update_object_handles(self):
        """
        Solicita al script principal que actualice los handles de todos los objetos.
        Útil después de crear nuevos objetos como el robot o cubos.
        
        Returns:
            bool: True si la solicitud se envió correctamente, False en caso contrario
        """
        command = {
            "action": "updateObjects"
        }
        return self.send_command_to_coppelia(command)

    def move_robot_velocity(self, left_velocity, right_velocity):
        """
        Envía un comando para mover el robot con velocidades específicas.
        
        Args:
            left_velocity: Velocidad para el motor izquierdo
            right_velocity: Velocidad para el motor derecho
        
        Returns:
            bool: True si el comando se envió correctamente, False en caso contrario
        """
        command = {
            "action": "moveRobot",
            "type": "velocity",
            "leftVelocity": float(left_velocity),
            "rightVelocity": float(right_velocity)
        }
        return self.send_command_to_coppelia(command)

    def move_robot_to_position(self, position):
        """
        Envía un comando para mover el robot a una posición específica.
        
        Args:
            position: Lista [x, y, z] con la posición objetivo
        
        Returns:
            bool: True si el comando se envió correctamente, False en caso contrario
        """
        command = {
            "action": "moveRobot",
            "type": "position",
            "position": position
        }
        return self.send_command_to_coppelia(command)

    def stop_robot(self):
        """
        Envía un comando para detener el robot.
        
        Returns:
            bool: True si el comando se envió correctamente, False en caso contrario
        """
        command = {
            "action": "moveRobot",
            "type": "stop"
        }
        return self.send_command_to_coppelia(command)

    def send_path_to_robot(self, waypoints):
        """
        Envía una ruta completa (lista de waypoints) para que el robot la siga.
        
        Args:
            waypoints: Lista de posiciones [x, y, z] que forman la ruta
        
        Returns:
            bool: True si el comando se envió correctamente, False en caso contrario
        """
        command = {
            "action": "moveRobot",
            "type": "path",
            "waypoints": waypoints
        }
        return self.send_command_to_coppelia(command)

    def get_robot_status(self):
        """
        Obtiene el estado actual del robot desde CoppeliaSim.
        
        Returns:
            dict: Diccionario con el estado del robot o None si hay error
        """
        if not self.connected:
            print("❌ No se puede obtener estado: no hay conexión activa")
            return None
        
        try:
            # Leer señal de estado
            status_str = self.sim.getStringSignal("RobotStatus")
            if status_str:
                # Desempaquetar estado
                status = self.sim.unpackTable(status_str)
                return status
            
            return None
        except Exception as e:
            print(f"❌ Error al obtener estado del robot: {e}")
            return None
        
    def update_cube_properties(self):
        """
        Solicita al script principal que actualice todas las propiedades de los cubos
        para asegurar que son obstáculos sólidos.
        
        Returns:
            bool: True si la solicitud se envió correctamente, False en caso contrario
        """
        if not self.connected:
            print("❌ No se puede actualizar propiedades: no hay conexión activa")
            return False
        
        # Primero actualizar los handles
        success = self.update_object_handles()
        
        if success:
            print("✅ Propiedades de cubos actualizadas")
        else:
            print("❌ Error al actualizar propiedades de cubos")
        
        return success