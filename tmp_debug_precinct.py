import psycopg2
import json
import requests
from app.config import Config
from app.services.monitoring_service import MonitoringService
from urllib.parse import urlparse

def debug_precinct_batteries():
    precinct_id = "0000100505"
    site_name = "T2230_AN_PAUCAS"
    
    # We need to find the right segment/region to get cookies
    from app.utils.constants import CONFIG_REGIONES
    
    # Assume it's transport - Ancash based on site name 'AN'
    db_type = "transport"
    region = "Ancash"
    cfg = CONFIG_REGIONES[db_type][region]
    url = cfg["url"]
    cookies = cfg["cookies"].copy()
    cookies.update({"loginUser": "yuri.carrasco"})
    parsed_url = urlparse(url)
    ip = parsed_url.hostname

    print(f"Discovering batteries for precinct {precinct_id} via {ip}...")
    baterias = MonitoringService.buscar_baterias_en_precinto(ip, cookies, precinct_id)
    print(f"Discovered {len(baterias)} batteries: {baterias}")

    try:
        conn = psycopg2.connect(
            host=Config.PG_HOST,
            port=Config.PG_PORT,
            database=Config.PG_DATABASE,
            user=Config.PG_USER,
            password=Config.PG_PASSWORD
        )
        cur = conn.cursor()
        
        for bat in baterias:
            device_id = bat['device_id']
            cur.execute("SELECT sitio, nombre, ultimo_update FROM battery_telemetry WHERE device_id = %s", (device_id,))
            row = cur.fetchone()
            if row:
                print(f"Device {device_id} ({bat['device_name']}) is ASSOCIATED WITH: {row[0]} (Last update: {row[2]})")
            else:
                print(f"Device {device_id} ({bat['device_name']}) IS NOT IN battery_telemetry")
                
        # Also check if any battery_telemetry exists for this site generally
        cur.execute("SELECT device_id, nombre, ultimo_update FROM battery_telemetry WHERE sitio = %s", (site_name,))
        rows = cur.fetchall()
        print(f"\nTotal records in DB for {site_name}: {len(rows)}")
        for r in rows:
            print(r)
            
        conn.close()
    except Exception as e:
        print(f"Error checking DB: {e}")

if __name__ == "__main__":
    debug_precinct_batteries()
