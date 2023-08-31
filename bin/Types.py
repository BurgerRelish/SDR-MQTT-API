import datetime

class Reading:
    def __init__(self, module: str, count: int, voltage: list[float], frequency: list[float], apparent_power: list[float], power_factor: list[float], kwh_usage: list[float], timestamp: list[datetime.datetime]):
        self.module = module
        self.voltage = voltage
        self.count = count
        self.frequency = frequency
        self.apparent_power = apparent_power
        self.power_factor = power_factor
        self.kwh_usage = kwh_usage
        self.timestamp = timestamp

class RelayStatus:
    def __init__(self, module: str, timestamp: datetime, status: bool) -> None:
        self.module = module
        self.timestamp = timestamp
        self.status = status