
import os
import sys
sys.path.append(os.getcwd())
from app.utils.db import query_db

def check_site(sitio):
    print(f"\n=== SITE: {sitio} ===")
    rows = query_db("SELECT nombre, device_id, soc, carga, descarga, voltaje, svoltage, current1, current2 FROM battery_telemetry WHERE sitio = %s", (sitio,))
    if not rows:
        print("No telemetry found in DB.")
        return
    for r in rows:
        print(f"Device: {r['nombre']} (ID: {r['device_id']})")
        print(f"  SOC: {r['soc']}, Carga: {r['carga']}, Descarga: {r['descarga']}")
        print(f"  Volt: {r['voltaje']}, SVolt: {r['svoltage']}, Cur1: {r['current1']}, Cur2: {r['current2']}")

if __name__ == "__main__":
    sites = [
        "A3422_LL_BUENA VISTA",
        "A4208_SM_SAN JOSE DE YANAYACU",
        "A3028_LL_LA GRAMA",
        "A2485_AN_UMBE"
    ]
    for s in sites:
        check_site(s)
