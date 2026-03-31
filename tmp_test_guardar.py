from app.services.monitoring_service import MonitoringService
from app.__init__ import create_app
import logging

logging.basicConfig(level=logging.DEBUG)

app = create_app()
with app.app_context():
    mock_alarm = {
        "station_name": "TEST_SITE",
        "alarm_name": "TEST_ALARM",
        "alarm_time": "2026-03-22 21:55:00",
        "alarm_span_time": "1m",
        "device_name": "TEST_DEV",
        "precinct_id": "123",
        "mete_name": "voltaje",
        "device_id": "00001",
        "valor": 220.0
    }
    
    print("Testing guardar_alarmas...")
    try:
        MonitoringService.guardar_alarmas("access", [mock_alarm], "Ancash", is_ac=True)
        print("Success (supposedly). Checking DB...")
        
        from app.utils.db import get_db_connection
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM alarmas_activas WHERE sitio='TEST_SITE'")
        row = cur.fetchone()
        if row:
            print(f"Found row: {row}")
        else:
            print("Row NOT found in DB!")
        conn.close()
    except Exception as e:
        print(f"Caught Exception: {e}")
