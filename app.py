from flask import Flask, jsonify, request
import threading
import time
import random
import csv
import io
import os
from datetime import datetime

app = Flask(__name__)

CSV_FILE = 'sensor_data.csv'
FIELDNAMES = [
    "id", "node_id", "timestamp",
    "pm2_5", "pm10", "NO", "NO2", "NOX", "NH3",
    "CO", "SO2", "O3", "Benzene", "Toluene", "Xylene",
    "AQI", "added_at"
]

def create_base_entry(idx: int):
    now = datetime.utcnow().isoformat() + "Z"
    return {
        "id": idx,
        "node_id": str(idx),
        "timestamp": now,
        "pm2_5": 175.0541244,
        "pm10": 225.6159204,
        "NO": 63.16595663,
        "NO2": 81.20394571,
        "NOX": 22.26520486,
        "NH3": 38.14978342,
        "CO": 18.55,
        "SO2": 54.37004314,
        "O3": 2.033851062,
        "Benzene": 1.29022789,
        "Toluene": 2.545848505,
        "Xylene": 5.436573227,
        "AQI": 0,
        "added_at": now
    }

def write_csv(data: list[dict]):
    with open(CSV_FILE, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(data)

def load_csv() -> list[dict]:
    if not os.path.exists(CSV_FILE):
        # bootstrap with 50 entries
        data = [create_base_entry(i) for i in range(1, 51)]
        write_csv(data)
        return data

    data = []
    with open(CSV_FILE, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # convert types
            sensor = {
                "id": int(row["id"]),
                "node_id": row["node_id"],
                "timestamp": row["timestamp"],
                "pm2_5": float(row["pm2_5"]),
                "pm10": float(row["pm10"]),
                "NO": float(row["NO"]),
                "NO2": float(row["NO2"]),
                "NOX": float(row["NOX"]),
                "NH3": float(row["NH3"]),
                "CO": float(row["CO"]),
                "SO2": float(row["SO2"]),
                "O3": float(row["O3"]),
                "Benzene": float(row["Benzene"]),
                "Toluene": float(row["Toluene"]),
                "Xylene": float(row["Xylene"]),
                "AQI": float(row["AQI"]),
                "added_at": row["added_at"]
            }
            data.append(sensor)
    return data

# Global in‐memory cache (always kept in sync with disk)
current_sensor_data = load_csv()

def update_sensor_data():
    while True:
        for sensor in current_sensor_data:
            for key in ["pm2_5","pm10","NO","NO2","NOX","NH3","CO","SO2","O3","Benzene","Toluene","Xylene"]:
                sensor[key] = max(0, round(sensor[key] + random.uniform(-10, 10), 6))
            new_aqi = sensor["AQI"] + random.gauss(0, 5)
            sensor["AQI"] = round(min(500, max(0, new_aqi)), 6)
            sensor["added_at"] = datetime.utcnow().isoformat() + "Z"
        # write every cycle
        write_csv(current_sensor_data)
        time.sleep(5)

@app.route('/sensordata', methods=['GET'])
def get_sensor_data():
    # Always return the latest in-memory data
    return jsonify({"message": "Success", "sensorData": current_sensor_data})

@app.route('/upload', methods=['POST'])
def upload_sensor_csv():
    if 'file' not in request.files:
        return ('No file part', 400)
    file = request.files['file']
    content = file.read().decode('utf-8')
    reader = csv.DictReader(io.StringIO(content))
    header_map = {
        'Timestamp': 'timestamp',
        'Node ID': 'node_id',
        'PM2.5': 'pm2_5',
        'PM10': 'pm10',
        'NO': 'NO',
        'NO2': 'NO2',
        'NOx': 'NOX',
        'NH3': 'NH3',
        'CO': 'CO',
        'SO2': 'SO2',
        'O3': 'O3',
        'Benzene': 'Benzene',
        'Toluene': 'Toluene',
        'Xylene': 'Xylene',
        'AQI': 'AQI'
    }
    updated = 0
    for row in reader:
        node = row.get('Node ID', '').strip()
        if not node:
            continue
        for sensor in current_sensor_data:
            if sensor['node_id'] == node:
                for csv_key, value in row.items():
                    sensor_key = header_map.get(csv_key)
                    if not sensor_key or sensor_key in ('id','node_id'):
                        continue
                    if sensor_key == 'timestamp':
                        sensor['timestamp'] = value
                    else:
                        try:
                            sensor[sensor_key] = float(value)
                        except ValueError:
                            pass
                sensor['added_at'] = datetime.utcnow().isoformat() + 'Z'
                updated += 1
                break
    # persist upload changes immediately
    write_csv(current_sensor_data)
    return (f'CSV processed. Updated {updated} sensors.', 200)

if __name__ == '__main__':
    # start background updater
    threading.Thread(target=update_sensor_data, daemon=True).start()
    app.run(host='0.0.0.0', port=4000, debug=True)
