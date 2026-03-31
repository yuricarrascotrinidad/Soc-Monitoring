from app.utils.db import query_db

def verify_collisions():
    # 1. Check for precinct_id collisions
    res = query_db("""
        SELECT precinct_id, count(DISTINCT station_name) as stations 
        FROM hvac_telemetry 
        GROUP BY precinct_id 
        HAVING count(DISTINCT station_name) > 1 
        ORDER BY stations DESC
        LIMIT 10
    """)
    print("Precinct collisions found in DB:")
    for r in res:
        stations = query_db("SELECT DISTINCT station_name FROM hvac_telemetry WHERE precinct_id = %s", (r['precinct_id'],))
        station_list = [s['station_name'] for s in stations]
        print(f"  Precinct {r['precinct_id']}: {len(station_list)} stations -> {station_list}")

if __name__ == "__main__":
    verify_collisions()
