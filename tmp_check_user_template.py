from app.services.monitoring_service import MonitoringService
from app.__init__ import create_app
from app.utils.constants import CONFIG_REGIONES, ALARM_TEMPLATE_AC
import json

app = create_app()
with app.app_context():
    template = ALARM_TEMPLATE_AC.copy()
    template["chk_level"] = "4" 
    template["only_major"] = "1"
    
    total_sites = set()
    for dt in ["access", "transport"]:
        for reg, cfg in CONFIG_REGIONES[dt].items():
            print(f"Checking {dt} - {reg} (chk_level=4, only_major=1)...")
            alarmas = MonitoringService.obtener_alarmas(cfg["url"], cfg["cookies"], template)
            if alarmas:
                for a in alarmas:
                    total_sites.add(a["station_name"])
    
    print(f"SITES (User Template): {len(total_sites)}")
    print(f"Sites found: {list(total_sites)[:10]}")
