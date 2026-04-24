import psycopg2
from psycopg2 import extras
import datetime

PG_HOST = 'localhost'
PG_PORT = '5432'
PG_DATABASE = 'monitoring'
PG_USER = 'postgres'
PG_PASSWORD = 'yofc'

def test_insert():
    try:
        conn = psycopg2.connect(host=PG_HOST, port=PG_PORT, database=PG_DATABASE, user=PG_USER, password=PG_PASSWORD)
        cur = conn.cursor()
        
        now = datetime.datetime.now()
        batch = [
            ('TEST_DEVICE_ID', 'Bateria ZTE 1', 'TEST_SITE', 'Ancash', 'access', 'ZTE',
             85.0, 0, 10.0, 48.5, None, 10.0, 0, 0, 100.0, None, None, now)
        ]
        
        print("Testing INSERT into battery_telemetry...")
        extras.execute_values(cur, """
            INSERT INTO battery_telemetry
            (device_id, nombre, sitio, region, tipo_sistema, tipo_dispositivo, 
            soc, carga, descarga, voltaje, svoltage, current1, current2, conexion, capacidad, 
            voltaje_gen, corriente_gen, ultimo_update)
            VALUES %s
            ON CONFLICT (device_id, nombre, sitio) DO UPDATE SET
                soc = EXCLUDED.soc, carga = EXCLUDED.carga, descarga = EXCLUDED.descarga,
                voltaje = EXCLUDED.voltaje, svoltage = EXCLUDED.svoltage, 
                current1 = EXCLUDED.current1, current2 = EXCLUDED.current2,
                conexion = EXCLUDED.conexion, capacidad = EXCLUDED.capacidad,
                voltaje_gen = EXCLUDED.voltaje_gen, corriente_gen = EXCLUDED.corriente_gen,
                ultimo_update = EXCLUDED.ultimo_update
        """, batch)
        
        conn.commit()
        print("Insert successful.")
        
        cur.execute("SELECT * FROM battery_telemetry WHERE device_id = 'TEST_DEVICE_ID'")
        print(cur.fetchone())
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_insert()
