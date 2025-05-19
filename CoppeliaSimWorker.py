from PyQt5.QtCore import QThread, pyqtSignal

class CoppeliaSimWorker(QThread):
    connection_status = pyqtSignal(bool)
    progress_update = pyqtSignal(int)
    operation_result = pyqtSignal(bool, str)  # Para informar sobre resultados de operaciones
    operation_complete = pyqtSignal(str, object)  # Para informar cuando una operación termina con un resultado

    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.operation = None
        self.params = {}

    def set_task(self, operation, **params):
        self.operation = operation
        self.params = params

    def run(self):
        try:
            self.operation_result.emit(True, f"Iniciando operación: {self.operation}")
            
            if self.operation == 'connect':
                self.handle_connect()
            elif self.operation == 'disconnect':
                self.handle_disconnect()
            elif self.operation == 'test':
                self.handle_test()
            elif self.operation == 'create_cuboid':
                self.handle_create_cuboid()
            elif self.operation == 'remove_cuboid':
                self.handle_remove_cuboid()
            elif self.operation == 'remove_all_cuboids':
                self.handle_remove_all_cuboids()
            elif self.operation == 'start_sim':
                self.handle_start_sim()
            elif self.operation == 'pause_sim':
                self.handle_pause_sim()
            elif self.operation == 'stop_sim':
                self.handle_stop_sim()
            elif self.operation == 'create_robot':
                self.handle_create_robot()
            elif self.operation == 'remove_robot':
                self.handle_remove_robot()
            else:
                self.operation_result.emit(False, f"Operación desconocida: {self.operation}")
        
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(f"❌ Error en el worker: {e}\n{tb}")
            self.operation_result.emit(False, f"Error: {str(e)}")

    def handle_create_robot(self):
        """Maneja la creación de un robot en CoppeliaSim"""
        self.progress_update.emit(25)
        
        try:
            robot_type = self.params.get('robot_type', '/PioneerP3DX')
            position = self.params.get('position', [0, 0, 0])
            orientation = self.params.get('orientation', [0, 0, 0])
            row = self.params.get('row')
            col = self.params.get('col')
            
            self.progress_update.emit(50)
            
            # Crear el robot
            if hasattr(self.controller, 'create_robot'):
                result = self.controller.create_robot(robot_type, position, orientation)
            else:
                # Implementación alternativa si el método no existe
                result = self._create_robot(robot_type, position, orientation)
            
            self.progress_update.emit(75)
            
            if result.get('success', False):
                handle = result.get('handle')
                
                # Emitir señal de éxito
                self.operation_result.emit(True, f"Robot {robot_type} creado correctamente")
                
                # Devolver información sobre la operación
                complete_result = {
                    'handle': handle,
                    'robot_type': robot_type,
                    'row': row,
                    'col': col
                }
                
                self.operation_complete.emit('create_robot', complete_result)
                
            else:
                error = result.get('error', 'Error desconocido')
                self.operation_result.emit(False, f"Error al crear robot: {error}")
        
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(f"❌ Error al crear robot: {e}\n{tb}")
            self.operation_result.emit(False, f"Error al crear robot: {str(e)}")
        
        finally:
            self.progress_update.emit(100)

    def _create_robot(self, robot_type, position, orientation):
        """Método alternativo para crear un robot en CoppeliaSim"""
        try:
            # Intentar cargar el modelo del robot
            if robot_type.startswith('/'):
                robot_type = robot_type[1:]  # Eliminar barra inicial si existe
                
            # Construir ruta al modelo
            model_path = f"models/robots/mobile/{robot_type}.ttm"
            
            # Cargar el modelo
            try:
                robot_handle = self.controller.sim.loadModel(model_path)
                print(f"Modelo cargado con handle: {robot_handle}")
            except:
                # Intentar rutas alternativas
                try:
                    robot_handle = self.controller.sim.loadModel(f"models/mobile/{robot_type}.ttm")
                except:
                    try:
                        robot_handle = self.controller.sim.loadModel(f"models/robots/{robot_type}.ttm")
                    except:
                        try:
                            robot_handle = self.controller.sim.loadModel(f"{robot_type}.ttm")
                        except Exception as e:
                            print(f"Error al cargar modelo: {e}")
                            # Crear un cubo rojo como representación visual
                            robot_handle = self.controller.sim.createPrimitiveShape(0, 18, [0.3, 0.4, 0.2])
                            self.controller.sim.setShapeColor(robot_handle, None, 0, [1, 0, 0])  # Color rojo
            
            # Establecer la posición del robot
            if robot_handle:
                self.controller.sim.setObjectPosition(robot_handle, -1, position)
                
                # Configurar orientación si se proporciona
                if orientation:
                    self.controller.sim.setObjectOrientation(robot_handle, -1, orientation)
                
                return {
                    'success': True,
                    'handle': robot_handle
                }
            else:
                return {
                    'success': False,
                    'error': 'No se pudo crear el robot'
                }
                
        except Exception as e:
            print(f"Error en _create_robot: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def handle_connect(self):
        """Maneja la conexión a CoppeliaSim"""
        self.progress_update.emit(25)
        
        try:
            success = self.controller.connect()
            
            self.progress_update.emit(75)
            
            if success:
                self.operation_result.emit(True, "Conexión establecida con CoppeliaSim")
                self.connection_status.emit(True)
            else:
                self.operation_result.emit(False, "Error al establecer conexión con CoppeliaSim")
                self.connection_status.emit(False)
        
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(f"❌ Error al conectar: {e}\n{tb}")
            self.operation_result.emit(False, f"Error de conexión: {str(e)}")
            self.connection_status.emit(False)
        
        finally:
            self.progress_update.emit(100)

    def handle_disconnect(self):
        """Maneja la desconexión de CoppeliaSim"""
        self.progress_update.emit(25)
        
        try:
            success = self.controller.disconnect()
            
            self.progress_update.emit(75)
            
            if success:
                self.operation_result.emit(True, "Desconexión de CoppeliaSim completada")
                self.connection_status.emit(False)
            else:
                self.operation_result.emit(False, "Error al desconectar de CoppeliaSim")
        
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(f"❌ Error al desconectar: {e}\n{tb}")
            self.operation_result.emit(False, f"Error al desconectar: {str(e)}")
        
        finally:
            self.progress_update.emit(100)

    def handle_test(self):
        """Maneja la prueba de conexión a CoppeliaSim"""
        self.progress_update.emit(25)
        
        try:
            # Probar la conexión
            success = self.controller.test_connection() if hasattr(self.controller, 'test_connection') else False
            
            self.progress_update.emit(75)
            
            if success:
                self.operation_result.emit(True, "Prueba de conexión exitosa")
                self.connection_status.emit(True)
            else:
                self.operation_result.emit(False, "Error en prueba de conexión")
                self.connection_status.emit(False)
        
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(f"❌ Error en prueba de conexión: {e}\n{tb}")
            self.operation_result.emit(False, f"Error en prueba: {str(e)}")
            self.connection_status.emit(False)
        
        finally:
            self.progress_update.emit(100)

    def handle_start_sim(self):
        """Maneja el inicio de la simulación en CoppeliaSim"""
        self.progress_update.emit(25)
        
        try:
            success = self.controller.start_simulation()
            
            self.progress_update.emit(75)
            
            if success:
                self.operation_result.emit(True, "Simulación iniciada correctamente")
            else:
                self.operation_result.emit(False, "Error al iniciar simulación")
        
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(f"❌ Error al iniciar simulación: {e}\n{tb}")
            self.operation_result.emit(False, f"Error al iniciar simulación: {str(e)}")
        
        finally:
            self.progress_update.emit(100)

    def handle_pause_sim(self):
        """Maneja la pausa de la simulación en CoppeliaSim"""
        self.progress_update.emit(25)
        
        try:
            success = self.controller.suspend_simulation() if hasattr(self.controller, 'suspend_simulation') else False
            
            self.progress_update.emit(75)
            
            if success:
                self.operation_result.emit(True, "Simulación pausada correctamente")
            else:
                self.operation_result.emit(False, "Error al pausar simulación")
        
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(f"❌ Error al pausar simulación: {e}\n{tb}")
            self.operation_result.emit(False, f"Error al pausar simulación: {str(e)}")
        
        finally:
            self.progress_update.emit(100)

    def handle_stop_sim(self):
        """Maneja la detención de la simulación en CoppeliaSim"""
        self.progress_update.emit(25)
        
        try:
            success = self.controller.stop_simulation()
            
            self.progress_update.emit(75)
            
            if success:
                self.operation_result.emit(True, "Simulación detenida correctamente")
            else:
                self.operation_result.emit(False, "Error al detener simulación")
        
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(f"❌ Error al detener simulación: {e}\n{tb}")
            self.operation_result.emit(False, f"Error al detener simulación: {str(e)}")
        
        finally:
            self.progress_update.emit(100)
        
    def handle_remove_robot(self):
        """Maneja la eliminación de un robot de CoppeliaSim"""
        self.progress_update.emit(25)
        
        try:
            handle = self.params.get('handle')
            
            if handle is None:
                self.operation_result.emit(False, "Handle de robot no especificado")
                return
            
            self.progress_update.emit(50)
            
            # Eliminar el robot
            result = self.controller.remove_robot(handle) if hasattr(self.controller, 'remove_robot') else None
            
            if result is None:
                # Implementar eliminación básica si el método no existe
                try:
                    self.controller.sim.removeObject(handle)
                    result = {'success': True}
                except Exception as e:
                    result = {'success': False, 'error': str(e)}
            
            self.progress_update.emit(75)
            
            if result.get('success', False):
                self.operation_result.emit(True, "Robot eliminado correctamente")
                self.operation_complete.emit('remove_robot', {'success': True, 'handle': handle})
            else:
                error = result.get('error', 'Error desconocido')
                self.operation_result.emit(False, f"Error al eliminar robot: {error}")
        
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(f"❌ Error al eliminar robot: {e}\n{tb}")
            self.operation_result.emit(False, f"Error al eliminar robot: {str(e)}")
        
        finally:
            self.progress_update.emit(100)

    def handle_create_cuboid(self):
        """Maneja la creación de cuboides detectables"""
        self.progress_update.emit(25)
        
        try:
            position = self.params.get('position', [0, 0, 0.05])
            size = self.params.get('size', [0.1, 0.1, 0.1])
            color = self.params.get('color', [0.2, 0.2, 0.2])
            row = self.params.get('row')
            col = self.params.get('col')
            
            self.progress_update.emit(50)
            
            # Crear el cubo
            handle = self.controller.cargar_muro_personalizado(size, position, color)
            
            self.progress_update.emit(75)
            
            # Emitir señal con el resultado
            if handle is not None:
                self.operation_complete.emit('create_cuboid', {'handle': handle, 'row': row, 'col': col})
                self.operation_result.emit(True, f"Cubo creado con handle {handle}")
            else:
                self.operation_result.emit(False, "No se pudo crear el cubo")
        
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(f"❌ Error al crear cubo: {e}\n{tb}")
            self.operation_result.emit(False, f"Error al crear cubo: {str(e)}")
        
        finally:
            self.progress_update.emit(100)

    def handle_remove_cuboid(self):
        """Maneja la eliminación de un cubo específico"""
        self.progress_update.emit(25)
        
        try:
            handle = self.params.get('handle')
            
            if handle is None:
                self.operation_result.emit(False, "Handle no proporcionado")
                return
            
            self.progress_update.emit(50)
            
            # Eliminar el cubo
            if hasattr(self.controller, 'eliminar_cubo_por_handle'):
                result = self.controller.eliminar_cubo_por_handle(handle)
            else:
                try:
                    self.controller.sim.removeObject(handle)
                    result = True
                except:
                    result = False
            
            self.progress_update.emit(75)
            
            self.operation_result.emit(result, f"Cubo {handle} {'eliminado' if result else 'no eliminado'}")
            self.operation_complete.emit('remove_cuboid', {'success': result, 'handle': handle})
        
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(f"❌ Error al eliminar cubo: {e}\n{tb}")
            self.operation_result.emit(False, f"Error al eliminar cubo: {str(e)}")
        
        finally:
            self.progress_update.emit(100)

    def handle_remove_all_cuboids(self):
        """Maneja la eliminación de todos los cubos"""
        self.progress_update.emit(25)
        
        try:
            self.progress_update.emit(50)
            
            # Eliminar todos los cubos
            result = self.controller.eliminar_cubos()
            
            self.progress_update.emit(75)
            
            message = "Cubos eliminados exitosamente" if result else "No se pudieron eliminar todos los cubos"
            self.operation_result.emit(result, message)
            self.operation_complete.emit('remove_all_cuboids', result)
        
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(f"❌ Error al eliminar cubos: {e}\n{tb}")
            self.operation_result.emit(False, f"Error al eliminar cubos: {str(e)}")
        
        finally:
            self.progress_update.emit(100)