import dht

from machine import I2C, Pin

from bh1750 import BH1750


class SensorSuite:
    def __init__(self, config):
        self.dht_sensor = dht.DHT22(Pin(config.DHT_PIN))
        self.i2c = I2C(
            config.I2C_BUS_ID,
            scl=Pin(config.I2C_SCL_PIN),
            sda=Pin(config.I2C_SDA_PIN),
            freq=100000,
        )
        self.init_errors = []
        self.i2c_addresses = self._scan_i2c()
        self.light_sensor = None

        if getattr(config, "BH1750_ENABLED", True):
            if config.BH1750_ADDR in self.i2c_addresses:
                try:
                    self.light_sensor = BH1750(self.i2c, config.BH1750_ADDR)
                except Exception:
                    self.init_errors.append("BH1750 OFFLINE")
            else:
                self.init_errors.append("BH1750 OFFLINE")

    def _scan_i2c(self):
        try:
            return self.i2c.scan()
        except Exception:
            self.init_errors.append("I2C SCAN FAILED")
            return []

    def format_i2c_addresses(self):
        if not self.i2c_addresses:
            return "none"
        return ",".join("0x%02X" % address for address in self.i2c_addresses)

    def read_all(self):
        values = {
            "temperature_c": None,
            "humidity_pct": None,
            "light_lux": None,
            "errors": list(self.init_errors),
        }

        try:
            self.dht_sensor.measure()
            values["temperature_c"] = round(float(self.dht_sensor.temperature()), 1)
            values["humidity_pct"] = round(float(self.dht_sensor.humidity()), 1)
        except Exception as exc:
            values["errors"].append("dht:%s" % exc)

        if self.light_sensor is not None:
            try:
                values["light_lux"] = self.light_sensor.read_lux()
            except Exception as exc:
                values["errors"].append("bh1750:%s" % exc)

        return values
