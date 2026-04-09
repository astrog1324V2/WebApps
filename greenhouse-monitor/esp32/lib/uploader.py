try:
    import ujson as json
except ImportError:
    import json

from http_client import post_json


class Uploader:
    def __init__(self, server_url, timeout_s=10):
        self.server_url = server_url
        self.timeout_s = timeout_s

    def send(self, payload):
        status_code, latency_ms, response_text = post_json(
            self.server_url, payload, timeout_s=self.timeout_s
        )
        success = 200 <= status_code < 300
        return success, status_code, latency_ms, response_text
