import sqlite3
import os
import requests
import json
from datetime import datetime
from flask import Flask

# Create a mock Flask app context
app = Flask(__name__)
class Config:
    DB_PATH = os.path.join(os.getcwd(), 'monitoring.db')
app.config.from_object(Config)

def verify_battery():
    print("Verifying battery telemetry and API...")
    
    # 1. Insert search alarm (BATERIA BAJA)
    conn = sqlite3.connect(Config.DB_PATH)
    cur = conn.cursor()
    
    # Ensure a device exists with BATERIA BAJA alarm
    cur.execute("""
        INSERT OR REPLACE INTO alarmas 
        (id, tipo, region, hora, duracion, sitio, alarma, alarmameta, categoria, estado, device_id)
        VALUES (9999, 'access', 'TestRegion', ?, 60, 'TEST_BATT_SITE', 'SOC Low', 'BATT_DEV_001', 'BATERIA BAJA', 'on', 'DEV-BATT-001')
    """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),))
    
    # 2. Insert telemetry
    cur.execute("""
        INSERT OR REPLACE INTO battery_telemetry (device_id, soc, carga, descarga, ultimo_update)
        VALUES ('DEV-BATT-001', 45.5, 0.0, 2.5, ?)
    """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),))
    
    conn.commit()
    conn.close()
    
    print("Test data inserted.")
    
    # 3. Verify API
    print("Checking `/api/battery_data`...")
    from app.routes.api import get_battery_data
    from app.utils.db import get_db_connection
    
    with app.app_context():
        # We need to manually call the function since it's a Flask route
        with app.test_request_context():
            from flask import jsonify
            response = get_battery_data()
            data = response.get_json()
            
            test_row = next((item for item in data if item["dispositivo"] == "BATT_DEV_001"), None)
            
            if test_row:
                print("Success: API returned battery telemetry!")
                print(f"Data: {json.dumps(test_row, indent=2)}")
            else:
                print("Failure: Mock data not found in API response.")

if __name__ == "__main__":
    verify_battery()
