import sqlite3
import os
from app.services.monitoring_service import MonitoringService
from flask import Flask

# Create a mock Flask app context
app = Flask(__name__)
# Mock configuration
class Config:
    DB_PATH = os.path.join(os.getcwd(), 'monitoring.db')

app.config.from_object(Config)

def test_save_alarm():
    print("Running integration test for device_id...")
    
    # Mock alarm data
    mock_alarms = [
        {
            "alarm_time": "2026-02-17 10:00:00",
            "station_name": "TEST_SITE",
            "alarm_name": "SOC",
            "device_name": "TEST_DEVICE",
            "alarm_span_time": "00:05:00",
            "device_id": "DEV-12345"
        }
    ]
    
    with app.app_context():
        MonitoringService.guardar_alarmas("access", mock_alarms, "TestRegion")
    
    # Verify in DB
    conn = sqlite3.connect(Config.DB_PATH)
    cur = conn.execute("SELECT device_id FROM alarmas WHERE sitio='TEST_SITE' AND hora='2026-02-17 10:00:00'")
    row = cur.fetchone()
    conn.close()
    
    if row and row[0] == "DEV-12345":
        print("Success: device_id saved correctly!")
    else:
        print(f"Failure: device_id not found or incorrect. Found: {row}")

if __name__ == "__main__":
    test_save_alarm()
