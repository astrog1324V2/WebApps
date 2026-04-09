import time


class BH1750:
    POWER_ON = 0x01
    RESET = 0x07
    CONTINUOUS_HIGH_RES_MODE = 0x10

    def __init__(self, i2c, address=0x23):
        self.i2c = i2c
        self.address = address
        self.i2c.writeto(self.address, bytes([self.POWER_ON]))
        self.i2c.writeto(self.address, bytes([self.RESET]))
        self.i2c.writeto(self.address, bytes([self.CONTINUOUS_HIGH_RES_MODE]))

    def read_lux(self):
        time.sleep_ms(180)
        data = self.i2c.readfrom(self.address, 2)
        raw = (data[0] << 8) | data[1]
        return round(raw / 1.2, 1)
