import machine
import time

from app_core import run_device


while True:
    try:
        run_device()
    except Exception as exc:
        print("Unhandled error:", exc)
        time.sleep(5)
        machine.reset()
