import psycopg2
from psycopg2 import extras

PG_HOST = 'localhost'
PG_PORT = '5432'
PG_DATABASE = 'monitoring'
PG_USER = 'postgres'
PG_PASSWORD = 'yofc'

def check_alarms():
    try:
        conn = psycopg2.connect(host=PG_HOST, port=PG_PORT, database=PG_DATABASE, user=PG_USER, password=PG_PASSWORD)
        cur = conn.cursor(cursor_factory=extras.RealDictCursor)
        
        print("Checking active alarms for ZTE...")
        cur.execute("SELECT * FROM alarmas_activas WHERE devicename LIKE '%ZTE%' OR alarma LIKE '%ZTE%'")
        rows = cur.fetchall()
        for row in rows:
            print(row)
            
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_alarms()
