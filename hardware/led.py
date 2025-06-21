class LED:
    def __init__(self, pin=None, num_pixels=8, simulation=False):
        self.simulation = simulation
        self.pin = pin
        self.num_pixels = num_pixels
        if not simulation and pin is not None:
            try:
                import neopixel  # type: ignore
                self.pixels = neopixel.NeoPixel(pin, num_pixels, brightness=0.3)
            except ImportError:
                self.pixels = None
        else:
            self.pixels = None
        self.sim_color = (255, 255, 255)
        self.sim_brightness = 0.3

    def set_color(self, color, brightness=0.3):
        if self.pixels:
            self.pixels.brightness = brightness
            self.pixels.fill(color)
            self.pixels.show()
        else:
            self.sim_color = color
            self.sim_brightness = brightness 