class LightSensor:
    def __init__(self, i2c=None, simulation=False):
        self.simulation = simulation
        self.i2c = i2c
        if not simulation and i2c is not None:
            try:
                import adafruit_tsl2591  # type: ignore
                self.sensor = adafruit_tsl2591.TSL2591(i2c)
            except ImportError:
                self.sensor = None
        else:
            self.sensor = None
        self.sim_light_level = 500

    def read(self):
        if self.sensor:
            return self.sensor.lux
        else:
            return self.sim_light_level 