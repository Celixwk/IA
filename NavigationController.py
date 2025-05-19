class NavigationController:
    """
    Controlador de navegación optimizado para el robot Pioneer P3DX en CoppeliaSim.
    Implementa navegación de punto a punto con evitación de obstáculos usando controladores PID.
    """
    def __init__(self, sim_controller):
        self.sim_controller = sim_controller
        self.sim = sim_controller.sim
        self.target_position = None
        self.navigation_active = False
        self.robot_handle = None
        self.left_motor = None
        self.right_motor = None
        self.sensors = []
        self.obstacle_detected = False
        self.obstacle_side = None  # 'left', 'right', 'front', None
        self.stuck_counter = 0
        self.prev_distance = float('inf')
        self.same_distance_counter = 0
        
        # Parámetros del robot Pioneer P3DX
        self.wheel_radius = 0.0975  # Radio de la rueda en metros
        self.wheel_distance = 0.331  # Distancia entre ruedas en metros
        
        # Parámetros de control PID
        self.linear_velocity = 0.8  # Velocidad lineal máxima (m/s)
        self.angular_velocity = 0.5  # Velocidad angular máxima (rad/s)
        
        # PID para control de orientación
        self.orientation_kp = 1.5   # Ganancia proporcional
        self.orientation_ki = 0.01  # Ganancia integral
        self.orientation_kd = 0.5   # Ganancia derivativa
        self.orientation_error_sum = 0
        self.orientation_error_prev = 0
        
        # PID para control de velocidad
        self.velocity_kp = 0.5
        self.velocity_ki = 0.01
        self.velocity_kd = 0.1
        self.velocity_error_sum = 0
        self.velocity_error_prev = 0
        
        # Umbrales
        self.distance_threshold = 0.1  # Distancia para considerar llegada (m)
        self.orientation_threshold = 0.05  # Radianes (~3 grados)
        self.obstacle_threshold = 0.5  # Distancia para considerar obstáculo (m)
        self.stuck_threshold = 20  # Conteo para considerar atascado
        self.same_distance_threshold = 10  # Conteo para considerar sin avance
        
        # Límites de la escena
        self.scene_size = 5.0  # Tamaño aproximado de la escena en metros
        self.scene_limit = self.scene_size / 2 - 0.5  # Margen de seguridad
    
    def initialize(self):
        """Inicializa el controlador encontrando los handles necesarios"""
        if not self.sim_controller.connected:
            print("❌ No se puede inicializar: no hay conexión activa")
            return False
        
        try:
            # Buscar los motores con múltiples intentos de nombres
            motor_names = [
                "Pioneer_p3dx_leftMotor", "/PioneerP3DX/leftMotor", "leftMotor",
                "/Pioneer_p3dx/leftMotor", "Pioneer_p3dx/leftMotor"
            ]
            
            for name in motor_names:
                try:
                    self.left_motor = self.sim.getObject(name)
                    # Si encontramos el izquierdo, intentamos el derecho con el mismo patrón
                    right_name = name.replace("left", "right")
                    self.right_motor = self.sim.getObject(right_name)
                    if self.left_motor and self.right_motor:
                        break
                except:
                    continue
            
            if not self.left_motor or not self.right_motor:
                print("❌ No se pudieron encontrar los motores del robot")
                return False
            
            # Buscar el robot con múltiples intentos de nombres
            robot_names = [
                "Pioneer_p3dx", "/PioneerP3DX", "PioneerP3DX",
                "/Pioneer_p3dx", "Pioneer_p3dx"
            ]
            
            for name in robot_names:
                try:
                    self.robot_handle = self.sim.getObject(name)
                    if self.robot_handle:
                        break
                except:
                    continue
            
            if not self.robot_handle:
                print("❌ No se pudo encontrar el robot")
                return False
            
            # Intentar encontrar los sensores ultrasónicos
            try:
                for i in range(1, 17):  # Pioneer P3DX tiene 16 sensores
                    try:
                        sensor = self.sim.getObject(f"Pioneer_p3dx_ultrasonicSensor{i}")
                        self.sensors.append(sensor)
                    except:
                        try:
                            sensor = self.sim.getObject(f"/PioneerP3DX/ultrasonicSensor{i}")
                            self.sensors.append(sensor)
                        except:
                            pass
            except:
                print("⚠️ No se pudieron encontrar todos los sensores ultrasónicos")
                # Continuamos sin sensores, usaremos solo navegación basada en posición
            
            print(f"✅ Controlador inicializado - Robot: {self.robot_handle}, Motor izq: {self.left_motor}, Motor der: {self.right_motor}, Sensores: {len(self.sensors)}")
            return True
            
        except Exception as e:
            print(f"❌ Error al inicializar controlador: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def set_target(self, target_position):
        """Establece la posición objetivo"""
        self.target_position = target_position
        self.orientation_error_sum = 0
        self.orientation_error_prev = 0
        self.velocity_error_sum = 0
        self.velocity_error_prev = 0
        self.stuck_counter = 0
        self.prev_distance = float('inf')
        self.same_distance_counter = 0
        print(f"✅ Objetivo establecido: {target_position}")
    
    def navigate_to_target(self):
        """Inicia la navegación hacia el objetivo establecido"""
        if not self.target_position or not self.robot_handle or not self.left_motor or not self.right_motor:
            print("❌ No se puede navegar: faltan componentes necesarios")
            return False
        
        self.navigation_active = True
        self.orientation_error_sum = 0
        self.orientation_error_prev = 0
        print(f"🚀 Iniciando navegación hacia {self.target_position}")
        
        # Crear un thread para la navegación
        import threading
        import time
        import math
        
        def navigation_loop():
            try:
                while self.navigation_active:
                    # 1. Obtener posición y orientación actual del robot
                    robot_pos = self.sim.getObjectPosition(self.robot_handle, -1)
                    robot_orient = self.sim.getObjectOrientation(self.robot_handle, -1)
                    robot_angle = robot_orient[2]  # Yaw (rotación en Z)
                    
                    # 2. Verificar límites de la escena para seguridad
                    at_limits = False
                    if abs(robot_pos[0]) > self.scene_limit or abs(robot_pos[1]) > self.scene_limit:
                        print("⚠️ Robot cerca del límite de la escena")
                        at_limits = True
                    
                    # 3. Calcular distancia y dirección al objetivo
                    dx = self.target_position[0] - robot_pos[0]
                    dy = self.target_position[1] - robot_pos[1]
                    distance = math.sqrt(dx*dx + dy*dy)
                    
                    print(f"Distancia al objetivo: {distance:.2f}m")
                    
                    # 4. Verificar si llegamos al objetivo
                    if distance < self.distance_threshold:
                        print("🏁 ¡Objetivo alcanzado!")
                        self.stop_motors()
                        self.navigation_active = False
                        break
                    
                    # 5. Verificar si estamos atascados (sin avance)
                    if abs(distance - self.prev_distance) < 0.01:
                        self.same_distance_counter += 1
                        if self.same_distance_counter > self.same_distance_threshold:
                            print("⚠️ Robot sin avance significativo, aplicando corrección")
                            self.apply_unstuck_maneuver()
                            self.same_distance_counter = 0
                    else:
                        self.same_distance_counter = 0
                    
                    self.prev_distance = distance
                    
                    # 6. Leer sensores para detectar obstáculos
                    self.obstacle_detected = False
                    left_detected = False
                    right_detected = False
                    front_detected = False
                    
                    if self.sensors:
                        for i, sensor in enumerate(self.sensors):
                            try:
                                # Leer sensor
                                result, detection_state, detected_point, _, _ = self.sim.readProximitySensor(sensor)
                                
                                if result == 1 and detection_state:
                                    # Calcular distancia
                                    detected_distance = math.sqrt(
                                        detected_point[0]*detected_point[0] + 
                                        detected_point[1]*detected_point[1] + 
                                        detected_point[2]*detected_point[2]
                                    )
                                    
                                    if detected_distance < self.obstacle_threshold:
                                        self.obstacle_detected = True
                                        
                                        # Determinar en qué lado está el obstáculo
                                        if i < 5 or i > 10:  # Sensores izquierdos
                                            left_detected = True
                                        elif i > 5 and i < 10:  # Sensores derechos
                                            right_detected = True
                                        if i >= 3 and i <= 7:  # Sensores frontales
                                            front_detected = True
                            except:
                                pass
                    
                    # Determinar la ubicación principal del obstáculo
                    if front_detected:
                        self.obstacle_side = 'front'
                    elif left_detected and not right_detected:
                        self.obstacle_side = 'left'
                    elif right_detected and not left_detected:
                        self.obstacle_side = 'right'
                    else:
                        self.obstacle_side = None
                    
                    # 7. Calcular velocidades basado en PID y obstáculos
                    left_velocity, right_velocity = self.calculate_motor_velocities(
                        robot_pos, robot_angle, distance, at_limits)
                    
                    # 8. Aplicar velocidades a los motores
                    self.sim.setJointTargetVelocity(self.left_motor, left_velocity)
                    self.sim.setJointTargetVelocity(self.right_motor, right_velocity)
                    
                    # Pausa breve para no saturar la CPU
                    time.sleep(0.05)
                
                # Al finalizar, asegurar que el robot se detiene
                self.stop_motors()
                print("✅ Navegación finalizada")
                
            except Exception as e:
                print(f"❌ Error en bucle de navegación: {e}")
                import traceback
                traceback.print_exc()
                self.stop_motors()
                self.navigation_active = False
        
        # Iniciar el bucle de navegación en un hilo separado
        nav_thread = threading.Thread(target=navigation_loop)
        nav_thread.daemon = True
        nav_thread.start()
        
        return True
    
    def calculate_motor_velocities(self, robot_pos, robot_angle, distance, at_limits):
        """Calcula las velocidades de los motores usando PID y evitación de obstáculos"""
        import math
        
        # 1. Calcular ángulo hacia el objetivo
        dx = self.target_position[0] - robot_pos[0]
        dy = self.target_position[1] - robot_pos[1]
        target_angle = math.atan2(dy, dx)
        
        # 2. Calcular error de orientación (normalizado a [-pi, pi])
        orientation_error = target_angle - robot_angle
        
        while orientation_error > math.pi:
            orientation_error -= 2 * math.pi
        while orientation_error < -math.pi:
            orientation_error += 2 * math.pi
        
        # 3. Control PID de orientación
        self.orientation_error_sum += orientation_error
        orientation_error_diff = orientation_error - self.orientation_error_prev
        self.orientation_error_prev = orientation_error
        
        # Limitar la suma de errores para evitar windup
        if self.orientation_error_sum > 5.0:
            self.orientation_error_sum = 5.0
        elif self.orientation_error_sum < -5.0:
            self.orientation_error_sum = -5.0
        
        # Calcular término PID de orientación
        orientation_control = (
            self.orientation_kp * orientation_error +
            self.orientation_ki * self.orientation_error_sum +
            self.orientation_kd * orientation_error_diff
        )
        
        # 4. Control PID de velocidad basado en la distancia
        velocity_error = min(1.0, distance / 2)  # Normalizar a [0, 1]
        self.velocity_error_sum += velocity_error
        velocity_error_diff = velocity_error - self.velocity_error_prev
        self.velocity_error_prev = velocity_error
        
        # Limitar la suma de errores para evitar windup
        if self.velocity_error_sum > 5.0:
            self.velocity_error_sum = 5.0
        elif self.velocity_error_sum < -5.0:
            self.velocity_error_sum = -5.0
        
        # Calcular término PID de velocidad
        velocity_control = (
            self.velocity_kp * velocity_error +
            self.velocity_ki * self.velocity_error_sum + 
            self.velocity_kd * velocity_error_diff
        )
        
        # 5. Ajustar según obstáculos y límites
        if self.obstacle_detected:
            print(f"⚠️ Obstáculo detectado: {self.obstacle_side}")
            
            if self.obstacle_side == 'front':
                # Girar a la derecha por defecto cuando hay obstáculo frontal
                left_velocity = self.angular_velocity
                right_velocity = -self.angular_velocity
            elif self.obstacle_side == 'left':
                # Girar a la derecha cuando hay obstáculo a la izquierda
                left_velocity = self.angular_velocity
                right_velocity = -self.angular_velocity / 2
            elif self.obstacle_side == 'right':
                # Girar a la izquierda cuando hay obstáculo a la derecha
                left_velocity = -self.angular_velocity / 2
                right_velocity = self.angular_velocity
            else:
                # Comportamiento por defecto basado en PID
                left_velocity = velocity_control - orientation_control
                right_velocity = velocity_control + orientation_control
        else:
            # No hay obstáculos, usar control PID normal
            left_velocity = velocity_control - orientation_control
            right_velocity = velocity_control + orientation_control
        
        # 6. Ajustar por límites de escena
        if at_limits:
            # Reducir velocidad cerca de los límites
            max_speed = self.linear_velocity * 0.3
            
            if abs(left_velocity) > max_speed:
                left_velocity = max_speed if left_velocity > 0 else -max_speed
            
            if abs(right_velocity) > max_speed:
                right_velocity = max_speed if right_velocity > 0 else -max_speed
        else:
            # Limitar las velocidades máximas
            max_speed = self.linear_velocity
            
            if abs(left_velocity) > max_speed:
                left_velocity = max_speed if left_velocity > 0 else -max_speed
            
            if abs(right_velocity) > max_speed:
                right_velocity = max_speed if right_velocity > 0 else -max_speed
        
        # 7. Verificar si el robot está atascado (un motor bloqueado)
        if abs(orientation_error) > 0.1 and abs(left_velocity - right_velocity) < 0.1:
            self.stuck_counter += 1
            if self.stuck_counter > self.stuck_threshold:
                print("⚠️ Robot posiblemente atascado, aplicando corrección")
                self.apply_unstuck_maneuver()
                self.stuck_counter = 0
        else:
            self.stuck_counter = 0
        
        # Mejorar la navegación agregando una pequeña velocidad angular cuando
        # el robot necesita reorientarse pero la corrección es muy pequeña
        if abs(orientation_error) > self.orientation_threshold and abs(orientation_control) < 0.1:
            orientation_boost = 0.2 * (1 if orientation_error > 0 else -1)
            left_velocity -= orientation_boost
            right_velocity += orientation_boost
        
        # 8. Diagnóstico
        print(f"Error orientación: {orientation_error:.2f}, Control: {orientation_control:.2f}")
        print(f"Velocidad: L={left_velocity:.2f}, R={right_velocity:.2f}")
        
        return left_velocity, right_velocity
    
    def apply_unstuck_maneuver(self):
        """Aplica una maniobra para desatascar el robot"""
        import random
        import time
        
        try:
            print("⚠️ Aplicando maniobra de desatasque")
            
            # 1. Detener motores
            self.stop_motors()
            time.sleep(0.1)
            
            # 2. Mover ligeramente hacia atrás
            self.sim.setJointTargetVelocity(self.left_motor, -0.5)
            self.sim.setJointTargetVelocity(self.right_motor, -0.5)
            time.sleep(0.5)
            
            # 3. Girar aleatoriamente
            direction = 1 if random.random() > 0.5 else -1
            self.sim.setJointTargetVelocity(self.left_motor, 0.5 * direction)
            self.sim.setJointTargetVelocity(self.right_motor, -0.5 * direction)
            time.sleep(0.8)
            
            # 4. Detener motores nuevamente
            self.stop_motors()
            time.sleep(0.1)
            
            print("✅ Maniobra de desatasque completada")
            
        except Exception as e:
            print(f"❌ Error en maniobra de desatasque: {e}")
    
    def stop_motors(self):
        """Detiene los motores del robot"""
        try:
            if self.left_motor and self.right_motor:
                self.sim.setJointTargetVelocity(self.left_motor, 0)
                self.sim.setJointTargetVelocity(self.right_motor, 0)
        except Exception as e:
            print(f"❌ Error al detener motores: {e}")
    
    def stop_navigation(self):
        """Detiene la navegación activa"""
        self.navigation_active = False
        self.stop_motors()
        print("✅ Navegación detenida manualmente")
        return True