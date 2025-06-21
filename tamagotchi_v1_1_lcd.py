# tamagotchi_v1_1_lcd.py
# LCD-based version of Tamagotchi (no pygame)
import time
import math
import random
import threading
import json
from enum import Enum
from datetime import datetime, timedelta
import logging
from hardware.hardware_manager import HardwareManager, EnvironmentState, Season
from hardware.buttons import Buttons
from hardware.led import LED
from hardware.buzzer import Buzzer
from hardware.servo_motor import ServoMotor
from hardware.light_sensor import LightSensor
from hardware.temperature_sensor import TemperatureSensor
from hardware.imu_sensor import IMUSensor
from hardware.sound_sensor import SoundSensor

# Placeholder for LCD library import
# from some_lcd_library import LCD

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
SCREEN_WIDTH = 128  # Example LCD width
SCREEN_HEIGHT = 64  # Example LCD height
FPS = 10

class EmotionState(Enum):
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    SLEEPY = "sleepy"
    EXCITED = "excited"
    NEUTRAL = "neutral"
    COLD = "cold"
    HOT = "hot"
    SCARED = "scared"
    PLAYFUL = "playful"

EMOTION_FACES = {
    EmotionState.HAPPY:    "^_^",
    EmotionState.SAD:      "T_T",
    EmotionState.ANGRY:    ">:(",
    EmotionState.SLEEPY:   "-_-",
    EmotionState.EXCITED:  "^o^",
    EmotionState.NEUTRAL:  ":|",
    EmotionState.COLD:     "*_*",
    EmotionState.HOT:      "~_~",
    EmotionState.SCARED:   ":O",
    EmotionState.PLAYFUL:  ":P"
}

class SmartTamagotchi:
    def __init__(self, hardware_manager):
        self.hardware = hardware_manager
        self.emotion = EmotionState.HAPPY
        self.happiness = 80
        self.energy = 70
        self.hunger = 60
        self.health = 90
        self.comfort = 75
        self.social = 60
        self.sleep_mode = False
        self.last_interaction = time.time()
        self.last_fed = time.time()
        self.message = "Hello!"
        self.message_timer = 0

    def update(self, dt):
        # Example: update stats and emotion from hardware
        sensor_data = self.hardware.sensor_data
        # Simple stat decay
        self.happiness = max(0, self.happiness - 0.1 * dt)
        self.energy = max(0, self.energy - 0.05 * dt)
        self.hunger = max(0, self.hunger - 0.08 * dt)
        self.comfort = max(0, self.comfort - 0.03 * dt)
        self.social = max(0, self.social - 0.02 * dt)
        # Example: change emotion based on stats
        if self.sleep_mode:
            self.emotion = EmotionState.SLEEPY
        elif self.health < 30:
            self.emotion = EmotionState.SAD
        elif self.hunger < 20:
            self.emotion = EmotionState.ANGRY
        elif self.comfort < 30:
            temp = sensor_data['temperature']
            self.emotion = EmotionState.COLD if temp < 18 else EmotionState.HOT
        elif self.happiness > 80 and self.energy > 70:
            self.emotion = EmotionState.EXCITED
        elif self.social < 30:
            self.emotion = EmotionState.SAD
        else:
            self.emotion = EmotionState.HAPPY
        # Message timer
        if self.message_timer > 0:
            self.message_timer -= dt
        else:
            self.message = ""

    def feed(self):
        self.hunger = min(100, self.hunger + 30)
        self.happiness = min(100, self.happiness + 10)
        self.health = min(100, self.health + 5)
        self.last_fed = time.time()
        self.last_interaction = time.time()
        self.message = "Yummy! Thank you!"
        self.message_timer = 3.0
        self.hardware.buzzer.play(600, 0.2)

    def pet(self):
        self.happiness = min(100, self.happiness + 20)
        self.social = min(100, self.social + 15)
        self.comfort = min(100, self.comfort + 10)
        self.last_interaction = time.time()
        self.message = "That feels nice!"
        self.message_timer = 3.0
        self.hardware.buzzer.play(800, 0.1)

    def play(self):
        self.happiness = min(100, self.happiness + 25)
        self.social = min(100, self.social + 20)
        self.energy = max(0, self.energy - 15)
        self.last_interaction = time.time()
        self.message = "Let's play again!"
        self.message_timer = 3.0
        self.hardware.buzzer.play(1000, 0.1)
        self.hardware.servo.move(90)

    def put_to_sleep(self):
        self.sleep_mode = True
        self.energy = min(100, self.energy + 30)
        self.last_interaction = time.time()
        self.message = "Goodnight!"
        self.message_timer = 3.0
        self.hardware.buzzer.play(400, 0.2)

    def wake_up(self):
        if self.sleep_mode:
            self.sleep_mode = False
            self.energy = min(100, self.energy + 10)
            self.happiness = min(100, self.happiness + 5)
            self.message = "Good morning!"
            self.message_timer = 3.0
            self.hardware.buzzer.play(800, 0.1)

    def draw(self, lcd):
        lcd.clear()
        face = EMOTION_FACES[self.emotion]
        lcd.draw_text(0, 0, f"Tama {face}")
        lcd.draw_text(0, 1, f"H:{int(self.happiness)} E:{int(self.energy)}")
        lcd.draw_text(0, 2, f"Hu:{int(self.hunger)} He:{int(self.health)}")
        lcd.draw_text(0, 3, f"C:{int(self.comfort)} S:{int(self.social)}")
        lcd.draw_text(0, 4, f"T:{self.hardware.sensor_data['temperature']:.1f}C L:{int(self.hardware.sensor_data['light_level'])}")
        lcd.draw_text(0, 5, f"Snd:{int(self.hardware.sensor_data['sound_level'])}")
        if self.message:
            lcd.draw_text(0, 6, self.message)
        lcd.draw_text(0, 7, f"{self.hardware.get_season().value.title()} {self.hardware.get_environment_state().value.title()}")

class LCDStub:
    # Replace this with your actual LCD library class
    def clear(self):
        print("[LCD] Clear screen")
    def draw_text(self, x, y, text):
        print(f"[LCD] ({x},{y}): {text}")

class GameManager:
    def __init__(self):
        self.lcd = LCDStub()  # Replace with your real LCD class
        self.hardware = HardwareManager()
        self.tamagotchi = SmartTamagotchi(self.hardware)
        self.running = True
        self.button_thread = threading.Thread(target=self._button_loop, daemon=True)
        self.button_thread.start()

    def _button_loop(self):
        # Simulate button presses for testing
        while self.running:
            button_states = self.hardware.buttons.read()
            if button_states.get('feed'):
                self.tamagotchi.feed()
            if button_states.get('pet'):
                self.tamagotchi.pet()
            if button_states.get('play'):
                self.tamagotchi.play()
            if button_states.get('sleep'):
                if self.tamagotchi.sleep_mode:
                    self.tamagotchi.wake_up()
                else:
                    self.tamagotchi.put_to_sleep()
            time.sleep(0.1)

    def run(self):
        try:
            while self.running:
                dt = 1.0 / FPS
                self.tamagotchi.update(dt)
                self.tamagotchi.draw(self.lcd)
                time.sleep(dt)
        except KeyboardInterrupt:
            print("Shutting down gracefully...")
        finally:
            self.running = False
            self.hardware.cleanup()

if __name__ == "__main__":
    print("Starting LCD Tamagotchi...")
    game = GameManager()
    game.run() 