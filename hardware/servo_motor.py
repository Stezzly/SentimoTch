class ServoMotor:
    def __init__(self, pin=None, simulation=False):
        self.simulation = simulation
        self.pin = pin
        if not simulation and pin is not None:
            try:
                import pwmio  # type: ignore
                from adafruit_motor import servo  # type: ignore
                self.servo_pwm = pwmio.PWMOut(pin, frequency=50)
                self.servo = servo.Servo(self.servo_pwm)
            except ImportError:
                self.servo = None
        else:
            self.servo = None
        self.sim_angle = 90

    def move(self, angle):
        if self.servo:
            self.servo.angle = max(0, min(180, angle))
        else:
            self.sim_angle = angle 