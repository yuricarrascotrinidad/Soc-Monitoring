from app import create_app
from app.services.monitoring_service import MonitoringService
from app.utils.constants import CONFIG_REGIONES, ALARM_TEMPLATE_AC, HEADERS
import requests
import json
import logging

def populate_names():
    app = create_app()
    with app.app_context():
        print("Populating battery names...")
        db_type = "access"
        region = "Ancash"
        cfg = CONFIG_REGIONES[db_type][region]
        url = cfg["url"]
        cookies = cfg["cookies"].copy()
        cookies.update({"loginUser": "yuri.carrasco"})
        
        data = {"queryObjStr": json.dumps(ALARM_TEMPLATE_AC)}
        r = requests.post(url, headers=HEADERS, cookies=cookies, data=data, timeout=10)
        resp = r.json()
        
        if resp.get("success"):
            alarmas = resp["info"]["data"]
            # Filter for specific sites to be fast
            target_sites = ["A2335_AN_ACHCAY", "A4012_SM_VALLE DE LA CONQUISTA", "A1042_AR_YUMINA"]
            filtered_alarms = [a for a in alarmas if a["station_name"] in target_sites]
            
            MonitoringService.guardar_alarmas(db_type, filtered_alarms, region, is_ac=True)
            print(f"Processed {len(filtered_alarms)} alarms. Names should be populated.")

if __name__ == "__main__":
    populate_names()
