from coppeliasim_zmqremoteapi_client import RemoteAPIClient

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
                
            return True
        except Exception as e:
            print(f"Error de conexión ZeroMQ: {e}")
            self.connected = False
            return False
    
    def crear_cubo(self, x=0.0, y=0.0, z=0.2):
        """Crea un cubo en la posición especificada"""
        if not self.connected:
            raise Exception("No hay conexión activa con CoppeliaSim.")

        print(f"📦 Creando cubo en: {x}, {y}, {z}")

        try:
            # Crear el cubo usando la API de ZeroMQ
            cubo_handle = self.sim.createPrimitiveShape(0, 0, [0.2, 0.2, 0.2])  # Tipo 0 = cubo
            
            # Posicionar el cubo
            self.sim.setObjectPosition(cubo_handle, -1, [x, y, z])
            
            # Registrar el cubo creado
            self.created_cubes.append(cubo_handle)
            print(f"✅ Cubo creado y posicionado con handle: {cubo_handle}")
            return cubo_handle
        except Exception as e:
            print(f"❌ Error al crear cubo: {e}")
            return None

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
        """Elimina todos los cubos que fueron creados por esta instancia"""
        if not self.connected:
            print("❌ No se puede eliminar cubos: no hay conexión activa")
            return False
        
        if not self.created_cubes:
            print("ℹ️ No hay cubos registrados para eliminar")
            return True
        
        count = 0
        cubos_a_eliminar = self.created_cubes.copy()  # Trabajar con una copia para evitar problemas al modificar durante la iteración
        
        for handle in cubos_a_eliminar:
            try:
                print(f"Intentando eliminar cubo con handle: {handle}")
                self.sim.removeObject(handle)
                
                if handle in self.created_cubes:
                    self.created_cubes.remove(handle)
                count += 1
                print(f"✅ Cubo {handle} eliminado correctamente")
            except Exception as e:
                print(f"❌ Error al eliminar cubo {handle}: {e}")
        
        print(f"🧹 Se eliminaron {count} cubos de {len(cubos_a_eliminar)} intentados")
        return count > 0
    
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
    
    def create_cuboid(self, size=[0.1, 0.1, 0.1], position=[0, 0, 0.05], color=None):
        """
        Crea un cuboide en la escena de CoppeliaSim con configuración mejorada para detección
        """
        if not self.connected:
            print("No se puede crear cuboide: no hay conexión activa")
            return None
                
        print(f"Intentando crear cuboide - Tamaño: {size}, Posición: {position}")
        
        try:
            # Crear un objeto detectable - usar flags específicos para asegurar detectabilidad
            try:
                # Bit 0: collidable (1), Bit 1: measurable (2), Bit 2: detectable (4), 
                # Bit 3: renderable (8), Bit 4: detectable by ultrasonic sensors (16)
                # Total: 31 (todos los bits activados)
                object_handle = self.sim.createPrimitiveShape(0, 31, size, 1, None)
            except:
                # Método alternativo si el anterior falla
                object_handle = self.sim.createPureShape(0, 31, size, 1, None)
                
            print(f"Cubo creado. Handle: {object_handle}")
            
            # Establecer la posición del objeto
            print(f"Estableciendo posición: {position}")
            self.sim.setObjectPosition(object_handle, -1, position)
            
            # Establecer color si se especifica
            if color:
                try:
                    self.sim.setShapeColor(object_handle, None, 0, color)
                except Exception as color_error:
                    print(f"Error al establecer color: {color_error}")
            
            # CONFIGURACIÓN MEJORADA PARA SENSORES ULTRASÓNICOS
            try:
                # 1. Hacer el objeto estático y respondable
                self.sim.setObjectInt32Param(object_handle, 3003, 1)  # static
                self.sim.setObjectInt32Param(object_handle, 3004, 1)  # respondable
                
                # 2. Configurar para que sea detectado por todos los tipos de sensores
                self.sim.setObjectSpecialProperty(object_handle, 31)  # todos los tipos
                
                # 3. Hacer que sea visible y colisionable en TODAS las capas
                self.sim.setObjectInt32Param(object_handle, 10100, 65535)  # visible en todas las capas
                self.sim.setObjectInt32Param(object_handle, 10101, 65535)  # colisionable en todas las capas
                
                # 4. Propiedades extra para mejorar la detectabilidad ultrasónica
                # Configurar respuesta ultrasónica (si está disponible en tu versión)
                try:
                    # Intento 1: usando setObjectFloatParam
                    self.sim.setObjectFloatParam(object_handle, 3005, 1.0)  # respuesta ultrasónica máxima
                except:
                    # Intento 2: usando setEngineFloatParam
                    try:
                        self.sim.setEngineFloatParam(self.sim.sim_obj_float_par_ultrasonic_response, object_handle, 1.0)
                    except:
                        pass
                
                print(f"✅ Cubo configurado completamente para detección")
            except Exception as e:
                print(f"⚠️ Error al configurar propiedades avanzadas: {e}")
            
            # Registrar el handle del cubo creado
            if object_handle is not None:
                if hasattr(self, 'created_cubes'):
                    self.created_cubes.append(object_handle)
                else:
                    self.created_cubes = [object_handle]
                print(f"Cubo registrado con handle: {object_handle}")
            
            return object_handle
                
        except Exception as e:
            print(f"Error general al crear objeto: {e}")
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
        
    def create_robot(self, robot_type, position, orientation=None):
        """
        Crea un robot en CoppeliaSim y configura sus sensores para detectar obstáculos
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
                    "Pioneer_p3dx.ttm"
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
                    robot_handle = self.sim.createPrimitiveShape(0, 0, [0.3, 0.4, 0.2])  # Cubo para representar el robot
                    self.sim.setShapeColor(robot_handle, None, 0, [1, 0, 0])  # Color rojo
                    print(f"Objeto visual creado con handle: {robot_handle}")
                except Exception as shape_error:
                    print(f"Error al crear forma visual: {shape_error}")
                    return {"success": False, "error": "No se pudo crear ninguna representación del robot"}
                    
            # Si llegamos aquí, tenemos un handle de robot. Posicionarlo.
            try:
                print(f"Estableciendo posición del robot a: {position}")
                self.sim.setObjectPosition(robot_handle, -1, position)
                
                # Verificar si el posicionamiento funcionó
                current_pos = self.sim.getObjectPosition(robot_handle, -1)
                print(f"Posición actual del robot: {current_pos}")
            except Exception as pos_error:
                print(f"Error al posicionar el robot: {pos_error}")
            
            # NUEVO: Configurar los sensores del robot
            try:
                print("Configurando sensores del robot...")
                
                # Buscar sensores ultrasónicos del robot
                sensors = []
                try:
                    # Obtener todos los objetos bajo el robot
                    children = self.sim.getObjectsInTree(robot_handle, 0, 0)  # Todos los objetos bajo el robot
                    
                    # Buscar objetos que podrían ser sensores
                    for child in children:
                        try:
                            # Obtener el nombre y tipo del objeto
                            name = self.sim.getObjectName(child)
                            obj_type = self.sim.getObjectType(child)
                            
                            # Verificar si es un sensor de proximidad
                            if obj_type == 5:  # object_proximitysensor_type = 5
                                sensors.append(child)
                                print(f"Sensor encontrado: {name}")
                                
                                # Configurar el sensor para detectar todo tipo de objetos
                                self.sim.setObjectInt32Param(child, 4000, 1+2+4+8)  # proxintparam_entity_to_detect = 4000
                                
                                # Aumentar el rango de detección
                                self.sim.setObjectFloatParam(child, 4001, 0.5)  # proxsensorfloatparam_far_clipping = 4001
                        except Exception as sensor_error:
                            print(f"Error al procesar posible sensor: {sensor_error}")
                    
                    print(f"Se encontraron y configuraron {len(sensors)} sensores")
                except Exception as tree_error:
                    print(f"Error al buscar sensores en el árbol de objetos: {tree_error}")
                
                # Si no se encontraron sensores, buscar de otra manera
                if len(sensors) == 0:
                    print("No se encontraron sensores en el robot. Buscando por nombre...")
                    
                    # Intentar encontrar sensores por nombre específico del Pioneer
                    sensor_names = [
                        "Pioneer_p3dx_ultrasonicSensor",
                        "ultrasonicSensor",
                        "Pioneer_p3dx_sensor"
                    ]
                    
                    for base_name in sensor_names:
                        for i in range(1, 17):  # El Pioneer p3dx tiene 16 sensores ultrasónicos
                            sensor_name = f"{base_name}{i}"
                            try:
                                sensor_handle = self.sim.getObject(sensor_name)
                                sensors.append(sensor_handle)
                                print(f"Sensor encontrado por nombre: {sensor_name}")
                                
                                # Configurar el sensor
                                self.sim.setObjectInt32Param(sensor_handle, 4000, 1+2+4+8)
                                self.sim.setObjectFloatParam(sensor_handle, 4001, 0.5)
                            except:
                                # No existe un sensor con este nombre, ignorar
                                pass
                    
                    print(f"Se encontraron {len(sensors)} sensores por nombre")
                
                # Si aún no hay sensores, crear algunos básicos
                if len(sensors) == 0:
                    print("No se encontraron sensores existentes. Creando sensores básicos...")
                    
                    # Posiciones relativas al robot para los nuevos sensores
                    sensor_positions = [
                        [0.15, 0.1, 0.1],   # Frente-derecha
                        [0.15, 0, 0.1],     # Frente-centro
                        [0.15, -0.1, 0.1]   # Frente-izquierda
                    ]
                    
                    for i, pos in enumerate(sensor_positions):
                        try:
                            # Crear sensor de proximidad
                            sensor = self.sim.createProximitySensor(1, 16, 0.02, [0.1, 0.1, 0.2, 0.5])  # 1 = ray type
                            sensors.append(sensor)
                            
                            # Establecer como hijo del robot
                            self.sim.setObjectParent(sensor, robot_handle, True)
                            
                            # Posicionar el sensor relativo al robot
                            self.sim.setObjectPosition(sensor, robot_handle, pos)
                            
                            # Configurar el sensor
                            self.sim.setObjectInt32Param(sensor, 4000, 1+2+4+8)
                            self.sim.setObjectFloatParam(sensor, 4001, 0.5)
                            
                            print(f"Sensor {i+1} creado en posición {pos}")
                        except Exception as create_error:
                            print(f"Error al crear sensor {i+1}: {create_error}")
                    
                    print(f"Se crearon {len(sensor_positions)} sensores básicos")
                
            except Exception as sensor_setup_error:
                print(f"Error general al configurar sensores: {sensor_setup_error}")
            
            print(f"✅ Robot creado y configurado con handle: {robot_handle}")
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
        
    def configure_sensors_for_obstacle_detection(self, robot_handle):
        """
        Configuración mejorada de sensores del robot para detectar obstáculos específicamente
        """
        if not self.connected:
            print("❌ No se puede configurar sensores: no hay conexión activa")
            return False
            
        try:
            print("🔍 Configurando sensores para detección de obstáculos...")
            
            # Obtener todos los objetos hijos del robot
            children = []
            try:
                children = self.sim.getObjectsInTree(robot_handle, 0, 0)
                print(f"Encontrados {len(children)} objetos relacionados con el robot")
            except Exception as e:
                print(f"Error al obtener hijos: {e}")
                return False
            
            # Identificar sensores ultrasónicos
            sensors_configured = 0
            
            for child in children:
                try:
                    # Obtener el nombre y tipo del objeto
                    name = self.sim.getObjectName(child).lower()
                    obj_type = self.sim.getObjectType(child)
                    
                    # Los sensores en Pioneer P3DX normalmente tienen nombres que contienen:
                    if ("sensor" in name or "ultrasonic" in name or obj_type == 5):
                        print(f"Sensor encontrado: {name} (tipo: {obj_type})")
                        
                        # Configuración crítica para detectar TODOS los objetos
                        try:
                            # Detectar todo tipo de objetos
                            self.sim.setObjectInt32Param(child, 4000, 1+2+4+8+16)  # Todos los tipos de entidades
                            
                            # Aumentar el rango de detección 
                            self.sim.setObjectFloatParam(child, 4001, 1.0)  # proxsensorfloatparam_far_clipping
                            
                            # Ajustar tamaño del cono ultrasónico
                            self.sim.setObjectFloatParam(child, 4004, 0.1)  # Ancho del sensor
                            
                            # Mejorar resolución de detección
                            self.sim.setObjectInt32Param(child, 4003, 5)  # Resolución alta
                            
                            # Hacer que el sensor pueda colisionar con cualquier objeto
                            self.sim.setObjectInt32Param(child, 10121, 65535)  # Colisión con todas las capas
                            
                            sensors_configured += 1
                            print(f"✅ Sensor {name} configurado correctamente")
                        except Exception as e:
                            print(f"⚠️ Error al configurar sensor {name}: {e}")
                            pass
                except:
                    continue
            
            print(f"✅ {sensors_configured} sensores configurados para detección de obstáculos")
            return sensors_configured > 0
        
        except Exception as e:
            print(f"❌ Error general al configurar sensores: {e}")
            return False