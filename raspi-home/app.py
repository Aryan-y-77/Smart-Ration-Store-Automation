from flask import Flask, jsonify, render_template
from collections import deque
import json
import os
import time
import threading
import RPi.GPIO as GPIO
from hx711 import HX711

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
QUEUE_LOG = os.path.join(BASE_DIR, "queue_log.csv")
ALERT_LOG = os.path.join(BASE_DIR, "alert_log.csv")

# ---------------- GLOBAL DATA ----------------
queue_data = []
current_count = 0
current_weight_1 = 0
current_weight_2 = 0
alert_history = deque(maxlen=30)
sensor_fault_1 = False
sensor_fault_2 = False
last_weight_1 = 0
last_weight_2 = 0
last_queue_count = 0


def load_config():
    default = {
        "CALIBRATION_FACTOR_1": 210000,
        "CALIBRATION_FACTOR_2": 210000,
        "WEIGHT_PER_PERSON_KG": 0.5,
        "MIN_WEIGHT_DROP_KG": 0.15,
        "MAX_REASONABLE_WEIGHT_KG": 12.0,
        "MAX_QUEUE_COUNT": 100,
        "LOW_STOCK_KG": 1.0,
        "SENSOR_FAULT_THRESHOLD_KG": 8.0,
        "ALERT_HISTORY_LIMIT": 30,
        "SMOOTHING_WINDOW": 10,
        "SUSTAINED_DROP_READINGS": 3
    }
    if not os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(default, f, indent=2)
        return default
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
        return {**default, **config}
    except Exception:
        return default


def append_alert(level, message, data=None):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    entry = {"time": ts, "level": level, "message": message, "data": data or {}}
    if alert_history and alert_history[0]["message"] == message:
        return
    alert_history.appendleft(entry)
    try:
        with open(ALERT_LOG, "a", encoding="utf-8") as f:
            f.write(f'{ts},{level},"{message}",{json.dumps(data or {})}\n')
    except Exception:
        pass


def append_queue_log(timestamp, count):
    try:
        with open(QUEUE_LOG, "a", encoding="utf-8") as f:
            f.write(f"{timestamp},{count}\n")
    except Exception:
        pass

config = load_config()
alert_history = deque(maxlen=config.get("ALERT_HISTORY_LIMIT", 30))
MIN_WEIGHT_DROP_KG = config["MIN_WEIGHT_DROP_KG"]
WEIGHT_PER_PERSON_KG = config["WEIGHT_PER_PERSON_KG"]
MAX_REASONABLE_WEIGHT_KG = config["MAX_REASONABLE_WEIGHT_KG"]
MAX_QUEUE_COUNT = config["MAX_QUEUE_COUNT"]
LOW_STOCK_KG = config["LOW_STOCK_KG"]
SENSOR_FAULT_THRESHOLD_KG = config["SENSOR_FAULT_THRESHOLD_KG"]
SMOOTHING_WINDOW = config.get("SMOOTHING_WINDOW", 10)
SUSTAINED_DROP_READINGS = config.get("SUSTAINED_DROP_READINGS", 3)

# Weight history for smoothing and sustained drop detection
weight_history_1 = deque(maxlen=SMOOTHING_WINDOW)
weight_history_2 = deque(maxlen=SMOOTHING_WINDOW)
sustained_drop_counter_1 = 0
sustained_drop_counter_2 = 0

# ---------------- HX711 SETUP ----------------
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Load Cell 1 — Rice / Wheat bin
# VCC=Pin4, GND=Pin6, DT=GPIO5 (Pin29), SCK=GPIO6 (Pin31)
hx1 = HX711(dout_pin=5, pd_sck_pin=6)
CALIBRATION_FACTOR_1 = config.get("CALIBRATION_FACTOR_1", 210000)  # adjust after calibrating cell 1
OFFSET_1 = 0

# Load Cell 2 — Sugar / Flour bin
# VCC=Pin2, GND=Pin9, DT=GPIO17 (Pin11), SCK=GPIO27 (Pin13)
hx2 = HX711(dout_pin=17, pd_sck_pin=27)
CALIBRATION_FACTOR_2 = config.get("CALIBRATION_FACTOR_2", 210000)  # adjust after calibrating cell 2
OFFSET_2 = 0

# ---------------- LOAD CELL FUNCTIONS ----------------
def read_average(hx, samples=5):
    readings = []
    for _ in range(samples):
        data = hx.get_raw_data()
        if data:
            avg = sum(data) / len(data)
            readings.append(avg)
        time.sleep(0.05)
    return sum(readings) / len(readings) if readings else None


def tare_cell(hx, label="Cell"):
    global OFFSET_1, OFFSET_2
    print(f"Taring {label}... Remove all weight")
    time.sleep(2)
    offset = read_average(hx)
    if hx is hx1:
        OFFSET_1 = offset
        print(f"{label} tare complete. Offset = {OFFSET_1}")
    else:
        OFFSET_2 = offset
        print(f"{label} tare complete. Offset = {OFFSET_2}")

def get_weight(hx, offset, calibration_factor):
    raw = read_average(hx)
    if raw is None:
        return None
    value = abs(raw - offset)
    weight = value / calibration_factor
    if weight < 0.02:
        weight = 0
    return round(weight, 3)


def safe_weight(hx, offset, calibration_factor, label, last_value):
    global sensor_fault_1, sensor_fault_2
    weight = get_weight(hx, offset, calibration_factor)
    if weight is None:
        append_alert("sensor", f"{label} read failed", {"label": label})
        if label == "Load Cell 1":
            sensor_fault_1 = True
        else:
            sensor_fault_2 = True
        return last_value
    if weight < 0 or weight > MAX_REASONABLE_WEIGHT_KG:
        append_alert("sensor", f"{label} abnormal reading {weight:.2f} kg", {"label": label, "weight": weight})
        if label == "Load Cell 1":
            sensor_fault_1 = True
        else:
            sensor_fault_2 = True
        return last_value
    if label == "Load Cell 1":
        sensor_fault_1 = False
    else:
        sensor_fault_2 = False
    return weight


