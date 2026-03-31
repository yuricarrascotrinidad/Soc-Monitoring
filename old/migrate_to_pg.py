import sqlite3
import psycopg2
from psycopg2 import extras
from app.config import Config
from datetime import datetime

def migrate():
    print("Iniciando migración de SQLite a PostgreSQL...")
    
    # Conexiones
    try:
        sqlite_conn = sqlite3.connect(Config.DB_PATH)
        sqlite_conn.row_factory = sqlite3.Row
        sqlite_cur = sqlite_conn.cursor()
        
        pg_conn = psycopg2.connect(
            host=Config.PG_HOST,
            port=Config.PG_PORT,
            database=Config.PG_DATABASE,
            user=Config.PG_USER,
            password=Config.PG_PASSWORD
        )
        pg_cur = pg_conn.cursor()
        
        # 1. Migrar access_cameras
        print("Migrando 'access_cameras'...")
        sqlite_cur.execute("SELECT site, ip FROM access_cameras")
        rows = sqlite_cur.fetchall()
        for row in rows:
            pg_cur.execute(
                "INSERT INTO access_cameras (site, ip) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (row['site'], row['ip'])
            )
        
        # 2. Migrar transport_cameras
        print("Migrando 'transport_cameras'...")
        sqlite_cur.execute("SELECT site, position, ip FROM transport_cameras")
        rows = sqlite_cur.fetchall()
        for row in rows:
            pg_cur.execute(
                "INSERT INTO transport_cameras (site, position, ip) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                (row['site'], row['position'], row['ip'])
            )
            
        # 3. Migrar battery_telemetry
        print("Migrando 'battery_telemetry'...")
        sqlite_cur.execute("SELECT * FROM battery_telemetry")
        rows = sqlite_cur.fetchall()
        for row in rows:
            pg_cur.execute("""
                INSERT INTO battery_telemetry (device_id, soc, carga, descarga, ultimo_update, sitio, nombre, voltaje)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (device_id) DO UPDATE SET
                soc=EXCLUDED.soc, carga=EXCLUDED.carga, descarga=EXCLUDED.descarga, 
                ultimo_update=EXCLUDED.ultimo_update, sitio=EXCLUDED.sitio, 
                nombre=EXCLUDED.nombre, voltaje=EXCLUDED.voltaje
            """, (row['device_id'], row['soc'], row['carga'], row['descarga'], row['ultimo_update'], 
                  row['sitio'], row['nombre'], row['voltaje']))

        # 4. Migrar notificaciones_enviadas
        print("Migrando 'notificaciones_enviadas'...")
        sqlite_cur.execute("SELECT * FROM notificaciones_enviadas")
        rows = sqlite_cur.fetchall()
        for row in rows:
            pg_cur.execute("""
                INSERT INTO notificaciones_enviadas (sitio, tipo_sistema, tipo_evento, resuelto_desde, ultimo_envio)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (sitio, tipo_sistema) DO NOTHING
            """, (row['sitio'], row['tipo_sistema'], row['tipo_evento'], row['resuelto_desde'], row['ultimo_envio']))

        # 5. Migrar alarmas (esto puede ser pesado)
        print("Migrando 'alarmas' (cargando datos)...")
        sqlite_cur.execute("SELECT * FROM alarmas")
        count = 0
        while True:
            batch = sqlite_cur.fetchmany(1000)
            if not batch:
                break
            
            for row in batch:
                pg_cur.execute("""
                    INSERT INTO alarmas (tipo, region, hora, duracion, sitio, alarma, deviceName, categoria, estado, device_id, precinct_id, mete_name, valor)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (tipo, region, hora, sitio, alarma) DO NOTHING
                """, (row['tipo'], row['region'], row['hora'], row['duracion'], row['sitio'], 
                      row['alarma'], row['deviceName'], row['categoria'], row['estado'], 
                      row['device_id'], row['precinct_id'], row['mete_name'], row['valor']))
            
            count += len(batch)
            print(f"Migrados {count} registros de alarmas...")
            pg_conn.commit()

        pg_conn.commit()
        print("✅ Migración completada exitosamente.")
        
    except Exception as e:
        print(f"❌ Error durante la migración: {e}")
        if 'pg_conn' in locals():
            pg_conn.rollback()
    finally:
        if 'sqlite_conn' in locals(): sqlite_conn.close()
        if 'pg_conn' in locals(): pg_conn.close()

if __name__ == "__main__":
    migrate()
