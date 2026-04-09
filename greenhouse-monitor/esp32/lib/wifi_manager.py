import network
import time


class WiFiManager:
    def __init__(self, ssid, password, timeout_s=15):
        self.ssid = ssid
        self.password = password
        self.timeout_s = timeout_s
        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(True)

    def connect(self):
        if self.wlan.isconnected():
            return True

        if not self.ssid or self.ssid == "YOUR_WIFI_SSID":
            return False
        if self.password == "YOUR_WIFI_PASSWORD":
            return False

        self.wlan.active(True)
        self.wlan.connect(self.ssid, self.password)
        deadline = time.ticks_add(time.ticks_ms(), int(self.timeout_s * 1000))
        while not self.wlan.isconnected():
            if time.ticks_diff(deadline, time.ticks_ms()) <= 0:
                return False
            time.sleep_ms(200)
        return True

    def ensure_connected(self):
        return self.wlan.isconnected() or self.connect()

    def rssi(self):
        try:
            return self.wlan.status("rssi")
        except Exception:
            return None

    def ip_address(self):
        if not self.wlan.isconnected():
            return None
        return self.wlan.ifconfig()[0]
