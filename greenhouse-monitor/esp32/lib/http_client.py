import socket
import time

try:
    import ujson as json
except ImportError:
    import json


def _parse_url(url):
    if not url.startswith("http://"):
        raise ValueError("Only plain http:// URLs are supported.")

    address = url[7:]
    host_port, _, path = address.partition("/")
    if ":" in host_port:
        host, port_text = host_port.split(":", 1)
        port = int(port_text)
    else:
        host = host_port
        port = 80
    return host, port, "/" + path


def post_json(url, payload, timeout_s=10):
    host, port, path = _parse_url(url)
    body = json.dumps(payload)
    request = (
        "POST {path} HTTP/1.1\r\n"
        "Host: {host}\r\n"
        "Content-Type: application/json\r\n"
        "Content-Length: {length}\r\n"
        "Connection: close\r\n\r\n"
        "{body}"
    ).format(path=path, host=host, length=len(body), body=body)

    start_ms = time.ticks_ms()
    sock = None
    try:
        address_info = socket.getaddrinfo(host, port)[0][-1]
        sock = socket.socket()
        sock.settimeout(timeout_s)
        sock.connect(address_info)
        sock.send(request.encode("utf-8"))
        response_chunk = sock.recv(128).decode("utf-8")
        latency_ms = time.ticks_diff(time.ticks_ms(), start_ms)
        status_line = response_chunk.split("\r\n", 1)[0]
        parts = status_line.split(" ")
        status_code = int(parts[1]) if len(parts) > 1 else 0
        return status_code, latency_ms, response_chunk
    finally:
        if sock is not None:
            sock.close()
