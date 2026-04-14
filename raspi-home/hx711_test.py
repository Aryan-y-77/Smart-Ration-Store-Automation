import time
import RPi.GPIO as GPIO
from hx711 import HX711

# ---------------- GPIO SETUP ----------------
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

hx = HX711(dout_pin=5, pd_sck_pin=6)

# ---------------- CALIBRATION VALUES ----------------
# 👉 Replace these after calibration
CALIBRATION_FACTOR = 220000   # example value (adjust!)
OFFSET = 0                    # will be set during tare

# ---------------- FUNCTIONS ----------------

def read_average(samples=10):
    readings = []
    for _ in range(samples):
        data = hx.get_raw_data()
        if data:
            avg = sum(data) / len(data)
            readings.append(avg)
        time.sleep(0.05)
    return sum(readings) / len(readings) if readings else 0


def tare():
    global OFFSET
    print("Taring... Remove all weight")
    time.sleep(2)
    OFFSET = read_average()
    print(f"Tare complete. Offset = {OFFSET}")


def get_weight():
    readings = []

    # Take multiple readings for stability
    for _ in range(5):
        raw = read_average()
        value = abs(raw - OFFSET)
        weight = value / CALIBRATION_FACTOR
        readings.append(weight)
        time.sleep(0.1)

    # Take median instead of average (better for noise)
    readings.sort()
    weight = readings[len(readings)//2]

    # Remove small noise
    if weight < 0.05:
        weight = 0

    return round(weight, 1)

# ---------------- MAIN ----------------

try:
    print("Initializing Load Cell...")
    time.sleep(2)

    tare()  # Set zero

    print("System Ready!\n")

    while True:
        weight = get_weight()

        print(f"Weight: {weight:.3f} kg")

        time.sleep(0.5)

except KeyboardInterrupt:
    print("\nStopping system...")
    GPIO.cleanup()
