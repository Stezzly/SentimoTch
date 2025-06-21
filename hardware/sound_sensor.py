class SoundSensor:
    def __init__(self, analog_in=None, simulation=False):
        self.simulation = simulation
        self.analog_in = analog_in
        if not simulation and analog_in is not None:
            self.sensor = analog_in
        else:
            self.sensor = None
        self.sim_sound_level = 30

    def read(self):
        if self.sensor:
            # Convert analog value to dB approximation
            sound_raw = self.sensor.value
            return (sound_raw / 65536) * 100
        else:
            return self.sim_sound_level 