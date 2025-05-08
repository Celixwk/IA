import websockets
import asyncio
import json

class CoppeliaSimController:
    def __init__(self, uri="ws://127.0.0.1:23050"):
        self.uri = uri
        self.websocket = None
        self.connected = False
        self.created_cubes = []  # Lista para rastrear los handles de cubos creados
        self.floor_handle = None  # Handle del objeto floor (escenario)
    
    async def connect(self):
        """Establece conexión con CoppeliaSim"""
        try:
            self.websocket = await websockets.connect(self.uri)
            self.connected = True
            print("✅ Conectado a CoppeliaSim usando WebSocket")
            
            # Verificar comandos disponibles
            methods = await self.get_available_methods()
            print(f"ℹ️ Disponibles {len(methods)} métodos")
            
            # Buscar el handle del floor
            await self.find_floor_handle()
            
            return True
        except Exception as e:
            print(f"❌ Error de conexión: {e}")
            self.connected = False
            return False
    
    async def find_floor_handle(self):
        """Encuentra el handle del objeto floor en la escena"""
        try:
            # Obtener todos los objetos en la escena y buscar uno que se llame "Floor" o similar
            response = await self.send_request("sim.getObjectsInScene")
            data = json.loads(response)
            
            if data.get("success", False):
                all_objects = data.get("result", [])
                
                # Primero intentar obtener directamente por nombre
                for possible_name in ["/Floor", "Floor", "floor", "/floor"]:
                    try:
                        response = await self.send_request("sim.getObjectHandle", possible_name)
                        name_data = json.loads(response)
                        if name_data.get("success", False):
                            self.floor_handle = name_data.get("result")
                            print(f"✅ Handle del floor encontrado: {self.floor_handle}")
                            return
                    except:
                        pass
                
                # Si no funciona, verificar todos los objetos y buscar por tipo
                for obj_handle in all_objects:
                    # Intentar obtener el nombre del objeto
                    name_response = await self.send_request("sim.getObjectName", obj_handle, True)  # True para incluir ruta completa
                    name_data = json.loads(name_response)
                    
                    if name_data.get("success", False):
                        name = name_data.get("result", "")
                        if "floor" in name.lower() or "plane" in name.lower():
                            self.floor_handle = obj_handle
                            print(f"✅ Handle del floor encontrado por nombre: {self.floor_handle} ({name})")
                            return
                    
                    # Verificar tipo de objeto (8 es plano, que podría ser un floor)
                    type_response = await self.send_request("sim.getObjectType", obj_handle)
                    type_data = json.loads(type_response)
                    
                    if type_data.get("success", False) and type_data.get("result") == 8:
                        # Si es un plano, verificar su posición (los floors suelen estar en Y=0)
                        pos_response = await self.send_request("sim.getObjectPosition", obj_handle, -1)
                        pos_data = json.loads(pos_response)
                        
                        if pos_data.get("success", False):
                            position = pos_data.get("result", [0, 0, 0])
                            if abs(position[2]) < 0.01:  # Si está cerca de z=0
                                self.floor_handle = obj_handle
                                print(f"✅ Handle del floor encontrado por tipo y posición: {self.floor_handle}")
                                return
                
                # Si llegamos aquí, no se encontró el floor
                print("⚠️ No se encontró el floor automáticamente, usando la escena como padre")
                self.floor_handle = -1
            else:
                print("⚠️ No se pudo obtener objetos de la escena, usando la escena como padre")
                self.floor_handle = -1
        except Exception as e:
            print(f"❌ Error al buscar floor handle: {e}")
            self.floor_handle = -1  # Usar escena como padre por defecto
    
    async def disconnect(self):
        """Cierra la conexión con CoppeliaSim"""
        if self.connected and self.websocket:
            await self.websocket.close()
            self.connected = False
            print("ℹ️ Desconectado de CoppeliaSim")
            return True
        return False
    
    async def eliminar_cubos(self):
        """Elimina todos los cubos que fueron creados por esta instancia"""
        if not self.connected:
            print("❌ No se puede eliminar cubos: no hay conexión activa")
            return False
        
        if not self.created_cubes:
            print("ℹ️ No hay cubos registrados para eliminar")
            return True
        
        # Intentar primero eliminar todos los cubos de una vez
        try:
            print(f"🔄 Intentando eliminar {len(self.created_cubes)} cubos de una vez")
            # Verificar primero cuáles cubos existen realmente
            existing_cubes = []
            for handle in self.created_cubes:
                try:
                    check_response = await self.send_request("sim.getObjectType", handle)
                    check_data = json.loads(check_response)
                    if check_data.get("success", False):
                        existing_cubes.append(handle)
                except:
                    pass  # Si hay error, no incluir el handle
            
            if existing_cubes:
                # Intentar eliminar todos los objetos en un solo comando
                response = await self.send_request("sim.removeObjects", existing_cubes)
                data = json.loads(response)
                
                if data.get("success", False):
                    print(f"✅ Eliminados {len(existing_cubes)} cubos exitosamente")
                    self.created_cubes = []  # Limpiar lista de cubos
                    return True
                else:
                    print(f"⚠️ No se pudieron eliminar todos los cubos de una vez: {data.get('error', '')}")
            else:
                print("ℹ️ No hay cubos existentes para eliminar")
                self.created_cubes = []  # Limpiar lista de cubos
                return True
        except Exception as e:
            print(f"❌ Error al eliminar cubos en lote: {e}")
        
        # Si el método anterior falla, intentar eliminar uno por uno
        count = 0
        cubos_a_eliminar = self.created_cubes.copy()  # Trabajar con una copia
        
        for handle in cubos_a_eliminar:
            if await self.eliminar_cubo_por_handle(handle):
                count += 1
        
        print(f"🧹 Se eliminaron {count} cubos de {len(cubos_a_eliminar)} intentados")
        
        # Si se eliminaron todos o no había ninguno, limpiar la lista
        if count == len(cubos_a_eliminar) or len(cubos_a_eliminar) == 0:
            self.created_cubes = []
            
        return count > 0 or len(cubos_a_eliminar) == 0
    
    async def eliminar_cubo_por_handle(self, handle):
        """Elimina un cubo específico por su handle"""
        if not self.connected:
            print(f"❌ No se puede eliminar el cubo {handle}: no hay conexión activa")
            return False
        
        # Verificar que el handle no sea None
        if handle is None:
            print("❌ No se puede eliminar el cubo: handle es None")
            return False

        try:
            # Verificar primero si el objeto existe
            check_response = await self.send_request("sim.getObjectType", handle)
            check_data = json.loads(check_response)
            
            if not check_data.get("success", False):
                # El objeto ya no existe
                if handle in self.created_cubes:
                    self.created_cubes.remove(handle)
                print(f"⚠️ El objeto con handle {handle} ya no existe en la escena")
                return True
            
            # Intentar eliminar usando removeObjects (plural, más confiable)
            response = await self.send_request("sim.removeObjects", [handle], 1)  # 1 para eliminar de forma asíncrona
            data = json.loads(response)
            
            if data.get("success", False):
                if handle in self.created_cubes:
                    self.created_cubes.remove(handle)
                print(f"✅ Cubo con handle {handle} eliminado exitosamente")
                return True
            else:
                # Intentar con removeObject (singular)
                alt_response = await self.send_request("sim.removeObject", handle, 1)  # 1 para eliminar de forma asíncrona
                alt_data = json.loads(alt_response)
                
                if alt_data.get("success", False):
                    if handle in self.created_cubes:
                        self.created_cubes.remove(handle)
                    print(f"✅ Cubo con handle {handle} eliminado con removeObject")
                    return True
                else:
                    # Un último intento: deleteObject (método directo)
                    delete_response = await self.send_request("sim.deleteObject", handle)
                    delete_data = json.loads(delete_response)
                    
                    if delete_data.get("success", False):
                        if handle in self.created_cubes:
                            self.created_cubes.remove(handle)
                        print(f"✅ Cubo con handle {handle} eliminado con deleteObject")
                        return True
                    
                    # Si todo lo anterior falla, intentar ocultar el objeto
                    visible_response = await self.send_request("sim.setObjectInt32Parameter", handle, 10, 0)
                    visible_data = json.loads(visible_response)
                    
                    if visible_data.get("success", False):
                        if handle in self.created_cubes:
                            self.created_cubes.remove(handle)
                        print(f"✅ Cubo con handle {handle} ocultado (no pudo ser eliminado)")
                        return True
                    
                    print(f"❌ Error al eliminar cubo con handle {handle}: {data.get('error', '')}")
                    return False
        except Exception as e:
            print(f"❌ Excepción al eliminar cubo con handle {handle}: {e}")
            return False
    
    async def get_available_methods(self):
        """Obtiene los métodos disponibles en la API de CoppeliaSim"""
        if not self.connected:
            print("❌ No hay conexión activa")
            return []
        
        try:
            response = await self.send_request("meta")
            try:
                meta_data = json.loads(response)
                return meta_data.get("methods", [])
            except json.JSONDecodeError:
                print(f"❌ Error al decodificar respuesta JSON: {response}")
                return []
        except Exception as e:
            print(f"❌ Error al obtener métodos disponibles: {e}")
            return []
    
    async def send_request(self, function_name, *args):
        """Envía un comando a CoppeliaSim"""
        if not self.connected:
            print("❌ No hay conexión activa")
            return json.dumps({"success": False, "error": "No hay conexión activa"})
            
        request = {
            "func": function_name,
            "args": list(args)
        }
        
        request_json = json.dumps(request)
        print(f"📤 Enviando: {request_json}")
        
        try:
            await self.websocket.send(request_json)
            response = await self.websocket.recv()
            print(f"📥 Respuesta recibida: {response}")
            return response
        except Exception as e:
            print(f"❌ Error al enviar/recibir solicitud: {e}")
            self.connected = False  # Marcar como desconectado en caso de error
            return json.dumps({"success": False, "error": str(e)})
    
    async def test_connection(self):
        """Prueba la conexión realizando una consulta simple"""
        if not self.connected:
            print("❌ No hay conexión activa para probar")
            return False
        
        try:
            # Intentar obtener la versión de CoppeliaSim
            response = await self.send_request("sim.getInt32Parameter", 0)
            data = json.loads(response)
            
            return data.get("success", False)
        except Exception as e:
            print(f"❌ Error al probar conexión: {e}")
            return False
    
    async def start_simulation(self):
        """Inicia la simulación en CoppeliaSim"""
        if not self.connected:
            print("❌ No hay conexión activa. No se puede iniciar la simulación.")
            return False

        response = await self.send_request("sim.startSimulation")
        
        if response is None:
            print("❌ No se recibió respuesta al intentar iniciar simulación.")
            return False

        try:
            response_data = json.loads(response)
            success = response_data.get("success", False)
            if success:
                print("✅ Simulación iniciada correctamente")
            else:
                print(f"❌ Error al iniciar simulación: {response_data.get('error', 'Razón desconocida')}")
            return success
        except json.JSONDecodeError:
            print(f"❌ Error al interpretar respuesta: {response}")
            return False
    
    async def stop_simulation(self):
        """Detiene la simulación en CoppeliaSim"""
        if not self.connected:
            print("❌ No hay conexión activa. No se puede detener la simulación.")
            return False
            
        response = await self.send_request("sim.stopSimulation")
        
        if response is None:
            print("❌ No se recibió respuesta al intentar detener simulación.")
            return False
            
        try:
            response_data = json.loads(response)
            success = response_data.get("success", False)
            if success:
                print("✅ Simulación detenida correctamente")
            else:
                print(f"❌ Error al detener simulación: {response_data.get('error', 'Razón desconocida')}")
            return success
        except json.JSONDecodeError:
            print(f"❌ Error al interpretar respuesta: {response}")
            return False
    
    async def reset_simulation(self):
        """Resetea la simulación en CoppeliaSim"""
        if not self.connected:
            print("❌ No hay conexión activa. No se puede resetear la simulación.")
            return False
            
        # Primero asegurarnos de que la simulación está detenida
        await self.stop_simulation()
        
        # Eliminar todos los cubos creados
        await self.eliminar_cubos()
        
        # Resetear la simulación
        response = await self.send_request("sim.resetSimulation")
        
        if response is None:
            print("❌ No se recibió respuesta al intentar resetear simulación.")
            return False
            
        try:
            response_data = json.loads(response)
            success = response_data.get("success", False)
            if success:
                print("✅ Simulación reseteada correctamente")
                self.created_cubes = []  # Limpiar la lista de cubos ya que la simulación ha sido reseteada
            else:
                print(f"❌ Error al resetear simulación: {response_data.get('error', 'Razón desconocida')}")
            return success
        except json.JSONDecodeError:
            print(f"❌ Error al interpretar respuesta: {response}")
            return False
    
    async def create_cuboid(self, size=[0.1, 0.1, 0.1], position=[0, 0, 0.05], color=[1, 0, 0], parent_handle=None):
        """
        Crea un cuboide en la escena de CoppeliaSim
        
        Args:
            size: Tamaño del cuboide [x, y, z]
            position: Posición del cuboide [x, y, z]
            color: Color del cuboide [r, g, b] (0-1)
            parent_handle: Handle del objeto padre (0 para el floor, -1 para la escena)
        
        Returns:
            Handle del objeto creado o None si falla
        """
        if not self.connected:
            print("❌ No se puede crear cuboide: no hay conexión activa")
            return None
        
        # Si no se especifica un padre, usar el floor si está disponible
        if parent_handle is None:
            parent_handle = self.floor_handle if self.floor_handle is not None else -1
            
        print(f"🔄 Intentando crear cuboide - Tamaño: {size}, Posición: {position}, Color: {color}, Parent: {parent_handle}")
        
        # Intentar métodos diferentes en orden
        methods_to_try = [
            self._create_cuboid_with_createPureShape,  # Método más simple y directo
            self._create_cuboid_with_primitiveShape,   # Método alternativo
            self._create_cuboid_with_meshShape         # Método más complejo pero flexible
        ]
        
        for method in methods_to_try:
            try:
                result = await method(size, position, color, parent_handle)
                if result is not None:
                    # Asegurarnos de que el resultado es un entero válido antes de devolverlo
                    if isinstance(result, (int, float)) and result >= 0:
                        return int(result)  # Convertir a entero para asegurar compatibilidad
                    print(f"⚠️ El método devolvió un resultado no válido: {result}")
            except Exception as e:
                print(f"⚠️ Método de creación falló: {e}")
        
        print("❌ Todos los métodos de creación fallaron")
        return None
    
    async def _create_cuboid_with_createPureShape(self, size, position, color, parent_handle):
        """
        Método 1: Usar createPureShape - el método más simple y directo
        """
        try:
            # Crear el objeto usando createPureShape
            response = await self.send_request("sim.createPureShape", 0, 8, size, 1, None)
            data = json.loads(response)
            
            if not data.get("success", False):
                print(f"⚠️ No se pudo crear forma pura: {data.get('error', '')}")
                return None
            
            handle = data.get("result")
            
            if handle is None or not isinstance(handle, (int, float)) or handle < 0:
                print(f"⚠️ Handle recibido no es válido: {handle}")
                return None
            
            # Establecer la posición
            pos_response = await self.send_request("sim.setObjectPosition", handle, -1, position)
            pos_data = json.loads(pos_response)
            
            if not pos_data.get("success", False):
                print(f"⚠️ No se pudo establecer la posición: {pos_data.get('error', '')}")
                await self.eliminar_cubo_por_handle(handle)
                return None
            
            # Establecer el color usando los tres componentes posibles (ambiente, difuso, especular)
            color_components = [0, 1, 2]  # 0=ambiente, 1=difuso, 2=especular
            
            for component in color_components:
                try:
                    # El formato correcto es: (handle, colorComponent, objectOption, rgbData)
                    color_response = await self.send_request("sim.setShapeColor", handle, component, 0, color)
                    color_data = json.loads(color_response)
                    
                    if not color_data.get("success", False):
                        print(f"⚠️ No se pudo establecer el color componente {component}: {color_data.get('error', '')}")
                except Exception as e:
                    print(f"⚠️ Error al establecer color componente {component}: {e}")
            
            # Establecer el padre si es diferente de -1 (escena)
            if parent_handle != -1:
                try:
                    # Verificar que el handle del padre exista
                    parent_check_response = await self.send_request("sim.getObjectType", parent_handle)
                    parent_check_data = json.loads(parent_check_response)
                    
                    if parent_check_data.get("success", False):
                        parent_response = await self.send_request("sim.setObjectParent", handle, parent_handle, True)
                        parent_data = json.loads(parent_response)
                        
                        if not parent_data.get("success", False):
                            print(f"⚠️ No se pudo establecer el padre: {parent_data.get('error', '')}")
                            # Intentar método alternativo
                            try:
                                await self.send_request("sim.setObjectParent", handle, parent_handle, False)
                            except:
                                pass
                    else:
                        print(f"⚠️ El handle del padre {parent_handle} no es válido")
                except Exception as e:
                    print(f"⚠️ Error al establecer padre: {e}")
            
            # Registramos el handle como creado exitosamente
            print(f"✅ Cuboide creado exitosamente con handle: {handle}")
            self.created_cubes.append(handle)
            return handle
            
        except Exception as e:
            print(f"❌ Error al crear cuboide con createPureShape: {e}")
            return None
    
    async def _create_cuboid_with_primitiveShape(self, size, position, color, parent_handle):
        """
        Método 2: Usar createPrimitiveShape - método alternativo
        """
        try:
            # Crear cuboid primitiva (0=cuboid, 1=sphere, etc)
            response = await self.send_request("sim.createPrimitiveShape", 0, size, 0)
            data = json.loads(response)
            
            if not data.get("success", False):
                print(f"⚠️ No se pudo crear primitiva: {data.get('error', '')}")
                return None
            
            handle = data.get("result")
            
            if handle is None or not isinstance(handle, (int, float)) or handle < 0:
                print(f"⚠️ Handle recibido no es válido: {handle}")
                return None
            
            # Establecer la posición
            pos_response = await self.send_request("sim.setObjectPosition", handle, -1, position)
            pos_data = json.loads(pos_response)
            
            if not pos_data.get("success", False):
                print(f"⚠️ No se pudo establecer la posición: {pos_data.get('error', '')}")
                await self.eliminar_cubo_por_handle(handle)
                return None
            
            # Establecer el color para todos los componentes disponibles
            for component in [0, 1, 2]:  # ambiente, difuso, especular
                try:
                    await self.send_request("sim.setShapeColor", handle, component, 0, color)
                except Exception as e:
                    print(f"⚠️ Error al establecer color componente {component}: {e}")
            
            # Establecer el padre si es diferente de -1 (escena)
            if parent_handle != -1:
                try:
                    # Verificar que el handle del padre exista
                    parent_check_response = await self.send_request("sim.getObjectType", parent_handle)
                    parent_check_data = json.loads(parent_check_response)
                    
                    if parent_check_data.get("success", False):
                        await self.send_request("sim.setObjectParent", handle, parent_handle, True)
                    else:
                        print(f"⚠️ El handle del padre {parent_handle} no es válido")
                except Exception as e:
                    print(f"⚠️ Error al establecer padre: {e}")
            
            # Registramos el handle como creado exitosamente
            print(f"✅ Cuboide creado exitosamente con handle: {handle}")
            self.created_cubes.append(handle)
            return handle
            
        except Exception as e:
            print(f"❌ Error al crear cuboide con createPrimitiveShape: {e}")
            return None
    
    async def _create_cuboid_with_meshShape(self, size, position, color, parent_handle):
        """
        Método 3: Usar createMeshShape - más complejo pero flexible
        """
        try:
            # Crear vértices para un cubo
            half_x = size[0]/2
            half_y = size[1]/2
            half_z = size[2]/2
            
            vertices = [
                [-half_x, -half_y, -half_z],
                [half_x, -half_y, -half_z],
                [half_x, half_y, -half_z],
                [-half_x, half_y, -half_z],
                [-half_x, -half_y, half_z],
                [half_x, -half_y, half_z],
                [half_x, half_y, half_z],
                [-half_x, half_y, half_z]
            ]
            
            # Crear índices para las caras
            indices = [
                [0,1,2], [0,2,3],  # Base
                [4,7,6], [4,6,5],  # Top
                [0,4,5], [0,5,1],  # Lado 1
                [1,5,6], [1,6,2],  # Lado 2
                [2,6,7], [2,7,3],  # Lado 3
                [3,7,4], [3,4,0]   # Lado 4
            ]
            
            # Crear la forma
            response = await self.send_request("sim.createMeshShape", 0, 0, vertices, indices)
            data = json.loads(response)
            
            if not data.get("success", False):
                print(f"⚠️ No se pudo crear forma mesh: {data.get('error', '')}")
                return None
            
            handle = data.get("result")
            
            if handle is None or not isinstance(handle, (int, float)) or handle < 0:
                print(f"⚠️ Handle recibido no es válido: {handle}")
                return None
            
            # Establecer la posición
            pos_response = await self.send_request("sim.setObjectPosition", handle, -1, position)
            pos_data = json.loads(pos_response)
            
            if not pos_data.get("success", False):
                print(f"⚠️ No se pudo establecer la posición: {pos_data.get('error', '')}")
                await self.eliminar_cubo_por_handle(handle)
                return None
            
            # Establecer el color para todos los componentes disponibles
            for component in [0, 1, 2]:  # ambiente, difuso, especular
                try:
                    await self.send_request("sim.setShapeColor", handle, component, 0, color)
                except Exception as e:
                    print(f"⚠️ Error al establecer color componente {component}: {e}")
            
            # Establecer el padre si es diferente de -1 (escena)
            if parent_handle != -1:
                try:
                    # Verificar que el handle del padre exista
                    parent_check_response = await self.send_request("sim.getObjectType", parent_handle)
                    parent_check_data = json.loads(parent_check_response)
                    
                    if parent_check_data.get("success", False):
                        await self.send_request("sim.setObjectParent", handle, parent_handle, True)
                    else:
                        print(f"⚠️ El handle del padre {parent_handle} no es válido")
                except Exception as e:
                    print(f"⚠️ Error al establecer padre: {e}")
            
            # Registramos el handle como creado exitosamente
            print(f"✅ Cuboide creado exitosamente con handle: {handle}")
            self.created_cubes.append(handle)
            return handle
            
        except Exception as e:
            print(f"❌ Error al crear cuboide con createMeshShape: {e}")
            return None