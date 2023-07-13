import datetime

class Reading:
    def __init__(self, module: str, voltage: float, frequency: float, apparent_power: float, power_factor: float, kwh_usage: float, timestamp: datetime, switch_status: bool):
        self.module = module
        self.voltage = voltage
        self.frequency = frequency
        self.apparent_power = apparent_power
        self.power_factor = power_factor
        self.kwh_usage = kwh_usage
        self.timestamp = timestamp
        self.switch_status = switch_status