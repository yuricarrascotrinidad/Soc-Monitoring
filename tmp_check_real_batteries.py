from app.utils.db import get_db_connection
conn = get_db_connection()
cur = conn.cursor()

# Get sites with AC_FAIL
cur.execute("SELECT DISTINCT sitio FROM alarmas_activas WHERE estado = 'on' AND categoria = 'AC_FAIL'")
ac_fail_sitios = [r[0] for r in cur.fetchall()]

# Check how many have any "real" battery telemetry
with_real_battery = 0
for sitio in ac_fail_sitios:
    cur.execute("SELECT nombre FROM battery_telemetry WHERE sitio = %s", (sitio,))
    telemetry_names = [row[0] or "" for row in cur.fetchall()]
    
    is_any_battery = any(
        any(word in name.lower() for word in ['bater', 'lithium', 'litio', 'bat'])
        for name in telemetry_names
    )
    
    if is_any_battery:
        with_real_battery += 1

print(f"Total AC_FAIL Sites: {len(ac_fail_sitios)}")
print(f"AC_FAIL Sites with 'Real' Battery Telemetry: {with_real_battery}")

conn.close()
