import logging
import requests
import time
import os
os.environ['PYTHONPATH'] = '.'
from app.services.battery_service import BatteryService
from app.utils.constants import load_dynamic_tokens, CONFIG_REGIONES

logging.basicConfig(level=logging.INFO)

def test_discovery():
    load_dynamic_tokens()
    
    target_sites = ['A3470_LL_PAYAMARCA', 'A3444_LL_CRUZ COLORADA', 'A2325_AN_PUMPA']
    
    for segment, regs in CONFIG_REGIONES.items():
        for region, cfg in regs.items():
            print(f"Searching in {segment} {region}...")
            sitios = BatteryService.obtener_sitios(segment, region, cfg)
            
            for s in sitios:
                if s['station_name'] in target_sites:
                    print(f"Found target site: {s['station_name']}")
                    dispositivos = BatteryService.obtener_dispositivos(s)
                    for d in dispositivos:
                        if d['tipo_dispositivo'] == 'ZTE':
                            print(f"Found ZTE device: {d['nombre']} (ID: {d['device_id']})")
                            res = BatteryService.obtener_valores(d)
                            if res:
                                print(f"Values: {res['valores']}")
                            else:
                                print(f"Failed to get values.")
                        else:
                            print(f"Other device: {d['nombre']} (Type: {d['tipo_dispositivo']})")

if __name__ == "__main__":
    test_discovery()
