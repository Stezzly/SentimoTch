#!/usr/bin/python
# Simple Tamagotchi with 3-button control
import os
import sys
import time
import random
import select
import termios
import tty
import glob
from gpiozero import Button
from threading import Thread
sys.path.append("..")
from lib import LCD_2inch
from PIL import Image, ImageDraw, ImageFont

# DISPLAY CONFIGURATION - Change these values to adjust the screen
SCREEN_ROTATION = 0        # Try: 0, 90, 180, 270
SCREEN_WIDTH = 240          # Display width
SCREEN_HEIGHT = 320         # Display height
FLIP_HORIZONTAL = False     # Set to True to flip horizontally
FLIP_VERTICAL = False       # Set to True to flip vertically

# EMOJI CONFIGURATION
EMOTIONS_FOLDER = "assets"  # Folder containing emotion images
ICONS_FOLDER = "assets/icons"  # Folder containing icon images

# TEMPERATURE SENSOR CONFIGURATION
TEMP_SENSOR_ID = "28-*"  # DS18B20 sensor ID pattern
TEMP_COLD_THRESHOLD = 18.0  # Below this is cold
TEMP_HOT_THRESHOLD = 25.0   # Above this is hot

class SimpleTamagotchi:
    def __init__(self):
        self.health = 100
        self.happy = 100
        self.hungry = 50
        self.last_update = time.time()
        self.current_action = 0  # 0=Feed, 1=Play, 2=Heal
        self.actions = ["FEED", "PLAY", "HEAL"]
        self.current_temperature = None
        
        # Emoji to image mapping
        self.emoji_map = {
            "happy": "heart_happy.png",
            "sad": "heart_sad.png", 
            "angry": "heart_angry.png",
            "sleepy": "heart_sleepy.png",
            "excited": "heart_excited.png",
            "neutral": "heart_neutral.png",
            "cold": "heart_cold.png",
            "scared": "heart_scared.png",
            "playful": "heart_playful.png"
        }
        
        # Temperature icons mapping
        self.temp_icon_map = {
            "cold": "temp_cold.png",
            "hot": "temp_hot.png",
            "neutral": "temp_neutral.png"
        }
        
        # Load emotion images and temperature icons
        self.emotion_images = {}
        self.temp_icons = {}
        self.load_emotion_images()
        self.load_temp_icons()
        
    def load_emotion_images(self):
        """Load emotion images from the emotions folder"""
        for emotion, filename in self.emoji_map.items():
            try:
                image_path = os.path.join(EMOTIONS_FOLDER, filename)
                if os.path.exists(image_path):
                    # Load and resize image to fit in the display area (60x60 pixels)
                    img = Image.open(image_path)
                    img = img.resize((60, 60), Image.Resampling.LANCZOS)
                    self.emotion_images[emotion] = img
                    print(f"Loaded emotion image: {emotion}")
                else:
                    print(f"Warning: Image not found: {image_path}")
            except Exception as e:
                print(f"Error loading {emotion} image: {e}")
        
        print(f"Loaded {len(self.emotion_images)} emotion images")
        
    def load_temp_icons(self):
        """Load temperature icons from the icons folder"""
        for temp_state, filename in self.temp_icon_map.items():
            try:
                image_path = os.path.join(ICONS_FOLDER, filename)
                if os.path.exists(image_path):
                    # Load and resize image to fit in the display area (30x30 pixels)
                    img = Image.open(image_path)
                    img = img.resize((30, 30), Image.Resampling.LANCZOS)
                    self.temp_icons[temp_state] = img
                    print(f"Loaded temperature icon: {temp_state}")
                else:
                    print(f"Warning: Temperature icon not found: {image_path}")
            except Exception as e:
                print(f"Error loading {temp_state} temperature icon: {e}")
        
        print(f"Loaded {len(self.temp_icons)} temperature icons")
        
    def read_temperature(self):
        """Read temperature from DS18B20 sensor"""
        try:
            # Find DS18B20 sensor files
            base_dir = '/sys/bus/w1/devices/'
            device_folders = glob.glob(base_dir + TEMP_SENSOR_ID)
            
            if not device_folders:
                print("No DS18B20 temperature sensor found")
                return None
                
            device_file = device_folders[0] + '/w1_slave'
            
            with open(device_file, 'r') as f:
                lines = f.readlines()
                
            # Check if reading is valid
            if lines[0].strip()[-3:] != 'YES':
                return None
                
            # Extract temperature
            temp_line = lines[1]
            temp_pos = temp_line.find('t=')
            if temp_pos != -1:
                temp_string = temp_line[temp_pos+2:]
                temp_c = float(temp_string) / 1000.0
                self.current_temperature = temp_c
                return temp_c
                
        except Exception as e:
            print(f"Error reading temperature: {e}")
            
        return None
        
    def get_temperature_status(self):
        """Get temperature status based on current reading"""
        if self.current_temperature is None:
            return "neutral"
        elif self.current_temperature < TEMP_COLD_THRESHOLD:
            return "cold"
        elif self.current_temperature > TEMP_HOT_THRESHOLD:
            return "hot"
        else:
            return "neutral"
        
    def get_current_emoji(self):
        # Determine emoji based on stats
        if self.health < 20:
            return "scared"
        elif self.hungry > 80:
            return "sleepy"
        elif self.hungry < 20:
            return "angry"
        elif self.happy > 80:
            return "excited"
        elif self.happy < 30:
            return "sad"
        elif self.happy > 60 and self.health > 60:
            return "happy"
        else:
            return "neutral"
    
    def update_stats(self):
        current_time = time.time()
        if current_time - self.last_update >= 10:  # Update every 10 seconds
            self.hungry = max(0, self.hungry - random.randint(5, 15))
            self.happy = max(0, self.happy - random.randint(3, 8))
            
            if self.hungry < 20:
                self.health = max(0, self.health - random.randint(5, 10))
            
            self.last_update = current_time
    
    def feed(self):
        self.hungry = min(100, self.hungry + 30)
        self.happy = min(100, self.happy + 5)
        
    def play(self):
        self.happy = min(100, self.happy + 25)
        self.hungry = max(0, self.hungry - 10)
        
    def heal(self):
        self.health = min(100, self.health + 20)
        self.hungry = max(0, self.hungry - 5)

