from coppeliasim_zmqremoteapi_client import RemoteAPIClient
import math
from heapq import heappush, heappop
from PyQt5.QtWidgets import (QMessageBox, QApplication)
from constants import GRID_SIZE, EMPTY, OBSTACLE, CELL_SIZE, START, END

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
            print(f"✅ Conectado a CoppeliaSim usando ZeroMQ. Estado de simulación: {state}")
            
            # Opcional: Verificar tiempo de simulación como prueba adicional
            try:
                sim_time = self.sim.getSimulationTime()
                print(f"Tiempo de simulación actual: {sim_time}")
            except Exception as e:
                print(f"Advertencia: No se pudo verificar tiempo de simulación: {e}")
                
            return True
        except Exception as e:
            print(f"❌ Error de conexión ZeroMQ: {e}")
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
    def execute_path(self, start_pos, end_pos, obstacles=None):
        """
        Implementa la navegación básica del robot Pioneer P3DX hacia un punto objetivo.
        
        Args:
            start_pos: Tupla (row, col) con la posición inicial del robot
            end_pos: Tupla (row, col) con la posición final deseada
            obstacles: Lista de obstáculos (no utilizada en esta implementación simplificada)
        """
        if not self.connected:
            print("❌ No se puede ejecutar recorrido: no hay conexión activa")
            return False
                
        print(f"Ejecutando recorrido desde {start_pos} hasta {end_pos}")
        
        try:
            # 1. Convertir coordenadas de cuadrícula a coordenadas CoppeliaSim
            reference_scale = 0.5
            
            # Calcular la posición objetivo
            end_x = (end_pos[1] - 5 + 0.5) * reference_scale
            end_y = (5 - end_pos[0] - 0.5) * reference_scale
            end_z = 0.1384  # Altura del Pioneer P3DX
            target_position = [end_x, end_y, end_z]
            
            print(f"Posición objetivo en coordenadas CoppeliaSim: {target_position}")
            
            # 2. Buscar el robot
            robot_handle = None
            possible_robot_names = ["Pioneer_p3dx", "/PioneerP3DX", "PioneerP3DX", "/Pioneer_p3dx"]
            
            for name in possible_robot_names:
                try:
                    robot_handle = self.sim.getObject(name)
                    if robot_handle:
                        print(f"Robot encontrado: {name}")
                        break
                except:
                    continue
            
            if not robot_handle:
                print("❌ No se pudo encontrar el robot")
                return False
            
            print(f"✅ Robot encontrado con handle: {robot_handle}")
            
            # 3. Buscar los motores
            left_motor = None
            right_motor = None
            
            motor_names = [
                ["Pioneer_p3dx_leftMotor", "Pioneer_p3dx_rightMotor"],
                ["/PioneerP3DX/leftMotor", "/PioneerP3DX/rightMotor"],
                ["leftMotor", "rightMotor"]
            ]
            
            for left_name, right_name in motor_names:
                try:
                    left_motor = self.sim.getObject(left_name)
                    right_motor = self.sim.getObject(right_name)
                    if left_motor and right_motor:
                        print(f"Motores encontrados: {left_name}, {right_name}")
                        break
                except:
                    continue
            
            if not left_motor or not right_motor:
                print("❌ No se pudieron encontrar los motores")
                return False
            
            # 4. Crear un objetivo visual (targetDummy)
            try:
                # Eliminar objetivo anterior si existe
                try:
                    old_target = self.sim.getObject("NavTarget")
                    self.sim.removeObject(old_target)
                except:
                    pass
                
                # Crear un dummy como objetivo
                target_handle = self.sim.createDummy(0.1)  # 10cm de diámetro
                self.sim.setObjectPosition(target_handle, -1, target_position)
                self.sim.setObjectAlias(target_handle, "NavTarget")
                
                # Intento de cambiar el color a blanco
                try:
                    self.sim.setShapeColor(target_handle, 0, 0, [1, 1, 1])
                except:
                    pass
                
                print(f"✅ Objetivo visual creado en: {target_position}")
            except Exception as e:
                print(f"⚠️ Error al crear objetivo visual: {e}")
            
            # 5. Iniciar navegación simple
            import threading
            import time
            import math
            
            # Variable de control para el hilo
            self.navigation_active = True
            
            def navigation_controller():
                """Controlador simple de navegación hacia el objetivo"""
                print("🚀 Iniciando navegación hacia el objetivo")
                
                try:
                    # Variables para control
                    max_velocity = 2.0  # Velocidad máxima
                    distance_threshold = 0.5  # Distancia para considerar llegada
                    
                    # Bucle de navegación
                    while self.navigation_active:
                        # Obtener posición y orientación del robot
                        robot_pos = self.sim.getObjectPosition(robot_handle, -1)
                        robot_orient = self.sim.getObjectOrientation(robot_handle, -1)
                        robot_angle = robot_orient[2]  # Yaw (rotación en Z)
                        
                        # Calcular distancia al objetivo
                        dx = target_position[0] - robot_pos[0]
                        dy = target_position[1] - robot_pos[1]
                        distance = math.sqrt(dx*dx + dy*dy)
                        
                        print(f"Distancia al objetivo: {distance:.2f}m")
                        
                        # Verificar llegada al objetivo
                        if distance < distance_threshold:
                            print("🏁 ¡Objetivo alcanzado!")
                            self.sim.setJointTargetVelocity(left_motor, 0)
                            self.sim.setJointTargetVelocity(right_motor, 0)
                            break
                        
                        # Calcular ángulo hacia el objetivo
                        target_angle = math.atan2(dy, dx)
                        
                        # Calcular error de orientación
                        orientation_error = target_angle - robot_angle
                        
                        # Normalizar el error a [-π, π]
                        while orientation_error > math.pi:
                            orientation_error -= 2 * math.pi
                        while orientation_error < -math.pi:
                            orientation_error += 2 * math.pi
                        
                        print(f"Orientación: actual={robot_angle:.2f}, objetivo={target_angle:.2f}, error={orientation_error:.2f}")
                        
                        # Calcular velocidades de los motores
                        if abs(orientation_error) > 0.3:  # Si la orientación es muy diferente, corregir primero
                            if orientation_error > 0:  # Girar a la izquierda
                                left_velocity = -max_velocity * 0.5
                                right_velocity = max_velocity * 0.5
                            else:  # Girar a la derecha
                                left_velocity = max_velocity * 0.5
                                right_velocity = -max_velocity * 0.5
                            print("Girando para orientarse al objetivo")
                        else:
                            # Avanzar con corrección de dirección
                            forward_speed = max_velocity * min(1.0, distance)
                            steering = orientation_error * 1.5
                            
                            left_velocity = forward_speed - steering
                            right_velocity = forward_speed + steering
                            print(f"Avanzando hacia el objetivo: L={left_velocity:.2f}, R={right_velocity:.2f}")
                        
                        # Aplicar velocidades a los motores
                        self.sim.setJointTargetVelocity(left_motor, left_velocity)
                        self.sim.setJointTargetVelocity(right_motor, right_velocity)
                        
                        # Pausa breve para no saturar la CPU
                        time.sleep(0.1)
                    
                    print("✅ Navegación finalizada")
                    
                except Exception as e:
                    print(f"❌ Error en navegación: {e}")
                    import traceback
                    traceback.print_exc()
                    
                finally:
                    # Detener motores al finalizar
                    try:
                        if left_motor and right_motor:
                            self.sim.setJointTargetVelocity(left_motor, 0)
                            self.sim.setJointTargetVelocity(right_motor, 0)
                            print("Robot detenido")
                    except:
                        pass
            
            # Iniciar el hilo de navegación
            nav_thread = threading.Thread(target=navigation_controller)
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
        
    def clear_scene(self):
        """
        Elimina todos los objetos de la escena excepto los elementos básicos como el suelo.
        """
        if not self.connected:
            print("❌ No se puede limpiar escena: no hay conexión activa")
            return False
        
        try:
            print("Limpiando escena...")
            
            # Lista de objetos que queremos preservar (no eliminar)
            preserved_objects = ["Floor", "DefaultCamera", "DefaultLight", "ResizableFloor"]
            preserved_handles = []
            
            # Obtener handles de objetos a preservar
            for obj_name in preserved_objects:
                try:
                    handle = self.sim.getObject(obj_name)
                    preserved_handles.append(handle)
                    print(f"Preservando objeto: {obj_name}")
                except:
                    pass
            
            # Obtener todos los objetos
            all_objects = self.sim.getObjects()
            print(f"Encontrados {len(all_objects)} objetos en total")
            
            # Eliminar objetos excepto los preservados
            removed_count = 0
            for obj in all_objects:
                if obj not in preserved_handles:
                    try:
                        obj_name = "<sin nombre>"
                        try:
                            obj_name = self.sim.getObjectName(obj)
                        except:
                            pass
                        
                        self.sim.removeObject(obj)
                        removed_count += 1
                        print(f"Eliminado objeto: {obj_name}")
                    except Exception as e:
                        print(f"Error al eliminar objeto {obj}: {e}")
            
            print(f"✅ Escena limpiada: {removed_count} objetos eliminados")
            return True
            
        except Exception as e:
            print(f"❌ Error al limpiar escena: {e}")
            import traceback
            traceback.print_exc()
            return False
        
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
    
    def execute_path_for_mobile_robot(self, start_pos, end_pos, obstacles=None):
        """
        Implementa la navegación para la escena mobileRobotPathPlanning, trabajando con
        el robot mobileRobot y el cilindro blanco como objetivo.
        
        Args:
            start_pos: Tupla (row, col) con la posición inicial (no utilizada ya que el robot ya está en la escena)
            end_pos: Tupla (row, col) con la posición final deseada
            obstacles: Lista de obstáculos (opcional, no utilizada en esta implementación)
        """
        if not self.connected:
            print("❌ No se puede ejecutar recorrido: no hay conexión activa")
            return False
                
        print(f"Ejecutando recorrido hacia posición {end_pos}")
        
        try:
            # 1. Convertir coordenadas de cuadrícula a coordenadas CoppeliaSim
            reference_scale = 0.5
            
            # Calcular la posición objetivo
            end_x = (end_pos[1] - 5 + 0.5) * reference_scale
            end_y = (5 - end_pos[0] - 0.5) * reference_scale
            end_z = 0.075  # Altura del cilindro blanco
            target_position = [end_x, end_y, end_z]
            
            print(f"Posición objetivo en coordenadas CoppeliaSim: {target_position}")
            
            # 2. Buscar el robot mobileRobot
            robot_handle = None
            try:
                robot_handle = self.sim.getObject("mobileRobot")
                print(f"Robot 'mobileRobot' encontrado con handle: {robot_handle}")
            except:
                try:
                    robot_handle = self.sim.getObject("/mobileRobot")
                    print(f"Robot '/mobileRobot' encontrado con handle: {robot_handle}")
                except Exception as e:
                    print(f"❌ No se pudo encontrar el robot mobileRobot: {e}")
                    return False
            
            # 3. Buscar el cilindro blanco (objetivo)
            target_handle = None
            target_names = ["Obstacle", "Cylinder", "Target", "targetObject", "Goal"]
            
            for name in target_names:
                try:
                    target_handle = self.sim.getObject(name)
                    print(f"Objetivo encontrado: '{name}' con handle: {target_handle}")
                    break
                except:
                    pass
            
            if not target_handle:
                # Buscar por color blanco entre todos los objetos
                print("Buscando cilindro blanco por propiedades...")
                try:
                    all_objects = self.sim.getObjects()
                    
                    for obj in all_objects:
                        try:
                            # Verificar si es una forma
                            obj_type = self.sim.getObjectType(obj)
                            if obj_type == 3:  # 3 = shape (forma)
                                # Intentar obtener el color
                                try:
                                    color = self.sim.getShapeColor(obj, 0, 0)
                                    # Si es blanco o cercano (R, G, B todos cerca de 1)
                                    if color and all(c > 0.8 for c in color):
                                        target_handle = obj
                                        print(f"Cilindro blanco encontrado con handle: {obj}")
                                        break
                                except:
                                    pass
                        except:
                            pass
                except Exception as e:
                    print(f"Error al buscar cilindro por propiedades: {e}")
            
            # Si aún no encontramos el objetivo, intentar buscar por otro método
            if not target_handle:
                # Buscar objetos en la jerarquía de la escena
                try:
                    cuboids = self.sim.getObjects()
                    for obj in cuboids:
                        try:
                            name = self.sim.getObjectName(obj)
                            if "Cuboid" in name or "Cylinder" in name or "Obstacle" in name:
                                # Verificar si es un cilindro (forma aproximadamente cilíndrica)
                                try:
                                    dims = self.sim.getShapeBB(obj)
                                    if dims and dims[0] > dims[2] * 0.8 and dims[1] > dims[2] * 0.8:
                                        target_handle = obj
                                        print(f"Encontrado objeto {name} como posible cilindro")
                                        break
                                except:
                                    pass
                        except:
                            pass
                except Exception as e:
                    print(f"Error al buscar en la jerarquía: {e}")
            
            # Si definitivamente no encontramos el objetivo, crear uno
            if not target_handle:
                try:
                    print("Creando un nuevo objetivo visual...")
                    target_handle = self.sim.createPrimitiveShape(2, [0.1, 0.1, 0.05])  # 2 = cilindro
                    self.sim.setObjectPosition(target_handle, -1, target_position)
                    self.sim.setShapeColor(target_handle, 0, 0, [1, 1, 1])  # Color blanco
                    self.sim.setObjectAlias(target_handle, "Target")
                    print(f"Objetivo creado con handle: {target_handle}")
                except Exception as e:
                    print(f"❌ Error al crear objetivo: {e}")
                    return False
            
            # 4. Mover el objetivo a la posición deseada
            self.sim.setObjectPosition(target_handle, -1, target_position)
            print(f"✅ Objetivo posicionado en: {target_position}")
            
            # 5. Iniciar la simulación si no está ya en ejecución
            try:
                sim_state = self.sim.getSimulationState()
                if sim_state != 1:  # 1 = simulación en ejecución
                    self.sim.startSimulation()
                    print("✅ Simulación iniciada")
                    import time
                    time.sleep(0.5)
            except Exception as e:
                print(f"⚠️ Advertencia al verificar estado de simulación: {e}")
            
            # 6. Intentar usar las funciones de navegación del script de la escena
            success = False
            
            # Intento 1: Buscar y llamar funciones de planificación de ruta en el script del robot
            try:
                planning_functions = [
                    "startPathPlanning", 
                    "startNavigation", 
                    "planPath", 
                    "computePath", 
                    "moveToTarget",
                    "navigateToGoal"
                ]
                
                for func_name in planning_functions:
                    try:
                        # Intentar llamar a la función en el script del robot
                        result = self.sim.callScriptFunction(
                            func_name, 
                            self.sim.scripttype_childscript,  # Script secundario asociado al robot
                            robot_handle,  # Objeto dueño del script
                            []  # Sin parámetros adicionales
                        )
                        print(f"Función '{func_name}' llamada en el robot, resultado: {result}")
                        success = True
                        break
                    except Exception as func_error:
                        print(f"Función {func_name} no encontrada en el robot: {func_error}")
            except Exception as e:
                print(f"Error al buscar funciones en el robot: {e}")
            
            # Intento 2: Probar con script principal
            if not success:
                try:
                    for func_name in planning_functions:
                        try:
                            # Intentar llamar a la función en el script principal
                            result = self.sim.callScriptFunction(
                                func_name, 
                                self.sim.scripttype_mainscript,  # Script principal
                                -1,  # No importa el objeto
                                []  # Sin parámetros adicionales
                            )
                            print(f"Función '{func_name}' llamada en script principal, resultado: {result}")
                            success = True
                            break
                        except Exception as func_error:
                            print(f"Función {func_name} no encontrada en script principal: {func_error}")
                except Exception as e:
                    print(f"Error al buscar funciones en script principal: {e}")
            
            # Intento 3: Enviar señales para activar la navegación
            if not success:
                try:
                    print("Enviando señales para iniciar navegación...")
                    signals = ["pathPlanning", "startNavigation", "targetPositionChanged"]
                    
                    for signal_name in signals:
                        try:
                            # Crear paquete de datos con la posición objetivo
                            data = {"position": target_position, "start": True}
                            packed_data = self.sim.packTable(data)
                            
                            # Enviar la señal
                            self.sim.setStringSignal(signal_name, packed_data)
                            print(f"Señal '{signal_name}' enviada")
                            success = True
                        except Exception as signal_error:
                            print(f"Error al enviar señal {signal_name}: {signal_error}")
                except Exception as e:
                    print(f"Error al enviar señales: {e}")
            
            # Intento 4: Implementar control directo del robot
            if not success:
                print("Implementando control directo como último recurso...")
                
                # Buscar motores del robot
                motors = []
                
                try:
                    # Obtener objetos hijos del robot
                    children = self.sim.getObjectsInTree(robot_handle)
                    
                    # Buscar motores entre los hijos
                    for child in children:
                        try:
                            # Verificar si es un joint (articulación/motor)
                            obj_type = self.sim.getObjectType(child)
                            if obj_type == 1:  # 1 = joint
                                motors.append(child)
                                name = self.sim.getObjectName(child)
                                print(f"Motor encontrado: {name}")
                        except:
                            pass
                except Exception as e:
                    print(f"Error al buscar motores: {e}")
                
                # Si encontramos al menos 2 motores, implementar navegación directa
                if len(motors) >= 2:
                    left_motor = motors[0]
                    right_motor = motors[1]
                    
                    # Iniciar navegación en un hilo separado
                    import threading
                    import time
                    import math
                    
                    # Variable de control para el hilo
                    self.navigation_active = True
                    
                    def navigation_controller():
                        """Controlador simple de navegación directa"""
                        print("🚀 Iniciando navegación directa")
                        
                        try:
                            # Variables para control
                            max_velocity = 2.0  # Velocidad máxima de los motores
                            distance_threshold = 0.3  # Distancia para considerar llegada (metros)
                            
                            # Bucle de navegación
                            while self.navigation_active:
                                try:
                                    # Obtener posiciones actuales
                                    robot_pos = self.sim.getObjectPosition(robot_handle, -1)
                                    target_pos = self.sim.getObjectPosition(target_handle, -1)
                                    robot_orient = self.sim.getObjectOrientation(robot_handle, -1)
                                    robot_angle = robot_orient[2]  # Yaw (rotación en Z)
                                    
                                    # Calcular vector y distancia al objetivo
                                    dx = target_pos[0] - robot_pos[0]
                                    dy = target_pos[1] - robot_pos[1]
                                    distance = math.sqrt(dx*dx + dy*dy)
                                    
                                    print(f"Distancia al objetivo: {distance:.2f}m")
                                    
                                    # Verificar llegada al objetivo
                                    if distance < distance_threshold:
                                        print("🏁 Objetivo alcanzado")
                                        # Detener motores
                                        self.sim.setJointTargetVelocity(left_motor, 0)
                                        self.sim.setJointTargetVelocity(right_motor, 0)
                                        self.navigation_active = False
                                        break
                                    
                                    # Calcular ángulo hacia el objetivo
                                    target_angle = math.atan2(dy, dx)
                                    
                                    # Calcular error de orientación
                                    orientation_error = target_angle - robot_angle
                                    
                                    # Normalizar a [-pi, pi]
                                    while orientation_error > math.pi:
                                        orientation_error -= 2 * math.pi
                                    while orientation_error < -math.pi:
                                        orientation_error += 2 * math.pi
                                    
                                    print(f"Ángulo al objetivo: {target_angle:.2f}, Error: {orientation_error:.2f}")
                                    
                                    # Determinar velocidades de los motores
                                    if abs(orientation_error) > 0.3:  # Si hay error grande de orientación
                                        # Girar en su lugar
                                        if orientation_error > 0:  # Girar a la izquierda
                                            left_velocity = -max_velocity * 0.5
                                            right_velocity = max_velocity * 0.5
                                        else:  # Girar a la derecha
                                            left_velocity = max_velocity * 0.5
                                            right_velocity = -max_velocity * 0.5
                                        print("Girando para orientarse al objetivo")
                                    else:
                                        # Avanzar con corrección de dirección
                                        forward_speed = max_velocity * min(1.0, distance)
                                        steering = orientation_error * 1.5
                                        
                                        left_velocity = forward_speed - steering
                                        right_velocity = forward_speed + steering
                                        print(f"Avanzando hacia objetivo: L={left_velocity:.2f}, R={right_velocity:.2f}")
                                    
                                    # Aplicar velocidades a los motores
                                    self.sim.setJointTargetVelocity(left_motor, left_velocity)
                                    self.sim.setJointTargetVelocity(right_motor, right_velocity)
                                    
                                except Exception as loop_error:
                                    print(f"Error en bucle de navegación: {loop_error}")
                                
                                # Pausa breve
                                time.sleep(0.1)
                            
                            print("✅ Navegación finalizada")
                            
                        except Exception as e:
                            print(f"❌ Error en controlador de navegación: {e}")
                            import traceback
                            traceback.print_exc()
                            
                        finally:
                            # Asegurar que los motores se detengan
                            try:
                                if left_motor and right_motor:
                                    self.sim.setJointTargetVelocity(left_motor, 0)
                                    self.sim.setJointTargetVelocity(right_motor, 0)
                                    print("Motores detenidos")
                            except:
                                pass
                    
                    # Iniciar el hilo de navegación
                    nav_thread = threading.Thread(target=navigation_controller)
                    nav_thread.daemon = True
                    nav_thread.start()
                    
                    success = True
                    print("✅ Control directo iniciado")
                else:
                    print("❌ No se encontraron suficientes motores para control directo")
            
            return success
            
        except Exception as e:
            print(f"❌ Error general al ejecutar recorrido: {e}")
            import traceback
            traceback.print_exc()
            return False
        
    def create_target(self, position):
        """
        Crea un punto objetivo (cilindro blanco) en la posición especificada.
        
        Args:
            position: Lista [x, y, z] con la posición donde crear el objetivo
        
        Returns:
            dict: Diccionario con el resultado {'success': bool, 'handle': int}
        """
        if not self.connected:
            print("❌ No se puede crear objetivo: no hay conexión activa")
            return {'success': False, 'handle': None}
        
        try:
            print(f"Creando punto objetivo en posición: {position}")
            
            # Crear un cilindro blanco
            size = [0.1, 0.1, 0.05]  # Diámetro x, diámetro y, altura
            target_handle = self.sim.createPrimitiveShape(2, 18, size)  # 2 = cilindro
            
            # Establecer la posición
            self.sim.setObjectPosition(target_handle, -1, position)
            
            # Establecer color blanco
            self.sim.setShapeColor(target_handle, 0, 0, [1, 1, 1])
            
            # Establecer alias para fácil referencia
            self.sim.setObjectAlias(target_handle, "Target")
            
            print(f"✅ Punto objetivo creado con handle: {target_handle}")
            return {'success': True, 'handle': target_handle}
            
        except Exception as e:
            print(f"❌ Error al crear punto objetivo: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'handle': None}
        
    def move_target(self, target_handle, position):
        """
        Mueve un objetivo existente a una nueva posición.
        
        Args:
            target_handle: Handle del objetivo a mover
            position: Lista [x, y, z] con la nueva posición
        
        Returns:
            bool: True si se movió correctamente, False en caso contrario
        """
        if not self.connected:
            print("❌ No se puede mover objetivo: no hay conexión activa")
            return False
        
        try:
            # Verificar que el objeto existe
            try:
                self.sim.getObjectPosition(target_handle, -1)
            except:
                print(f"❌ El objetivo con handle {target_handle} no existe")
                return False
            
            # Mover el objeto
            self.sim.setObjectPosition(target_handle, -1, position)
            print(f"✅ Objetivo movido a posición: {position}")
            return True
            
        except Exception as e:
            print(f"❌ Error al mover objetivo: {e}")
            return False
        
    def navigate_robot_to_target(self, robot_handle, target_handle):
        """
        Hace que el robot navegue hacia el objetivo.
        
        Args:
            robot_handle: Handle del robot
            target_handle: Handle del objetivo
        
        Returns:
            bool: True si se inició la navegación correctamente, False en caso contrario
        """
        if not self.connected:
            print("❌ No se puede iniciar navegación: no hay conexión activa")
            return False
        
        try:
            # Verificar que ambos objetos existen
            robot_pos = None
            target_pos = None
            
            try:
                robot_pos = self.sim.getObjectPosition(robot_handle, -1)
                target_pos = self.sim.getObjectPosition(target_handle, -1)
            except Exception as e:
                print(f"❌ Error al obtener posiciones: {e}")
                return False
            
            print(f"Iniciando navegación desde {robot_pos} hacia {target_pos}")
            
            # Buscar motores del robot
            motors = []
            
            try:
                # Obtener objetos hijos del robot
                children = self.sim.getObjectsInTree(robot_handle)
                
                # Buscar motores entre los hijos
                for child in children:
                    try:
                        name = self.sim.getObjectName(child)
                        if "motor" in name.lower() or "wheel" in name.lower() or "joint" in name.lower():
                            motors.append(child)
                            print(f"Motor encontrado: {name}")
                    except:
                        pass
            except Exception as e:
                print(f"Error al buscar motores: {e}")
            
            # Si no encontramos los motores por nombre, buscarlos por tipo
            if len(motors) < 2:
                try:
                    children = self.sim.getObjectsInTree(robot_handle)
                    for child in children:
                        try:
                            obj_type = self.sim.getObjectType(child)
                            if obj_type == 1:  # 1 = joint
                                motors.append(child)
                        except:
                            pass
                    print(f"Encontrados {len(motors)} motores por tipo de objeto")
                except:
                    pass
            
            # Si aún no tenemos suficientes motores, fallar
            if len(motors) < 2:
                print("❌ No se encontraron suficientes motores para el robot")
                return False
            
            # Seleccionar los dos primeros motores como izquierdo y derecho
            left_motor = motors[0]
            right_motor = motors[1]
            
            # Iniciar navegación en un hilo separado
            import threading
            import time
            import math
            
            # Variable de control para el hilo
            self.navigation_active = True
            
            def navigation_controller():
                """Controlador simple de navegación directa"""
                print("🚀 Iniciando navegación")
                
                try:
                    # Variables para control
                    max_velocity = 2.0  # Velocidad máxima
                    distance_threshold = 0.3  # Distancia para considerar llegada
                    
                    # Bucle de navegación
                    while self.navigation_active:
                        try:
                            # Obtener posiciones actuales
                            robot_pos = self.sim.getObjectPosition(robot_handle, -1)
                            target_pos = self.sim.getObjectPosition(target_handle, -1)
                            robot_orient = self.sim.getObjectOrientation(robot_handle, -1)
                            robot_angle = robot_orient[2]  # Yaw (rotación en Z)
                            
                            # Calcular vector al objetivo
                            dx = target_pos[0] - robot_pos[0]
                            dy = target_pos[1] - robot_pos[1]
                            distance = math.sqrt(dx*dx + dy*dy)
                            
                            print(f"Distancia al objetivo: {distance:.2f}m")
                            
                            # Verificar llegada
                            if distance < distance_threshold:
                                print("🏁 Objetivo alcanzado")
                                self.sim.setJointTargetVelocity(left_motor, 0)
                                self.sim.setJointTargetVelocity(right_motor, 0)
                                self.navigation_active = False
                                break
                            
                            # Calcular ángulo al objetivo
                            target_angle = math.atan2(dy, dx)
                            
                            # Calcular error de orientación
                            orientation_error = target_angle - robot_angle
                            
                            # Normalizar a [-pi, pi]
                            while orientation_error > math.pi:
                                orientation_error -= 2 * math.pi
                            while orientation_error < -math.pi:
                                orientation_error += 2 * math.pi
                            
                            print(f"Ángulo al objetivo: {target_angle:.2f}, Error: {orientation_error:.2f}")
                            
                            # Determinar velocidades
                            if abs(orientation_error) > 0.3:
                                # Girar en su lugar
                                if orientation_error > 0:
                                    left_velocity = -max_velocity * 0.5
                                    right_velocity = max_velocity * 0.5
                                else:
                                    left_velocity = max_velocity * 0.5
                                    right_velocity = -max_velocity * 0.5
                                print("Girando para orientarse al objetivo")
                            else:
                                # Avanzar con corrección
                                forward_speed = max_velocity * min(1.0, distance)
                                steering = orientation_error * 1.5
                                
                                left_velocity = forward_speed - steering
                                right_velocity = forward_speed + steering
                                print(f"Avanzando hacia objetivo: L={left_velocity:.2f}, R={right_velocity:.2f}")
                            
                            # Aplicar velocidades
                            self.sim.setJointTargetVelocity(left_motor, left_velocity)
                            self.sim.setJointTargetVelocity(right_motor, right_velocity)
                            
                        except Exception as e:
                            print(f"Error en bucle de navegación: {e}")
                        
                        time.sleep(0.1)
                    
                    print("✅ Navegación finalizada")
                    
                except Exception as e:
                    print(f"❌ Error en controlador de navegación: {e}")
                    import traceback
                    traceback.print_exc()
                    
                finally:
                    # Detener motores
                    try:
                        self.sim.setJointTargetVelocity(left_motor, 0)
                        self.sim.setJointTargetVelocity(right_motor, 0)
                        print("Motores detenidos")
                    except:
                        pass
            
            # Iniciar el hilo de navegación
            nav_thread = threading.Thread(target=navigation_controller)
            nav_thread.daemon = True
            nav_thread.start()
            
            print("✅ Navegación iniciada")
            return True
            
        except Exception as e:
            print(f"❌ Error al iniciar navegación: {e}")
            import traceback
            traceback.print_exc()
            return False
        
    def move_goal_dummy(self, target_position):
        """
        Mueve DIRECTAMENTE el objeto goalDummy a la posición especificada.
        
        Args:
            target_position: Lista [x, y, z] con la posición objetivo
        
        Returns:
            bool: True si se movió correctamente, False en caso contrario
        """
        if not self.connected:
            print("❌ No se puede mover goalDummy: no hay conexión activa")
            return False
        
        try:
            print(f"Moviendo goalDummy a posición: {target_position}")
            
            # 1. Buscar el goalDummy por su nombre exacto
            goal_dummy_handle = None
            try:
                # El nombre exacto es importante
                goal_dummy_handle = self.sim.getObject("goalDummy")
                print(f"✅ goalDummy encontrado con handle: {goal_dummy_handle}")
            except Exception as e1:
                print(f"No se pudo encontrar 'goalDummy': {e1}")
                try:
                    # Intentar con ruta completa
                    goal_dummy_handle = self.sim.getObject("/goalDummy")
                    print(f"✅ /goalDummy encontrado con handle: {goal_dummy_handle}")
                except Exception as e2:
                    print(f"No se pudo encontrar '/goalDummy': {e2}")
                    return False
            
            # 2. Mover directamente el goalDummy
            self.sim.setObjectPosition(goal_dummy_handle, -1, target_position)
            print(f"✅ goalDummy movido a posición: {target_position}")
            
            # 3. Verificar que se movió correctamente
            new_position = self.sim.getObjectPosition(goal_dummy_handle, -1)
            print(f"Nueva posición verificada: {new_position}")
            
            # 4. Si hay un cilindro hijo, asegurarse de que se mueva también
            try:
                cylinder_handle = self.sim.getObject("goalDummy/cylinder")
                self.sim.setObjectPosition(cylinder_handle, goal_dummy_handle, [0, 0, 0])
                print("✅ cylinder dentro de goalDummy alineado")
            except:
                # No hay problema si no podemos encontrar el cilindro
                pass
                
            return True
            
        except Exception as e:
            print(f"❌ Error al mover goalDummy: {e}")
            import traceback
            traceback.print_exc()
            return False
        
    def control_mobile_robot_path_planning(self, target_position):
        """
        Método optimizado para controlar la navegación del robot en la escena mobileRobotPathPlanning
        mediante diferentes enfoques combinados.
        
        Args:
            target_position: Lista [x, y, z] con la posición objetivo
        
        Returns:
            bool: True si se estableció correctamente, False en caso contrario
        """
        if not self.connected:
            print("❌ No hay conexión activa")
            return False
        
        try:
            print(f"Estableciendo destino en: {target_position}")
            
            # 1. Mover directamente el goalDummy (técnica principal)
            goal_dummy_handle = None
            try:
                # Intentar con diferentes variantes del nombre
                possible_names = ["goalDummy", "/goalDummy", "mobileRobot/goalDummy"]
                for name in possible_names:
                    try:
                        goal_dummy_handle = self.sim.getObject(name)
                        if goal_dummy_handle != -1:
                            print(f"✅ goalDummy encontrado como '{name}'")
                            break
                    except:
                        pass
                
                if goal_dummy_handle is None or goal_dummy_handle == -1:
                    print("⚠️ No se pudo encontrar el goalDummy por nombre, buscando por tipo...")
                    # Buscar por tipo de objeto (dummy)
                    all_objects = self.sim.getObjects()
                    for obj in all_objects:
                        try:
                            obj_type = self.sim.getObjectType(obj)
                            if obj_type == self.sim.object_type_dummy:
                                obj_name = self.sim.getObjectName(obj)
                                if "goal" in obj_name.lower() or "dummy" in obj_name.lower():
                                    goal_dummy_handle = obj
                                    print(f"✅ goalDummy encontrado por tipo: {obj_name}")
                                    break
                        except:
                            pass
            
                if goal_dummy_handle is None or goal_dummy_handle == -1:
                    print("❌ No se pudo encontrar el goalDummy")
                    return False
                
                # Mover el goalDummy a la posición objetivo
                self.sim.setObjectPosition(goal_dummy_handle, -1, target_position)
                print(f"✅ goalDummy movido a posición: {target_position}")
                
                # Opcional: verificar que se ha movido correctamente
                new_pos = self.sim.getObjectPosition(goal_dummy_handle, -1)
                print(f"Posición actual del goalDummy: {new_pos}")
            except Exception as e:
                print(f"⚠️ Error al mover goalDummy: {e}")
            
            # 2. Enviar señales para activar la navegación (enfoque complementario)
            try:
                # Crear las estructuras de datos necesarias
                pose_data = {"position": target_position, "orientation": [0, 0, 0]}
                path_data = {"start": True, "target": target_position}
                
                # Empaquetar los datos para las señales
                packed_pose = self.sim.packTable(pose_data)
                packed_path = self.sim.packTable(path_data)
                
                # Enviar múltiples señales - diferentes versiones pueden usar diferentes nombres
                signal_pairs = [
                    ("targetPose", packed_pose),
                    ("pathPlanningStart", packed_path),
                    ("mobileRobotTarget", packed_pose),
                    ("targetPosition", packed_pose),
                    ("startNavigation", packed_path),
                    ("goalPosition", packed_pose)
                ]
                
                for signal_name, signal_data in signal_pairs:
                    try:
                        self.sim.setStringSignal(signal_name, signal_data)
                        print(f"✅ Señal '{signal_name}' enviada")
                    except Exception as signal_error:
                        print(f"⚠️ Error al enviar señal '{signal_name}': {signal_error}")
            except Exception as e:
                print(f"⚠️ Error al enviar señales: {e}")
            
            # 3. Llamar a funciones del script en el simulador (enfoque alternativo)
            try:
                # Intentar llamar a funciones específicas en scripts de la escena
                script_targets = [
                    (self.sim.scripttype_mainscript, -1),  # Script principal
                    (self.sim.scripttype_childscript, goal_dummy_handle)  # Script del goalDummy
                ]
                
                function_names = [
                    "setTargetPosition", 
                    "startPathPlanning", 
                    "initiateNavigation",
                    "moveToPosition",
                    "setGoalPosition"
                ]
                
                for script_type, script_handle in script_targets:
                    for func_name in function_names:
                        try:
                            result = self.sim.callScriptFunction(
                                func_name, 
                                script_type, 
                                script_handle, 
                                [target_position]
                            )
                            print(f"✅ Función '{func_name}' llamada, resultado: {result}")
                        except:
                            pass
            except Exception as e:
                print(f"⚠️ Error al llamar funciones: {e}")
            
            # 4. Asegurar que la simulación está en marcha
            try:
                sim_state = self.sim.getSimulationState()
                if sim_state != 1:  # 1 = simulación en ejecución
                    self.sim.startSimulation()
                    print("✅ Simulación iniciada")
                else:
                    print("✅ Simulación ya en marcha")
            except Exception as e:
                print(f"⚠️ Error al verificar estado de simulación: {e}")
            
            print("✅ Configuración de destino completada")
            return True
            
        except Exception as e:
            print(f"❌ Error general: {e}")
            import traceback
            traceback.print_exc()
            return False
        
    def monitor_signals(self, duration=5.0):
        """
        Monitorea las señales de CoppeliaSim durante un período para entender 
        cómo funciona la planificación de ruta.
        
        Args:
            duration: Duración del monitoreo en segundos
        """
        if not self.connected:
            print("❌ No se pueden monitorear señales: no hay conexión activa")
            return
        
        import threading
        import time
        
        def monitor_thread():
            print("🔍 Iniciando monitoreo de señales...")
            start_time = time.time()
            
            # Lista de señales a monitorear
            signal_names = [
                "pathPlanningRequest", "targetPosition", "goalReached",
                "startNavigation", "mobileRobotTarget", "pathPlanningStart",
                "navigationStatus", "targetPose"
            ]
            
            while time.time() - start_time < duration:
                for signal_name in signal_names:
                    try:
                        signal_value = self.sim.getStringSignal(signal_name)
                        if signal_value:
                            # Intentar desempaquetar la tabla
                            try:
                                unpacked = self.sim.unpackTable(signal_value)
                                print(f"Señal '{signal_name}': {unpacked}")
                            except:
                                print(f"Señal '{signal_name}' recibida (formato no tabla)")
                    except:
                        pass
                
                time.sleep(0.5)
            
            print("🔍 Monitoreo de señales finalizado")
        
        # Iniciar en un hilo separado
        monitor_thread = threading.Thread(target=monitor_thread)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        print(f"✅ Monitoreo iniciado por {duration} segundos")

    def mark_end_point(self, row, col):
        """
        Marca específicamente el punto B (meta) y verifica que todo esté funcionando correctamente.
        
        Args:
            row: Fila en la cuadrícula
            col: Columna en la cuadrícula
        
        Returns:
            bool: True si se pudo marcar y verificar correctamente
        """
        if not self.is_connected:
            print("❌ No conectado a CoppeliaSim")
            return False
        
        try:
            print(f"Marcando punto B en posición ({row}, {col}) y verificando proceso completo")
            
            # 1. Marcar el punto en la cuadrícula
            self.grid_manager.clear_type(END)
            self.grid_manager.grid[row][col] = END
            self.grid_manager.end_set = True
            self.grid_widget.update()
            print("✅ Punto B marcado en la cuadrícula")
            
            # 2. Convertir a coordenadas de CoppeliaSim
            reference_scale = float(self.scale_combo.currentText())
            end_x = (col - GRID_SIZE/2 + 0.5) * reference_scale
            end_y = (GRID_SIZE/2 - row - 0.5) * reference_scale
            end_z = 0.075  # Altura del objetivo
            
            target_position = [end_x, end_y, end_z]
            print(f"✅ Coordenadas convertidas a CoppeliaSim: {target_position}")
            
            # 3. Verificar objetos en la escena
            try:
                # Imprimir todos los objetos de la escena para depuración
                all_objects = self.sim_controller.sim.getObjects()
                print(f"Objetos en la escena: {len(all_objects)}")
                
                relevant_objects = []
                for obj in all_objects:
                    try:
                        obj_name = self.sim_controller.sim.getObjectName(obj)
                        if "dummy" in obj_name.lower() or "goal" in obj_name.lower() or "robot" in obj_name.lower():
                            relevant_objects.append(f"{obj_name} (handle: {obj})")
                    except:
                        pass
                
                print(f"Objetos relevantes encontrados: {relevant_objects}")
            except Exception as e:
                print(f"⚠️ Error al listar objetos: {e}")
            
            # 4. Intentar mover el goalDummy directamente
            goal_found = False
            try:
                # Buscar el goalDummy con diferentes nombres posibles
                possible_names = ["goalDummy", "/goalDummy", "Dummy", "Goal", "Target"]
                for name in possible_names:
                    try:
                        goal_handle = self.sim_controller.sim.getObject(name)
                        print(f"✅ Objeto '{name}' encontrado con handle: {goal_handle}")
                        
                        # Intentar mover el objeto
                        self.sim_controller.sim.setObjectPosition(goal_handle, -1, target_position)
                        print(f"✅ '{name}' movido a posición: {target_position}")
                        
                        # Verificar nueva posición
                        new_pos = self.sim_controller.sim.getObjectPosition(goal_handle, -1)
                        print(f"Nueva posición verificada: {new_pos}")
                        
                        goal_found = True
                        break
                    except Exception as obj_error:
                        print(f"⚠️ Error con objeto '{name}': {obj_error}")
            except Exception as e:
                print(f"⚠️ Error al mover goalDummy: {e}")
            
            if not goal_found:
                print("❌ No se pudo encontrar o mover el goalDummy")
            
            # 5. Enviar señales para activar la planificación de ruta
            try:
                # Crear paquetes de datos para las señales
                pose_data = {"position": target_position}
                packed_data = self.sim_controller.sim.packTable(pose_data)
                
                # Enviar señal por varios nombres
                signals_to_try = [
                    "targetPose", 
                    "pathPlanningStart", 
                    "mobileRobotTarget",
                    "targetPosition", 
                    "startNavigation", 
                    "goalPosition"
                ]
                
                for signal_name in signals_to_try:
                    try:
                        self.sim_controller.sim.setStringSignal(signal_name, packed_data)
                        print(f"✅ Señal '{signal_name}' enviada con datos: {pose_data}")
                    except Exception as signal_error:
                        print(f"⚠️ Error al enviar señal '{signal_name}': {signal_error}")
            except Exception as e:
                print(f"⚠️ Error al enviar señales: {e}")
            
            # 6. Verificar estado de la simulación
            try:
                sim_state = self.sim_controller.sim.getSimulationState()
                print(f"Estado actual de simulación: {sim_state}")
                
                if sim_state != 1:  # 1 = simulación en ejecución
                    self.sim_controller.sim.startSimulation()
                    print("✅ Simulación iniciada")
                else:
                    print("✅ Simulación ya en marcha")
            except Exception as e:
                print(f"⚠️ Error al verificar simulación: {e}")
            
            print("✅ Proceso de marcado y verificación completo")
            return True
            
        except Exception as e:
            print(f"❌ Error general en mark_end_point: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    