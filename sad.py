#!/usr/bin/python
# Simple Tamagotchi with 3-button control and LED eyes
import os
import sys
import time
import random
import select
import termios
import tty
import glob
import RPi.GPIO as GPIO
from gpiozero import Button, PWMLED
from threading import Thread
sys.path.append("..")
from lib import LCD_2inch
from PIL import Image, ImageDraw, ImageFont

# =============================================================================
# CONFIGURATION VARIABLES - Modify these to customize behavior
# =============================================================================

# DISPLAY CONFIGURATION - Change these values to adjust the screen
SCREEN_ROTATION = 0        # Try: 0, 90, 180, 270
SCREEN_WIDTH = 240          # Display width
SCREEN_HEIGHT = 320         # Display height
FLIP_HORIZONTAL = False     # Set to True to flip horizontally
FLIP_VERTICAL = False       # Set to True to flip vertically

# LED EYES CONFIGURATION
LED_RED_PIN = 20           # GPIO pin for red LED
LED_GREEN_PIN = 22         # GPIO pin for green LED
LED_BRIGHTNESS = 0.8       # LED brightness (0.0 to 1.0)

# EMOJI CONFIGURATION
EMOTIONS_FOLDER = "assets"  # Folder containing emotion images
ICONS_FOLDER = "assets/icons"  # Folder containing icon images

# STATS ICONS CONFIGURATION
STATS_ICONS = {
    "health": {
        "empty": "health_empty.png",    # 0-33%
        "half": "health_half.png",      # 34-66%
        "full": "health_full.png"       # 67-100%
    },
    "happy": {
        "sad": "face_sad.png",          # 0-33%
        "neutral": "face_neutral.png",  # 34-66%
        "happy": "face_happy.png"       # 67-100%
    },
    "hungry": {
        "empty": "stomach_empty.png",   # 0-33%
        "half": "stomach_half.png",     # 34-66%
        "full": "stomach_full.png"      # 67-100%
    }
}

# TEMPERATURE SENSOR CONFIGURATION
TEMP_SENSOR_ID = "28-*"  # DS18B20 sensor ID pattern
TEMP_COLD_THRESHOLD = 18.0  # Below this is cold
TEMP_HOT_THRESHOLD = 25.0   # Above this is hot

# IR OBSTACLE SENSOR CONFIGURATION
IR_PIN = 26  # GPIO pin for IR obstacle sensor

# HARDWARE PINS
RST = 27
DC = 25
BL = 18
LEFT_BUTTON_PIN = 19
SELECT_BUTTON_PIN = 17

# GAME SETTINGS
STATS_UPDATE_INTERVAL = 10  # How often stats decrease (seconds)
SENSOR_CHECK_INTERVAL = 0.5  # How often to check sensors (seconds)
INTERACTION_DURATION = 3    # How long interactions last (seconds)
INTERACTION_COOLDOWN = 3    # Cooldown between interactions (seconds)

# =============================================================================
# END OF CONFIGURATION
# =============================================================================

