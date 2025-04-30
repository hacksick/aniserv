from flask import Flask, jsonify, request
import threading
import time
import random
import csv
import io
from datetime import datetime

app = Flask(__name__)

# Base single sensor template
def create_base_entry():
    return {
        "id": 0,
        "node_id": "0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
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
        "added_at": datetime.utcnow().isoformat() + "Z"
    }

# Initialize global sensor data store
current_sensor_data = [create_base_entry() for _ in range(50)]
for idx, sensor in enumerate(current_sensor_data, start=1):
    sensor["id"] = idx
    sensor["node_id"] = str(idx)

# Background updater for synthetic data
def update_sensor_data():
    while True:
        for sensor in current_sensor_data:
            for key in ["pm2_5","pm10","NO","NO2","NOX","NH3","CO","SO2","O3","Benzene","Toluene","Xylene"]:
                sensor[key] = max(0, round(sensor[key] + random.uniform(-10, 10), 6))
            # AQI small gaussian changes, clamp 0-500
            new_aqi = sensor["AQI"] + random.gauss(0, 5)
            sensor["AQI"] = round(min(500, max(0, new_aqi)), 6)
            sensor["added_at"] = datetime.utcnow().isoformat() + "Z"
        time.sleep(5)

@app.route('/sensordata', methods=['GET'])
def get_sensor_data():
    return jsonify({"message": "Success", "sensorData": current_sensor_data})

@app.route('/upload', methods=['POST'])
def upload_sensor_csv():
    # Expect CSV file under 'file'
    if 'file' not in request.files:
        return ('No file part', 400)
    file = request.files['file']
    content = file.read().decode('utf-8')
    reader = csv.DictReader(io.StringIO(content))
    # Map CSV headers to sensor keys
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
                # Update fields
                for csv_key, value in row.items():
                    sensor_key = header_map.get(csv_key)
                    if not sensor_key or sensor_key in ('id','node_id'):
                        continue
                    if sensor_key == 'timestamp':
                        sensor['timestamp'] = value
                    else:
                        try:
                            sensor[sensor_key] = float(value)
                        except:
                            pass
                sensor['added_at'] = datetime.utcnow().isoformat() + 'Z'
                updated += 1
                break
    return (f'CSV processed. Updated {updated} sensors.', 200)

if __name__ == '__main__':
    threading.Thread(target=update_sensor_data, daemon=True).start()
    app.run(host='0.0.0.0', port=5000, debug=True)
