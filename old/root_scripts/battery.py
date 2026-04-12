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
import csv
import psycopg2
from psycopg2.extras import execute_values

# Configuración de base de datos
DB_CONFIG = {
    "host": "localhost",
    "database": "tu_basedatos",
    "user": "tu_usuario",
    "password": "tu_password",
    "port": 5432
}

# Configuración PEIM
CONFIG_REGIONES = {
    "access": {
        "Ancash": {"ip": "10.254.1.135", "cookies": {"PEIMWEBID": "264F83D9E6EA7F370B10E5E926D987F9"}},
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

# Sensores para baterías de Litio
SENSORES_LITIO = {
    "0147116001": "soc",
    "0147106001": "carga",
    "0147106002": "descarga",
    "0147099001": "conexion",
}

# Sensores para baterías ZTE
SENSORES_ZTE = {
    "0132125001": "soc_1",
    "0132125002": "soc_2",
    "0132125003": "soc_3",
    "0132125004": "soc_4",
    "0132123001": "cur_1",
    "0132123002": "cur_2",
    "0132123003": "cur_3",
    "0132123004": "cur_4",
    "0132099001": "conexion",
}

# Sensores para rectificadores
SENSORES_RECTIFICADOR = {
    "0106101001": "voltaje",
    "0106111001": "svoltaje",
    "0106184001": "current1",
    "0106184002": "current2",
    "0106099001": "conexion",  # Asumiendo que usan el mismo código de conexión
}

# Tipos de interés
TIPOS_INTERES = [32, 47, 8, 6]  # ZTE, Litio, Rectificador

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
_site_ip_cache = {}

# ==================== FUNCIONES DE BASE DE DATOS ====================

def get_db_connection():
    """Obtiene conexión a PostgreSQL"""
    return psycopg2.connect(**DB_CONFIG)

def insertar_en_bd(dispositivos_data):
    """Inserta múltiples dispositivos en la tabla battery_telemetry"""
    if not dispositivos_data:
        return
    
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        
        # Preparar datos para inserción batch
        values = []
        for data in dispositivos_data:
            values.append((
                data["device_id"],
                data.get("soc"),
                data.get("carga"),
                data.get("descarga"),
                data.get("ultimo_update"),
                data["sitio"],
                data["nombre"],
                data.get("voltaje"),
                data.get("svoltaje"),
                data.get("current1"),
                data.get("current2"),
                data.get("conexion")
            ))
        
        # Insertar en batch
        execute_values(cur, """
            INSERT INTO battery_telemetry 
            (device_id, soc, carga, descarga, ultimo_update, sitio, nombre, 
             voltaje, svoltaje, current1, current2, conexion)
            VALUES %s
        """, values)
        
        conn.commit()
        print(f"   ✅ Insertados {len(values)} registros en BD")
        
    except Exception as e:
        print(f"   ❌ Error insertando en BD: {e}")
        conn.rollback()
    finally:
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

def get_ip_and_cookies_for_site(sitio_nombre, tipo):
    """Obtiene IP y cookies para un sitio según su nombre"""
    cache_key = f"{tipo}_{sitio_nombre}"
    
    if cache_key in _site_ip_cache:
        return _site_ip_cache[cache_key]
    
    if "_AR_" in sitio_nombre:
        region = "Arequipa"
    elif "_LL_" in sitio_nombre:
        region = "La Libertad"
    elif "_SM_" in sitio_nombre:
        region = "San Martin"
    elif "_AN_" in sitio_nombre:
        region = "Ancash"
    else:
        region = list(CONFIG_REGIONES[tipo].keys())[0]
    
    config = CONFIG_REGIONES[tipo][region]
    cookies = config["cookies"].copy()
    cookies.update({
        "contextPath": "/peim",
        "language": "es_ES",
        "loginUser": "yuri.carrasco",
        "proversion": "null"
    })
    
    result = (config["ip"], cookies)
    _site_ip_cache[cache_key] = result
    return result

def obtener_sitios_de_region(config, tipo, region):
    """Obtiene TODOS los sitios de una región"""
    cache_key = f"{tipo}_{region}"

    with _site_cache_lock:
        if cache_key in _site_cache:
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
                    sitios.append({
                        "precinct_id": item.get("precinct_id"),
                        "station_name": item.get("station_name") or item.get("name"),
                        "region": region,
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
    """Obtiene todos los dispositivos de interés de un sitio"""
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
            for item in data.get("info", []):
                if item.get("device_id"):
                    device_type = int(item.get("device_type", 0)) if item.get("device_type") else 0
                    if device_type in TIPOS_INTERES:
                        dispositivos.append({
                            "device_id": item.get("device_id"),
                            "device_name": item.get("device_name", ""),
                            "device_type": device_type,
                            "parent_id": item.get("pId") if item.get("pId") != sitio["precinct_id"] else None
                        })

        with _device_cache_lock:
            _device_cache[cache_key] = dispositivos

        return dispositivos
    except Exception as e:
        return []

def consultar_valores_dispositivo(device_id, sitio_nombre, tipo, device_type, nombre):
    """Consulta valores según el tipo de dispositivo"""
    ip, cookies = get_ip_and_cookies_for_site(sitio_nombre, tipo)
    
    url = f"http://{ip}:8090/peim/request/realtime/getMeteValue"
    headers = HEADERS_BASE.copy()
    headers["Host"] = f"{ip}:8090"
    
    if device_type == 32:  # ZTE
        headers["Referer"] = f"http://{ip}:8090/peim/main/realtime/realtimedevice.html?id={device_id}&device_type=32"
        sensores_map = SENSORES_ZTE
    elif device_type == 47:  # Litio
        headers["Referer"] = f"http://{ip}:8090/peim/main/realtime/realtimedevice.html?id={device_id}"
        sensores_map = SENSORES_LITIO
    else:  # Rectificador (8 o 6)
        headers["Referer"] = f"http://{ip}:8090/peim/main/realtime/realtimedevice.html?id={device_id}&device_type=8"
        sensores_map = SENSORES_RECTIFICADOR
    
    payload = f"device_id={device_id}&is_manual=0"
    valores = {}
    
    try:
        session = get_session_for_ip(ip)
        resp = session.post(url, headers=headers, cookies=cookies, data=payload, timeout=8)
        resp.raise_for_status()
        sensores = resp.json()
        
        for sensor in sensores:
            mete_id = sensor.get("meteId", "")
            mete_value = sensor.get("meteValue", "")
            update_time = sensor.get("updateTime", "")
            
            if mete_id in sensores_map:
                campo = sensores_map[mete_id]
                try:
                    if mete_value and mete_value != '':
                        valor_limpio = str(mete_value).strip().replace(',', '.')
                        valores[campo] = float(valor_limpio)
                except:
                    valores[campo] = mete_value
            
            if update_time and "ultimo_update" not in valores:
                valores["ultimo_update"] = update_time
        
        # Preparar datos para inserción según el tipo
        if device_type == 32:  # ZTE - crear 4 registros
            registros = []
            conexion = valores.get("conexion")
            for i in range(1, 5):
                soc = valores.get(f"soc_{i}")
                cur = valores.get(f"cur_{i}")
                if soc is not None or cur is not None:
                    registros.append({
                        "device_id": f"{device_id}_{i}",
                        "sitio": sitio_nombre,
                        "nombre": f"{nombre} {i}",
                        "soc": soc,
                        "carga": cur if cur and cur > 0 else None,
                        "descarga": abs(cur) if cur and cur < 0 else None,
                        "current1": cur,
                        "conexion": conexion,
                        "ultimo_update": valores.get("ultimo_update")
                    })
            return registros
        
        elif device_type == 47:  # Litio - 1 registro
            return [{
                "device_id": device_id,
                "sitio": sitio_nombre,
                "nombre": nombre,
                "soc": valores.get("soc"),
                "carga": valores.get("carga"),
                "descarga": valores.get("descarga"),
                "conexion": valores.get("conexion"),
                "ultimo_update": valores.get("ultimo_update")
            }]
        
        else:  # Rectificador - 1 registro
            return [{
                "device_id": device_id,
                "sitio": sitio_nombre,
                "nombre": nombre,
                "voltaje": valores.get("voltaje"),
                "svoltaje": valores.get("svoltaje"),
                "current1": valores.get("current1"),
                "current2": valores.get("current2"),
                "conexion": valores.get("conexion"),
                "ultimo_update": valores.get("ultimo_update")
            }]
            
    except Exception as e:
        print(f"   ⚠️ Error consultando {device_id}: {e}")
        return []

def procesar_tipo_sistema(tipo_sistema):
    """Procesa un tipo de sistema (access o transport)"""
    print(f"\n{'=' * 80}")
    print(f"📊 PROCESANDO {tipo_sistema.upper()}")
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
            except Exception:
                pass

    print(f"\n📋 Total sitios: {len(todos_los_sitios)}")
    
    if not todos_los_sitios:
        return []

    # Procesar sitios en lotes
    todos_los_dispositivos = []
    
    for batch_num, batch_start in enumerate(range(0, len(todos_los_sitios), BATCH_SIZE)):
        batch_end = min(batch_start + BATCH_SIZE, len(todos_los_sitios))
        batch = todos_los_sitios[batch_start:batch_end]
        
        print(f"\n📦 Lote {batch_num + 1}/{(len(todos_los_sitios)-1)//BATCH_SIZE + 1}")
        
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
        
        print(f"   📊 {len(dispositivos_lote)} dispositivos encontrados")
        
        if not dispositivos_lote:
            continue
        
        # Consultar valores en paralelo
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = {}
            for disp in dispositivos_lote:
                future = executor.submit(
                    consultar_valores_dispositivo,
                    disp["device_id"],
                    disp["site_name"] if "site_name" in disp else batch[0]["station_name"],  # Necesitas ajustar
                    tipo_sistema,
                    disp["device_type"],
                    disp["device_name"]
                )
                futures[future] = disp
            
            for future in as_completed(futures):
                try:
                    registros = future.result(timeout=10)
                    if registros:
                        todos_los_dispositivos.extend(registros)
                except Exception:
                    pass
        
        # Insertar en BD cada lote
        if todos_los_dispositivos:
            insertar_en_bd(todos_los_dispositivos)
            todos_los_dispositivos = []  # Limpiar para el siguiente lote
    
    return True

def main():
    print("=" * 100)
    print("🔋 MONITOR DE BATERÍAS Y RECTIFICADORES - INSERCIÓN EN PostgreSQL")
    print("=" * 100)
    
    inicio_total = time.time()
    
    # Procesar Access
    procesar_tipo_sistema("access")
    
    # Procesar Transport
    procesar_tipo_sistema("transport")
    
    tiempo_total = time.time() - inicio_total
    
    print("\n" + "=" * 100)
    print("📊 PROCESO COMPLETADO")
    print("=" * 100)
    print(f"⏱️ Tiempo total: {tiempo_total:.1f}s")
    print("=" * 100)

if __name__ == "__main__":
    main()