class SimpleTamagotchi:
    def __init__(self):
        self.health = 100
        self.happy = 100
        self.hungry = 50
        self.last_update = time.time()
        self.current_action = 0  # 0=Feed, 1=Play, 2=Heal
        self.actions = ["FEED", "PLAY", "HEAL"]
        self.current_temperature = None
        self.interaction_mode = None  # Current interaction mode from IR sensor
        self.interaction_message = ""  # Message to display
        self.interaction_timer = 0  # Timer for how long to show interaction
        self.forced_emotion = None  # Override emotion during interaction
        
        # Initialize GPIO for IR sensor
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(IR_PIN, GPIO.IN)
        
        # Initialize LED eyes - do this after GPIO setup to avoid conflicts
        try:
            self.led_red = PWMLED(LED_RED_PIN)
            self.led_green = PWMLED(LED_GREEN_PIN)
            self.current_led_state = "sleep"  # Track current LED state
            print(f"LED Eyes initialized: Red=GPIO{LED_RED_PIN}, Green=GPIO{LED_GREEN_PIN}")
        except Exception as e:
            print(f"Error initializing LED eyes: {e}")
            self.led_red = None
            self.led_green = None
        
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
        self.stats_icons = {}
        self.load_emotion_images()
        self.load_temp_icons()
        self.load_stats_icons()
        
        # Set initial LED state
        self.update_led_eyes()
        
    def get_led_state(self):
        """Determine LED state based on pet's condition"""
        # If interaction is active, use forced emotion for LED state
        if self.forced_emotion is not None:
            if self.forced_emotion in ["angry"]:
                return "angry"
            elif self.forced_emotion in ["excited", "happy"]:
                return "happy"
            else:
                return "sleep"
        
        # Determine LED state based on stats
        if self.health < 30 or self.hungry > 80:
            return "sleep"  # Pet is too weak/tired
        elif self.hungry < 20 or self.health < 20:
            return "angry"  # Pet is angry due to neglect
        elif self.happy > 60 and self.health > 60:
            return "happy"  # Pet is content
        else:
            return "sleep"  # Default neutral state
    
    def update_led_eyes(self):
        """Update LED eyes based on current state"""
        new_state = self.get_led_state()
        
        # Only update if state has changed to reduce unnecessary GPIO operations
        if new_state != self.current_led_state:
            # Always turn off both LEDs first to ensure clean state
            if self.led_red:
                self.led_red.off()
            if self.led_green:
                self.led_green.off()
            
            if new_state == "sleep":
                # Both LEDs already off
                print("LED Eyes: Sleep (OFF)")
                
            elif new_state == "happy":
                # Turn on green LED only
                if self.led_green:
                    self.led_green.value = LED_BRIGHTNESS
                print("LED Eyes: Happy (GREEN)")
                
            elif new_state == "angry":
                # Turn on red LED only
                if self.led_red:
                    self.led_red.value = LED_BRIGHTNESS
                print("LED Eyes: Angry (RED)")
            
            self.current_led_state = new_state
        
    def load_emotion_images(self):
        """Load emotion images from the emotions folder"""
        for emotion, filename in self.emoji_map.items():
            try:
                image_path = os.path.join(EMOTIONS_FOLDER, filename)
                if os.path.exists(image_path):
                    # Load and resize image to fit in the display area (80x80 pixels - increased from 60x60)
                    img = Image.open(image_path)
                    img = img.resize((100, 100), Image.Resampling.LANCZOS)
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
        
    def load_stats_icons(self):
        """Load stats icons from the icons folder"""
        for stat_type, icon_dict in STATS_ICONS.items():
            self.stats_icons[stat_type] = {}
            for state, filename in icon_dict.items():
                try:
                    image_path = os.path.join(ICONS_FOLDER, filename)
                    if os.path.exists(image_path):
                        # Load and resize image to fit next to text (20x20 pixels)
                        img = Image.open(image_path)
                        img = img.resize((20, 20), Image.Resampling.LANCZOS)
                        self.stats_icons[stat_type][state] = img
                        print(f"Loaded {stat_type} icon: {state}")
                    else:
                        print(f"Warning: Stats icon not found: {image_path}")
                except Exception as e:
                    print(f"Error loading {stat_type} {state} icon: {e}")
        
        print(f"Loaded stats icons for {len(self.stats_icons)} stat types")
        
    def get_stat_icon_state(self, stat_value, stat_type):
        """Get the appropriate icon state based on stat value"""
        if stat_value <= 33:
            if stat_type == "health":
                return "empty"
            elif stat_type == "happy":
                return "sad"
            elif stat_type == "hungry":
                return "empty"
        elif stat_value <= 66:
            if stat_type == "health":
                return "half"
            elif stat_type == "happy":
                return "neutral"
            elif stat_type == "hungry":
                return "half"
        else:
            if stat_type == "health":
                return "full"
            elif stat_type == "happy":
                return "happy"
            elif stat_type == "hungry":
                return "full"
        return "empty"  # fallback
        
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
            
    def check_ir_sensor(self):
        """Check IR obstacle sensor and trigger interactions"""
        try:
            sensor_value = GPIO.input(IR_PIN)
            
            if sensor_value == 0:  # Obstacle detected
                current_time = time.time()
                
                # Only trigger new interaction if no current interaction or timer expired
                if self.interaction_timer == 0 or current_time - self.interaction_timer > INTERACTION_COOLDOWN:
                    # Randomly choose interaction type
                    interaction_type = random.choice([1, 2, 3])
                    
                    if interaction_type == 1:
                        # Angry reaction - "DON'T TOUCH ME"
                        self.interaction_mode = "angry"
                        self.interaction_message = "DON'T TOUCH ME!"
                        self.forced_emotion = "angry"
                        self.happy = max(0, self.happy - 15)
                        print("IR: Angry reaction triggered")
                        
                    elif interaction_type == 2:
                        # Happy reaction - "I LOVE PETS"
                        self.interaction_mode = "happy"
                        self.interaction_message = "I LOVE PETS!"
                        self.forced_emotion = "excited"
                        self.happy = min(100, self.happy + 20)
                        print("IR: Happy reaction triggered")
                        
                    else:
                        # Neutral reaction
                        self.interaction_mode = "neutral"
                        self.interaction_message = "..."
                        self.forced_emotion = "neutral"
                        print("IR: Neutral reaction triggered")
                    
                    self.interaction_timer = current_time
                    
            else:
                # No obstacle - check if interaction should end
                if self.interaction_timer > 0:
                    current_time = time.time()
                    if current_time - self.interaction_timer > INTERACTION_DURATION:  # Show interaction for configured duration
                        self.interaction_mode = None
                        self.interaction_message = ""
                        self.forced_emotion = None
                        self.interaction_timer = 0
                        print("IR: Interaction ended")
                        
        except Exception as e:
            print(f"Error reading IR sensor: {e}")
        
    def get_current_emoji(self):
        # If interaction is active, override with forced emotion
        if self.forced_emotion is not None:
            return self.forced_emotion
            
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
        if current_time - self.last_update >= STATS_UPDATE_INTERVAL:  # Update using configured interval
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
    
    def cleanup(self):
        """Clean up LED resources"""
        self.led_red.close()
        self.led_green.close()

