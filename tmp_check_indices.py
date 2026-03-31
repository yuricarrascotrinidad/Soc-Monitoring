import psycopg2
from app.config import Config

def check_indices():
    conn = psycopg2.connect(
        host=Config.PG_HOST,
        port=Config.PG_PORT,
        database=Config.PG_DATABASE,
        user=Config.PG_USER,
        password=Config.PG_PASSWORD
    )
    cur = conn.cursor()
    
    tables = ['alarmas_activas', 'catalogo_dispositivos', 'battery_telemetry']
    for table in tables:
        print(f"\n--- Indices for {table} ---")
        cur.execute(f"""
            SELECT indexname, indexdef 
            FROM pg_indexes 
            WHERE tablename = '{table}'
        """)
        for row in cur.fetchall():
            print(row)
            
    conn.close()

if __name__ == "__main__":
    check_indices()
