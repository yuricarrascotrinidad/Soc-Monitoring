import psycopg2
from psycopg2 import extras

PG_HOST = 'localhost'
PG_PORT = '5432'
PG_DATABASE = 'monitoring'
PG_USER = 'postgres'
PG_PASSWORD = 'yofc'

def check_site(site):
    try:
        conn = psycopg2.connect(host=PG_HOST, port=PG_PORT, database=PG_DATABASE, user=PG_USER, password=PG_PASSWORD)
        cur = conn.cursor(cursor_factory=extras.RealDictCursor)
        
        print(f"Checking {site} in battery_telemetry...")
        cur.execute("SELECT * FROM battery_telemetry WHERE sitio = %s", (site,))
        rows = cur.fetchall()
        for row in rows:
            print(row)
        
        print(f"\nChecking {site} in battery_telemetry_global...")
        cur.execute("SELECT * FROM battery_telemetry_global WHERE sitio = %s", (site,))
        rows = cur.fetchall()
        for row in rows:
            print(row)
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_site('A2325_AN_PUMPA')
