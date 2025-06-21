import time
import threading
import random
from enum import Enum
from .light_sensor import LightSensor
from .temperature_sensor import TemperatureSensor
from .imu_sensor import IMUSensor
from .sound_sensor import SoundSensor
from .led import LED
from .buzzer import Buzzer
from .servo_motor import ServoMotor
from .buttons import Buttons

class Season(Enum):
    SPRING = "spring"
    SUMMER = "summer"
    AUTUMN = "autumn"
    WINTER = "winter"

class EnvironmentState(Enum):
    DAY = "day"
    NIGHT = "night"
    DAWN = "dawn"
    DUSK = "dusk"

class HardwareManager:
    def __init__(self, simulation=False):
        self.simulation = simulation
        self.sim_season_list = list(Season)
        self.sim_time_list = list(EnvironmentState)
        self.sim_season_idx = 0
        self.sim_time_idx = 0
        self.sim_season = Season.SPRING
        self.sim_time = EnvironmentState.DAY
        self.sim_light_level = 500
        self.sim_temperature = 22.0
        self.sim_sound_level = 30
        self.simulate_motion_flag = False
        self.sensor_data = {
            'light_level': self.sim_light_level,
            'temperature': self.sim_temperature,
            'humidity': 50.0,
            'acceleration': {'x': 0, 'y': 0, 'z': 0},
            'gyro': {'x': 0, 'y': 0, 'z': 0},
            'sound_level': self.sim_sound_level,
            'button_states': {'feed': False, 'pet': False, 'play': False, 'sleep': False},
            'last_movement': time.time(),
            'is_picked_up': False,
            'shake_detected': False
        }
        # Hardware modules
        self.light_sensor = LightSensor(simulation=simulation)
        self.temp_sensor = TemperatureSensor(simulation=simulation)
        self.imu_sensor = IMUSensor(simulation=simulation)
        self.sound_sensor = SoundSensor(simulation=simulation)
        self.led = LED(simulation=simulation)
        self.buzzer = Buzzer(simulation=simulation)
        self.servo = ServoMotor(simulation=simulation)
        self.buttons = Buttons(simulation=simulation)
        self.running = True
        self.sensor_thread = threading.Thread(target=self._sensor_loop, daemon=True)
        self.sensor_thread.start()

    def _sensor_loop(self):
        while self.running:
            try:
                self._read_sensors()
                self._process_sensor_data()
                time.sleep(0.1)
            except Exception as e:
                time.sleep(1)

    def _read_sensors(self):
        self.sensor_data['light_level'] = self.light_sensor.read()
        self.sensor_data['temperature'] = self.temp_sensor.read()
        self.sensor_data['sound_level'] = self.sound_sensor.read()
        self.sensor_data['acceleration'] = self.imu_sensor.read_acceleration()
        self.sensor_data['gyro'] = self.imu_sensor.read_gyro()
        self.sensor_data['button_states'] = self.buttons.read()
        # Simulate motion if flag is set
        if self.simulate_motion_flag:
            self.sensor_data['acceleration']['x'] = 3.5
            self.sensor_data['acceleration']['y'] = 3.5
            self.sensor_data['acceleration']['z'] = 12.0
            self.sensor_data['last_movement'] = time.time()
            self.simulate_motion_flag = False
        else:
            if random.random() < 0.01:
                self.sensor_data['acceleration']['x'] = random.uniform(-2, 2)
                self.sensor_data['acceleration']['y'] = random.uniform(-2, 2)
                self.sensor_data['acceleration']['z'] = random.uniform(8, 12)
                self.sensor_data['last_movement'] = time.time()
            else:
                self.sensor_data['acceleration']['z'] = 9.8

    def _process_sensor_data(self):
        accel_z = abs(self.sensor_data['acceleration']['z'])
        if accel_z < 8 or accel_z > 11:
            self.sensor_data['is_picked_up'] = True
            self.sensor_data['last_movement'] = time.time()
        else:
            self.sensor_data['is_picked_up'] = False
        total_accel = sum(abs(self.sensor_data['acceleration'][axis]) for axis in ['x', 'y'])
        if total_accel > 3:
            self.sensor_data['shake_detected'] = True
            self.sensor_data['last_movement'] = time.time()
        else:
            self.sensor_data['shake_detected'] = False

    def get_environment_state(self):
        if not self.simulation:
            light = self.sensor_data['light_level']
            if light > 600:
                return EnvironmentState.DAY
            elif light > 200:
                return EnvironmentState.DUSK
            elif light > 50:
                return EnvironmentState.DAWN
            else:
                return EnvironmentState.NIGHT
        else:
            return self.sim_time

    def get_season(self):
        if not self.simulation:
            temp = self.sensor_data['temperature']
            if temp > 25:
                return Season.SUMMER
            elif temp > 15:
                return Season.SPRING
            elif temp > 5:
                return Season.AUTUMN
            else:
                return Season.WINTER
        else:
            return self.sim_season

    def set_led_color(self, color, brightness=0.3):
        self.led.set_color(color, brightness)

    def play_sound(self, frequency, duration=0.1):
        self.buzzer.play(frequency, duration)

    def move_servo(self, angle):
        self.servo.move(angle)

    def cleanup(self):
        self.running = False
        if hasattr(self, 'sensor_thread'):
            self.sensor_thread.join(timeout=1) 