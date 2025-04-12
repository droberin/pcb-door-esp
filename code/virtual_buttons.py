from machine import Pin
from time import sleep_ms


class VirtualButton:
    def __init__(self, pin_num):
        self.pin = pin_num
        print(f"Initialising virtual button using GPIO: {self.pin}")
        self.button = Pin(pin_num, Pin.IN)  # Start in high-impedance "released" state

    def push(self, duration_ms=200):
        print(f"⚡ Virtual push on GPIO{self.pin} for {duration_ms}ms")
        self.button.init(mode=Pin.OUT)
        self.button.value(0)  # Simulate button press
        sleep_ms(duration_ms)
        self.button.init(mode=Pin.IN)  # Release (high impedance)
        print(f"⚡ Virtual push on GPIO{self.pin} released")
