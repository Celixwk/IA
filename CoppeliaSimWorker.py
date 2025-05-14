from PyQt5.QtCore import QThread, pyqtSignal

class CoppeliaSimWorker(QThread):
    connection_status = pyqtSignal(bool)
    progress_update = pyqtSignal(int)
    operation_result = pyqtSignal(bool, str)  # Para informar sobre resultados de operaciones
    operation_complete = pyqtSignal(str, object)  # Señal para informar cuando una operación termina con un resultado

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
        """
        Maneja la creación de un robot en CoppeliaSim
        """
        self.progress_update.emit(25)
        
        try:
            robot_type = self.params.get('robot_type', '/PioneerP3DX')
            position = self.params.get('position', [0, 0, 0])
            orientation = self.params.get('orientation', [0, 0, 0])
            row = self.params.get('row')
            col = self.params.get('col')
            
            self.progress_update.emit(50)
            
            # Llamar al controlador para crear el robot
            result = self.controller.create_robot(robot_type, position, orientation)
            
            self.progress_update.emit(75)
            
            if result.get('success', False):
                handle = result.get('handle')
                
                # NUEVO: Configurar los sensores del robot para detectar obstáculos
                self.controller.configure_sensors_for_obstacle_detection(handle)
                
                # Emitir señal de éxito
                self.operation_result.emit(True, f"Robot {robot_type} creado correctamente")
                
                # Devolver información completa sobre la operación
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


    def handle_connect(self):
        """
        Maneja la conexión a CoppeliaSim
        """
        self.progress_update.emit(25)
        
        try:
            # Intentar establecer conexión
            success = self.controller.connect()
            
            self.progress_update.emit(75)
            
            if success:
                # Emitir señal de éxito
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
        """
        Maneja la desconexión de CoppeliaSim
        """
        self.progress_update.emit(25)
        
        try:
            # Intentar desconectar
            success = self.controller.disconnect()
            
            self.progress_update.emit(75)
            
            if success:
                # Emitir señal de éxito
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
        """
        Maneja la prueba de conexión a CoppeliaSim
        """
        self.progress_update.emit(25)
        
        try:
            # Probar la conexión
            success = self.controller.test_connection()
            
            self.progress_update.emit(75)
            
            if success:
                # Emitir señal de éxito
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
        """
        Maneja el inicio de la simulación en CoppeliaSim
        """
        self.progress_update.emit(25)
        
        try:
            # Llamar al controlador para iniciar la simulación
            success = self.controller.start_simulation()
            
            self.progress_update.emit(75)
            
            if success:
                # Emitir señal de éxito
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
        """
        Maneja la pausa de la simulación en CoppeliaSim
        """
        self.progress_update.emit(25)
        
        try:
            # Esta función no está en tu controller, necesitarías implementarla
            # Por ahora, podemos simularla con stop_simulation
            success = self.controller.suspend_simulation()
            
            self.progress_update.emit(75)
            
            if success:
                # Emitir señal de éxito
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
        """
        Maneja la detención de la simulación en CoppeliaSim
        """
        self.progress_update.emit(25)
        
        try:
            # Llamar al controlador para detener la simulación
            success = self.controller.stop_simulation()
            
            self.progress_update.emit(75)
            
            if success:
                # Emitir señal de éxito
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
        """
        Maneja la eliminación de un robot de CoppeliaSim
        """
        self.progress_update.emit(25)
        
        try:
            handle = self.params.get('handle')
            
            if handle is None:
                self.operation_result.emit(False, "Handle de robot no especificado")
                return
            
            self.progress_update.emit(50)
            
            # Llamar al controlador para eliminar el robot
            result = self.controller.remove_robot(handle)
            
            self.progress_update.emit(75)
            
            if result.get('success', False):
                # Emitir señal de éxito
                self.operation_result.emit(True, "Robot eliminado correctamente")
                
                # Devolver información sobre la operación completada
                complete_result = {
                    'success': True,
                    'handle': handle
                }
                
                self.operation_complete.emit('remove_robot', complete_result)
                
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
        """Maneja la creación de cuboides de manera sincrónica"""
        position = self.params.get('position', [0, 0, 0.05])
        size = self.params.get('size', [0.1, 0.1, 0.1])
        color = self.params.get('color', [1, 0, 0])
        row = self.params.get('row')
        col = self.params.get('col')

        handle = self.controller.create_cuboid(size, position, color)
        
        # Emitir señal con el handle creado y la posición
        if handle is not None:
            self.operation_complete.emit('create_cuboid', {'handle': handle, 'row': row, 'col': col})
            self.operation_result.emit(True, f"Cubo creado con handle {handle}")
        else:
            self.operation_result.emit(False, "No se pudo crear el cubo")

    def handle_remove_cuboid(self):
        """Maneja la eliminación de un cubo específico"""
        handle = self.params.get('handle')
        if handle is None:
            self.operation_result.emit(False, "Handle no proporcionado")
            return
        
        result = self.controller.eliminar_cubo_por_handle(handle)
        self.operation_result.emit(result, f"Cubo {handle} {'eliminado' if result else 'no eliminado'}")

    def handle_remove_all_cuboids(self):
        """Maneja la eliminación de todos los cubos"""
        try:
            result = self.controller.eliminar_cubos()
            message = "Cubos eliminados exitosamente" if result else "No se pudieron eliminar todos los cubos"
            self.operation_result.emit(result, message)
            self.operation_complete.emit('remove_all_cuboids', result)
        except Exception as e:
            print(f"❌ Error al eliminar cubos: {e}")
            self.operation_result.emit(False, f"Error al eliminar cubos: {str(e)}")