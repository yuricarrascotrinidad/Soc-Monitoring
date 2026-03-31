import sqlite3
import os

DB_PATH = 'monitoring.db'

def create_database():
    """
    Crea la base de datos monitoring.db con todas sus tablas e índices.
    También aplica optimizaciones de rendimiento como el modo WAL.
    """
    print(f"Iniciando creación de la base de datos en: {os.path.abspath(DB_PATH)}")
    
    # Conectar a la base de datos
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        # --- Optimizaciones de Rendimiento ---
        print("Aplicando optimizaciones (WAL mode)...")
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("PRAGMA cache_size=-64000;")  # ~64MB de caché
        cursor.execute("PRAGMA foreign_keys=ON;")

        # --- Creación de Tablas ---
        
        # 1. Tabla de Alarmas
        print("Creando tabla 'alarmas'...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alarmas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo TEXT NOT NULL,          -- 'access' o 'transport'
                region TEXT NOT NULL,
                hora TEXT NOT NULL,          -- Formato ISO8601 o similar
                duracion INTEGER,
                sitio TEXT NOT NULL,
                alarma TEXT NOT NULL,
                categoria TEXT,
                estado TEXT,                 -- 'active', 'resolved', etc.
                device_id TEXT,
                deviceName TEXT,
                precinct_id TEXT,
                mete_name TEXT,
                valor REAL,
                UNIQUE(tipo, region, hora, sitio, alarma, deviceName)
            )
        """)

        # 2. Tabla de Cámaras Access
        print("Creando tabla 'access_cameras'...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS access_cameras (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                site TEXT NOT NULL,
                ip TEXT NOT NULL,
                UNIQUE(site, ip)
            )
        """)

        # 3. Tabla de Cámaras Transport
        print("Creando tabla 'transport_cameras'...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transport_cameras (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                site TEXT NOT NULL,
                position TEXT NOT NULL,
                ip TEXT NOT NULL,
                UNIQUE(site, position)
            )
        """)

        # 4. Tabla de Notificaciones Enviadas
        print("Creando tabla 'notificaciones_enviadas'...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notificaciones_enviadas (
                sitio TEXT,
                tipo_sistema TEXT,
                tipo_evento TEXT,
                resuelto_desde DATETIME,
                ultimo_envio DATETIME,
                PRIMARY KEY (sitio, tipo_sistema)
            )
        """)

        # 5. Tabla de Telemetría de Batería
        print("Creando tabla 'battery_telemetry'...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS battery_telemetry (
                device_id TEXT PRIMARY KEY,
                soc REAL,
                carga REAL,
                descarga REAL,
                ultimo_update DATETIME,
                sitio TEXT,
                nombre TEXT,
                voltaje REAL
            )
        """)

        # --- Creación de Índices ---
        print("Creando índices para optimizar consultas...")
        
        # Índices para la tabla 'alarmas'
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alarmas_tipo_sitio ON alarmas(tipo, sitio)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alarmas_estado ON alarmas(estado)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alarmas_region ON alarmas(region)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alarmas_tipo_region_estado ON alarmas(tipo, region, estado)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alarmas_hora ON alarmas (hora)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alarmas_tipo_hora ON alarmas (tipo, hora)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alarmas_device_id ON alarmas(device_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alarmas_categoria ON alarmas(categoria)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alarmas_dashboard_v2 ON alarmas (tipo, hora, estado)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alarmas_pruning_v2 ON alarmas (hora, estado)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alarmas_lookup_v3 ON alarmas (tipo, region, hora, sitio, alarma, deviceName)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_alarmas_events_v2 ON alarmas (tipo, estado, hora, sitio)")
        
        # Índices para la tabla 'battery_telemetry'
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_battery_telemetry_sitio ON battery_telemetry (sitio)")

        conn.commit()
        print("¡Base de datos y tablas creadas exitosamente!")

    except sqlite3.Error as e:
        print(f"Error al crear la base de datos: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    create_database()
