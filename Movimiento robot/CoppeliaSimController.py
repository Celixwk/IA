import websockets
import asyncio
import json

class CoppeliaSimController:
    def __init__(self, uri="ws://127.0.0.1:23050"):
        self.uri = uri
        self.websocket = None
        self.connected = False
        self.created_cubes = []  # Lista para rastrear los handles de cubos creados
    
    async def connect(self):
        """Establece conexión con CoppeliaSim"""
        try:
            self.websocket = await websockets.connect(self.uri)
            self.connected = True
            print("Conectado a CoppeliaSim usando WebSocket")
            
            # Verificar comandos disponibles
            methods = await self.get_available_methods()
            print(f"Disponibles {len(methods)} métodos")
            return True
        except Exception as e:
            print(f"Error de conexión: {e}")
            self.connected = False
            return False
    
    async def crear_cubo(self, x=0.0, y=0.0, z=0.2):
        if not self.connected:
            raise Exception("No hay conexión activa con CoppeliaSim.")

        print(f"📦 Creando cubo en: {x}, {y}, {z}")

        # Crear el cubo
        response = await self.send_request("sim.createPrimitiveShape", 0, [0.2, 0.2, 0.2], 0)
        data = json.loads(response)

        if not data.get("success", False):
            print("❌ Error al crear el cubo:", data.get("error", ""))
            return None

        cubo_handle = data.get("result")

        # Posicionar el cubo
        response = await self.send_request("sim.setObjectPosition", cubo_handle, -1, [x, y, z])
        data = json.loads(response)

        if not data.get("success", False):
            print("❌ Error al posicionar el cubo:", data.get("error", ""))
            return None

        # Registrar el cubo creado
        self.created_cubes.append(cubo_handle)
        print(f"✅ Cubo creado y posicionado con handle: {cubo_handle}")
        return cubo_handle


    async def disconnect(self):
        """Cierra la conexión con CoppeliaSim"""
        if self.connected and self.websocket:
            await self.websocket.close()
            self.connected = False
            print("Desconectado de CoppeliaSim")
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
        
        count = 0
        cubos_a_eliminar = self.created_cubes.copy()  # Trabajar con una copia para evitar problemas al modificar durante la iteración
        
        for handle in cubos_a_eliminar:
            try:
                response = await self.send_request("sim.removeObject", handle)
                data = json.loads(response)
                
                if data.get("success", False):
                    self.created_cubes.remove(handle)
                    count += 1
                else:
                    print(f"⚠️ No se pudo eliminar el cubo {handle}: {data.get('error', '')}")
            except Exception as e:
                print(f"❌ Error al eliminar cubo {handle}: {e}")
        
        print(f"🧹 Se eliminaron {count} cubos de {len(cubos_a_eliminar)} intentados")
        return count > 0
    
    async def eliminar_cubo_por_handle(self, handle):
        """Elimina un cubo específico por su handle"""
        if not self.connected:
            print("❌ No se puede eliminar el cubo: no hay conexión activa")
            return False

        try:
            response = await self.send_request("sim.removeObject", handle)
            data = json.loads(response)
            
            if data.get("success", False):
                if handle in self.created_cubes:
                    self.created_cubes.remove(handle)
                print(f"✅ Cubo con handle {handle} eliminado exitosamente")
                return True
            else:
                print(f"❌ Error al eliminar cubo con handle {handle}: {data.get('error', '')}")
                return False
        except Exception as e:
            print(f"❌ Excepción al eliminar cubo con handle {handle}: {e}")
            return False
    
    async def get_available_methods(self):
        """Obtiene los métodos disponibles en la API de CoppeliaSim"""
        if not self.connected:
            print("No hay conexión activa")
            return []
        
        try:
            response = await self.send_request("meta")
            try:
                meta_data = json.loads(response)
                return meta_data.get("methods", [])
            except json.JSONDecodeError:
                print(f"Error al decodificar respuesta JSON: {response}")
                # Al menos estamos conectados, aunque no podamos interpretar la respuesta
                return []
        except Exception as e:
            print(f"Error al obtener métodos disponibles: {e}")
            return []
    
    async def send_request(self, function_name, *args):
        """Envía un comando a CoppeliaSim"""
        if not self.connected:
            print("No hay conexión activa")
            return None
            
        request = {
            "func": function_name,
            "args": list(args)
        }
        
        request_json = json.dumps(request)
        print(f"Enviando: {request_json}")
        
        try:
            await self.websocket.send(request_json)
            response = await self.websocket.recv()
            print(f"Respuesta recibida: {response}")
            return response
        except Exception as e:
            print(f"Error al enviar/recibir solicitud: {e}")
            self.connected = False  # Marcar como desconectado en caso de error
            return json.dumps({"success": False, "error": str(e)})
    
    async def start_simulation(self):
        """Inicia la simulación en CoppeliaSim"""
        if not self.connected:
            print("No hay conexión activa. No se puede iniciar la simulación.")
            return False

        response = await self.send_request("sim.startSimulation")
        
        if response is None:
            print("❌ No se recibió respuesta al intentar iniciar simulación.")
            return False

        try:
            response_data = json.loads(response)
            return response_data.get("success", False)
        except json.JSONDecodeError:
            print(f"❌ Error al interpretar respuesta: {response}")
            return False

    
    async def stop_simulation(self):
        """Detiene la simulación en CoppeliaSim"""
        response = await self.send_request("sim.stopSimulation")
        response_data = json.loads(response)
        return response_data.get("success", False)
    
    async def create_cuboid(self, size=[0.1, 0.1, 0.1], position=[0, 0, 0.05], color=None):
        """Crea un cuboide en la escena de CoppeliaSim"""
        if not self.connected:
            print("No se puede crear cuboide: no hay conexión activa")
            return None
            
        print(f"Intentando crear cuboide - Tamaño: {size}, Posición: {position}")
        
        try:
            # Vamos a intentar primero con un enfoque más directo
            # usando sim.createPureShape que es una alternativa común
            try:
                print("Intentando crear forma pura (cuboide)...")
                response = await self.send_request("sim.createPureShape", 0, 8, size, 1, None)
                response_data = json.loads(response)

                if not response_data.get("success", False) or response_data.get("result") is None:
                    raise Exception("❌ No se pudo obtener el handle del cuboide creado.")

                # Si el método no existe, intentaremos el método alternativo
                if not response_data.get("success", False):
                    raise Exception(f"Método no disponible: {response_data.get('error', '')}")
                    
            except Exception as e1:
                print(f"Error al crear forma pura: {e1}")
                print("Intentando método alternativo...")
                
                # Segundo intento con createPrimitiveShape
                response = await self.send_request("sim.createPrimitiveShape", 0, 0, size)
                response_data = json.loads(response)
                
                if not response_data.get("success", False):
                    print(f"Error al crear cuboide: {response_data.get('error', '')}")
                    
                    # Último intento - crear un objeto simple
                    print("Intentando crear objeto simple...")
                    response = await self.send_request("sim.createDummy", 0.1)
                    response_data = json.loads(response)
                    
                    if not response_data.get("success", False):
                        print("Todos los intentos de creación de objetos fallaron")
                        return None
            
            # Obtener el handle del objeto creado
            result = response_data.get("ret", [])
            object_handle = result[0] if isinstance(result, list) and result else None
            print(f"Objeto creado con éxito. Handle: {object_handle}")
            
            # Establecer la posición del objeto
            print(f"Estableciendo posición: {position}")
            pos_response = await self.send_request("sim.setObjectPosition", 
                                                  object_handle, -1, position)
            
            try:
                pos_data = json.loads(pos_response)
                if not pos_data.get("success", False):
                    print(f"Error al posicionar objeto: {pos_data.get('error', '')}")
            except json.JSONDecodeError:
                print(f"No se pudo interpretar la respuesta de posición: {pos_response}")
            
            # Intentar establecer el color si se especifica
            if color:
                try:
                    print(f"Estableciendo color: {color}")
                    color_response = await self.send_request("sim.setShapeColor", 
                                                           object_handle, None, 0, color)
                    
                    try:
                        color_data = json.loads(color_response)
                        if not color_data.get("success", False):
                            print(f"Error al establecer color: {color_data.get('error', '')}")
                    except json.JSONDecodeError:
                        print(f"No se pudo interpretar la respuesta de color: {color_response}")
                        
                except Exception as color_error:
                    print(f"Error al establecer color: {color_error}")
            
            # Registrar el handle del cubo creado
            if object_handle is not None:
                self.created_cubes.append(object_handle)
                print(f"Cubo registrado con handle: {object_handle}")
            
            return object_handle
            
        except Exception as e:
            print(f"Error general al crear objeto: {e}")
            return None
    
    async def test_connection(self):
        """Prueba la conexión enviando una solicitud simple"""
        if not self.connected:
            return False
            
        try:
            response = await self.send_request("sim.getSimulationState")
            response_data = json.loads(response)
            return response_data.get("success", False)
        except Exception as e:
            print(f"Error al probar conexión: {e}")
            return False