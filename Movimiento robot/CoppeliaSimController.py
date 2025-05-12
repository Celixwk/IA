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
        """Inicia la simulación en CoppeliaSim"""
        if not self.connected:
            print("No hay conexión activa. No se puede iniciar la simulación.")
            return False

        try:
            self.sim.startSimulation()
            print("✅ Simulación iniciada correctamente")
            return True
        except Exception as e:
            print(f"❌ Error al iniciar simulación: {e}")
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
        """Crea un cuboide en la escena de CoppeliaSim"""
        if not self.connected:
            print("No se puede crear cuboide: no hay conexión activa")
            return None
            
        print(f"Intentando crear cuboide - Tamaño: {size}, Posición: {position}")
        
        try:
            # Crear forma con ZeroMQ API
            object_handle = self.sim.createPrimitiveShape(0, 0, size)  # 0 = cubo
            print(f"Objeto creado con éxito. Handle: {object_handle}")
            
            # Establecer la posición del objeto
            print(f"Estableciendo posición: {position}")
            self.sim.setObjectPosition(object_handle, -1, position)
            
            # Intentar establecer el color si se especifica
            if color:
                try:
                    print(f"Estableciendo color: {color}")
                    self.sim.setShapeColor(object_handle, None, 0, color)
                except Exception as color_error:
                    print(f"Error al establecer color: {color_error}")
            
            # Registrar el handle del cubo creado
            if object_handle is not None:
                self.created_cubes.append(object_handle)
                print(f"Cubo registrado con handle: {object_handle}")
            
            return object_handle
            
        except Exception as e:
            print(f"Error general al crear objeto: {e}")
            # Intento alternativo en caso de error
            try:
                # Alternativa usando createPureShape
                print("Intentando método alternativo...")
                object_handle = self.sim.createPureShape(0, 8, size, 1, None)
                
                # Posicionar el objeto
                self.sim.setObjectPosition(object_handle, -1, position)
                
                # Registrar handle
                self.created_cubes.append(object_handle)
                return object_handle
            except Exception as e2:
                print(f"Error en método alternativo: {e2}")
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
        Crea un robot en CoppeliaSim cargando el modelo desde la biblioteca de modelos
        """
        if not self.connected:
            print("❌ No se puede crear robot: no hay conexión activa")
            return {"success": False, "error": "No hay conexión activa"}
        
        try:
            print(f"Intentando cargar el modelo del robot {robot_type} en posición {position}")
            
            # Intentar varias rutas posibles para encontrar el modelo
            possible_paths = [
                "models/robots/mobile/pioneer p3dx.ttm",
                "models/mobile/pioneer p3dx.ttm",
                "models/robots/Pioneer_p3dx.ttm",
                "models/robots/mobile/Pioneer_p3dx.ttm"
            ]
            
            # Probar cada ruta hasta encontrar una que funcione
            robot_handle = None
            for path in possible_paths:
                try:
                    print(f"Intentando cargar modelo desde: {path}")
                    # La función loadModel puede retornar un handle o una lista de handles
                    result = self.sim.loadModel(path)
                    
                    # Manejar ambos casos (int o lista)
                    if isinstance(result, list) and len(result) > 0:
                        robot_handle = result[0]
                    elif isinstance(result, int):
                        robot_handle = result
                    
                    if robot_handle is not None:
                        print(f"✅ Modelo cargado correctamente desde: {path} con handle: {robot_handle}")
                        break
                except Exception as path_error:
                    print(f"No se pudo cargar desde {path}: {path_error}")
            
            # Si no se pudo cargar el modelo, intentar otra estrategia
            if robot_handle is None:
                # Intentar usar una API alternativa para encontrar el modelo pioneer
                try:
                    print("Intentando estrategia alternativa para encontrar el robot...")
                    # En algunas versiones, podemos buscar objetos por nombre
                    all_objects = self.sim.getObjects()
                    for obj in all_objects:
                        try:
                            name = self.sim.getObjectName(obj)
                            if "pioneer" in name.lower() or "p3dx" in name.lower():
                                print(f"Encontrado objeto existente: {name} con handle {obj}")
                                # Clonar el objeto existente
                                robot_handle = self.sim.copyObject(obj, -1, 0)
                                print(f"Robot clonado con handle: {robot_handle}")
                                break
                        except:
                            continue
                except Exception as e:
                    print(f"Error en estrategia alternativa: {e}")
            
            # Si aún no se ha encontrado un robot, intentar crear uno directamente
            if robot_handle is None:
                print("No se pudo cargar el modelo. Intentando crear un objeto simple...")
                try:
                    # Crear un objeto simple como fallback
                    # Primero intentar con createPureShape
                    robot_handle = self.sim.createPureShape(0, 16, [0.2, 0.3, 0.1], 1, None)
                    print(f"Objeto simple creado con handle: {robot_handle}")
                except Exception as e:
                    print(f"Error creando objeto simple: {e}")
                    return {"success": False, "error": "No se pudo crear ninguna representación del robot"}
            
            # Si llegamos aquí, tenemos un handle de robot. Ahora posicionarlo.
            print(f"Estableciendo posición del robot a: {position}")
            
            # Intentar varias formas de establecer la posición
            try:
                # Método 1: Establecer posición directamente
                self.sim.setObjectPosition(robot_handle, -1, position)
                print("Posición establecida usando setObjectPosition")
            except Exception as e1:
                print(f"Error con setObjectPosition: {e1}")
                try:
                    # Método 2: Establecer matriz de posición/orientación
                    # Crear una matriz de transformación simple (solo translación)
                    matrix = [
                        1, 0, 0, position[0],
                        0, 1, 0, position[1],
                        0, 0, 1, position[2],
                        0, 0, 0, 1
                    ]
                    self.sim.setObjectMatrix(robot_handle, -1, matrix)
                    print("Posición establecida usando setObjectMatrix")
                except Exception as e2:
                    print(f"Error con setObjectMatrix: {e2}")
                    try:
                        # Método 3: Establecer pose
                        pose = position + [0, 0, 0]  # posición + orientación
                        self.sim.setObjectPose(robot_handle, -1, pose)
                        print("Posición establecida usando setObjectPose")
                    except Exception as e3:
                        print(f"Error con setObjectPose: {e3}")
                        print("ADVERTENCIA: No se pudo posicionar el robot correctamente")
            
            # Verificar la posición actual
            try:
                current_pos = self.sim.getObjectPosition(robot_handle, -1)
                print(f"Posición actual del robot: {current_pos}")
            except:
                print("No se pudo obtener la posición actual")
            
            # Si orientación se proporciona, establecerla
            if orientation:
                try:
                    self.sim.setObjectOrientation(robot_handle, -1, orientation)
                    print(f"Orientación establecida: {orientation}")
                except Exception as e:
                    print(f"Error al establecer orientación: {e}")
            
            print(f"✅ Robot creado/posicionado con handle: {robot_handle}")
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
        Elimina un robot de CoppeliaSim
        
        Args:
            handle (int): Handle del robot a eliminar
        
        Returns:
            dict: Información sobre el resultado de la operación
        """
        if not self.connected:
            print("❌ No se puede eliminar robot: no hay conexión activa")
            return {
                "success": False,
                "error": "No hay conexión con CoppeliaSim"
            }
        
        try:
            print(f"Eliminando robot con handle: {handle}")
            
            # Verificar si el objeto existe
            exists = False
            try:
                # Intentar obtener la posición para verificar si existe
                self.sim.getObjectPosition(handle, -1)
                exists = True
            except:
                print(f"⚠️ El objeto con handle {handle} no existe o ya fue eliminado")
                return {
                    "success": False,
                    "error": f"El objeto con handle {handle} no existe"
                }
            
            if exists:
                # Eliminar el objeto - esto debería funcionar para cualquier objeto, incluyendo robots
                self.sim.removeObject(handle)
                print(f"✅ Robot con handle {handle} eliminado correctamente")
                return {
                    "success": True
                }
            
        except Exception as e:
            print(f"❌ Error al eliminar robot: {e}")
            return {
                "success": False,
                "error": str(e)
            }