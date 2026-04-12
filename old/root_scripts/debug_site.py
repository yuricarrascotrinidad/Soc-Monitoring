
import sys
import os
import logging
from urllib.parse import urlparse
from app import create_app
from app.services.monitoring_service import MonitoringService
from app.utils.constants import CONFIG_REGIONES

logging.basicConfig(level=logging.INFO)

def diagnose_site(sitio_target):
    app = create_app()
    with app.app_context():
        from app.utils.db import get_db_connection
        import psycopg2.extras
        
        print(f"--- Diagnostiando Sitio: {sitio_target} ---")
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        
        # 1. Buscar alarmas activas para el sitio
        cur.execute("SELECT * FROM alarmas_activas WHERE sitio = %s", (sitio_target,))
        alarms = cur.fetchall()
        if not alarms:
            print(f"❌ No se encontraron alarmas activas para el sitio {sitio_target}.")
            return
        
        d = alarms[0]
        site = d['sitio']
        precinct_id = d['precinct_id']
        tipo_sistema = d['tipo']
        region = d['region']
        
        print(f"Info: Region={region}, System={tipo_sistema}, PrecinctID={precinct_id}")
        
        cfg = CONFIG_REGIONES.get(tipo_sistema, {}).get(region)
        if not cfg:
            print(f"❌ No hay configuración para {tipo_sistema}/{region}")
            return
            
        ip = urlparse(cfg["url"]).hostname
        cookies = MonitoringService._enriquecer_cookies(cfg["cookies"])
        
        print(f"Poll IP: {ip}")
        
        # 2. Buscar dispositivos en el precinto
        print("Buscando dispositivos...")
        baterias = MonitoringService.buscar_baterias_en_precinto(ip, cookies, precinct_id)
        print(f"Dispositivos encontrados: {len(baterias)}")
        for b in baterias:
            print(f"  - {b['device_name']} (ID: {b['device_id']}, Type: {b['type']})")
        
        # 3. Obtener telemetría de cada uno
        batch = []
        for bat in baterias:
            did = str(bat["device_id"]).strip().zfill(16)
            print(f"Poll Device: {bat['device_name']} ({did})...")
            vals = MonitoringService.obtener_valores_dispositivo(ip, did, cookies)
            if vals:
                print(f"    Raw Values: {vals}")
                dtype = 5 if bat['type'] == 'generador' else (47 if bat['type'] == 'litio' else 8)
                processed = MonitoringService._procesar_telemetria_dispositivo(did, vals, site, bat["device_name"], dtype)
                print(f"    Processed: {processed}")
                batch.extend(processed)
            else:
                print("    ❌ No se obtuvo respuesta.")
        
        # 4. Intentar guardar
        if batch:
            print(f"Guardando {len(batch)} registros...")
            MonitoringService.actualizar_telemetria_bateria_batch(batch)
            print("✅ Hecho.")
        else:
            print("❌ Nada que guardar.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        diagnose_site(sys.argv[1])
    else:
        print("Uso: python debug_site.py <NOMBRE_SITIO>")
