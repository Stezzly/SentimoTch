class TemperatureSensor:
    def __init__(self, i2c=None, simulation=False):
        self.simulation = simulation
        self.i2c = i2c
        if not simulation and i2c is not None:
            try:
                import adafruit_bmp280  # type: ignore
                self.sensor = adafruit_bmp280.Adafruit_BMP280_I2C(i2c)
                self.sensor.sea_level_pressure = 1013.25
            except (ImportError, AttributeError, Exception):
                self.sensor = None
        else:
            self.sensor = None
        self.sim_temperature = 22.0

    def read(self):
        if self.sensor:
            return self.sensor.temperature
        else:
            return self.sim_temperature 