def draw_ui(draw, pet, font_small, font_large):
    # Clear screen
    draw.rectangle([(0, 0), (SCREEN_WIDTH, SCREEN_HEIGHT)], fill="WHITE")
    
    # Title
    draw.text((80, 10), "TAMAGOTCHI", fill="BLACK", font=font_large)
    
    # Display temperature icon in top right corner
    temp_status = pet.get_temperature_status()
    temp_icon_x, temp_icon_y = SCREEN_WIDTH - 40, 10
    
    if temp_status in pet.temp_icons:
        temp_img = pet.temp_icons[temp_status]
        temp_rgba = temp_img.convert("RGBA")
        temp_overlay = Image.new("RGBA", (SCREEN_WIDTH, SCREEN_HEIGHT), (255, 255, 255, 0))
        temp_overlay.paste(temp_rgba, (temp_icon_x, temp_icon_y), temp_rgba)
        draw._image.paste(temp_overlay, (0, 0), temp_overlay)
    
    # Display current temperature value
    if pet.current_temperature is not None:
        draw.text((temp_icon_x - 30, temp_icon_y + 35), f"{pet.current_temperature:.1f}°C", 
                 fill="BLACK", font=font_small)
    
    # Display emotion image or fallback to text
    emoji_name = pet.get_current_emoji()
    emoji_x, emoji_y = 90, 50
    emoji_size = 60
    
    if emoji_name in pet.emotion_images:
        # Paste the actual emotion image
        emotion_img = pet.emotion_images[emoji_name]
        image_to_paste = emotion_img.convert("RGBA")
        # Create a temporary image to paste onto
        temp_img = Image.new("RGBA", (SCREEN_WIDTH, SCREEN_HEIGHT), (255, 255, 255, 0))
        temp_img.paste(image_to_paste, (emoji_x, emoji_y), image_to_paste)
        # Convert back and paste
        draw._image.paste(temp_img, (0, 0), temp_img)
    else:
        # Fallback to text display
        draw.rectangle([(emoji_x, emoji_y), (emoji_x + emoji_size, emoji_y + emoji_size)], 
                      fill="LIGHTGRAY", outline="BLACK")
        draw.text((emoji_x + 10, emoji_y + 25), emoji_name.upper(), fill="BLACK", font=font_small)
    
    # Stats
    y = 130
    draw.text((20, y), f"Health: {pet.health}%", fill="BLACK", font=font_small)
    draw.text((20, y+25), f"Happy: {pet.happy}%", fill="BLACK", font=font_small)
    draw.text((20, y+50), f"Hungry: {pet.hungry}%", fill="BLACK", font=font_small)
    
    # Action selection
    y = 220
    draw.text((20, y), "Actions:", fill="BLACK", font=font_small)
    
    for i, action in enumerate(pet.actions):
        color = "YELLOW" if i == pet.current_action else "LIGHTGRAY"
        draw.rectangle([(20 + i*70, y+25), (80 + i*70, y+50)], fill=color, outline="BLACK")
        draw.text((25 + i*70, y+30), action, fill="BLACK", font=font_small)
    
    # Controls
    draw.text((20, 290), "Keys: A/D=Navigate  S=Action", fill="BLACK", font=font_small)

