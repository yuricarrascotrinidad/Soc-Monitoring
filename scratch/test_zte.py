import logging
import requests
import time
from app.services.battery_service import BatteryService
from app.utils.constants import load_dynamic_tokens, CONFIG_REGIONES

logging.basicConfig(level=logging.INFO)

def test_discovery():
    load_dynamic_tokens()
    # Let's try one region, e.g., 'Ancash' in 'access'
    region = 'Ancash'
    segment = 'access'
    if segment in CONFIG_REGIONES and region in CONFIG_REGIONES[segment]:
        cfg = CONFIG_REGIONES[segment][region]
        print(f"Testing discovery for {segment} {region}...")
        sitios = BatteryService.obtener_sitios(segment, region, cfg)
        print(f"Found {len(sitios)} sites.")
        
        zte_count = 0
        for sitio in sitios[:10]: # Test first 10 sites
            dispositivos = BatteryService.obtener_dispositivos(sitio)
            for d in dispositivos:
                if d['tipo_dispositivo'] == 'ZTE':
                    print(f"Found ZTE device: {d['nombre']} in {sitio['station_name']}")
                    zte_count += 1
                    # Test getting values
                    res = BatteryService.obtener_valores(d)
                    if res:
                        print(f"Values for {d['nombre']}: {res['valores']}")
                    else:
                        print(f"Failed to get values for {d['nombre']}")
        
        print(f"Total ZTE devices found in 10 sites: {zte_count}")
    else:
        print(f"Region {region} not found in config.")

if __name__ == "__main__":
    test_discovery()
