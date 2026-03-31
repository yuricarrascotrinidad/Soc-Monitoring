import requests, json, time
from app import create_app
from app.utils.constants import CONFIG_REGIONES
from urllib.parse import urlparse

app = create_app()
with app.app_context():
    # T2255_AN_UCO is transport / Ancash
    cfg = CONFIG_REGIONES.get("transport", {}).get("Ancash", {})
    ip = urlparse(cfg["url"]).hostname
    cookies = cfg["cookies"].copy()
    cookies.update({
        "loginUser": "yuri.carrasco", "contextPath": "/peim",
        "language": "es_ES", "proversion": "null"
    })
    
    # First, find the precinct_id for T2255_AN_UCO from alarmas_activas
    from app.utils.db import get_db_connection
    import psycopg2.extras
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT sitio, precinct_id, device_id FROM alarmas_activas WHERE sitio LIKE '%UCO%' AND tipo='transport' LIMIT 5")
    rows = cur.fetchall()
    conn.close()
    print("UCO rows:", rows)
    
    if not rows:
        print("No rows found for UCO - trying a transport AC_FAIL site...")
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute("SELECT sitio, precinct_id, device_id FROM alarmas_activas WHERE tipo='transport' AND categoria='AC_FAIL' LIMIT 3")
        rows = cur.fetchall()
        conn.close()
        print("Transport AC_FAIL rows:", rows)
    
    for row in rows[:2]:
        pid = row['precinct_id']
        sitio = row['sitio']
        print(f"\n=== {sitio} (precinct_id={pid}) ===")
        
        # Search device tree level 1
        url = f"http://{ip}:8090/peim/request/region/getDeviceTree"
        hdrs = {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "Host": f"{ip}:8090", "Referer": f"http://{ip}:8090/peim/main/realtime/realtimemanage.html"}
        params = {"tree_type": 0, "id": pid, "node_type_show": 3, "_": int(time.time()*1000)}
        
        resp = requests.get(url, headers=hdrs, cookies=cookies, params=params, timeout=10)
        data = resp.json()
        
        if data.get("success"):
            items = data.get("info", [])
            print(f"  Level 1 devices ({len(items)}):")
            for item in items:
                print(f"    type={item.get('device_type')} id={item.get('device_id')} name={item.get('device_name')}")
                # If it's an FSU (type 6), check its children
                if item.get("device_type") in ["6", "8"]:
                    params2 = {"tree_type": 0, "id": item["device_id"], "node_type_show": 3, "_": int(time.time()*1000)}
                    r2 = requests.get(url, headers=hdrs, cookies=cookies, params=params2, timeout=10)
                    d2 = r2.json()
                    if d2.get("success"):
                        for sub in d2.get("info", []):
                            print(f"      [FSU child] type={sub.get('device_type')} id={sub.get('device_id')} name={sub.get('device_name')}")
        else:
            print("  FAILED:", data)
