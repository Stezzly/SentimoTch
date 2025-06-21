class IMUSensor:
    def __init__(self, i2c=None, simulation=False):
        self.simulation = simulation
        self.i2c = i2c
        if not simulation and i2c is not None:
            try:
                import adafruit_mpu6050  # type: ignore
                self.sensor = adafruit_mpu6050.MPU6050(i2c)
            except ImportError:
                self.sensor = None
        else:
            self.sensor = None
        self.sim_acceleration = {'x': 0, 'y': 0, 'z': 9.8}
        self.sim_gyro = {'x': 0, 'y': 0, 'z': 0}

    def read_acceleration(self):
        if self.sensor:
            accel = self.sensor.acceleration
            return {'x': accel[0], 'y': accel[1], 'z': accel[2]}
        else:
            return self.sim_acceleration

    def read_gyro(self):
        if self.sensor:
            gyro = self.sensor.gyro
            return {'x': gyro[0], 'y': gyro[1], 'z': gyro[2]}
        else:
            return self.sim_gyro 