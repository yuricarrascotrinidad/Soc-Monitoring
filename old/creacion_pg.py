import psycopg2
from psycopg2 import extras
import sqlite3
import os
from app.config import Config

def create_pg_database():
    """
    Crea las tablas e índices en PostgreSQL según el esquema proporcionado por el usuario.
    """
    print("Conectando a PostgreSQL para crear el esquema...")
    
    try:
        conn = psycopg2.connect(
            host=Config.PG_HOST,
            port=Config.PG_PORT,
            database=Config.PG_DATABASE,
            user=Config.PG_USER,
            password=Config.PG_PASSWORD
        )
        cur = conn.cursor()

        # 1. Tabla alarmas
        print("Creando tabla 'alarmas'...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS alarmas (
                id SERIAL PRIMARY KEY,
                tipo TEXT NOT NULL,
                region TEXT NOT NULL,
                hora TIMESTAMP NOT NULL,
                duracion INTEGER,
                sitio TEXT NOT NULL,
                alarma TEXT NOT NULL,
                deviceName TEXT,
                categoria TEXT,
                estado TEXT,
                device_id TEXT,
                precinct_id TEXT,
                mete_name TEXT,
                valor DOUBLE PRECISION,
                UNIQUE(tipo, region, hora, sitio, alarma)
            );
        """)

        # 2. Tabla access_cameras
        print("Creando tabla 'access_cameras'...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS access_cameras (
                id SERIAL PRIMARY KEY,
                site TEXT NOT NULL,
                ip TEXT NOT NULL,
                UNIQUE(site, ip)
            );
        """)

        # 3. Tabla transport_cameras
        print("Creando tabla 'transport_cameras'...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS transport_cameras (
                id SERIAL PRIMARY KEY,
                site TEXT NOT NULL,
                position TEXT NOT NULL,
                ip TEXT NOT NULL,
                UNIQUE(site, position)
            );
        """)

        # 4. Tabla notificaciones_enviadas
        print("Creando tabla 'notificaciones_enviadas'...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS notificaciones_enviadas (
                sitio TEXT,
                tipo_sistema TEXT,
                tipo_evento TEXT,
                resuelto_desde TIMESTAMP,
                ultimo_envio TIMESTAMP,
                PRIMARY KEY (sitio, tipo_sistema)
            );
        """)

        # 5. Tabla battery_telemetry
        print("Creando tabla 'battery_telemetry'...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS battery_telemetry (
                device_id TEXT PRIMARY KEY,
                soc DOUBLE PRECISION,
                carga DOUBLE PRECISION,
                descarga DOUBLE PRECISION,
                ultimo_update TIMESTAMP,
                sitio TEXT,
                nombre TEXT,
                voltaje DOUBLE PRECISION,
                svoltage DOUBLE PRECISION,
                current1 DOUBLE PRECISION,
                current2 DOUBLE PRECISION,
                conexion INTEGER
            );
        """)

        # --- Índices ---
        print("Creando índices...")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_alarmas_tipo_sitio ON alarmas(tipo, sitio);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_alarmas_estado ON alarmas(estado);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_alarmas_region ON alarmas(region);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_alarmas_tipo_region_estado ON alarmas(tipo, region, estado);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_alarmas_hora ON alarmas(hora);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_alarmas_tipo_hora ON alarmas(tipo, hora);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_alarmas_device_id ON alarmas(device_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_alarmas_categoria ON alarmas(categoria);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_alarmas_dashboard_v2 ON alarmas(tipo, hora, estado);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_alarmas_pruning_v2 ON alarmas(hora, estado);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_alarmas_lookup_v3 ON alarmas(tipo, region, hora, sitio, alarma, deviceName);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_alarmas_events_v2 ON alarmas(tipo, estado, hora, sitio);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_battery_telemetry_sitio ON battery_telemetry(sitio);")

        conn.commit()
        print("✅ Esquema de PostgreSQL creado exitosamente.")
        cur.close()
        conn.close()

    except Exception as e:
        print(f"❌ Error creando esquema en PostgreSQL: {e}")

if __name__ == "__main__":
    create_pg_database()
