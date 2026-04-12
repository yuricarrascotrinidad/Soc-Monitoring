
import psycopg2
from app.config import Config

try:
    conn = psycopg2.connect(
        host=Config.PG_HOST,
        port=Config.PG_PORT,
        database=Config.PG_DATABASE,
        user=Config.PG_USER,
        password=Config.PG_PASSWORD
    )
    cur = conn.cursor()
    cur.execute("SELECT nombre, voltaje, carga, ultimo_update FROM battery_telemetry WHERE sitio = 'T1045_AR_TARUCANI' AND nombre LIKE '%Grupo%'")
    rows = cur.fetchall()
    print("--- RESULTADOS DB (Grupo Electrógeno) ---")
    for r in rows:
        print(f"Nombre: {r[0]} | Voltaje: {r[1]} | Carga (Corriente): {r[2]} | Update: {r[3]}")
    conn.close()
except Exception as e:
    print(f"Error: {e}")
