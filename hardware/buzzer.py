class Buzzer:
    def __init__(self, pin=None, simulation=False):
        self.simulation = simulation
        self.pin = pin
        if not simulation and pin is not None:
            try:
                import pwmio  # type: ignore
                self.buzzer = pwmio.PWMOut(pin, frequency=440, duty_cycle=0)
            except ImportError:
                self.buzzer = None
        else:
            self.buzzer = None

    def play(self, frequency, duration=0.1):
        import time
        if self.buzzer:
            self.buzzer.frequency = frequency
            self.buzzer.duty_cycle = 32768
            time.sleep(duration)
            self.buzzer.duty_cycle = 0
        else:
            # Simulate sound (could print or log)
            pass 