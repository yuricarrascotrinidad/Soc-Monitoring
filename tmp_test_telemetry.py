from app.services.monitoring_service import MonitoringService
from app.__init__ import create_app
from app.utils.constants import CONFIG_REGIONES
from app.utils.db import get_db_connection
import psycopg2.extras

app = create_app()
with app.app_context():
    # Get a known AC fail site with a battery
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT DISTINCT sitio, region, device_id, devicename, tipo 
        FROM alarmas_activas 
        WHERE categoria='AC_FAIL' AND estado='on'
        LIMIT 3
    """)
    rows = cur.fetchall()
    conn.close()
    
    for row in rows:
        cfg = CONFIG_REGIONES.get(row['tipo'], {}).get(row['region'])
        if not cfg: continue
        from urllib.parse import urlparse
        ip = urlparse(cfg["url"]).hostname
        did = str(row['device_id']).strip().zfill(16)
        print(f"Testing: {row['sitio']} ({row['tipo']}/{row['region']}) device={did}")
        vals = MonitoringService.obtener_valores_dispositivo(ip, did, cfg["cookies"])
        non_null = {k:v for k,v in vals.items() if v is not None}
        print(f"  Values: {non_null if non_null else 'NO DATA'}")
