import requests
import json
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import os
from collections import defaultdict
import threading
import psycopg2
from psycopg2.extras import execute_values

# Configuración de base de datos
DB_CONFIG = {
    "host": "localhost",
    "database": "monitoring",
    "user": "postgres",
    "password": "yofc",
    "port": 5432
}

# Configuración PEIM
CONFIG_REGIONES = {
    "access": {
        "Ancash": {"ip": "10.254.1.135", "cookies": {"PEIMWEBID": "537C0F40B4F05D4160F8E9548151B30B"}},
        "Arequipa": {"ip": "10.254.11.135", "cookies": {"PEIMWEBID": "6C4BD7A1CC8C636C1781570EB5D8EF81"}},
        "La Libertad": {"ip": "10.254.21.135", "cookies": {"PEIMWEBID": "1465F9AEE485A3A1BE1BF372D21F6A40"}},
        "San Martin": {"ip": "10.254.31.135", "cookies": {"PEIMWEBID": "A60700835EFB7AEA56D1CD1BC8F67A94"}},
    },
    "transport": {
        "Ancash": {"ip": "10.255.1.135", "cookies": {"PEIMWEBID": "53B69B502B858C25C5E0BE0FDDF355D4"}},
        "Arequipa": {"ip": "10.255.11.135", "cookies": {"PEIMWEBID": "0B2DE9E0EBF4F8E6D34A8ECCF78D7AB2"}},
        "La Libertad": {"ip": "10.255.21.135", "cookies": {"PEIMWEBID": "EA07691F1658E89C7DF4B4B647EA11FA"}},
        "San Martin": {"ip": "10.255.31.135", "cookies": {"PEIMWEBID": "27DFD962EB5CB3E3F89D7695341F2CC7"}},
    }
}

HEADERS_BASE = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "es-419,es-US;q=0.9,es;q=0.8",
    "Connection": "keep-alive",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "X-Requested-With": "XMLHttpRequest"
}

# TIPOS DE DISPOSITIVOS QUE NOS INTERESAN
TIPOS_INTERES = {
    47: "litio",
    32: "zte",
    8: "rectificador",
    6: "rectificador",
    12: "aa",
    5: "ge"
}

# Configuración de optimización
MAX_WORKERS = 200
BATCH_SIZE = 200
REQUEST_TIMEOUT = 15
DEVICE_TIMEOUT = 10

# Cache
_device_cache = {}
_device_cache_lock = threading.Lock()
_site_cache = {}
_site_cache_lock = threading.Lock()
_sessions = {}
_sessions_lock = threading.Lock()

# ==================== FUNCIONES DE BASE DE DATOS ====================

def get_db_connection():
    """Obtiene conexión a PostgreSQL"""
    return psycopg2.connect(**DB_CONFIG)