def get_smoothed_weight(history):
    """Calculate smoothed weight from history using moving average."""
    if not history:
        return 0
    return round(sum(history) / len(history), 3)

# ---------------- ANOMALY DETECTION ----------------
def detect_anomalies(current_count):
    global last_weight_1, last_weight_2, last_queue_count, sustained_drop_counter_1, sustained_drop_counter_2

    # Use smoothed weights from history for more stable detection
    smoothed_weight_1 = get_smoothed_weight(weight_history_1)
    smoothed_weight_2 = get_smoothed_weight(weight_history_2)
    total_weight = smoothed_weight_1 + smoothed_weight_2
    
    stock_capacity = int(total_weight / WEIGHT_PER_PERSON_KG)
    expected_weight = current_count * WEIGHT_PER_PERSON_KG
    queue_over_stock = total_weight + 0.1 < expected_weight
    sensor_fault = sensor_fault_1 or sensor_fault_2
    corruption = False
    drop_1 = 0
    drop_2 = 0

    # Sustained drop detection - only flag if drop persists across multiple readings
    if not sensor_fault and current_count >= last_queue_count and len(weight_history_1) >= 2:
        drop_1 = (last_weight_1 or 0) - smoothed_weight_1
        drop_2 = (last_weight_2 or 0) - smoothed_weight_2
        
        # Check if drops are sustained
        if drop_1 > MIN_WEIGHT_DROP_KG:
            sustained_drop_counter_1 += 1
        else:
            sustained_drop_counter_1 = 0
            
        if drop_2 > MIN_WEIGHT_DROP_KG:
            sustained_drop_counter_2 += 1
        else:
            sustained_drop_counter_2 = 0
        
        # Flag corruption only if drop persists for N consecutive readings
        if sustained_drop_counter_1 >= SUSTAINED_DROP_READINGS or sustained_drop_counter_2 >= SUSTAINED_DROP_READINGS:
            corruption = True
            sustained_drop_counter_1 = 0
            sustained_drop_counter_2 = 0

    if sensor_fault:
        append_alert("sensor", "Sensor fault detected", {"weight1": current_weight_1, "weight2": current_weight_2})
    elif corruption:
        append_alert("corruption", "Suspicious stock drop while queue stable", {"drop_1": round(drop_1, 3), "drop_2": round(drop_2, 3), "queue": current_count})

    if queue_over_stock:
        append_alert("stock", "Queue exceeds available stock", {"capacity": stock_capacity, "queue": current_count, "stock_kg": round(total_weight, 3)})

    last_weight_1 = smoothed_weight_1
    last_weight_2 = smoothed_weight_2
    last_queue_count = current_count

    return {
        "corruption": corruption,
        "queue_over_stock": queue_over_stock,
        "sensor_fault": sensor_fault,
        "stock_capacity": stock_capacity,
        "stock_available": round(total_weight, 3),
        "expected_weight": round(expected_weight, 3)
    }

# ---------------- BACKGROUND THREAD ----------------
def update_weight_continuously():
    global current_weight_1, current_weight_2, weight_history_1, weight_history_2
    while True:
        current_weight_1 = safe_weight(hx1, OFFSET_1, CALIBRATION_FACTOR_1, "Load Cell 1", current_weight_1)
        current_weight_2 = safe_weight(hx2, OFFSET_2, CALIBRATION_FACTOR_2, "Load Cell 2", current_weight_2)
        
        # Add to history for smoothing and sustained drop detection
        weight_history_1.append(current_weight_1)
        weight_history_2.append(current_weight_2)
        
        time.sleep(0.5)

# ---------------- ROUTES ----------------
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/update/<int:count>")
def update(count):
    global current_count
    if count < 0 or count > MAX_QUEUE_COUNT:
        return jsonify({"error": "Invalid queue count"}), 400

    current_count = count
    timestamp = time.strftime("%H:%M:%S")
    queue_data.append({"time": timestamp, "count": count})
    append_queue_log(timestamp, count)
    return jsonify({"status": "ok", "current": current_count})

@app.route("/data")
def data():
    anomalies = detect_anomalies(current_count)
    return jsonify({
        "current":         current_count,
        "weight":          current_weight_1,
        "weight_2":        current_weight_2,
        "total_weight":    round((current_weight_1 or 0) + (current_weight_2 or 0), 3),
        "history":         queue_data[-20:],
        "corruption":      anomalies["corruption"],
        "queue_over_stock": anomalies["queue_over_stock"],
        "sensor_fault":    anomalies["sensor_fault"],
        "stock_capacity":  anomalies["stock_capacity"],
        "stock_available": anomalies["stock_available"],
        "expected_weight": anomalies["expected_weight"],
        "alert_history":   list(alert_history)
    })

# Individual endpoints for debugging
@app.route("/weight/1")
def weight_cell_1():
    return jsonify({"cell": 1, "weight": current_weight_1})

@app.route("/weight/2")
def weight_cell_2():
    return jsonify({"cell": 2, "weight": current_weight_2})

# ---------------- MAIN ----------------
if __name__ == "__main__":
    print("Initializing Load Cells...")
    tare_cell(hx1, label="Load Cell 1")
    tare_cell(hx2, label="Load Cell 2")
    thread = threading.Thread(target=update_weight_continuously)
    thread.daemon = True
    thread.start()
    print("Server started...")
    app.run(host="0.0.0.0", port=5000)
