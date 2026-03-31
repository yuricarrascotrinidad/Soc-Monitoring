from app.utils.db import query_db

def inspect():
    # 1. Total sites and units
    sites = query_db("SELECT count(DISTINCT station_name) as cnt FROM hvac_telemetry")
    units = query_db("SELECT count(*) as cnt FROM hvac_telemetry")
    print(f"DB Summary: {sites[0]['cnt']} sites, {units[0]['cnt']} units total.")
    
    # 2. Check A1006 specifically
    print("\n--- A1006 Details in DB ---")
    res = query_db("SELECT station_name, site_prefix, device_name FROM hvac_telemetry WHERE station_name LIKE '%%A1006%%'")
    for r in res:
        print(f"Site: '{r['station_name']}' | Prefix: '{r['site_prefix']}' | Unit: '{r['device_name']}'")
    
    # 3. Sample of stations per precinct (proving isolation)
    print("\n--- Sample of Stations per Precinct (Isolation Check) ---")
    res = query_db("""
        SELECT precinct_id, count(DISTINCT station_name) as stations 
        FROM hvac_telemetry 
        GROUP BY precinct_id 
        HAVING count(DISTINCT station_name) > 1 
        LIMIT 5
    """)
    for r in res:
        print(f"Precinct {r['precinct_id']} now has data for {r['stations']} distinct stations.")

if __name__ == "__main__":
    inspect()
