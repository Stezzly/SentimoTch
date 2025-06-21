class Buttons:
    def __init__(self, pins=None, simulation=False):
        self.simulation = simulation
        self.pins = pins or {}
        if not simulation and pins is not None:
            try:
                import digitalio  # type: ignore
                self.buttons = {name: digitalio.DigitalInOut(pin) for name, pin in pins.items()}
                for button in self.buttons.values():
                    button.direction = digitalio.Direction.INPUT
                    button.pull = digitalio.Pull.UP
            except ImportError:
                self.buttons = None
        else:
            self.buttons = None
        self.sim_button_states = {name: False for name in (pins or ['feed','pet','play','sleep'])}

    def read(self):
        if self.buttons:
            return {name: not btn.value for name, btn in self.buttons.items()}
        else:
            return self.sim_button_states 