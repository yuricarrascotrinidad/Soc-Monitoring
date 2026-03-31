from app.services.monitoring_service import MonitoringService
from app.__init__ import create_app
from app.utils.constants import CONFIG_REGIONES, ALARM_TEMPLATE_AC
import json

app = create_app()
with app.app_context():
    # Pick a region that has AC fail
    dt = "access"
    region = "Ancash"
    cfg = CONFIG_REGIONES[dt][region]
    
    print(f"Checking {dt} - {region}...")
    try:
        alarmas = MonitoringService.obtener_alarmas(cfg["url"], cfg["cookies"], ALARM_TEMPLATE_AC)
        if alarmas is None:
            print("Failed to get alarms (auth issue?)")
        else:
            print(f"API Alarms found: {len(alarmas)}")
            for a in alarmas[:2]:
                print(f"  API Key: {(a['station_name'], a['alarm_name'], a['alarm_time'])}")
                print(f"  Type of alarm_time: {type(a['alarm_time'])}")
            
            from app.utils.db import get_db_connection
            import psycopg2.extras
            conn = get_db_connection()
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("SELECT sitio, alarma, hora FROM alarmas_activas WHERE tipo=%s AND region=%s AND categoria='AC_FAIL'", (dt, region))
            rows = cur.fetchall()
            print(f"DB Alarms found: {len(rows)}")
            for r in rows[:2]:
                print(f"  DB Key: {(r['sitio'], r['alarma'], r['hora'])}")
                print(f"  Type of hora: {type(r['hora'])}")
            conn.close()
    except Exception as e:
        print(f"Error: {e}")
