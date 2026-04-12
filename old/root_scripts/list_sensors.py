
import sys
from urllib.parse import urlparse
from app import create_app
from app.services.monitoring_service import MonitoringService
from app.utils.constants import CONFIG_REGIONES

def list_all_sensors(sitio_target):
    app = create_app()
    with app.app_context():
        from app.utils.db import get_db_connection
        import psycopg2.extras
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT * FROM alarmas_activas WHERE sitio = %s", (sitio_target,))
        d = cur.fetchone()
        if not d: return
        
        cfg = CONFIG_REGIONES.get(d['tipo'], {}).get(d['region'])
        ip = urlparse(cfg["url"]).hostname
        cookies = MonitoringService._enriquecer_cookies(cfg["cookies"])
        
        baterias = MonitoringService.buscar_baterias_en_precinto(ip, cookies, d['precinct_id'])
        for bat in baterias:
            did = str(bat["device_id"]).strip().zfill(16)
            print(f"\n--- {bat['device_name']} ({did}) ---")
            url = f"http://{ip}:8090/peim/request/realtime/getDeviceRealTimeData"
            payload = f"device_id={did}&is_manual=0"
            hdrs = {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8", "Host": f"{ip}:8090"}
            session = MonitoringService._get_session()
            with session.post(url, headers=hdrs, cookies=cookies, data=payload, timeout=25) as resp:
                data = resp.json()
                for item in data:
                    print(f"ID: {item.get('mete_id')} | Name: {item.get('mete_name')} | Value: {item.get('mete_value')}")

if __name__ == "__main__":
    list_all_sensors(sys.argv[1])
