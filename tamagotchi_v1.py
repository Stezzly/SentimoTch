#!/usr/bin/env python3

import pygame
import math
import random
import time
import threading
import json
from enum import Enum
from datetime import datetime, timedelta
import logging
from hardware.hardware_manager import HardwareManager, EnvironmentState, Season

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
MIN_SCREEN_WIDTH = 640
MIN_SCREEN_HEIGHT = 480
SCREEN_WIDTH = max(MIN_SCREEN_WIDTH, 1080)
SCREEN_HEIGHT = max(MIN_SCREEN_HEIGHT, 720)
FPS = 30

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
PINK = (255, 182, 193)
LIGHT_BLUE = (173, 216, 230)
YELLOW = (255, 255, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
PURPLE = (147, 112, 219)
ORANGE = (255, 165, 0)
GRAY = (128, 128, 128)
DARK_GRAY = (64, 64, 64)
BLUE = (0, 0, 255)

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

class SmartTamagotchi:
    """Enhanced Tamagotchi with hardware sensor integration"""
    def __init__(self, x, y, hardware_manager):
        self.x = x
        self.y = y
        self.hardware = hardware_manager
        self.emotion = EmotionState.HAPPY
        self.animation_frame = 0
        self.animation_speed = 0.15
        self.bounce_offset = 0
        self.blink_timer = 0
        self.is_blinking = False
        self.message = "Hello! I'm your smart companion!"
        self.message_timer = 0
        self.scale = 1.0
        self.target_scale = 1.0
        # Enhanced stats
        self.happiness = 80
        self.energy = 70
        self.hunger = 60
        self.health = 90
        self.comfort = 75
        self.social = 60
        # Behavioral states
        self.sleep_mode = False
        self.last_interaction = time.time()
        self.last_fed = time.time()
        self.idle_timeout = 300
        self.neglect_timeout = 600
        # Environmental responses
        self.preferred_temp_min = 18
        self.preferred_temp_max = 26
        self.light_sensitive = True
        # Memory system
        self.interaction_history = []
        self.daily_stats = {'interactions': 0, 'feedings': 0, 'play_time': 0}

    def update(self, dt):
        current_time = time.time()
        sensor_data = self.hardware.sensor_data
        # Update animation
        self.animation_frame += self.animation_speed * dt * 60
        if self.animation_frame >= 2 * math.pi:
            self.animation_frame = 0
        self.bounce_offset = math.sin(self.animation_frame) * 3
        # Update blinking
        self.blink_timer += dt
        if self.blink_timer >= 3.0:
            self.is_blinking = True
            if self.blink_timer >= 3.2:
                self.is_blinking = False
                self.blink_timer = 0
        # Update scale animation
        if abs(self.scale - self.target_scale) > 0.01:
            self.scale += (self.target_scale - self.scale) * 0.1
        else:
            self.scale = self.target_scale
            self.target_scale = 1.0
        # Update message timer
        if self.message_timer > 0:
            self.message_timer -= dt
        # Process sensor-based behaviors
        self._process_movement_detection(sensor_data, current_time)
        self._process_environmental_conditions(sensor_data)
        self._process_time_based_needs(current_time, dt)
        self._update_emotion_from_sensors()
        self._update_led_feedback()
        self._decay_stats(dt)

    def _process_movement_detection(self, sensor_data, current_time):
        if sensor_data['is_picked_up']:
            if not hasattr(self, '_pickup_message_shown'):
                self.message = "Wheee! Thanks for picking me up!"
                self.message_timer = 2.0
                self.happiness = min(100, self.happiness + 5)
                self.social = min(100, self.social + 3)
                self.last_interaction = current_time
                self._pickup_message_shown = True
                self.hardware.play_sound(800, 0.2)
        else:
            if hasattr(self, '_pickup_message_shown'):
                delattr(self, '_pickup_message_shown')
        if sensor_data['shake_detected']:
            if not hasattr(self, '_shake_message_shown'):
                self.message = "That's fun! Shake me more!"
                self.message_timer = 2.0
                self.happiness = min(100, self.happiness + 8)
                self.energy = max(0, self.energy - 5)
                self.emotion = EmotionState.PLAYFUL
                self.last_interaction = current_time
                self._shake_message_shown = True
                self.hardware.play_sound(1000, 0.1)
                self.hardware.move_servo(random.randint(30, 150))
        else:
            if hasattr(self, '_shake_message_shown'):
                delattr(self, '_shake_message_shown')
        time_since_movement = current_time - sensor_data['last_movement']
        if time_since_movement > self.idle_timeout and not self.sleep_mode:
            if time_since_movement > self.neglect_timeout:
                self.emotion = EmotionState.SAD
                self.message = "I feel lonely... Please interact with me!"
                self.message_timer = 3.0
                self.social = max(0, self.social - 1)
            else:
                self.emotion = EmotionState.SLEEPY

    def _process_environmental_conditions(self, sensor_data):
        temp = sensor_data['temperature']
        light = sensor_data['light_level']
        sound = sensor_data['sound_level']
        if temp < self.preferred_temp_min:
            self.comfort = max(0, self.comfort - 0.5)
            if temp < 10:
                self.emotion = EmotionState.COLD
                self.message = "Brrr! It's so cold!"
                self.message_timer = 2.0
        elif temp > self.preferred_temp_max:
            self.comfort = max(0, self.comfort - 0.5)
            if temp > 30:
                self.emotion = EmotionState.HOT
                self.message = "It's too hot! I need some shade!"
                self.message_timer = 2.0
        else:
            self.comfort = min(100, self.comfort + 0.2)
        env_state = self.hardware.get_environment_state()
        if env_state == EnvironmentState.NIGHT and not self.sleep_mode:
            if self.energy < 50:
                self.sleep_mode = True
                self.message = "It's dark and I'm tired. Time for sleep!"
                self.message_timer = 3.0
                self.emotion = EmotionState.SLEEPY
        elif env_state == EnvironmentState.DAY and self.sleep_mode:
            self.sleep_mode = False
            self.message = "Good morning! The sun is shining!"
            self.message_timer = 3.0
            self.energy = min(100, self.energy + 20)
            self.emotion = EmotionState.HAPPY
        if sound > 80:
            self.emotion = EmotionState.SCARED
            self.message = "That was loud! I'm scared!"
            self.message_timer = 2.0
            self.happiness = max(0, self.happiness - 5)

    def _process_time_based_needs(self, current_time, dt):
        time_since_fed = current_time - self.last_fed
        if time_since_fed > 1800:
            self.hunger = max(0, self.hunger - 10 * dt)
        if self.sleep_mode:
            self.energy = min(100, self.energy + 5 * dt)
        else:
            self.energy = max(0, self.energy - 2 * dt)
        avg_care = (self.happiness + self.hunger + self.energy + self.comfort) / 4
        if avg_care < 30:
            self.health = max(0, self.health - 1 * dt)
        elif avg_care > 70:
            self.health = min(100, self.health + 0.5 * dt)

    def _decay_stats(self, dt):
        if not self.sleep_mode:
            self.happiness = max(0, self.happiness - 0.3 * dt)
            self.social = max(0, self.social - 0.2 * dt)

    def _update_emotion_from_sensors(self):
        if self.sleep_mode:
            self.emotion = EmotionState.SLEEPY
            return
        if self.health < 30:
            self.emotion = EmotionState.SAD
        elif self.hunger < 20:
            self.emotion = EmotionState.ANGRY
        elif self.comfort < 30:
            temp = self.hardware.sensor_data['temperature']
            self.emotion = EmotionState.COLD if temp < self.preferred_temp_min else EmotionState.HOT
        elif self.happiness > 80 and self.energy > 70:
            self.emotion = EmotionState.EXCITED
        elif self.social < 30:
            self.emotion = EmotionState.SAD
        else:
            self.emotion = EmotionState.HAPPY

    def _update_led_feedback(self):
        emotion_colors = {
            EmotionState.HAPPY: (0, 255, 0),
            EmotionState.SAD: (0, 0, 255),
            EmotionState.ANGRY: (255, 0, 0),
            EmotionState.SLEEPY: (128, 0, 128),
            EmotionState.EXCITED: (255, 255, 0),
            EmotionState.COLD: (0, 255, 255),
            EmotionState.HOT: (255, 128, 0),
            EmotionState.SCARED: (255, 0, 255),
            EmotionState.PLAYFUL: (0, 255, 128),
            EmotionState.NEUTRAL: (255, 255, 255)
        }
        color = emotion_colors.get(self.emotion, (255, 255, 255))
        brightness = 0.1 if self.sleep_mode else 0.3
        self.hardware.set_led_color(color, brightness)

    def feed(self):
        self.hunger = min(100, self.hunger + 30)
        self.happiness = min(100, self.happiness + 10)
        self.health = min(100, self.health + 5)
        self.last_fed = time.time()
        self.last_interaction = time.time()
        self.message = "Yummy! Thank you for the delicious food!"
        self.message_timer = 3.0
        self.target_scale = 1.2
        self.daily_stats['feedings'] += 1
        self.hardware.play_sound(600, 0.3)

    def pet(self):
        self.happiness = min(100, self.happiness + 20)
        self.social = min(100, self.social + 15)
        self.comfort = min(100, self.comfort + 10)
        self.last_interaction = time.time()
        self.message = "That feels wonderful! I love you so much!"
        self.message_timer = 3.0
        self.target_scale = 1.1
        self.daily_stats['interactions'] += 1
        self.hardware.play_sound(800, 0.2)

    def play(self):
        self.happiness = min(100, self.happiness + 25)
        self.social = min(100, self.social + 20)
        self.energy = max(0, self.energy - 15)
        self.last_interaction = time.time()
        self.message = "Playing is the best! Let's do it again!"
        self.message_timer = 3.0
        self.emotion = EmotionState.PLAYFUL
        self.daily_stats['play_time'] += 1
        self.hardware.play_sound(1000, 0.1)
        self.hardware.move_servo(90)

    def put_to_sleep(self):
        self.sleep_mode = True
        self.energy = min(100, self.energy + 30)
        self.last_interaction = time.time()
        self.message = "Goodnight! Sweet dreams!"
        self.message_timer = 3.0
        self.emotion = EmotionState.SLEEPY
        self.hardware.play_sound(400, 0.5)

    def wake_up(self):
        if self.sleep_mode:
            self.sleep_mode = False
            self.energy = min(100, self.energy + 10)
            self.happiness = min(100, self.happiness + 5)
            self.message = "Good morning! I feel refreshed!"
            self.message_timer = 3.0
            self.emotion = EmotionState.HAPPY
            self.hardware.play_sound(800, 0.3)

    def draw_body(self, screen):
        """Draw a cute, detailed Tamagotchi body with ears, belly, feet, and tail/heart"""
        body_colors = {
            EmotionState.HAPPY: PINK,
            EmotionState.SAD: LIGHT_BLUE,
            EmotionState.ANGRY: (255, 200, 200),
            EmotionState.SLEEPY: (230, 230, 250),
            EmotionState.EXCITED: YELLOW,
            EmotionState.COLD: (200, 220, 255),
            EmotionState.HOT: (255, 220, 200),
            EmotionState.SCARED: (240, 200, 240),
            EmotionState.PLAYFUL: (200, 255, 200),
            EmotionState.NEUTRAL: PINK
        }
        base_scale = min(SCREEN_WIDTH, SCREEN_HEIGHT) / 600
        self.scale = base_scale
        body_color = body_colors.get(self.emotion, PINK)
        body_y = self.y + self.bounce_offset
        # Shadow
        pygame.draw.ellipse(screen, (120, 120, 120, 80), (self.x - 32 * self.scale, body_y + 38 * self.scale, 64 * self.scale, 18 * self.scale))
        # Ears
        pygame.draw.ellipse(screen, body_color, (self.x - 30 * self.scale, body_y - 48 * self.scale, 18 * self.scale, 28 * self.scale))
        pygame.draw.ellipse(screen, body_color, (self.x + 12 * self.scale, body_y - 48 * self.scale, 18 * self.scale, 28 * self.scale))
        # Main body
        pygame.draw.ellipse(screen, body_color, (self.x - 36 * self.scale, body_y - 26 * self.scale, 72 * self.scale, 52 * self.scale))
        # Belly
        pygame.draw.ellipse(screen, (255, 255, 255), (self.x - 18 * self.scale, body_y + 2 * self.scale, 36 * self.scale, 28 * self.scale))
        # Feet
        pygame.draw.ellipse(screen, (255, 200, 200), (self.x - 24 * self.scale, body_y + 24 * self.scale, 16 * self.scale, 10 * self.scale))
        pygame.draw.ellipse(screen, (255, 200, 200), (self.x + 8 * self.scale, body_y + 24 * self.scale, 16 * self.scale, 10 * self.scale))
        # Body outline
        pygame.draw.ellipse(screen, BLACK, (self.x - 36 * self.scale, body_y - 26 * self.scale, 72 * self.scale, 52 * self.scale), 2)
        # Ear outlines
        pygame.draw.ellipse(screen, BLACK, (self.x - 30 * self.scale, body_y - 48 * self.scale, 18 * self.scale, 28 * self.scale), 2)
        pygame.draw.ellipse(screen, BLACK, (self.x + 12 * self.scale, body_y - 48 * self.scale, 18 * self.scale, 28 * self.scale), 2)
        # Feet outlines
        pygame.draw.ellipse(screen, BLACK, (self.x - 24 * self.scale, body_y + 24 * self.scale, 16 * self.scale, 10 * self.scale), 1)
        pygame.draw.ellipse(screen, BLACK, (self.x + 8 * self.scale, body_y + 24 * self.scale, 16 * self.scale, 10 * self.scale), 1)
        # Blush
        pygame.draw.ellipse(screen, (255, 182, 193), (self.x - 24 * self.scale, body_y + 6 * self.scale, 12 * self.scale, 6 * self.scale))
        pygame.draw.ellipse(screen, (255, 182, 193), (self.x + 12 * self.scale, body_y + 6 * self.scale, 12 * self.scale, 6 * self.scale))

    def draw_face(self, screen):
        """Draw cute facial features with big shiny eyes, highlights, and expressive mouth"""
        body_y = self.y + self.bounce_offset
        # Eyes based on emotion and sleep state
        if self.sleep_mode or self.is_blinking:
            # Closed eyes
            pygame.draw.line(screen, BLACK, (self.x - 15 * self.scale, body_y - 8 * self.scale), (self.x - 8 * self.scale, body_y - 8 * self.scale), 2)
            pygame.draw.line(screen, BLACK, (self.x + 8 * self.scale, body_y - 8 * self.scale), (self.x + 15 * self.scale, body_y - 8 * self.scale), 2)
        else:
            # Big shiny eyes
            for dx in [-12, 12]:
                # Eye white
                pygame.draw.ellipse(screen, WHITE, (self.x + dx * self.scale - 6 * self.scale, body_y - 12 * self.scale, 12 * self.scale, 16 * self.scale))
                # Pupil
                pygame.draw.ellipse(screen, BLACK, (self.x + dx * self.scale - 3 * self.scale, body_y - 6 * self.scale, 6 * self.scale, 8 * self.scale))
                # Eye highlight
                pygame.draw.ellipse(screen, (180, 240, 255), (self.x + dx * self.scale - 1.5 * self.scale, body_y - 3 * self.scale, 2.5 * self.scale, 3 * self.scale))
            # Extra emotion overlays
            if self.emotion == EmotionState.SCARED:
                # Wide open eyes
                for dx in [-12, 12]:
                    pygame.draw.ellipse(screen, (255, 255, 255), (self.x + dx * self.scale - 8 * self.scale, body_y - 14 * self.scale, 16 * self.scale, 20 * self.scale), 2)
            elif self.emotion == EmotionState.ANGRY:
                # Angry eyebrows
                pygame.draw.line(screen, BLACK, (self.x - 18 * self.scale, body_y - 18 * self.scale), (self.x - 6 * self.scale, body_y - 14 * self.scale), 3)
                pygame.draw.line(screen, BLACK, (self.x + 6 * self.scale, body_y - 14 * self.scale), (self.x + 18 * self.scale, body_y - 18 * self.scale), 3)
        # Mouth based on emotion
        if self.emotion == EmotionState.HAPPY or self.emotion == EmotionState.EXCITED:
            # Happy smile
            pygame.draw.arc(screen, BLACK, (self.x - 10 * self.scale, body_y + 8 * self.scale, 20 * self.scale, 15 * self.scale), 0, math.pi, 2)
        elif self.emotion == EmotionState.SAD:
            # Sad frown
            pygame.draw.arc(screen, BLACK, (self.x - 10 * self.scale, body_y + 16 * self.scale, 20 * self.scale, 15 * self.scale), math.pi, 2 * math.pi, 2)
        elif self.emotion == EmotionState.ANGRY:
            # Angry mouth
            pygame.draw.line(screen, BLACK, (self.x - 8 * self.scale, body_y + 12 * self.scale), (self.x + 8 * self.scale, body_y + 12 * self.scale), 2)
        elif self.emotion == EmotionState.SCARED:
            # Small "o" mouth
            pygame.draw.ellipse(screen, BLACK, (self.x - 4 * self.scale, body_y + 12 * self.scale, 8 * self.scale, 10 * self.scale), 2)
        elif self.emotion == EmotionState.PLAYFUL:
            # Tongue out
            pygame.draw.arc(screen, BLACK, (self.x - 8 * self.scale, body_y + 8 * self.scale, 16 * self.scale, 12 * self.scale), 0, math.pi, 2)
            pygame.draw.ellipse(screen, (255, 100, 100), (self.x - 3 * self.scale, body_y + 16 * self.scale, 6 * self.scale, 4 * self.scale))
        else:
            # Neutral mouth
            pygame.draw.ellipse(screen, BLACK, (self.x - 4 * self.scale, body_y + 12 * self.scale, 8 * self.scale, 6 * self.scale), 2)

    def draw_accessories(self, screen):
        """Draw seasonal or emotion-based accessories that fit the character well. (No heart animation for happy.)"""
        season = self.hardware.get_season()
        body_y = self.y + self.bounce_offset
        t = pygame.time.get_ticks() / 1000.0
        # WINTER: snug beanie and scarf
        if season == Season.WINTER or self.emotion == EmotionState.COLD:
            # Play beanie/scarf sound once per appearance
            if not hasattr(self, '_winter_sound_played') or not self._winter_sound_played:
                self.hardware.play_sound(350, 0.18)
                self._winter_sound_played = True
            # Beanie (snug, with brim)
            pygame.draw.ellipse(screen, RED, (self.x - 28 * self.scale, body_y - 38 * self.scale, 56 * self.scale, 22 * self.scale))
            pygame.draw.ellipse(screen, (220, 220, 220), (self.x - 28 * self.scale, body_y - 28 * self.scale, 56 * self.scale, 10 * self.scale))
            pygame.draw.circle(screen, WHITE, (int(self.x), int(body_y - 38 * self.scale)), int(7 * self.scale))
            # Scarf (wraps neck)
            pygame.draw.arc(screen, (180, 0, 0), (self.x - 22 * self.scale, body_y + 10 * self.scale, 44 * self.scale, 18 * self.scale), math.pi, 2 * math.pi, int(8 * self.scale))
            pygame.draw.rect(screen, (220, 50, 50), (self.x - 8 * self.scale, body_y + 18 * self.scale, 16 * self.scale, 14 * self.scale))
        else:
            self._winter_sound_played = False
        # SPRING: flower crown arcing the head
        if season == Season.SPRING:
            if not hasattr(self, '_spring_sound_played') or not self._spring_sound_played:
                self.hardware.play_sound(900, 0.12)
                self._spring_sound_played = True
            flower_colors = [(255, 182, 193), (255, 255, 0), (173, 216, 230), (144, 238, 144)]
            for i in range(6):
                angle = math.pi/2 + i * math.pi/7
                fx = self.x + math.cos(angle) * 30 * self.scale
                fy = body_y - 22 * self.scale + math.sin(angle) * 10 * self.scale
                pygame.draw.circle(screen, flower_colors[i % len(flower_colors)], (int(fx), int(fy)), int(7 * self.scale))
                pygame.draw.circle(screen, (255, 255, 255), (int(fx), int(fy)), int(2.5 * self.scale))
        else:
            self._spring_sound_played = False
        # SUMMER: sunglasses curved over eyes
        if season == Season.SUMMER or self.emotion == EmotionState.HOT:
            if not hasattr(self, '_summer_sound_played') or not self._summer_sound_played:
                self.hardware.play_sound(1200, 0.09)
                self._summer_sound_played = True
            # Sunglasses (arc over eyes)
            pygame.draw.arc(screen, BLACK, (self.x - 22 * self.scale, body_y - 16 * self.scale, 44 * self.scale, 18 * self.scale), math.pi, 2 * math.pi, int(8 * self.scale))
            pygame.draw.ellipse(screen, (40, 40, 40), (self.x - 18 * self.scale, body_y - 10 * self.scale, 16 * self.scale, 10 * self.scale))
            pygame.draw.ellipse(screen, (40, 40, 40), (self.x + 2 * self.scale, body_y - 10 * self.scale, 16 * self.scale, 10 * self.scale))
            pygame.draw.line(screen, BLACK, (self.x - 10 * self.scale, body_y - 6 * self.scale), (self.x + 10 * self.scale, body_y - 6 * self.scale), int(3 * self.scale))
        else:
            self._summer_sound_played = False
        # AUTUMN: leaf hat at an angle
        if season == Season.AUTUMN:
            if not hasattr(self, '_autumn_sound_played') or not self._autumn_sound_played:
                self.hardware.play_sound(600, 0.13)
                self._autumn_sound_played = True
            # Leaf hat (angled)
            pygame.draw.ellipse(screen, (139, 69, 19), (self.x - 10 * self.scale, body_y - 36 * self.scale, 28 * self.scale, 12 * self.scale))
            pygame.draw.ellipse(screen, (255, 140, 0), (self.x - 6 * self.scale, body_y - 40 * self.scale, 20 * self.scale, 8 * self.scale))
            pygame.draw.line(screen, (139, 69, 19), (self.x + 4 * self.scale, body_y - 34 * self.scale), (self.x + 10 * self.scale, body_y - 44 * self.scale), 2)
        else:
            self._autumn_sound_played = False
        # EXCITED: sparkles
        if self.emotion == EmotionState.EXCITED:
            if not hasattr(self, '_excited_sound_played') or not self._excited_sound_played:
                self.hardware.play_sound(1500, 0.08)
                self._excited_sound_played = True
            for i in range(6):
                angle = i * math.pi / 3
                sx = self.x + math.cos(angle) * 40 * self.scale
                sy = body_y + math.sin(angle) * 30 * self.scale
                pygame.draw.circle(screen, YELLOW, (int(sx), int(sy)), int(5 * self.scale))
        else:
            self._excited_sound_played = False

    def draw_status_bars(self, screen):
        """Draw status bars for all stats, scaled to window size"""
        bar_width = int(SCREEN_WIDTH * 0.18)
        bar_height = int(SCREEN_HEIGHT * 0.018)
        start_x = int(SCREEN_WIDTH * 0.04)
        start_y = int(SCREEN_HEIGHT * 0.13)
        spacing = int(SCREEN_HEIGHT * 0.035)
        stats = [
            ("Health", self.health, RED),
            ("Happiness", self.happiness, YELLOW),
            ("Energy", self.energy, BLUE),
            ("Hunger", self.hunger, GREEN),
            ("Comfort", self.comfort, PURPLE),
            ("Social", self.social, ORANGE)
        ]
        font = pygame.font.Font(None, int(SCREEN_HEIGHT * 0.03))
        for i, (name, value, color) in enumerate(stats):
            y = start_y + i * spacing
            # Background bar
            pygame.draw.rect(screen, DARK_GRAY, 
                           (start_x, y, bar_width, bar_height))
            # Filled bar
            fill_width = int((value / 100) * bar_width)
            pygame.draw.rect(screen, color, 
                           (start_x, y, fill_width, bar_height))
            # Border
            pygame.draw.rect(screen, BLACK, 
                           (start_x, y, bar_width, bar_height), 1)
            # Label
            text = font.render(f"{name}: {int(value)}", True, BLACK)
            screen.blit(text, (start_x + bar_width + int(SCREEN_WIDTH * 0.01), y - 2))

    def draw_environmental_info(self, screen):
        """Draw environmental sensor information, scaled to window size"""
        font = pygame.font.Font(None, int(SCREEN_HEIGHT * 0.025))
        sensor_data = self.hardware.sensor_data
        info_lines = [
            f"Light: {sensor_data['light_level']:.0f} lux",
            f"Temp: {sensor_data['temperature']:.1f}°C",
            f"Season: {self.hardware.get_season().value.title()}",
            f"Time: {self.hardware.get_environment_state().value.title()}",
            f"Movement: {'Yes' if sensor_data['is_picked_up'] else 'No'}",
            f"Sound: {sensor_data['sound_level']:.0f} dB"
        ]
        for i, line in enumerate(info_lines):
            text = font.render(line, True, BLACK)
            screen.blit(text, (SCREEN_WIDTH - int(SCREEN_WIDTH * 0.18), int(SCREEN_HEIGHT * 0.13) + i * int(SCREEN_HEIGHT * 0.04)))

    def draw(self, screen):
        """Main draw method"""
        self.draw_body(screen)
        self.draw_face(screen)
        self.draw_accessories(screen)
        # Draw message if active
        if self.message_timer > 0:
            font = pygame.font.Font(None, int(SCREEN_HEIGHT * 0.035))
            lines = self.message.split('\n')
            # Center above Tamagotchi
            msg_y = int(self.y - 80 * self.scale)
            for i, line in enumerate(lines):
                text = font.render(line, True, BLACK)
                text_rect = text.get_rect(center=(self.x, msg_y + i * int(SCREEN_HEIGHT * 0.04)))
                pygame.draw.rect(screen, WHITE, text_rect.inflate(20, 10))
                pygame.draw.rect(screen, BLACK, text_rect.inflate(20, 10), 2)
                screen.blit(text, text_rect)

class GameManager:
    """Main game manager class"""
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
        pygame.display.set_caption("Smart Raspberry Pi Tamagotchi")
        self.clock = pygame.time.Clock()
        self.running = True
        self.hardware = HardwareManager()
        if getattr(self.hardware, 'simulation', False):
            print("[WARNING] Hardware not available, running in simulation mode.")
        self.tamagotchi = SmartTamagotchi(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, self.hardware)
        self.buttons = self._create_ui_buttons()
        self.env_buttons = self._create_env_buttons()
        self.show_debug = False

    def _create_ui_buttons(self):
        """Create UI buttons for interaction"""
        button_width = int(SCREEN_WIDTH * 0.07)
        button_height = int(SCREEN_HEIGHT * 0.055)
        button_y = SCREEN_HEIGHT - button_height - 20
        spacing = int(SCREEN_WIDTH * 0.02)
        buttons = []
        for i, (text, action, color) in enumerate([
            ("Feed", "feed", GREEN),
            ("Pet", "pet", PINK),
            ("Play", "play", YELLOW),
            ("Sleep", "sleep", PURPLE),
            ("Debug", "debug", GRAY),
            ("Motion", "motion", BLUE)
        ]):
            x = 20 + i * (button_width + spacing)
            buttons.append({
                "rect": pygame.Rect(x, button_y, button_width, button_height),
                "text": text, "action": action, "color": color
            })
        return buttons
        
    def _create_env_buttons(self):
        """Create UI buttons for environment/sensor control"""
        env_buttons = []
        top = 20
        col_w = int(SCREEN_WIDTH * 0.037)
        label_w = int(SCREEN_WIDTH * 0.074)
        h = int(SCREEN_HEIGHT * 0.045)
        spacing = int(SCREEN_WIDTH * 0.012)
        # Light
        env_buttons.append({"rect": pygame.Rect(20, top, col_w, h), "text": "-", "action": "light_down", "color": DARK_GRAY})
        env_buttons.append({"rect": pygame.Rect(20 + col_w + spacing, top, label_w, h), "text": "Light", "action": None, "color": WHITE})
        env_buttons.append({"rect": pygame.Rect(20 + col_w + spacing + label_w + spacing, top, col_w, h), "text": "+", "action": "light_up", "color": DARK_GRAY})
        # Temp
        env_buttons.append({"rect": pygame.Rect(20 + 2*(col_w + label_w + 2*spacing), top, col_w, h), "text": "-", "action": "temp_down", "color": DARK_GRAY})
        env_buttons.append({"rect": pygame.Rect(20 + 2*(col_w + label_w + 2*spacing) + col_w + spacing, top, label_w, h), "text": "Temp", "action": None, "color": WHITE})
        env_buttons.append({"rect": pygame.Rect(20 + 2*(col_w + label_w + 2*spacing) + col_w + spacing + label_w + spacing, top, col_w, h), "text": "+", "action": "temp_up", "color": DARK_GRAY})
        # Sound
        env_buttons.append({"rect": pygame.Rect(20 + 4*(col_w + label_w + 2*spacing), top, col_w, h), "text": "-", "action": "sound_down", "color": DARK_GRAY})
        env_buttons.append({"rect": pygame.Rect(20 + 4*(col_w + label_w + 2*spacing) + col_w + spacing, top, label_w, h), "text": "Sound", "action": None, "color": WHITE})
        env_buttons.append({"rect": pygame.Rect(20 + 4*(col_w + label_w + 2*spacing) + col_w + spacing + label_w + spacing, top, col_w, h), "text": "+", "action": "sound_up", "color": DARK_GRAY})
        # Season
        env_buttons.append({"rect": pygame.Rect(SCREEN_WIDTH - 2*label_w - 2*spacing, top, label_w, h), "text": "Season", "action": "season_next", "color": LIGHT_BLUE})
        # Time
        env_buttons.append({"rect": pygame.Rect(SCREEN_WIDTH - label_w - spacing, top, label_w, h), "text": "Time", "action": "time_next", "color": YELLOW})
        return env_buttons
        
    def handle_hardware_buttons(self):
        """Handle physical button presses"""
        button_states = self.tamagotchi.hardware.sensor_data['button_states']
        
        if button_states['feed']:
            self.tamagotchi.feed()
        if button_states['pet']:
            self.tamagotchi.pet()
        if button_states['play']:
            self.tamagotchi.play()
        if button_states['sleep']:
            if self.tamagotchi.sleep_mode:
                self.tamagotchi.wake_up()
            else:
                self.tamagotchi.put_to_sleep()
    
    def handle_events(self):
        """Handle pygame events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.VIDEORESIZE:
                global SCREEN_WIDTH, SCREEN_HEIGHT
                SCREEN_WIDTH = max(MIN_SCREEN_WIDTH, event.w)
                SCREEN_HEIGHT = max(MIN_SCREEN_HEIGHT, event.h)
                self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
                self.buttons = self._create_ui_buttons()
                self.env_buttons = self._create_env_buttons()
                self.tamagotchi.x = SCREEN_WIDTH // 2
                self.tamagotchi.y = SCREEN_HEIGHT // 2
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_d:
                    self.show_debug = not self.show_debug
                elif event.key == pygame.K_f:
                    self.tamagotchi.feed()
                elif event.key == pygame.K_p:
                    self.tamagotchi.pet()
                elif event.key == pygame.K_g:
                    self.tamagotchi.play()
                elif event.key == pygame.K_s:
                    if self.tamagotchi.sleep_mode:
                        self.tamagotchi.wake_up()
                    else:
                        self.tamagotchi.put_to_sleep()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mouse_pos = pygame.mouse.get_pos()
                for button in self.buttons:
                    if button["rect"].collidepoint(mouse_pos):
                        action = button["action"]
                        if action == "feed":
                            self.tamagotchi.feed()
                        elif action == "pet":
                            self.tamagotchi.pet()
                        elif action == "play":
                            self.tamagotchi.play()
                        elif action == "sleep":
                            if self.tamagotchi.sleep_mode:
                                self.tamagotchi.wake_up()
                            else:
                                self.tamagotchi.put_to_sleep()
                        elif action == "debug":
                            self.show_debug = not self.show_debug
                        elif action == "motion":
                            # Set flag to simulate motion in the next sensor cycle
                            self.tamagotchi.hardware.simulate_motion_flag = True
                for button in self.env_buttons:
                    if button["action"] and button["rect"].collidepoint(mouse_pos):
                        self.handle_env_button(button["action"])
    
    def handle_env_button(self, action):
        """Handle environment/sensor control button actions"""
        if action == "light_up":
            self.tamagotchi.hardware.sim_light_level = min(1000, self.tamagotchi.hardware.sim_light_level + 50)
        elif action == "light_down":
            self.tamagotchi.hardware.sim_light_level = max(0, self.tamagotchi.hardware.sim_light_level - 50)
        elif action == "temp_up":
            self.tamagotchi.hardware.sim_temperature = min(40, self.tamagotchi.hardware.sim_temperature + 1)
        elif action == "temp_down":
            self.tamagotchi.hardware.sim_temperature = max(-10, self.tamagotchi.hardware.sim_temperature - 1)
        elif action == "sound_up":
            self.tamagotchi.hardware.sim_sound_level = min(120, self.tamagotchi.hardware.sim_sound_level + 5)
        elif action == "sound_down":
            self.tamagotchi.hardware.sim_sound_level = max(0, self.tamagotchi.hardware.sim_sound_level - 5)
        elif action == "season_next":
            self.tamagotchi.hardware.sim_season_idx = (self.tamagotchi.hardware.sim_season_idx + 1) % len(self.tamagotchi.hardware.sim_season_list)
            self.tamagotchi.hardware.sim_season = self.tamagotchi.hardware.sim_season_list[self.tamagotchi.hardware.sim_season_idx]
        elif action == "time_next":
            self.tamagotchi.hardware.sim_time_idx = (self.tamagotchi.hardware.sim_time_idx + 1) % len(self.tamagotchi.hardware.sim_time_list)
            self.tamagotchi.hardware.sim_time = self.tamagotchi.hardware.sim_time_list[self.tamagotchi.hardware.sim_time_idx]
    
    def draw_ui_buttons(self):
        """Draw interactive UI buttons, scaled to window size and align top UI text under buttons"""
        font = pygame.font.Font(None, int(SCREEN_HEIGHT * 0.03))
        font_small = pygame.font.Font(None, int(SCREEN_HEIGHT * 0.025))
        # Draw main buttons
        for button in self.buttons:
            pygame.draw.rect(self.screen, button["color"], button["rect"])
            pygame.draw.rect(self.screen, BLACK, button["rect"], 2)
            text = font.render(button["text"], True, BLACK)
            text_rect = text.get_rect(center=button["rect"].center)
            self.screen.blit(text, text_rect)
        # Draw environment/sensor control buttons and center value text under each
        for button in self.env_buttons:
            pygame.draw.rect(self.screen, button["color"], button["rect"])
            pygame.draw.rect(self.screen, BLACK, button["rect"], 2)
            text = font.render(button["text"], True, BLACK)
            text_rect = text.get_rect(center=button["rect"].center)
            self.screen.blit(text, text_rect)
            # Center value text under the label button (not -/+), and always for Season/Time
            label = button["text"].lower()
            show_value = (button["action"] is None) or (label == "season") or (label == "time")
            if show_value:
                if label == "light":
                    val_text = font_small.render(f"{int(self.tamagotchi.hardware.sim_light_level)}", True, BLACK)
                elif label == "temp":
                    val_text = font_small.render(f"{self.tamagotchi.hardware.sim_temperature:.1f}C", True, BLACK)
                elif label == "sound":
                    val_text = font_small.render(f"{int(self.tamagotchi.hardware.sim_sound_level)}dB", True, BLACK)
                elif label == "season":
                    val_text = font_small.render(self.tamagotchi.hardware.sim_season.value.title(), True, BLACK)
                elif label == "time":
                    val_text = font_small.render(self.tamagotchi.hardware.sim_time.value.title(), True, BLACK)
                else:
                    val_text = None
                if val_text:
                    val_rect = val_text.get_rect(center=(button["rect"].centerx, button["rect"].bottom + int(SCREEN_HEIGHT * 0.012)))
                    self.screen.blit(val_text, val_rect)
    
    def draw_background(self):
        """Draw environment-appropriate background"""
        env_state = self.tamagotchi.hardware.get_environment_state()
        season = self.tamagotchi.hardware.get_season()
        
        # Base colors
        if env_state == EnvironmentState.DAY:
            bg_color = (135, 206, 235)  # Sky blue
        elif env_state == EnvironmentState.NIGHT:
            bg_color = (25, 25, 112)    # Midnight blue
        elif env_state == EnvironmentState.DAWN:
            bg_color = (255, 165, 0)    # Orange
        else:  # DUSK
            bg_color = (255, 69, 0)     # Red-orange
            
        self.screen.fill(bg_color)
        
        # Seasonal elements
        if season == Season.WINTER:
            # Draw snowflakes
            for _ in range(20):
                x = random.randint(0, SCREEN_WIDTH)
                y = random.randint(0, SCREEN_HEIGHT)
                pygame.draw.circle(self.screen, WHITE, (x, y), 2)
        elif season == Season.SPRING:
            # Draw flowers
            for _ in range(10):
                x = random.randint(50, SCREEN_WIDTH - 50)
                y = random.randint(SCREEN_HEIGHT - 100, SCREEN_HEIGHT - 50)
                pygame.draw.circle(self.screen, (255, 182, 193), (x, y), 5)
    
    def run(self):
        """Main game loop"""
        try:
            while self.running:
                dt = self.clock.tick(FPS) / 1000.0
                
                # Handle events
                self.handle_events()
                self.handle_hardware_buttons()
                
                # Update game state
                self.tamagotchi.update(dt)
                
                # Draw everything
                self.draw_background()
                self.tamagotchi.draw(self.screen)
                self.tamagotchi.draw_status_bars(self.screen)
                
                if self.show_debug:
                    self.tamagotchi.draw_environmental_info(self.screen)
                
                self.draw_ui_buttons()
                
                # Draw instructions at bottom right, stacking upwards
                font = pygame.font.Font(None, 20)
                instructions = [
                    "Keys: F=Feed, P=Pet, G=Play, S=Sleep, D=Debug, ESC=Quit",
                    "Hardware: Use physical buttons or shake/pick up device"
                ]
                for i, instruction in enumerate(reversed(instructions)):
                    text = font.render(instruction, True, BLACK)
                    text_rect = text.get_rect(bottomright=(SCREEN_WIDTH - 10, SCREEN_HEIGHT - 10 - i * 24))
                    self.screen.blit(text, text_rect)
                
                pygame.display.flip()
                
        except KeyboardInterrupt:
            print("Shutting down gracefully...")
        finally:
            pygame.quit()

def main():
    """Main entry point"""
    print("Starting Smart Raspberry Pi Tamagotchi...")
    print("Hardware sensors: Light, Temperature, 6DOF IMU, Sound, Buttons")
    print("Hardware outputs: RGB LEDs, Buzzer, Servo motor")
    print("Press Ctrl+C to exit")
    
    game = GameManager()
    game.run()

if __name__ == "__main__":
    main()