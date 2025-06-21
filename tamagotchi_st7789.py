# Need to: 
#    pip3 install luma.lcd pillow
#    python3 tamagotchi_st7789.py

from luma.core.interface.serial import spi
from luma.lcd.device import st7789
from PIL import Image, ImageDraw, ImageFont
import time
import math
import random
import threading
from enum import Enum
import logging
from hardware.hardware_manager import HardwareManager, EnvironmentState, Season

# LCD setup (adjust gpio_DC and gpio_RST as needed for your wiring)
serial = spi(port=0, device=0, gpio_DC=24, gpio_RST=25, bus_speed_hz=40000000)
device = st7789(serial, width=240, height=320, rotate=0, bgr=True)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
            temp = self.hardware.sensor_data['temperature']
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
        self.hardware.play_sound(600, 0.2)

    def pet(self):
        self.happiness = min(100, self.happiness + 20)
        self.social = min(100, self.social + 15)
        self.comfort = min(100, self.comfort + 10)
        self.last_interaction = time.time()
        self.message = "That feels nice!"
        self.message_timer = 3.0
        self.hardware.play_sound(800, 0.1)

    def play(self):
        self.happiness = min(100, self.happiness + 25)
        self.social = min(100, self.social + 20)
        self.energy = max(0, self.energy - 15)
        self.last_interaction = time.time()
        self.message = "Let's play again!"
        self.message_timer = 3.0
        self.hardware.play_sound(1000, 0.1)
        self.hardware.move_servo(90)

    def put_to_sleep(self):
        self.sleep_mode = True
        self.energy = min(100, self.energy + 30)
        self.last_interaction = time.time()
        self.message = "Goodnight!"
        self.message_timer = 3.0
        self.hardware.play_sound(400, 0.2)

    def wake_up(self):
        if self.sleep_mode:
            self.sleep_mode = False
            self.energy = min(100, self.energy + 10)
            self.happiness = min(100, self.happiness + 5)
            self.message = "Good morning!"
            self.message_timer = 3.0
            self.hardware.play_sound(800, 0.1)

    def draw(self, device):
        img = Image.new("RGB", (device.width, device.height), "black")
        draw = ImageDraw.Draw(img)
        font = ImageFont.load_default()
        face = EMOTION_FACES[self.emotion]
        # Draw face
        draw.text((100, 120), face, fill="white", font=font)
        # Draw stats
        draw.text((10, 10), f"H:{int(self.happiness)} E:{int(self.energy)}", fill="white", font=font)
        draw.text((10, 30), f"Hu:{int(self.hunger)} He:{int(self.health)}", fill="white", font=font)
        draw.text((10, 50), f"C:{int(self.comfort)} S:{int(self.social)}", fill="white", font=font)
        # Draw message
        if self.message:
            draw.text((10, 200), self.message, fill="yellow", font=font)
        # Draw environment info
        draw.text((10, 220), f"T:{self.hardware.sensor_data['temperature']:.1f}C L:{int(self.hardware.sensor_data['light_level'])}", fill="white", font=font)
        draw.text((10, 240), f"Snd:{int(self.hardware.sensor_data['sound_level'])}", fill="white", font=font)
        device.display(img)

class GameManager:
    def __init__(self):
        self.hardware = HardwareManager()
        self.tamagotchi = SmartTamagotchi(self.hardware)
        self.running = True

    def run(self):
        try:
            while self.running:
                dt = 1.0 / 10
                self.tamagotchi.update(dt)
                self.tamagotchi.draw(device)
                time.sleep(dt)
        except KeyboardInterrupt:
            print("Shutting down gracefully...")
        finally:
            self.hardware.cleanup()

if __name__ == "__main__":
    print("Starting Tamagotchi on ST7789 LCD...")
    game = GameManager()
    game.run() 