def crear_tabla_si_no_existe():
    """Crea la tabla de catálogo si no existe"""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        # Verificar si la tabla existe
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'catalogo_dispositivos'
            )
        """)
        existe = cur.fetchone()[0]
        
        if not existe:
            cur.execute("""
                CREATE TABLE catalogo_dispositivos (
                    id SERIAL PRIMARY KEY,
                    sitio VARCHAR(100) NOT NULL,
                    region VARCHAR(50),
                    tipo_sistema VARCHAR(20),
                    device_id VARCHAR(50) NOT NULL UNIQUE,
                    nombre_dispositivo VARCHAR(200),
                    tipo_dispositivo VARCHAR(30),
                    device_type INTEGER,
                    parent_device_id VARCHAR(50),
                    fecha_descubrimiento TIMESTAMP DEFAULT NOW(),
                    activo BOOLEAN DEFAULT TRUE
                )
            """)
            cur.execute("CREATE INDEX idx_catalogo_tipo ON catalogo_dispositivos(tipo_dispositivo)")
            cur.execute("CREATE INDEX idx_catalogo_sitio ON catalogo_dispositivos(sitio)")
            cur.execute("CREATE INDEX idx_catalogo_device_id ON catalogo_dispositivos(device_id)")
            conn.commit()
            print("✅ Tabla 'catalogo_dispositivos' creada exitosamente")
        else:
            print("✅ Tabla 'catalogo_dispositivos' ya existe")
            
    except Exception as e:
        print(f"❌ Error creando tabla: {e}")
    finally:
        conn.close()

def guardar_en_catalogo(dispositivos):
    """Guarda o actualiza dispositivos en el catálogo"""
    if not dispositivos:
        return
    
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Preparar datos para upsert - SOLO 8 VALORES (sin activo)
        values = []
        for d in dispositivos:
            values.append((
                d["sitio"],
                d["region"],
                d["tipo_sistema"],
                d["device_id"],
                d["nombre"],
                d["tipo_dispositivo"],
                d["device_type"],
                d.get("parent_id")  # puede ser None
            ))
        
        # UPSERT: insertar o actualizar si ya existe
        execute_values(cur, """
            INSERT INTO catalogo_dispositivos 
            (sitio, region, tipo_sistema, device_id, nombre_dispositivo, 
             tipo_dispositivo, device_type, parent_device_id)
            VALUES %s
            ON CONFLICT (device_id) DO UPDATE SET
                sitio = EXCLUDED.sitio,
                region = EXCLUDED.region,
                nombre_dispositivo = EXCLUDED.nombre_dispositivo,
                parent_device_id = EXCLUDED.parent_device_id,
                activo = TRUE,
                fecha_descubrimiento = NOW()
        """, values)
        
        conn.commit()
        print(f"   ✅ Guardados {len(values)} dispositivos en catálogo")
        
    except Exception as e:
        print(f"   ❌ Error guardando en catálogo: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

# ==================== FUNCIONES PEIM ====================

def get_session_for_ip(ip):
    """Obtiene o crea una sesión para una IP específica"""
    with _sessions_lock:
        if ip not in _sessions:
            session = requests.Session()
            retry = Retry(total=2, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
            adapter = HTTPAdapter(max_retries=retry, pool_connections=100, pool_maxsize=200)
            session.mount('http://', adapter)
            _sessions[ip] = session
        return _sessions[ip]

def obtener_sitios_de_region(config, tipo, region):
    """Obtiene TODOS los sitios de una región"""
    cache_key = f"{tipo}_{region}"

    with _site_cache_lock:
        if cache_key in _site_cache:
            print(f"   📦 Usando cache para {region} ({tipo})")
            return _site_cache[cache_key]

    ip = config["ip"]
    cookies = config["cookies"].copy()
    cookies.update({
        "contextPath": "/peim",
        "language": "es_ES",
        "loginUser": "yuri.carrasco",
        "proversion": "null"
    })

    url = f"http://{ip}:8090/peim/request/region/getDeviceTree"
    headers = HEADERS_BASE.copy()
    headers["Host"] = f"{ip}:8090"

    params = {
        "tree_type": 0,
        "id": "00001005000000000000",
        "node_type_show": 3,
        "_": int(time.time() * 1000)
    }

    try:
        session = get_session_for_ip(ip)
        resp = session.get(url, headers=headers, cookies=cookies, params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        sitios = []
        if data.get("success"):
            for item in data.get("info", []):
                if item.get("node_kind") == "5":
                    # Determinar región por el nombre si es necesario
                    station_name = item.get("station_name") or item.get("name")
                    region_detectada = region
                    if "_AR_" in station_name:
                        region_detectada = "Arequipa"
                    elif "_LL_" in station_name:
                        region_detectada = "La Libertad"
                    elif "_SM_" in station_name:
                        region_detectada = "San Martin"
                    elif "_AN_" in station_name:
                        region_detectada = "Ancash"
                    
                    sitios.append({
                        "precinct_id": item.get("precinct_id"),
                        "station_name": station_name,
                        "region": region_detectada,
                        "tipo": tipo,
                        "ip": ip,
                        "cookies": cookies
                    })

        with _site_cache_lock:
            _site_cache[cache_key] = sitios

        return sitios
    except Exception as e:
        print(f"   ❌ Error en {region}: {e}")
        return []

def obtener_dispositivos_de_sitio(sitio):
    """Obtiene todos los dispositivos de interés de un sitio con su jerarquía"""
    cache_key = f"{sitio['ip']}_{sitio['precinct_id']}"

    with _device_cache_lock:
        if cache_key in _device_cache:
            return _device_cache[cache_key]

    url = f"http://{sitio['ip']}:8090/peim/request/region/getDeviceTree"
    headers = HEADERS_BASE.copy()
    headers["Host"] = f"{sitio['ip']}:8090"

    params = {
        "tree_type": 0,
        "id": sitio["precinct_id"],
        "node_type_show": 3,
        "_": int(time.time() * 1000)
    }

    try:
        session = get_session_for_ip(sitio['ip'])
        resp = session.get(url, headers=headers, cookies=sitio["cookies"],
                           params=params, timeout=DEVICE_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()

        dispositivos = []
        if data.get("success"):
            # Primero, mapear todos los dispositivos
            todos_los_disp = {}
            
            for item in data.get("info", []):
                if item.get("device_id"):
                    device_id = item.get("device_id")
                    device_name = item.get("device_name", "")
                    device_type = int(item.get("device_type", 0)) if item.get("device_type") else 0
                    parent_id = item.get("pId")
                    
                    todos_los_disp[device_id] = {
                        "device_id": device_id,
                        "device_name": device_name,
                        "device_type": device_type,
                        "parent_id": parent_id if parent_id and parent_id != sitio["precinct_id"] else None
                    }
            
            # Ahora, extraer solo los que nos interesan
            for device_id, disp in todos_los_disp.items():
                if disp["device_type"] in TIPOS_INTERES:
                    dispositivo = {
                        "sitio": sitio["station_name"],
                        "region": sitio["region"],
                        "tipo_sistema": sitio["tipo"],
                        "device_id": device_id,
                        "nombre": disp["device_name"],
                        "device_type": disp["device_type"],
                        "tipo_dispositivo": TIPOS_INTERES[disp["device_type"]],
                        "parent_id": disp["parent_id"]
                    }
                    dispositivos.append(dispositivo)

        with _device_cache_lock:
            _device_cache[cache_key] = dispositivos

        return dispositivos
    except Exception as e:
        print(f"   ⚠️ Error obteniendo dispositivos de {sitio['station_name']}: {e}")
        return []

def procesar_tipo_sistema(tipo_sistema):
    """Procesa un tipo de sistema y guarda en catálogo"""
    print(f"\n{'=' * 80}")
    print(f"📊 ESCANEANDO {tipo_sistema.upper()} PARA CATÁLOGO")
    print(f"{'=' * 80}")

    # Obtener sitios
    todos_los_sitios = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = []
        for region, config in CONFIG_REGIONES[tipo_sistema].items():
            futures.append(executor.submit(obtener_sitios_de_region, config, tipo_sistema, region))
        
        for future in as_completed(futures):
            try:
                sitios = future.result(timeout=30)
                todos_los_sitios.extend(sitios)
                print(f"   ✓ {len(sitios)} sitios en {sitios[0]['region'] if sitios else 'desconocida'}")
            except Exception:
                pass

    print(f"\n📋 Total sitios {tipo_sistema}: {len(todos_los_sitios)}")
    
    if not todos_los_sitios:
        return 0

    # Procesar sitios en lotes
    total_dispositivos = 0
    
    for batch_num, batch_start in enumerate(range(0, len(todos_los_sitios), BATCH_SIZE)):
        batch_end = min(batch_start + BATCH_SIZE, len(todos_los_sitios))
        batch = todos_los_sitios[batch_start:batch_end]
        
        print(f"\n📦 Lote {batch_num + 1}/{(len(todos_los_sitios)-1)//BATCH_SIZE + 1}")
        print(f"   Procesando {len(batch)} sitios...")
        
        # Obtener dispositivos del lote
        dispositivos_lote = []
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {executor.submit(obtener_dispositivos_de_sitio, sitio): sitio for sitio in batch}
            for future in as_completed(futures):
                try:
                    dispositivos = future.result(timeout=DEVICE_TIMEOUT)
                    dispositivos_lote.extend(dispositivos)
                except Exception:
                    pass
        
        if dispositivos_lote:
            print(f"   📊 {len(dispositivos_lote)} dispositivos de interés encontrados")
            
            # Guardar en catálogo
            guardar_en_catalogo(dispositivos_lote)
            total_dispositivos += len(dispositivos_lote)
    
    return total_dispositivos

def main():
    print("=" * 100)
    print("📚 GENERADOR DE CATÁLOGO DE DISPOSITIVOS - BATERÍAS, AA, GE, RECTIFICADORES")
    print("=" * 100)
    print("📡 Access | 🚛 Transport")
    print()
    
    # Crear tabla si no existe
    crear_tabla_si_no_existe()
    
    inicio_total = time.time()
    
    # Procesar Access
    total_access = procesar_tipo_sistema("access")
    
    # Procesar Transport
    total_transport = procesar_tipo_sistema("transport")
    
    tiempo_total = time.time() - inicio_total
    
    print("\n" + "=" * 100)
    print("📊 RESUMEN DEL CATÁLOGO")
    print("=" * 100)
    print(f"📡 Access: {total_access} dispositivos")
    print(f"🚛 Transport: {total_transport} dispositivos")
    print(f"📦 TOTAL: {total_access + total_transport} dispositivos en catálogo")
    print(f"⏱️ Tiempo total: {tiempo_total:.1f}s")
    print("=" * 100)

if __name__ == "__main__":
    main()