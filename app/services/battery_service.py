import time
import json
import logging
import threading
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# App modules
from app.config import Config
from app.utils.db import get_db_connection, execute_db
from app.utils.constants import load_dynamic_tokens, SENSORES_INTERES

# ==================== CONFIGURACIÓN ====================
# Estos valores se sincronizan dinámicamente, pero usamos HEADERS base
HEADERS_BASE = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "es-419,es-US;q=0.9,es;q=0.8",
    "Connection": "keep-alive",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "X-Requested-With": "XMLHttpRequest"
}

# Las constantes de sensores ahora se obtienen de SENSORES_INTERES en constants.py

class BatteryService:
    _session_pool = {}
    _pool_lock = threading.Lock()
    _monitoring_started = False
    
    # Cache para evitar Redescubrimiento constante (15s es muy rápido)
    _sitios_cache = [] # Lista de sitios descubiertos en el último escaneo global
    _dispositivos_cache = {} # sitio_name -> lista de dispositivos
    _last_history_save = {} # device_key -> datetime (último guardado en históricos)

    @classmethod
    def _get_session(cls, ip):
        """Retorna una sesión HTTP con pool de conexiones para una IP específica."""
        with cls._pool_lock:
            if ip not in cls._session_pool:
                session = requests.Session()
                retry = Retry(total=2, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
                adapter = HTTPAdapter(max_retries=retry, pool_connections=50, pool_maxsize=100)
                session.mount('http://', adapter)
                cls._session_pool[ip] = session
            return cls._session_pool[ip]

    @staticmethod
    def _init_db():
        """Inicializa todas las tablas de telemetría (Global, Prioridad, Rectificadores)."""
        try:
            # 1. Tabla de PRIORITARIA (Solo fallas AC/Batería - 15s)
            execute_db("""
                CREATE TABLE IF NOT EXISTS battery_telemetry (
                    device_id TEXT, nombre TEXT, sitio TEXT, region TEXT, 
                    tipo_sistema TEXT, tipo_dispositivo TEXT,
                    soc FLOAT, carga FLOAT, descarga FLOAT, voltaje FLOAT, svoltage FLOAT, 
                    current1 FLOAT, current2 FLOAT, conexion INTEGER, capacidad FLOAT, 
                    voltaje_gen FLOAT, corriente_gen FLOAT,
                    ultimo_update TIMESTAMP,
                    PRIMARY KEY (device_id, nombre, sitio)
                )
            """)

            # 2. Tabla GLOBAL (Todas las baterías - 1h) - Simplificada
            execute_db("""
                CREATE TABLE IF NOT EXISTS battery_telemetry_global (
                    device_id TEXT, nombre TEXT, sitio TEXT, region TEXT, 
                    tipo_sistema TEXT, tipo_dispositivo TEXT,
                    soc FLOAT, conexion INTEGER, capacidad FLOAT, 
                    ultimo_update TIMESTAMP,
                    PRIMARY KEY (device_id, nombre, sitio)
                )
            """)

            # 3. Tabla de RECTIFICADORES (Live - 5m/15s) - Simplificada
            execute_db("""
                CREATE TABLE IF NOT EXISTS rectifier_telemetry (
                    device_id TEXT, nombre TEXT, sitio TEXT, region TEXT, 
                    tipo_sistema TEXT, tipo_dispositivo TEXT,
                    voltaje FLOAT, svoltage FLOAT, 
                    current1 FLOAT, current2 FLOAT, conexion INTEGER, 
                    ultimo_update TIMESTAMP,
                    PRIMARY KEY (device_id, nombre, sitio)
                )
            """)

            # 4. Tabla de HISTÓRICO RECTIFICADORES (Snapshot - 5m) - Simplificada
            execute_db("""
                CREATE TABLE IF NOT EXISTS rectifier_telemetry_history (
                    id SERIAL PRIMARY KEY,
                    device_id TEXT, nombre TEXT, sitio TEXT, region TEXT, 
                    tipo_sistema TEXT, tipo_dispositivo TEXT,
                    voltaje FLOAT, svoltage FLOAT, 
                    current1 FLOAT, current2 FLOAT, conexion INTEGER, 
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Migraciones para columnas de Generador (si las tablas ya existían)
            tablas = ["battery_telemetry"]
            columnas = {"voltaje_gen": "FLOAT", "corriente_gen": "FLOAT"}
            for tabla in tablas:
                for col, tipo in columnas.items():
                    try:
                        execute_db(f"ALTER TABLE {tabla} ADD COLUMN {col} {tipo}")
                        logging.info(f"➕ Columna '{col}' añadida a {tabla}.")
                    except Exception: pass # Ya existe

            logging.info("💾 Estructura de tablas de telemetría (Global/Prioridad/Rect) inicializada.")
        except Exception as e:
            logging.error(f"Error inicializando DB: {e}")

    @staticmethod
    def _get_cookies_base(cookies_original):
        cookies = cookies_original.copy()
        cookies.update({
            "contextPath": "/peim",
            "language": "es_ES",
            "loginUser": "noc_reports",
            "proversion": "null",
            "sessionUser": "%7B%22retUrl%22%3A%22/peim/views/default_design%22%2C%22fr_use%22%3A%221%22%2C%22user_name%22%3A%22noc_reports%22%2C%22proversion%22%3Anull%2C%22operate_id%22%3A%221%2C2%2C3%2C4%2C5%2C6%2C7%2C8%2C9%2C10%22%2C%22isAdmin%22%3A%22false%22%2C%22userid%22%3A%2200001001000000000047%22%2C%22username%22%3A%22noc_reports%22%7D"
        })
        return cookies

    @staticmethod
    def obtener_sitios(tipo, region, config):
        ip = config.get("ip") or requests.utils.urlparse(config["url"]).hostname
        cookies = BatteryService._get_cookies_base(config["cookies"])
        url = f"http://{ip}:8090/peim/request/region/getDeviceTree"
        headers = {**HEADERS_BASE, "Host": f"{ip}:8090"}
        
        sitios = []
        
        def explore(node_id):
            params = {"tree_type": 0, "id": node_id, "node_type_show": 3, "_": int(time.time() * 1000)}
            try:
                session = BatteryService._get_session(ip)
                resp = session.get(url, headers=headers, cookies=cookies, params=params, timeout=15)
                data = resp.json()
                if data.get("success"):
                    for item in data.get("info", []):
                        n_kind = str(item.get("node_kind"))
                        if n_kind == "5": # Site
                            sitios.append({
                                "tipo": tipo, "region": region, "ip": ip, "cookies": cookies,
                                "precinct_id": item.get("precinct_id") or item.get("id"),
                                "station_name": item.get("station_name") or item.get("name")
                            })
                        elif n_kind in ["3", "4"]: # Region/Province/Area - Explore deeper
                            explore(item.get("id"))
            except Exception: pass

        explore("00001005000000000000")
        return sitios

    @staticmethod
    def obtener_dispositivos(sitio):
        ip, cookies = sitio["ip"], sitio["cookies"]
        url = f"http://{ip}:8090/peim/request/region/getDeviceTree"
        headers = {**HEADERS_BASE, "Host": f"{ip}:8090"}
        params = {"tree_type": 0, "id": sitio["precinct_id"], "node_type_show": 3, "_": int(time.time() * 1000)}
        
        dispositivos_dict = {}
        snmps = []
        try:
            session = BatteryService._get_session(ip)
            resp = session.get(url, headers=headers, cookies=cookies, params=params, timeout=10)
            data = resp.json()
            if data.get("success"):
                for item in data.get("info", []):
                    dtype, did, name = item.get("device_type"), item.get("device_id"), item.get("device_name", "")
                    
                    if dtype == "47": # Litio
                        dispositivos_dict[did] = {"tipo_dispositivo": "Litio", "device_id": did, "nombre": name, "ip": ip, "cookies": cookies, "sitio": sitio["station_name"], "region": sitio["region"], "tipo_sistema": sitio["tipo"]}
                    elif dtype in ["6", "8"]: # Rectificador
                        dispositivos_dict[did] = {"tipo_dispositivo": "Rectificador", "device_id": did, "nombre": name, "ip": ip, "cookies": cookies, "sitio": sitio["station_name"], "region": sitio["region"], "tipo_sistema": sitio["tipo"]}
                    elif dtype == "5": # Generador
                        dispositivos_dict[did] = {"tipo_dispositivo": "Generador", "device_id": did, "nombre": name, "ip": ip, "cookies": cookies, "sitio": sitio["station_name"], "region": sitio["region"], "tipo_sistema": sitio["tipo"]}
                    elif dtype == "32": # ZTE (Directo)
                        dispositivos_dict[did] = {"tipo_dispositivo": "ZTE", "device_id": did, "nombre": name, "ip": ip, "cookies": cookies, "sitio": sitio["station_name"], "region": sitio["region"], "tipo_sistema": sitio["tipo"]}
                    elif dtype == "38" and "SNMP" in name:
                        snmps.append(did)
            
            for snmp_id in snmps:
                p2 = {**params, "id": snmp_id}
                try:
                    r2 = session.get(url, headers=headers, cookies=cookies, params=p2, timeout=10)
                    d2 = r2.json()
                    if d2.get("success"):
                        for item in d2.get("info", []):
                            dt, did, name = item.get("device_type"), item.get("device_id"), item.get("device_name", "")
                            
                            if did not in dispositivos_dict:
                                if dt == "32": # ZTE
                                    dispositivos_dict[did] = {"tipo_dispositivo": "ZTE", "device_id": did, "nombre": name, "ip": ip, "cookies": cookies, "sitio": sitio["station_name"], "region": sitio["region"], "tipo_sistema": sitio["tipo"]}
                                elif dt in ["6", "8"]:
                                    dispositivos_dict[did] = {"tipo_dispositivo": "Rectificador", "device_id": did, "nombre": name, "ip": ip, "cookies": cookies, "sitio": sitio["station_name"], "region": sitio["region"], "tipo_sistema": sitio["tipo"]}
                except: pass
            return list(dispositivos_dict.values())
        except Exception: return []

    @staticmethod
    def obtener_valores(dispositivo):
        ip, cookies, did, tipo = dispositivo["ip"], dispositivo["cookies"], dispositivo["device_id"], dispositivo["tipo_dispositivo"]
        url = f"http://{ip}:8090/peim/request/realtime/getMeteValue"
        headers = {**HEADERS_BASE, "Host": f"{ip}:8090", "Origin": f"http://{ip}:8090"}
        
        if tipo == "Litio":
            headers["Referer"] = f"http://{ip}:8090/peim/main/realtime/realtimedevice.html?id={did}&device_type=47"
        elif tipo == "ZTE":
            headers["Referer"] = f"http://{ip}:8090/peim/main/realtime/realtimedevice.html?id={did}"
        elif tipo == "Generador":
            headers["Referer"] = f"http://{ip}:8090/peim/main/realtime/realtimedevice.html?id={did}"
        else:
            headers["Referer"] = f"http://{ip}:8090/peim/main/realtime/realtimedevice.html?id={did}&device_type=8"
        
        s_map = SENSORES_INTERES
            
        try:
            session = BatteryService._get_session(ip)
            resp = session.post(url, headers=headers, cookies=cookies, data=f"device_id={did}&is_manual=0", timeout=10)
            sensores = resp.json()
            valores = {}
            for s in sensores:
                mid, mval = str(s.get("meteId", "")).strip(), s.get("meteValue", "")
                if mid in s_map and mval is not None and mval != '':
                    campo = s_map[mid]
                    try:
                        v = float(str(mval).strip().replace(',', '.'))
                        valores[campo] = int(v) if campo == "conexion" else v
                    except: pass
            
            if tipo == "ZTE":
                for i in range(1, 5):
                    if valores.get(f'soc_{i}') is not None:
                        valores["soc"] = valores[f'soc_{i}']
                        break
            
            return {**dispositivo, "valores": valores}
        except Exception: return None

    @staticmethod
    def sync_battery_data(app, mode='priority'):
        """
        Ejecuta la sincronización de telemetría.
        'global': Todas las baterías -> battery_telemetry_global (1h)
        'priority': Baterías con alarma -> battery_telemetry (15s)
        'rectifiers': Todos los rectificadores -> rectifier_telemetry + history (5m)
        """
        start_time = time.time()
        now = datetime.now()
        logging.info(f"🔋 Iniciando escaneo de baterías [Modo: {mode.upper()}]...")
        
        from app.utils.constants import CONFIG_REGIONES
        load_dynamic_tokens()
        
        dispositivos_a_escanear = []

        if mode == 'global':
            # 1. Modo Global: Todas las baterías de todos los sitios
            todos_los_sitios = []
            with ThreadPoolExecutor(max_workers=16) as executor:
                fs = []
                for t, regs in CONFIG_REGIONES.items():
                    for r, cfg in regs.items():
                        fs.append(executor.submit(BatteryService.obtener_sitios, t, r, cfg))
                for f in as_completed(fs): todos_los_sitios.extend(f.result())
            
            BatteryService._sitios_cache = todos_los_sitios
            
            with ThreadPoolExecutor(max_workers=50) as executor:
                fs = {executor.submit(BatteryService.obtener_dispositivos, s): s for s in todos_los_sitios}
                for f in as_completed(fs):
                    s_meta = fs[f]
                    devs = f.result()
                    BatteryService._dispositivos_cache[s_meta["station_name"]] = devs
                    # En modo global, filtramos estrictamente solo baterías (Litio y ZTE) para esta tabla
                    dispositivos_a_escanear.extend([d for d in devs if d["tipo_dispositivo"] in ["Litio", "ZTE"]])

        elif mode == 'rectifiers':
            # 2. Modo Rectificadores: Todos los rectificadores (de la caché si es posible)
            if not BatteryService._dispositivos_cache:
                # Si no hay caché, forzar un descubrimiento mínimo o esperar al global
                logging.warning("Caché vacía para rectificadores, esperando escaneo global.")
                return

            for devs in BatteryService._dispositivos_cache.values():
                dispositivos_a_escanear.extend([d for d in devs if d["tipo_dispositivo"] == "Rectificador"])

        else:
            # 3. Modo Priority: Solo sitios con alarma crítica
            conn = get_db_connection()
            sitios_alerta = []
            try:
                cur = conn.cursor()
                cur.execute("""
                    SELECT DISTINCT sitio FROM alarmas_activas 
                    WHERE estado = 'on' 
                    AND categoria IN ('AC_FAIL', 'BATERIA BAJA', 'AC_FAIL_GEN', 'AC FAIL (GEN)', 'AC FAIL', 'AC_FAIL_GE', 'AC_FAIL_GE')
                """)
                sitios_alerta = [r[0] for r in cur.fetchall()]
            except Exception as e:
                logging.error(f"Error Priority: {e}")
            finally: conn.close()

            if not sitios_alerta: return

            for s_name in sitios_alerta:
                try:
                    devs = BatteryService._dispositivos_cache.get(s_name)
                    # Usar caché de sitios para obtener la configuración (ip, cookies, etc)
                    s_config = next((s for s in BatteryService._sitios_cache if s["station_name"] == s_name), None)
                    
                    if not s_config:
                        # Si el caché está vacío (ej: reinicio reciente), intentamos reconstruirlo mínimamente
                        # para los sitios con alarmas actuales.
                        logging.warning(f"⚠️ Cache vacío para {s_name}. Intentando descubrimiento rápido...")
                        for sys_type, regions in CONFIG_REGIONES.items():
                            for reg, cfg in regions.items():
                                found = BatteryService.obtener_sitios(sys_type, reg, cfg)
                                if found:
                                    # Evitar duplicados en el caché de sitios
                                    sitios_existentes = {s["station_name"] for s in BatteryService._sitios_cache}
                                    BatteryService._sitios_cache.extend([s for s in found if s["station_name"] not in sitios_existentes])
                        
                        # Re-intentar buscar la config tras el descubrimiento
                        s_config = next((s for s in BatteryService._sitios_cache if s["station_name"] == s_name), None)

                    if not devs and s_config:
                        devs = BatteryService.obtener_dispositivos(s_config)
                        if devs:
                            BatteryService._dispositivos_cache[s_name] = devs
                    
                    if devs:
                        # En modo priority, incluimos TODOS los equipos del sitio (Bateria, Rectificador, Generador)
                        dispositivos_a_escanear.extend(devs)
                except Exception as e:
                    logging.error(f"Error procesando sitio prioritario {s_name}: {e}")

        if not dispositivos_a_escanear: return

        # Escaneo de Telemetría
        resultados = []
        with ThreadPoolExecutor(max_workers=100) as executor:
            fs = {executor.submit(BatteryService.obtener_valores, d): d for d in dispositivos_a_escanear}
            for f in as_completed(fs):
                res = f.result()
                if res: resultados.append(res)
        
        # Persistencia Multi-Tabla
        target_table = "battery_telemetry_global" if mode == "global" else "battery_telemetry"
        if mode == "rectifiers": target_table = "rectifier_telemetry"

        batch = []
        history_batch = []
        for r in resultados:
            v = r["valores"]
            
            # Caso Especial ZTE: Expandir a 4 baterías físicas si es Type 32
            if r["tipo_dispositivo"] == "ZTE":
                for i in range(1, 5):
                    soc_val = v.get(f'soc_{i}')
                    cur_val = v.get(f'cur_{i}')
                    
                    # Solo crear fila si hay datos para esta batería
                    if soc_val is not None or cur_val is not None:
                        # Lógica de Corriente ZTE (Usuario): Negativo = Descarga, Positivo = Carga
                        cur_val_num = float(cur_val or 0)
                        carga_val = cur_val_num if cur_val_num > 0 else 0
                        descarga_val = abs(cur_val_num) if cur_val_num < 0 else 0
                        
                        # En modo global solo guardamos SOC, Conexión y Capacidad
                        if mode == 'global':
                            carga_val, descarga_val, cur_val = None, None, None
                            v_volt, v_svolt = None, None
                        else:
                            v_volt, v_svolt = v.get("voltaje"), v.get("svoltage")

                        row = (
                            r["device_id"], f"Bateria ZTE {i}", r["sitio"], r["region"], r["tipo_sistema"], r["tipo_dispositivo"],
                            soc_val, carga_val, descarga_val, v_volt, v_svolt,
                            cur_val, 0, v.get("conexion"), v.get("capacidad"),
                            v.get("voltaje_gen"), v.get("corriente_gen"), now
                        )
                        batch.append(row)
            else:
                # Caso Estándar (Litio, Rectificador, Generador)
                soc_val = v.get("soc")
                carga_val = v.get("carga")
                descarga_val = v.get("descarga")
                volt_val = v.get("voltaje")
                svolt_val = v.get("svoltage")
                cur1_val = v.get("current1")
                cur2_val = v.get("current2")
                cap_val = v.get("capacidad")

                if mode == 'global':
                    # Solo baterías en global y solo SOC, Conexión, Capacidad
                    carga_val, descarga_val, volt_val, svolt_val, cur1_val, cur2_val = None, None, None, None, None, None

                row = (
                    r["device_id"], r["nombre"], r["sitio"], r["region"], r["tipo_sistema"], r["tipo_dispositivo"],
                    soc_val, carga_val, descarga_val, volt_val, svolt_val,
                    cur1_val, cur2_val, v.get("conexion"), cap_val,
                    v.get("voltaje_gen"), v.get("corriente_gen"), now
                )
                batch.append(row)
            
            
            if mode == "rectifiers":
                # Solo en modo rectifiers guardamos historial (cada 5m)
                history_batch.append(row[:-1]) # Sin el 'now' extra del update

        if batch:
            conn = get_db_connection()
            try:
                import psycopg2.extras
                with conn:
                    cur = conn.cursor()
                    if target_table == 'battery_telemetry_global':
                        # Insertar solo los campos simplificados
                        global_batch = []
                        for row in batch:
                            # row index: 0:did, 1:nom, 2:sit, 3:reg, 4:sys, 5:dtype, 6:soc, 7:carga, 8:desc, 9:volt, 10:svolt, 11:cur1, 12:cur2, 13:con, 14:cap, 15:vgen, 16:cgen, 17:now
                            global_batch.append((row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[13], row[14], row[17]))
                        
                        psycopg2.extras.execute_values(cur, f"""
                            INSERT INTO battery_telemetry_global
                            (device_id, nombre, sitio, region, tipo_sistema, tipo_dispositivo, 
                            soc, conexion, capacidad, ultimo_update)
                            VALUES %s
                            ON CONFLICT (device_id, nombre, sitio) DO UPDATE SET
                                soc = EXCLUDED.soc,
                                conexion = EXCLUDED.conexion,
                                capacidad = EXCLUDED.capacidad,
                                ultimo_update = EXCLUDED.ultimo_update
                        """, global_batch)
                    elif target_table == 'rectifier_telemetry':
                        # Insertar solo los campos de rectificador
                        rect_batch = []
                        for row in batch:
                            # row index: 0:did, 1:nom, 2:sit, 3:reg, 4:sys, 5:dtype, 9:volt, 10:svolt, 11:cur1, 12:cur2, 13:con, 17:now
                            rect_batch.append((row[0], row[1], row[2], row[3], row[4], row[5], row[9], row[10], row[11], row[12], row[13], row[17]))
                        
                        psycopg2.extras.execute_values(cur, f"""
                            INSERT INTO rectifier_telemetry
                            (device_id, nombre, sitio, region, tipo_sistema, tipo_dispositivo, 
                            voltaje, svoltage, current1, current2, conexion, ultimo_update)
                            VALUES %s
                            ON CONFLICT (device_id, nombre, sitio) DO UPDATE SET
                                voltaje = EXCLUDED.voltaje, svoltage = EXCLUDED.svoltage, 
                                current1 = EXCLUDED.current1, current2 = EXCLUDED.current2,
                                conexion = EXCLUDED.conexion, ultimo_update = EXCLUDED.ultimo_update
                        """, rect_batch)
                    else:
                        # Para battery_telemetry (Priority) se mantienen todos los campos
                        psycopg2.extras.execute_values(cur, f"""
                            INSERT INTO {target_table}
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

                    if history_batch:
                        # Filtrar history_batch para rectificadores
                        rect_hist_batch = []
                        for row in history_batch:
                            # row index: 0:did, 1:nom, 2:sit, 3:reg, 4:sys, 5:dtype, 9:volt, 10:svolt, 11:cur1, 12:cur2, 13:con
                            rect_hist_batch.append((row[0], row[1], row[2], row[3], row[4], row[5], row[9], row[10], row[11], row[12], row[13]))

                        psycopg2.extras.execute_values(cur, """
                            INSERT INTO rectifier_telemetry_history 
                            (device_id, nombre, sitio, region, tipo_sistema, tipo_dispositivo, 
                            voltaje, svoltage, current1, current2, conexion)
                            VALUES %s
                        """, rect_hist_batch)

                logging.info(f"✅ Escaneo {mode.upper()} guardado en {target_table} ({len(batch)} registros).")
            except Exception as e:
                logging.error(f"Error DB {mode}: {e}")
            finally: conn.close()

    @staticmethod
    def cleanup_history():
        """Elimina registros históricos de más de 30 días."""
        try:
            limit_date = datetime.now() - timedelta(days=30)
            execute_db("DELETE FROM rectifier_telemetry_history WHERE timestamp < %s", (limit_date,))
            logging.info("🧹 Limpieza de historial de baterías completada (retención 30 días).")
        except Exception as e:
            logging.error(f"Error en limpieza de historial: {e}")

    @staticmethod
    def start_battery_monitoring(app):
        """Inicia el hilo de monitoreo con frecuencias diferenciadas para 3 tablas."""
        def loop():
            BatteryService._init_db()
            last_global_scan = datetime.min
            last_rectifier_scan = datetime.min
            
            with app.app_context():
                while True:
                    try:
                        now = datetime.now()
                        
                        # 1. Escaneo Global cada 1 hora (Carga batería_telemetry_global)
                        if (now - last_global_scan) >= timedelta(hours=1):
                            BatteryService.sync_battery_data(app, mode='global')
                            last_global_scan = now
                        
                        # 2. Escaneo de Rectificadores cada 5 minutos (Carga rectifier_telemetry + history)
                        if (now - last_rectifier_scan) >= timedelta(minutes=5):
                            BatteryService.sync_battery_data(app, mode='rectifiers')
                            last_rectifier_scan = now

                        # 3. Escaneo de Prioridad cada 15 segundos (Carga battery_telemetry - alarmas)
                        BatteryService.sync_battery_data(app, mode='priority')
                            
                        # Limpieza de históricos a las 03:00 AM
                        if now.hour == 3 and now.minute == 0 and now.second < 20:
                            BatteryService.cleanup_history()
                            
                    except Exception as e:
                        logging.error(f"Error en loop de servicio de batería: {e}")
                    
                    time.sleep(15) # Ciclo base de 15 segundos
        
        thread = threading.Thread(target=loop, daemon=True)
        thread.start()
        logging.info("🚀 Hilo de BatteryService iniciado (Priority: 15s, Rect: 5m, Global: 1h).")