def keyboard_input_handler():
    """Handle keyboard input in a separate thread"""
    global pet, update_display
    
    # Set terminal to raw mode for immediate key detection
    old_settings = termios.tcgetattr(sys.stdin)
    try:
        tty.setraw(sys.stdin.fileno())
        
        while True:
            # Check if input is available
            if select.select([sys.stdin], [], [], 0.1)[0]:
                key = sys.stdin.read(1).lower()
                
                if key == 'a':  # Left
                    left_pressed()
                    print(f"Left pressed - Action: {pet.actions[pet.current_action]}")
                elif key == 'd':  # Right
                    right_pressed()
                    print(f"Right pressed - Action: {pet.actions[pet.current_action]}")
                elif key == 's':  # Select
                    action_name = pet.actions[pet.current_action]
                    select_pressed()
                    print(f"Action executed: {action_name}")
                elif key == 'q':  # Quit
                    print("Quitting...")
                    break
                elif key == 'h':  # Help
                    print("\nControls:")
                    print("A - Navigate Left")
                    print("D - Navigate Right") 
                    print("S - Select Action")
                    print("H - Show this help")
                    print("Q - Quit")
                    print(f"Current stats: Health={pet.health}, Happy={pet.happy}, Hungry={pet.hungry}")
                    
    except Exception as e:
        print(f"Keyboard input error: {e}")
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

# Initialize hardware
RST = 27
DC = 25
BL = 18

# Buttons
left_btn = Button(19)
# right_btn = Button(17)  # Re-enabled right button since GPIO 16 is used for temperature sensor
select_btn = Button(17)  # GPIO 16 is now used for DS18B20 temperature sensor

# Global variables
pet = SimpleTamagotchi()
update_display = True

def left_pressed():
    global pet, update_display
    pet.current_action = (pet.current_action - 1) % 3
    update_display = True

def right_pressed():
    global pet, update_display
    pet.current_action = (pet.current_action + 1) % 3
    update_display = True

def select_pressed():
    global pet, update_display
    if pet.current_action == 0:
        pet.feed()
    elif pet.current_action == 1:
        pet.play()
    elif pet.current_action == 2:
        pet.heal()
    update_display = True

def stats_updater():
    global pet, update_display
    while True:
        pet.update_stats()
        pet.read_temperature()  # Read temperature every update cycle
        update_display = True
        time.sleep(10)

# Setup button callbacks
left_btn.when_pressed = left_pressed
# right_btn.when_pressed = right_pressed
select_btn.when_pressed = select_pressed  # GPIO 16 is now used for temperature sensor

try:
    # Initialize display
    disp = LCD_2inch.LCD_2inch()
    disp.Init()
    disp.clear()
    disp.bl_DutyCycle(50)
    
    # Load fonts
    font_small = ImageFont.load_default()
    font_large = ImageFont.load_default()
    
    # Start stats updater thread
    stats_thread = Thread(target=stats_updater, daemon=True)
    stats_thread.start()
    
    # Start keyboard input handler thread
    keyboard_thread = Thread(target=keyboard_input_handler, daemon=True)
    keyboard_thread.start()
    
    print("Tamagotchi Started!")
    print("Use buttons: GPIO19=Left, GPIO17=Right")
    print("Or use keyboard: A=Left, D=Right, S=Select, H=Help, Q=Quit")
    print("Temperature sensor on GPIO16")
    
    # Main loop
    while True:
        if update_display:
            image = Image.new("RGB", (SCREEN_WIDTH, SCREEN_HEIGHT), "WHITE")
            draw = ImageDraw.Draw(image)
            draw_ui(draw, pet, font_small, font_large)
            
            # Apply transformations based on configuration
            if FLIP_HORIZONTAL:
                image = image.transpose(Image.FLIP_LEFT_RIGHT)
            if FLIP_VERTICAL:
                image = image.transpose(Image.FLIP_TOP_BOTTOM)
            if SCREEN_ROTATION != 0:
                image = image.rotate(SCREEN_ROTATION)
            
            disp.ShowImage(image)
            update_display = False
        
        time.sleep(0.1)  # Small delay to prevent excessive CPU usage

except KeyboardInterrupt:
    disp.module_exit()
    print("Game ended by user")



