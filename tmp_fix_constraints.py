import psycopg2
from app.config import Config

def migrate():
    conn = psycopg2.connect(
        host=Config.PG_HOST,
        port=Config.PG_PORT,
        database=Config.PG_DATABASE,
        user=Config.PG_USER,
        password=Config.PG_PASSWORD
    )
    cur = conn.cursor()
    
    try:
        print("Eliminando duplicados en battery_telemetry...")
        # Mantener solo el registro más reciente para cada device_id
        cur.execute("""
            DELETE FROM battery_telemetry a
            USING battery_telemetry b
            WHERE a.id < b.id AND a.device_id = b.device_id;
        """)
        print(f"Registros duplicados eliminados: {cur.rowcount}")
        
        print("Agregando restricción UNIQUE a device_id...")
        cur.execute("""
            ALTER TABLE battery_telemetry 
            ADD CONSTRAINT battery_telemetry_device_id_key UNIQUE (device_id);
        """)
        conn.commit()
        print("Migración exitosa: UNIQUE(device_id) agregado.")
    except Exception as e:
        print(f"Error en migración: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
