# Smart Ration Store Automation System

An IoT-based automation system for public ration distribution stores, built on a Raspberry Pi. The system combines weight sensing, computer vision, and cloud sync to monitor stock levels, detect potential fraud, and track customer queues in real time.

> ESS Lab Project — Group 1

## Overview

Public ration distribution stores often rely on manual record-keeping, which makes them prone to errors, pilferage, and long, unmonitored queues. This project automates key aspects of store operations using low-cost hardware and a lightweight software stack, giving store operators and administrators a real-time dashboard of stock and activity.

## Features

- **Automated Weight Monitoring** — Dual load cell setup tracks stock levels in real time
- **Queue / People Counting** — Computer vision-based detection counts people in the store queue
- **Fraud Detection** — Flags irregular weight/dispensing patterns
- **Stock Alerts** — Notifies when stock levels fall below a threshold
- **Live Web Dashboard** — Real-time visualization of store status
- **Cloud Sync** — Firebase Realtime Database keeps data available beyond the local device

## System Architecture

- **Hardware**
  - 2x HX711 load cell amplifiers
    - Load Cell 1 — DOUT → GP5, SCK → GP6
    - Load Cell 2 — DOUT → GP20, SCK → GP21
  - USB camera (`/dev/video0`)
  - Raspberry Pi (5V sensor power supply)

- **Computer Vision**
  - MobileNet SSD (Caffe model) for people/queue detection
  - Runs as a background daemon thread inside the Flask app, with thread-safe shared state

- **Backend**
  - Flask web server (`app.py`) serving both the API and the live dashboard

- **Cloud**
  - Firebase Realtime Database for remote data sync

- **Frontend**
  - Real-time dashboard with fraud detection and stock alert logic

## Tech Stack

| Component        | Technology                     |
|-------------------|--------------------------------|
| Language          | Python                          |
| Web Framework     | Flask                            |
| Computer Vision   | OpenCV (`cv2`), MobileNet SSD (Caffe) |
| Sensors           | HX711, `RPi.GPIO`                |
| Cloud Database    | Firebase Realtime Database       |
| Reporting         | `python-docx`                    |

## Getting Started

### Prerequisites

- Raspberry Pi (with GPIO access)
- Python 3.x
- USB camera connected at `/dev/video0`
- 2x HX711 load cell modules wired as described above

### Installation

```bash
git clone https://github.com/<your-username>/smart-ration-store-automation.git
cd smart-ration-store-automation
pip install -r requirements.txt
```

### Running the App

```bash
python app.py
```

The dashboard will be available at `http://<raspberry-pi-ip>:5000`.

> **Note:** If port 5000 is already in use, free it with:
> ```bash
> sudo fuser -k 5000/tcp
> ```

## Project Notes

- Designed for headless Raspberry Pi deployment — no GUI/display calls are used
- The people-counting logic runs inside `app.py` as a background thread rather than as a separate process, keeping the system simpler to run and maintain

## Contributors

- [Aryan Yadav](https://github.com/Aryan-y-77)
- [Pranjal Bawa](https://github.com/pranjalbawa)
- [Adwaita Patane](https://github.com/adwaita-patane-username)

## License

This project was developed as part of an academic lab submission. Feel free to reach out to the contributors for reuse or collaboration inquiries.
