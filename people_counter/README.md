# Raspberry Pi Lightweight People Counter

Lightweight people counting prototype optimized for Raspberry Pi 4 (no hardware accelerator required).

Features
- Capture from CSI/USB/IP camera or video file
- Background-subtraction + contour detection (low CPU) with a small centroid tracker
- Simple crossing-line counting (configurable)

Quick start

1. On Raspberry Pi install dependencies (recommended via apt for OpenCV):

```bash
# Install system OpenCV (recommended on Pi):
sudo apt update
sudo apt install -y python3-opencv python3-pip
pip3 install -r requirements.txt
```

2. Run the prototype (camera index `0` or replace with path/RTSP):

```bash
python3 count_people.py --source 0 --display
```

Files
- [count_people.py](count_people.py): main prototype script
- [requirements.txt](requirements.txt): Python packages

Notes and next steps
- Tune `--min-area` and `--width` for optimal throughput/accuracy.
- For better accuracy or higher FPS consider Coral Edge TPU or NCS2.