def draw_ui(draw, pet, font_small, font_large):
    # Clear screen
    draw.rectangle([(0, 0), (SCREEN_WIDTH, SCREEN_HEIGHT)], fill="WHITE")
    
    # Stats - display horizontally with icons at the top
    y = 10
    
    # Display stats with evenly spaced icons in a row (4 stats now including temperature)
    total_width = SCREEN_WIDTH - 40  # Leave 20px margin on each side
    icon_spacing = total_width // 4  # Divide space evenly for 4 stats
    start_x = 20 + (icon_spacing - 20) // 2  # Center icons within their sections
    
    # Health with icon
    health_icon_x = start_x
    health_state = pet.get_stat_icon_state(pet.health, "health")
    if "health" in pet.stats_icons and health_state in pet.stats_icons["health"]:
        health_icon = pet.stats_icons["health"][health_state]
        icon_rgba = health_icon.convert("RGBA")
        icon_overlay = Image.new("RGBA", (SCREEN_WIDTH, SCREEN_HEIGHT), (255, 255, 255, 0))
        icon_overlay.paste(icon_rgba, (health_icon_x, y), icon_rgba)
        draw._image.paste(icon_overlay, (0, 0), icon_overlay)
    # Health percentage below icon
    draw.text((health_icon_x - 5, y + 25), f"{pet.health}%", fill="BLACK", font=font_small)
    
    # Happy with icon
    happy_icon_x = start_x + icon_spacing
    happy_state = pet.get_stat_icon_state(pet.happy, "happy")
    if "happy" in pet.stats_icons and happy_state in pet.stats_icons["happy"]:
        happy_icon = pet.stats_icons["happy"][happy_state]
        icon_rgba = happy_icon.convert("RGBA")
        icon_overlay = Image.new("RGBA", (SCREEN_WIDTH, SCREEN_HEIGHT), (255, 255, 255, 0))
        icon_overlay.paste(icon_rgba, (happy_icon_x, y), icon_rgba)
        draw._image.paste(icon_overlay, (0, 0), icon_overlay)
    # Happy percentage below icon
    draw.text((happy_icon_x - 8, y + 25), f"{pet.happy}%", fill="BLACK", font=font_small)
    
    # Hungry with icon
    hungry_icon_x = start_x + 2 * icon_spacing
    hungry_state = pet.get_stat_icon_state(pet.hungry, "hungry")
    if "hungry" in pet.stats_icons and hungry_state in pet.stats_icons["hungry"]:
        hungry_icon = pet.stats_icons["hungry"][hungry_state]
        icon_rgba = hungry_icon.convert("RGBA")
        icon_overlay = Image.new("RGBA", (SCREEN_WIDTH, SCREEN_HEIGHT), (255, 255, 255, 0))
        icon_overlay.paste(icon_rgba, (hungry_icon_x, y), icon_rgba)
        draw._image.paste(icon_overlay, (0, 0), icon_overlay)
    # Hungry percentage below icon
    draw.text((hungry_icon_x - 10, y + 25), f"{pet.hungry}%", fill="BLACK", font=font_small)
    
    # Temperature with icon
    temp_icon_x = start_x + 3 * icon_spacing
    temp_status = pet.get_temperature_status()
    if temp_status in pet.temp_icons:
        temp_img = pet.temp_icons[temp_status]
        temp_rgba = temp_img.convert("RGBA")
        temp_overlay = Image.new("RGBA", (SCREEN_WIDTH, SCREEN_HEIGHT), (255, 255, 255, 0))
        # Resize temp icon to match stats icons (20x20)
        temp_resized = temp_img.resize((20, 20), Image.Resampling.LANCZOS)
        temp_rgba = temp_resized.convert("RGBA")
        temp_overlay.paste(temp_rgba, (temp_icon_x, y), temp_rgba)
        draw._image.paste(temp_overlay, (0, 0), temp_overlay)
    # Temperature value below icon
    if pet.current_temperature is not None:
        draw.text((temp_icon_x - 15, y + 25), f"{pet.current_temperature:.1f}°C", fill="BLACK", font=font_small)
    else:
        draw.text((temp_icon_x - 8, y + 25), "N/A", fill="BLACK", font=font_small)
    
    # Display interaction message if active
    if pet.interaction_message:
        # Create a background box for the message
        message_x, message_y = 20, 80
        message_width, message_height = 200, 25
        draw.rectangle([(message_x, message_y), (message_x + message_width, message_y + message_height)], 
                      fill="YELLOW", outline="BLACK")
        draw.text((message_x + 5, message_y + 5), pet.interaction_message, fill="BLACK", font=font_small)
    
    # Text output area (empty space for future text messages)
    text_area_y = 80
    if not pet.interaction_message:  # Only show when no interaction message
        draw.rectangle([(20, text_area_y), (220, text_area_y + 25)], fill="WHITE", outline="WHITE")
        draw.text((25, text_area_y + 5), "", fill="GRAY", font=font_small)
    
    # Display emotion image or fallback to text
    emoji_name = pet.get_current_emoji()
    emoji_x, emoji_y = 80, 120  # Adjusted position for larger image
    emoji_size = 80  # Increased size from 60 to 80
    
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
    
    # Action selection
    y = 240
    for i, action in enumerate(pet.actions):
        color = "YELLOW" if i == pet.current_action else "LIGHTGRAY"
        draw.rectangle([(20 + i*70, y+25), (80 + i*70, y+50)], fill=color, outline="BLACK")
        draw.text((25 + i*70, y+30), action, fill="BLACK", font=font_small)

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
                    print(f"LED Eyes: {pet.current_led_state}")
                    
    except Exception as e:
        print(f"Keyboard input error: {e}")
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

# Initialize hardware
# Buttons
left_btn = Button(LEFT_BUTTON_PIN)
select_btn = Button(SELECT_BUTTON_PIN)

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
        pet.check_ir_sensor()   # Check IR sensor for interactions
        pet.update_led_eyes()   # Update LED eyes based on current state
        update_display = True
        time.sleep(SENSOR_CHECK_INTERVAL)  # Use configured interval

# Setup button callbacks
left_btn.when_pressed = left_pressed
select_btn.when_pressed = select_pressed

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
    print(f"Use buttons: GPIO{LEFT_BUTTON_PIN}=Left, GPIO{SELECT_BUTTON_PIN}=Select")
    print("Or use keyboard: A=Left, D=Right, S=Select, H=Help, Q=Quit")
    print(f"Temperature sensor on GPIO16, IR sensor on GPIO{IR_PIN}")
    print(f"LED Eyes: Red=GPIO{LED_RED_PIN}, Green=GPIO{LED_GREEN_PIN}")
    
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
    pet.cleanup()  # Clean up LED resources
    GPIO.cleanup()  # Clean up GPIO on exit
    disp.module_exit()
    print("Game ended by user")
