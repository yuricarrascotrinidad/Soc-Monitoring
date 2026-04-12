import time
import json
import requests
import logging
import threading
import psycopg2
import psycopg2.extras
import cv2
import os
import asyncio
from datetime import datetime, timedelta
from urllib.parse import urlparse, urljoin
from concurrent.futures import ThreadPoolExecutor, as_completed

# Requests & urllib3 components
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

# App modules
from app.config import Config
from app.utils.db import get_db_connection, execute_db, query_db
from app.utils.constants import (
    CONFIG_REGIONES, REGLAS_EVENTOS, DATA_TEMPLATE, HEADERS, 
    ALARM_TEMPLATE_AC, SENSORES_INTERES, load_dynamic_tokens
)
from app.utils.helpers import (
    clasificar_evento_access, clasificar_evento_transport, 
    convertir_duracion, filtrar_eventos_generales, determinar_tipo_evento
)
from app.services.camera_service import CameraService
from app.services.email_service import EmailService
from app.services.login_service import LoginService
from app.services.hvac_service import HvacService

class AuthFailureException(Exception):
    """Excepción para indicar que el token ha fallado."""
    def __init__(self, segment, region, url_base):
        self.segment = segment
        self.region = region
        self.url_base = url_base
        super().__init__(f"Fallo de autenticación en {region} ({segment})")

class MonitoringService:
    # --- PROPIEDADES DE ESTADO Y LOCKS ---
    _cleanup_lock = threading.Lock()
    _last_cleanup = None
    _notif_cleanup_active = False
    
    # Protección contra hilos duplicados
    _monitoring_started = False
    _monitoring_lock = threading.Lock()
    
    _dashboard_lock = threading.Lock()
    _dashboard_state = None
    _last_dashboard_update = None
    _connection_errors = {}

    _http_session = None
    _http_session_lock = threading.Lock()

    # --- SECCIÓN 1: CONFIGURACIÓN, INICIALIZACIÓN Y SESIÓN ---

    @classmethod
    def _get_session(cls):
        """Retorna una sesión HTTP compartida con pool de conexiones (Thread-Safe)."""
        if cls._http_session is None:
            with cls._http_session_lock:
                if cls._http_session is None:
                    session = requests.Session()
                    adapter = HTTPAdapter(
                        pool_connections=50, 
                        pool_maxsize=150, 
                        max_retries=Retry(total=2, backoff_factor=0.5,status_forcelist=[500, 502, 503, 504])
                    )
                    session.mount('http://', adapter)
                    session.mount('https://', adapter)
                    cls._http_session = session
        return cls._http_session

    @staticmethod
    def _init_db_notifications():
        """Inicializa la tabla de historial de notificaciones y maneja migraciones."""
        try:
            execute_db("""
                CREATE TABLE IF NOT EXISTS notificaciones_enviadas (
                    sitio TEXT, tipo_sistema TEXT, tipo_evento TEXT,
                    resuelto_desde TIMESTAMP, ultimo_envio TIMESTAMP,
                    PRIMARY KEY (sitio, tipo_sistema)
                )
            """)
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'notificaciones_enviadas'")
            columns = [col[0] for col in cur.fetchall()]
            conn.close()
            if 'resuelto_desde' not in columns:
                execute_db("DROP TABLE IF EXISTS notificaciones_enviadas")
                execute_db("""
                    CREATE TABLE notificaciones_enviadas (
                        sitio TEXT, tipo_sistema TEXT, tipo_evento TEXT,
                        resuelto_desde TIMESTAMP, ultimo_envio TIMESTAMP,
                        PRIMARY KEY (sitio, tipo_sistema)
                    )
                """)
        except Exception as e:
            logging.error(f"Error inicializando DB: {e}")

    @staticmethod
    def start_monitoring_threads(app):
        """Inicia todos los hilos de monitoreo."""
        with MonitoringService._monitoring_lock:
            if MonitoringService._monitoring_started:
                logging.info("⚠️ El monitoreo ya está en ejecución. Saltando arranque de hilos.")
                return
            MonitoringService._monitoring_started = True

        MonitoringService._init_db_notifications()
        threads = [
            threading.Thread(target=MonitoringService.monitorear_tipo, args=(app, "access"), daemon=True),
            threading.Thread(target=MonitoringService.monitorear_tipo, args=(app, "transport"), daemon=True),
            threading.Thread(target=MonitoringService.monitorear_fallas_ac, args=(app,), daemon=True),
            threading.Thread(target=MonitoringService._refresh_dashboard_cache_loop, args=(app,), daemon=True),
            threading.Thread(target=MonitoringService.monitorear_telemetria_global, args=(app,), daemon=True)
        ]
        for t in threads: t.start()
        logging.info("🚀 Hilos de monitoreo iniciados.")

    # --- SECCIÓN 2: PETICIONES API (PEIM) ---

    @staticmethod
    def obtener_alarmas(url, cookies, template=None, region=None, db_type=None, headers_override=None):
        if template is None: template = DATA_TEMPLATE
        try:
            data = {"queryObjStr": json.dumps(template)}
            session = MonitoringService._get_session()
            hdrs = headers_override if headers_override else HEADERS
            with session.post(url, headers=hdrs, cookies=cookies, data=data, timeout=25) as r:
                if r.status_code in [401, 403]:
                    parsed = urlparse(url)
                    url_base = f"{parsed.scheme}://{parsed.netloc}"
                    for seg, regions in CONFIG_REGIONES.items():
                        for reg, cfg in regions.items():
                            if cfg["url"] == url: raise AuthFailureException(seg, reg, url_base)
                r.raise_for_status()
                response_text = r.text
                try: resp = r.json()
                except: resp = None

            is_login = False
            if resp:
                if not resp.get("success"):
                    msg = str(resp.get("msg", "")).lower()
                    if any(w in msg for w in ["login", "session", "sesión", "timeout", "autenticación", "expir", "unauthorized"]): is_login = True
            else:
                low = response_text.lower()
                if any(w in low for w in ["tbuser", "tbpass", "authimg", "identifycode"]) or 'location.href="./login"' in low or "login" in r.url.lower(): is_login = True
            
            if is_login:
                parsed = urlparse(url)
                url_base = f"{parsed.scheme}://{parsed.netloc}"
                with MonitoringService._http_session_lock:
                    session = MonitoringService._get_session()
                    domain = parsed.hostname
                    keys = [c.name for c in session.cookies if c.domain == domain]
                    for k in keys: session.cookies.set(k, None, domain=domain)
                for seg, regions in CONFIG_REGIONES.items():
                    for reg, cfg in regions.items():
                        if cfg["url"] == url: raise AuthFailureException(seg, reg, url_base)
            
            if resp and resp.get("success"):
                error_key = f"{db_type}:{region}" if region else url
                MonitoringService._connection_errors[error_key] = None
                return resp["info"]["data"]
        except AuthFailureException: raise
        except Exception as e:
            error_key = f"{db_type}:{region}" if region else url
            MonitoringService._connection_errors[error_key] = str(e)
            logging.error(f"Error alarmas {region}: {e}")
            return None
        return []

    @staticmethod
    def obtener_valores_dispositivo(ip, device_id, cookies_base):
        url = f"http://{ip}:8090/peim/request/realtime/getMeteValue"
        cookies = cookies_base.copy()
        # Cookies completas según script validado del usuario
        cookies.update({
            "loginUser": "noc_reports",
            "contextPath": "/peim",
            "language": "es_ES",
            "proversion": "null",
            "sessionUser": "%7B%22retUrl%22%3A%22/peim/views/default_design%22%2C%22fr_use%22%3A%221%22%2C%22user_name%22%3A%22noc_reports%22%2C%22proversion%22%3Anull%2C%22operate_id%22%3A%221%2C2%2C3%2C4%2C5%2C6%2C7%2C8%2C9%2C10%22%2C%22isAdmin%22%3A%22false%22%2C%22userid%22%3A%2200001001000000000047%22%2C%22username%22%3A%22noc_reports%22%7D"
        })
        # Headers específicos por IP
        hdrs = dict(HEADERS)
        hdrs["Host"] = f"{ip}:8090"
        hdrs["Origin"] = f"http://{ip}:8090"
        hdrs["Referer"] = f"http://{ip}:8090/peim/main/realtime/realtimedevice.html"
        valores = {'soc': None, 'carga': None, 'descarga': None, 'voltaje': None, 'svoltage': None, 'current1': None, 'current2': None, 'conexion': None, 'voltaje_gen': None, 'corriente_gen': None}
        for i in range(1, 5): valores[f'soc_{i}'], valores[f'cur_{i}'] = None, None
        payload = f"device_id={device_id}&is_manual=0"
        try:
            session = MonitoringService._get_session()
            with session.post(url, headers=hdrs, cookies=cookies, data=payload, timeout=25) as resp:
                resp.raise_for_status()
                sensores = resp.json()
            for s in sensores:
                mid, mval = s.get("meteId", ""), s.get("meteValue")
                mid = str(mid).strip()
                
                from app.utils.constants import SENSORES_INTERES
                field = SENSORES_INTERES.get(mid)

                if field:
                    try:
                        val = float(mval) if mval else None
                        if val is not None and field == "conexion":
                            val = int(val)
                        if field in valores and valores[field] is None:
                            valores[field] = val
                    except: pass
            
            return valores
        except Exception as e:
            logging.error(f"Error telemetria {device_id}: {e}")
            return valores

    @staticmethod
    def _extraer_bateria_de_item(item):
        """Extrae info de batería o rectificador de un nodo del árbol de dispositivos."""
        dtype = str(item.get("device_type"))
        if dtype == "47":  # Litio
            extend_props = {}
            try:
                if item.get("extend_props"):
                    extend_props = json.loads(item.get("extend_props", "{}"))
            except: pass
            return {"device_id": item.get("device_id"), "device_name": item.get("device_name", "Batería de Litio"), "type": "litio", "extend_props": extend_props}
        elif dtype == "32":  # ZTE
            return {"device_id": item.get("device_id"), "device_name": item.get("device_name", "Batería ZTE"), "type": "zte", "extend_props": {}}
        elif dtype in ["6", "8"]:  # Rectificadores
            return {"device_id": item.get("device_id"), "device_name": item.get("device_name", "Rectificador"), "type": "rectificador", "extend_props": {}}
        elif dtype == "5":  # Generador
            return {"device_id": item.get("device_id"), "device_name": item.get("device_name", "Grupo Electrógeno"), "type": "generador", "extend_props": {}}
        return None

    @staticmethod
    def buscar_baterias_en_precinto(ip, cookies, precinct_id):
        url = f"http://{ip}:8090/peim/request/region/getDeviceTree"
        hdrs = dict(HEADERS)
        hdrs["Host"] = f"{ip}:8090"
        hdrs["Referer"] = f"http://{ip}:8090/peim/main/realtime/realtimemanage.html"
        base_params = {"tree_type": 0, "node_type_show": 3, "_": int(time.time() * 1000)}
        baterias = []
        try:
            session = MonitoringService._get_session()
            # Nivel 1: hijos directos del precinto
            params = {**base_params, "id": precinct_id}
            with session.get(url, headers=hdrs, cookies=cookies, params=params, timeout=30) as resp:
                resp.raise_for_status()
                data = resp.json()
                if not data.get("success"): return []
                for item in data.get("info", []):
                    dtype = str(item.get("device_type"))
                    bat = MonitoringService._extraer_bateria_de_item(item)
                    if bat:
                        baterias.append(bat)
                    
                    if dtype == "38" and "SNMP" in str(item.get("device_name", "")):
                        # ZTE: buscar type=32 dentro del SNMP
                        pz = {**base_params, "id": item["device_id"]}
                        with session.get(url, headers=hdrs, cookies=cookies, params=pz, timeout=20) as rz:
                            if rz.status_code == 200:
                                dz = rz.json()
                                if dz.get("success"):
                                    for iz in dz.get("info", []):
                                        b = MonitoringService._extraer_bateria_de_item(iz)
                                        if b: baterias.append(b)
                    elif dtype in ["6", "8"]:
                        # FSU/Rectificador: buscar baterías anidadas (caso transport)
                        pf = {**base_params, "id": item["device_id"]}
                        try:
                            with session.get(url, headers=hdrs, cookies=cookies, params=pf, timeout=30) as rf:
                                if rf.status_code == 200:
                                    df = rf.json()
                                    if df.get("success"):
                                        for if_ in df.get("info", []):
                                            b = MonitoringService._extraer_bateria_de_item(if_)
                                            if b: baterias.append(b)
                        except Exception: pass  # Timeout en FSU no aborta búsqueda
                    elif dtype == "5":
                        # Generador directo
                        bat = MonitoringService._extraer_bateria_de_item(item)
                        if bat: baterias.append(bat)
        except Exception as e:
            logging.error(f"Error buscando baterias {precinct_id}: {e}")
        return baterias

    # --- SECCIÓN 3: OPERACIONES DE BASE DE DATOS Y SINCRONIZACIÓN ---

    @staticmethod
    def guardar_alarmas(db_type, alarmas, region, is_ac=False, source='general'):
        conn = get_db_connection()
        try:
            cf = clasificar_evento_access if db_type == "access" else clasificar_evento_transport
            CSL = {'AC_FAIL', 'BATERIA BAJA', 'BATERIA', 'Bateria Lit. disc.'}
            AHORA = datetime.now()
            CATEGORIAS_REINICIO = {'AC_FAIL', 'BATERIA BAJA', 'Bateria Lit. disc.'}
            with conn:
                cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                
                # Identificar sitios que ya tienen alarmas de descarga activas (globalmente)
                cur.execute("SELECT DISTINCT sitio FROM alarmas_activas WHERE categoria IN %s", (tuple(CATEGORIAS_REINICIO),))
                sitios_con_descarga_registrada = {r['sitio'] for r in cur.fetchall()}

                # Seleccionar solo alarmas pertenecientes al 'source' actual para sincronización local
                cur.execute("SELECT * FROM alarmas_activas WHERE tipo=%s AND region=%s AND source=%s", (db_type, region, source))
                rows = cur.fetchall()
                activas = {}
                for a in rows:
                    # Normalizar hora y device_id para comparación consistente
                    h_str = a['hora'].strftime("%Y-%m-%d %H:%M:%S") if isinstance(a['hora'], datetime) else str(a['hora'])
                    did = str(a['device_id']).strip().zfill(16) if a['device_id'] else ""
                    # CLAVE EXPANDIDA: sitio, alarma, hora, device_id para evitar colisiones y limpieza incompleta
                    activas[(a['sitio'], a['alarma'], h_str, did)] = a
                
                batch_nuevas, para_en_limbo = [], set()
                sitios_a_reiniciar = set()
                
                for a in alarmas:
                    s, alm, h = a["station_name"], a["alarm_name"], a["alarm_time"]
                    did_new = str(a.get("device_id", "")).strip().zfill(16)
                    
                    if is_ac: cat = 'AC_FAIL'
                    else: cat = cf(a)
                    
                    # Lógica de reinicio: Si entra una categoría de descarga y el sitio no tenía una previa
                    if cat in CATEGORIAS_REINICIO and s not in sitios_con_descarga_registrada:
                        sitios_a_reiniciar.add(s)

                    key = (s, alm, h, did_new)
                    para_en_limbo.add(key)
                    dur = convertir_duracion(a.get("alarm_span_time", ""))
                    batch_nuevas.append((db_type, region, h, dur, s, alm, a.get("device_name", ""), a.get("precinct_id", ""), a.get("mete_name", ""), cat, 'on', did_new, a.get("valor"), None, source))

                # Ejecutar borrado de telemetría para los nuevos ingresos a estado de descarga
                if sitios_a_reiniciar:
                    for s in sitios_a_reiniciar:
                        # logging.info(f"⚡ Nueva alarma crítica detectada para {s}. Reiniciando telemetría de baterías.")
                        cur.execute("DELETE FROM battery_telemetry WHERE sitio = %s", (s,))

                fh_hist, fh_limbo = [], []
                for key, data in activas.items():
                    if key not in para_en_limbo:
                        if data['estado'] == 'limbo':
                            if data['limbo_desde'] and (AHORA - data['limbo_desde']).total_seconds() > 120: fh_hist.append(data)
                        else:
                            if data['categoria'] in CSL: fh_hist.append(data)
                            else: fh_limbo.append(data)

                if fh_hist:
                    rh = [(d['tipo'], d['region'], d['hora'], d['duracion'], d['sitio'], d['alarma'], d['devicename'], d['precinct_id'], d['mete_name'], d['categoria'], 'off', d['device_id'], d['valor'], d['source']) for d in fh_hist]
                    cur.executemany("INSERT INTO alarmas_historicas (tipo, region, hora, duracion, sitio, alarma, deviceName, precinct_id, mete_name, categoria, estado, device_id, valor, source) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", rh)
                    cur.execute("DELETE FROM alarmas_activas WHERE id IN %s", (tuple(d['id'] for d in fh_hist),))

                if fh_limbo: cur.execute("UPDATE alarmas_activas SET estado='limbo', limbo_desde=%s WHERE id IN %s", (AHORA, tuple(d['id'] for d in fh_limbo)))

                if batch_nuevas:
                    cur.executemany("""
                        INSERT INTO alarmas_activas (tipo, region, hora, duracion, sitio, alarma, deviceName, precinct_id, mete_name, categoria, estado, device_id, valor, limbo_desde, source)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (tipo, region, hora, sitio, alarma, device_id) 
                        DO UPDATE SET duracion=EXCLUDED.duracion, estado='on', limbo_desde=NULL, valor=EXCLUDED.valor, source=EXCLUDED.source, categoria=EXCLUDED.categoria
                    """, batch_nuevas)

        except Exception as e:
            logging.error(f"Error guardando alarmas: {e}")
            conn.rollback()
        finally: conn.close()
    @staticmethod
    def actualizar_telemetria_bateria_batch(batch_data):
        if not batch_data: return
        # Deduplicar por (device_id, nombre, sitio) – evita error ON CONFLICT cuando
        # la misma batería aparece por dos rutas del árbol (nivel1 y dentro del FSU)
        seen = {}
        for row in batch_data:
            key = (row[0], row[5], row[6])  # device_id, sitio, nombre
            seen[key] = row
        batch_data = list(seen.values())
        for row in batch_data:
            if "Rectificad" in str(row[6]) or row[8] is not None:
                logging.debug(f"[DEBUG_TEL] ID: {row[0]} | Name: {row[6]} | Svolt: {row[8]}")
        conn = get_db_connection()
        try:
            with conn:
                cur = conn.cursor()
                psycopg2.extras.execute_values(cur, """
                    INSERT INTO battery_telemetry 
                    (device_id, soc, carga, descarga, ultimo_update, sitio, nombre,
                     voltaje, svoltage, current1, current2, conexion)
                    VALUES %s
                    ON CONFLICT (device_id, nombre, sitio) DO UPDATE SET
                        soc = EXCLUDED.soc,
                        carga = EXCLUDED.carga,
                        descarga = EXCLUDED.descarga,
                        voltaje = EXCLUDED.voltaje,
                        svoltage = EXCLUDED.svoltage,
                        current1 = EXCLUDED.current1,
                        current2 = EXCLUDED.current2,
                        conexion = EXCLUDED.conexion,
                        ultimo_update = EXCLUDED.ultimo_update
                """, batch_data)
                
        except Exception as e: logging.error(f"Error UPSERT batch: {e}")
        finally: conn.close()

    @staticmethod
    def actualizar_telemetria_bateria(device_id, valores, sitio=None, nombre=None):
        MonitoringService.actualizar_telemetria_bateria_batch([(device_id, valores, sitio, nombre)])

    @staticmethod
    def _procesar_telemetria_dispositivo(device_id, valores, sitio, nombre, device_type=None, categoria=None):
        """Procesa la telemetría según el tipo de dispositivo (basado en el nuevo script del usuario)."""
        now = datetime.now()
        
        # Intentar detectar tipo si es None
        if device_type is None:
            if any(valores.get(f'soc_{i}') is not None for i in range(1, 5)): device_type = 32
            elif valores.get('soc') is not None: device_type = 47
            else: device_type = 8 # Default a rectificador si tiene voltajes

        if device_type == 47:  # Litio
            return [(
                device_id, valores.get("soc"), valores.get("carga"), valores.get("descarga"),
                now, sitio, nombre, None, None, None, None, valores.get("conexion")
            )]
        elif device_type == 32:  # ZTE (No colapsar, guardar bancos independientes)
            rows = []
            conexion = valores.get("conexion")
            for i in range(1, 5):
                soc_val = valores.get(f'soc_{i}')
                cur_val = valores.get(f'cur_{i}')
                # Si existe SOC o Corriente para el banco i, crear registro independiente
                if soc_val is not None or cur_val is not None:
                    rows.append((
                        device_id, soc_val, None, None, now, sitio, f"Bateria ZTE {i}",
                        None, None, cur_val, None, conexion
                    ))
            
            # Si no se encontraron bancos pero hay señal de conexión, mantener un registro base
            if not rows and conexion is not None:
                rows.append((
                    device_id, None, None, None, now, sitio, nombre,
                    None, None, None, None, conexion
                ))
            return rows
        else:  # Rectificador (8 o 6) o Generador
            v_final = valores.get("voltaje")
            c_gen = None
            # Si es Grupo Electrógeno (Type 5) o por nombre o categoría de alarma AC_FAIL_GE
            if str(device_type) == "5" or (nombre and 'Grupo Electrógeno' in nombre) or categoria == 'AC_FAIL_GE':
                v_final = valores.get("voltaje_gen")
                c_gen = valores.get("corriente_gen")
            
            return [(
                device_id, None, c_gen, None, now, sitio, nombre,
                v_final, valores.get("svoltage"), valores.get("current1"), valores.get("current2"), valores.get("conexion")
            )]

    @staticmethod
    def cleanup_db():
        """Limpia periódicamente la tabla de alarmas_historicas de forma segura (batch deletion)."""
        with MonitoringService._cleanup_lock:
            now = datetime.now()
            # Frecuencia mínima: 1 hora para evitar colisiones excesivas
            if MonitoringService._last_cleanup and (now - MonitoringService._last_cleanup).total_seconds() < 3600:
                return
            
            conn = get_db_connection()
            try:
                cur = conn.cursor()
                limit_date = now - timedelta(days=7)
                
                # Borrado en lotes pequeños para evitar deadlocks y bloqueos masivos
                # Borramos hasta 5000 registros por ciclo (10 lotes de 500)
                for _ in range(10):
                    cur.execute("""
                        DELETE FROM alarmas_historicas 
                        WHERE id IN (
                            SELECT id FROM alarmas_historicas 
                            WHERE hora < %s 
                            LIMIT 500
                        )
                    """, (limit_date,))
                    
                    if cur.rowcount == 0:
                        break
                    conn.commit()
                    time.sleep(0.1) # Breve pausa para dejar respirar a la DB
                
                MonitoringService._last_cleanup = now
            except Exception as e:
                # Si hay un deadlock o error de bloqueo, simplemente reintentamos en el próximo ciclo
                msg = str(e).lower()
                if "deadlock" in msg or "lock" in msg:
                    logging.debug("PostgreSQL: Salto de cleanup por bloqueo/deadlock (se reintentará)")
                else:
                    logging.error(f"Error cleanup: {e}")
                if conn: conn.rollback()
            finally:
                if conn: conn.close()

    # --- SECCIÓN 4: BUCLES DE MONITOREO (THREADS) ---

    @staticmethod
    def monitorear_tipo(app, db_type):
        logging.info(f"Iniciando monitoreo {db_type}...")
        with app.app_context():
            while True:
                try:
                    load_dynamic_tokens()
                    any_success = False
                    if db_type in CONFIG_REGIONES:
                        for region, cfg in CONFIG_REGIONES[db_type].items():
                            try: alarmas = MonitoringService.obtener_alarmas(cfg["url"], cfg["cookies"], region=region, db_type=db_type)
                            except AuthFailureException as ae:
                                token = asyncio.run(LoginService().refresh_token(ae.segment, ae.region, ae.url_base))
                                if token:
                                    cfg["cookies"]["PEIMWEBID"] = token
                                    alarmas = MonitoringService.obtener_alarmas(cfg["url"], cfg["cookies"], region=region, db_type=db_type)
                                else: alarmas = None
                            if alarmas is not None:
                                any_success = True
                                MonitoringService.guardar_alarmas(db_type, alarmas, region, is_ac=False, source='general')
                        if any_success:
                            eventos = MonitoringService.obtener_eventos_cumplidos(db_type)
                            sitios = [e["sitio"] for e in eventos]
                            conn = get_db_connection()
                            try:
                                with conn:
                                    cur = conn.cursor()
                                    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    if sitios:
                                        p = ', '.join(['%s'] * len(sitios))
                                        cur.execute(f"UPDATE notificaciones_enviadas SET resuelto_desde=%s WHERE tipo_sistema=%s AND resuelto_desde IS NULL AND sitio NOT IN ({p})", (now_str, db_type, *sitios))
                                        cur.execute(f"UPDATE notificaciones_enviadas SET resuelto_desde=NULL WHERE tipo_sistema=%s AND sitio IN ({p})", (db_type, *sitios))
                                    else: cur.execute("UPDATE notificaciones_enviadas SET resuelto_desde=%s WHERE tipo_sistema=%s AND resuelto_desde IS NULL", (now_str, db_type))
                                    lim = (datetime.now() - timedelta(seconds=60)).strftime("%Y-%m-%d %H:%M:%S")
                                    cur.execute("DELETE FROM notificaciones_enviadas WHERE tipo_sistema=%s AND resuelto_desde IS NOT NULL AND resuelto_desde < %s", (db_type, lim))
                            except: pass
                            finally: conn.close()
                            MonitoringService.procesar_nuevos_eventos(eventos, db_type)
                except Exception as e: logging.error(f"Error {db_type}: {e}")
                if MonitoringService._last_cleanup is None or (datetime.now() - MonitoringService._last_cleanup).total_seconds() > 1800: MonitoringService.cleanup_db()
                time.sleep(15)

    @staticmethod
    def monitorear_fallas_ac(app):
        logging.info("Iniciando monitoreo AC...")
        with app.app_context():
            while True:
                try:
                    load_dynamic_tokens()
                    for dt in ["access", "transport"]:
                        if dt in CONFIG_REGIONES:
                            for reg, cfg in CONFIG_REGIONES[dt].items():
                                url, cookies = cfg["url"], cfg["cookies"].copy()
                                ip = urlparse(url).hostname
                                # Cookies exactas según script validado del usuario
                                cookies.update({
                                    "loginUser": "noc_reports",
                                    "contextPath": "/peim",
                                    "language": "es_ES",
                                    "proversion": "null",
                                    "sessionUser": "%7B%22retUrl%22%3A%22/peim/views/default_design%22%2C%22fr_use%22%3A%221%22%2C%22user_name%22%3A%22noc_reports%22%2C%22proversion%22%3Anull%2C%22operate_id%22%3A%221%2C2%2C3%2C4%2C5%2C6%2C7%2C8%2C9%2C10%22%2C%22isAdmin%22%3A%22false%22%2C%22userid%22%3A%2200001001000000000047%22%2C%22username%22%3A%22noc_reports%22%7D"
                                })
                                # Headers específicos por IP (como en el script validado)
                                headers_ac = dict(HEADERS)
                                headers_ac["Host"] = f"{ip}:8090"
                                headers_ac["Origin"] = f"http://{ip}:8090"
                                headers_ac["Referer"] = f"http://{ip}:8090/peim/main/alarm/alarmlistmerge.html"
                                try:
                                    try: alarmas = MonitoringService.obtener_alarmas(url, cookies, ALARM_TEMPLATE_AC, headers_override=headers_ac)
                                    except AuthFailureException as ae:
                                        token = asyncio.run(LoginService().refresh_token(ae.segment, ae.region, ae.url_base))
                                        if token:
                                            cookies["PEIMWEBID"] = token; cfg["cookies"]["PEIMWEBID"] = token
                                            alarmas = MonitoringService.obtener_alarmas(url, cookies, ALARM_TEMPLATE_AC, headers_override=headers_ac)
                                        else: alarmas = None
                                    if alarmas is not None:
                                        proc = []
                                        for a in alarmas:
                                            try: a["valor"] = float(a.get("meteValue"))
                                            except:
                                                v = MonitoringService.obtener_valores_dispositivo(ip, a.get("device_id"), cookies)
                                                a["valor"] = v.get("voltaje")
                                            proc.append(a)
                                        MonitoringService.guardar_alarmas(dt, proc, reg, is_ac=True, source='ac')
                                except Exception as e: logging.error(f"Error AC {reg}: {e}")
                except Exception as e: logging.error(f"Error AC general: {e}")
                time.sleep(10)

    @staticmethod
    def _enriquecer_cookies(cookies_base):
        """Enriquece las cookies base con los valores del script validado."""
        c = cookies_base.copy()
        c.update({
            "loginUser": "noc_reports",
            "contextPath": "/peim",
            "language": "es_ES",
            "proversion": "null",
            "sessionUser": "%7B%22retUrl%22%3A%22/peim/views/default_design%22%2C%22fr_use%22%3A%221%22%2C%22user_name%22%3A%22noc_reports%22%2C%22proversion%22%3Anull%2C%22operate_id%22%3A%221%2C2%2C3%2C4%2C5%2C6%2C7%2C8%2C9%2C10%22%2C%22isAdmin%22%3A%22false%22%2C%22userid%22%3A%2200001001000000000047%22%2C%22username%22%3A%22noc_reports%22%7D"
        })
        return c

    @staticmethod
    def _telemetria_sitio_ac(sitio, precinct_id, tipo_sistema, region):
        """
        Para un sitio con AC_FAIL, busca las baterías en el precinto
        (tipo 47 litio, tipo 32 ZTE) y obtiene su telemetría.
        Igual que el script validado del usuario.
        """
        cfg = CONFIG_REGIONES.get(tipo_sistema, {}).get(region)
        if not cfg: return []
        ip = urlparse(cfg["url"]).hostname
        cookies = MonitoringService._enriquecer_cookies(cfg["cookies"])
        batch = []
        # Buscar baterías en el precinto
        baterias = MonitoringService.buscar_baterias_en_precinto(ip, cookies, precinct_id)
        for bat in baterias:
            did = str(bat["device_id"]).strip().zfill(16)
            vals = MonitoringService.obtener_valores_dispositivo(ip, did, cookies)
            if vals:
                # Determinar dtype para el procesamiento
                if bat.get("type") == "litio": 
                    dtype = 47
                elif bat.get("type") == "zte": 
                    dtype = 32
                elif bat.get("type") == "generador":
                    dtype = 5
                else: 
                    dtype = 8  # Rectificadores (6 o 8)
                
                batch.extend(MonitoringService._procesar_telemetria_dispositivo(did, vals, sitio, bat["device_name"], dtype))
        return batch

    @staticmethod
    def monitorear_telemetria_global(app):
        logging.info("🔋 Telemetria global...")
        with app.app_context():
            while True:
                try:
                    start = time.time()
                    conn = get_db_connection()
                    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                    # Para AC_FAIL: recuperar por precinct_id (para buscar baterías)
                    cur.execute("""
                        SELECT DISTINCT ON (sitio, tipo, region) sitio, region, precinct_id, device_id, devicename as nombre, tipo as tipo_sistema
                        FROM alarmas_activas
                        WHERE estado = 'on' AND categoria IN ('AC_FAIL', 'AC_FAIL_GE')
                        ORDER BY sitio, tipo, region, hora DESC
                    """)
                    ac_sites = cur.fetchall()

                    # Para otras categorías y Rectificadores (AC_FAIL/GE): usar device_id directamente
                    cur.execute("""
                        SELECT DISTINCT sitio, region, device_id, devicename as nombre, tipo as tipo_sistema, categoria
                        FROM alarmas_activas
                        WHERE estado = 'on'
                        AND (
                            categoria IN ('Bateria Lit. disc.', 'BATERIA BAJA', 'AC_FAIL', 'AC_FAIL_GE')
                            OR (devicename LIKE '%%ZTE%%' OR alarma LIKE '%%ZTE%%')
                        )
                    """)
                    other_devs = cur.fetchall()
                    conn.close()

                    batch = []

                    # --- Telemetría AC_FAIL: buscar baterías por precinto ---
                    with ThreadPoolExecutor(max_workers=20) as ex:
                        fs = {
                            ex.submit(
                                MonitoringService._telemetria_sitio_ac,
                                d['sitio'], d['precinct_id'], d['tipo_sistema'], d['region']
                            ): d['sitio']
                            for d in ac_sites if d.get('precinct_id')
                        }
                        for f in as_completed(fs):
                            try:
                                result = f.result(timeout=60)
                                batch.extend(result)
                            except Exception as e:
                                logging.debug(f"Error telemetria AC site {fs[f]}: {e}")

                    # --- Telemetría otras categorías: device_id directo ---
                    for i in range(0, len(other_devs), 200):
                        chunk = other_devs[i : i + 200]
                        with ThreadPoolExecutor(max_workers=20) as ex:
                            fs = {}
                            for d in chunk:
                                did = str(d['device_id']).strip().zfill(16)
                                cfg = CONFIG_REGIONES.get(d['tipo_sistema'], {}).get(d['region'])
                                if cfg:
                                    ip = urlparse(cfg["url"]).hostname
                                    cookies_tel = MonitoringService._enriquecer_cookies(cfg["cookies"])
                                    f = ex.submit(MonitoringService.obtener_valores_dispositivo, ip, did, cookies_tel)
                                    fs[f] = (did, d['sitio'], d['nombre'], d.get('device_type'), d['categoria'])
                            for f in as_completed(fs):
                                did, sit, nom, dtype, cat = fs[f]
                                try:
                                    r = f.result(timeout=30)
                                    if r: batch.extend(MonitoringService._procesar_telemetria_dispositivo(did, r, sit, nom, dtype, cat))
                                except: pass
                        if i + 100 < len(other_devs): time.sleep(0.5)
                    if batch:
                        MonitoringService.actualizar_telemetria_bateria_batch(batch)
                        logging.info(f"✅ Telemetria: {len(batch)} registros en {time.time()-start:.1f}s")
                except Exception as e: logging.error(f"Error telemetria global: {e}")
                time.sleep(30)

    # --- SECCIÓN 5: PROCESAMIENTO DE EVENTOS Y NOTIFICACIONES ---

    @staticmethod
    def procesar_nuevos_eventos(eventos_cumplidos, tipo_sistema):
        if not eventos_cumplidos:
            return

        ahora = datetime.now()
        from app.services.email_service import EmailService

        for evento in eventos_cumplidos:
            sitio = evento["sitio"]
            try:
                eventos_lista = evento["eventos"]
                tipo = evento["tipo"]
                tipo_evento = determinar_tipo_evento(eventos_lista)
                
                # --- LÓGICA FAIL-CLOSED: Verificar e Insertar en un solo bloque ---
                debe_proceder = False
                conn = None
                try:
                    conn = get_db_connection()
                    cur = conn.cursor()
                    cur.execute(
                        "SELECT 1 FROM notificaciones_enviadas WHERE sitio=%s AND tipo_sistema=%s", 
                        (sitio, tipo_sistema)
                    )
                    if cur.fetchone():
                        # Ya notificado
                        conn.close()
                        continue
                    
                    # No notificado: Marcar inmediatamente para bloquear (Fail-Closed)
                    cur.execute("""
                        INSERT INTO notificaciones_enviadas (sitio, tipo_sistema, tipo_evento, resuelto_desde, ultimo_envio)
                        VALUES (%s, %s, %s, NULL, %s)
                    """, (sitio, tipo_sistema, tipo_evento, ahora))
                    conn.commit()
                    debe_proceder = True
                except Exception as e:
                    # En caso de ERROR (DB bloqueada, etc), NO enviamos para evitar duplicados
                    logging.warning(f"DB Bloqueada o error para {sitio}. Saltando notificación por seguridad: {e}")
                    debe_proceder = False
                finally:
                    if conn: conn.close()

                if not debe_proceder:
                    continue

                # --- PROCESO DE CAPTURA Y ENVÍO (Solo si el bloqueo en DB fue exitoso) ---
                imagenes_dict = {}
                if tipo == "access":
                    if CameraService.has_camera(sitio, "access"):
                        img = CameraService.capture_snapshot(sitio, "access", "principal")
                        imagenes_dict["principal"] = img
                else: # transport
                     cameras = CameraService.get_transport_cameras_for_site(sitio)
                     for pos in cameras:
                         img = CameraService.capture_snapshot(sitio, "transport", pos)
                         imagenes_dict[pos] = img
                
                # Configurar estilos
                if tipo == "transport":
                    color_borde = "#dc3545"
                    icono_sistema = "🚚"
                    nivel_alerta = "CRÍTICO"
                else:
                    color_borde = "#ffc107"
                    icono_sistema = "🚪"
                    nivel_alerta = "ALERTA"
                
                asunto = f"{icono_sistema} {nivel_alerta} - {sitio} - {tipo_evento}"
                cuerpo = f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; border-left: 4px solid {color_borde}; padding-left: 20px;">
                    <div style="margin-bottom: 25px;">
                        <h1 style="color: {color_borde}; margin-bottom: 5px; font-size: 24px;">
                            {icono_sistema} Alerta de Seguridad SOC
                        </h1>
                        <div style="background-color: #f8f9fa; padding: 10px 15px; border-radius: 5px;">
                            <strong>Sitio:</strong> {sitio}<br>
                            <strong>Nivel:</strong> <span style="color: {color_borde}; font-weight: bold;">{nivel_alerta}</span>
                        </div>
                    </div>
                    <div style="margin-bottom: 25px; background-color: #fff3cd; padding: 15px; border-radius: 5px;">
                        <h3 style="margin: 0; color: #856404;">Eventos Detectados</h3>
                        <p>{', '.join(eventos_lista)}</p>
                    </div>
                    <!-- EVENTOS DETECTADOS -->
                    <div style="margin-top: 30px; font-size: 12px; color: #6c757d;">
                        Mensaje automático del Sistema SOC - {ahora.strftime('%Y-%m-%d %H:%M:%S')}
                    </div>
                </div>
                """
                
                logging.debug(f"Enviando alerta para {sitio} ({tipo_evento})")
                EmailService.enviar_alerta_email(asunto, cuerpo, imagenes_dict, sitio, tipo_evento)

            except Exception as e:
                logging.error(f"Error procesando evento {sitio}: {e}")

    @staticmethod
    def obtener_eventos_cumplidos(db_type):
        reglas = REGLAS_EVENTOS[db_type]
        conn = get_db_connection()
        try:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            limite = (datetime.now() - timedelta(hours=25)).strftime("%Y-%m-%d %H:%M:%S")
            cur.execute("SELECT * FROM alarmas_activas WHERE tipo = %s AND hora >= %s", (db_type, limite))
            filas = cur.fetchall()
        finally: conn.close()
        sitios = {}
        for f in filas:
            s = f['sitio']
            sitios.setdefault(s, {"cat": set(), "max_h": "0000"})
            sitios[s]["cat"].add(f['categoria'])
            ts = f['hora'].strftime("%Y-%m-%d %H:%M:%S"); 
            if ts > sitios[s]["max_h"]: sitios[s]["max_h"] = ts
        res = []
        for s, d in sitios.items():
            evs = [ev for ev, req in reglas.items() if req.issubset(d["cat"])]
            evs = filtrar_eventos_generales(evs, reglas)
            if evs:
                if db_type == "transport":
                    tc = CameraService.get_transport_cameras_for_site(s)
                    info = {"has_camera": len(tc) > 0, "cameras": tc, "available_positions": list(tc.keys())}
                else: info = {"has_camera": CameraService.has_camera(s, "access")}
                res.append({"sitio": s, "eventos": evs, "tipo": db_type, "cameras": info, "ultima_hora": d["max_h"]})
        return res

    # --- SECCIÓN 6: DASHBOARD Y ESTADO EN CACHÉ ---

    @staticmethod
    def get_cached_dashboard_state():
        with MonitoringService._dashboard_lock: return MonitoringService._dashboard_state

    @staticmethod
    def _refresh_dashboard_cache_loop(app):
        with app.app_context():
            contador = 0
            while True:
                try:
                    inc = (contador % 10 == 0)
                    new = MonitoringService._calculate_dashboard_state(inc)
                    with MonitoringService._dashboard_lock:
                        if not inc and MonitoringService._dashboard_state:
                            new['access']['anomalias'] = MonitoringService._dashboard_state['access']['anomalias']
                            new['transport']['anomalias'] = MonitoringService._dashboard_state['transport']['anomalias']
                        MonitoringService._dashboard_state = new
                        MonitoringService._last_dashboard_update = datetime.now()
                    contador += 1; time.sleep(3)
                except Exception as e: logging.error(f"Error loop cache: {e}"); time.sleep(5)

    @staticmethod
    def _calculate_dashboard_state(include_anomalias=True):
        acc, tra = MonitoringService.obtener_datos_completos_v2("access", include_anomalias), MonitoringService.obtener_datos_completos_v2("transport", include_anomalias)
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT site, ip FROM access_cameras"); acam = [{"site": r[0], "ip": r[1]} for r in cur.fetchall()]
            cur.execute("SELECT site, position, ip FROM transport_cameras"); tcam = [{"site": r[0], "position": r[1], "ip": r[2]} for r in cur.fetchall()]
            cur.execute("SELECT COUNT(DISTINCT sitio) FROM alarmas_activas WHERE estado = 'on' AND categoria = 'AC_FAIL'"); ac_c = cur.fetchone()[0]
            cur.execute("SELECT COUNT(DISTINCT device_id) FROM alarmas_activas WHERE estado = 'on' AND categoria = 'BATERIA BAJA'"); bat_c = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM alarmas_activas WHERE estado = 'on' AND categoria = 'Bateria Lit. disc.'"); disc_c = cur.fetchone()[0]
            h_data = HvacService.get_current_data(); h_c = sum(len(r.get("aires", [])) for r in h_data)
        finally: conn.close()
        return {'access': acc, 'transport': tra, 'ac_failures_count': ac_c, 'battery_alerts_count': bat_c, 'disconnection_count': disc_c, 'hvac_total_count': h_c, 
                'cameras': {'access': acam, 'transport': tcam}, 'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                'connection_errors': MonitoringService._connection_errors}
    
    @staticmethod
    def obtener_datos_desconexion(filtro_region=None, filtro_tipo=None):
        """
        Obtiene alarmas de baterías desconectadas (Bateria Lit. disc.)
        con duración calculada desde la hora de la alarma hasta ahora.
        
        Args:
            filtro_region (str, optional): Filtrar por región
            filtro_tipo (str, optional): Filtrar por tipo ('access' o 'transport')
        
        Returns:
            list: Lista de diccionarios con los datos
        """
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            
            # Construir consulta base
            query = """
                SELECT tipo, region, hora, sitio, alarma, devicename, device_id
                FROM alarmas_activas
                WHERE categoria = %s AND estado = %s
            """
            params = ['Bateria Lit. disc.', 'on']
            
            # Aplicar filtros si existen
            if filtro_region and filtro_region != 'Todas':
                query += " AND region = %s"
                params.append(filtro_region)
            
            if filtro_tipo and filtro_tipo != 'Todos':
                query += " AND tipo = %s"
                params.append(filtro_tipo)
            
            query += " ORDER BY hora DESC"
            
            cur.execute(query, params)
            rows = cur.fetchall()
            
            # Formatear duración compacta
            def format_duration_compact(hora_dt):
                delta = datetime.now() - hora_dt
                total_seconds = int(delta.total_seconds())
                days = total_seconds // 86400
                hours = (total_seconds % 86400) // 3600
                minutes = (total_seconds % 3600) // 60
                seconds = total_seconds % 60
                
                parts = []
                if days > 0:
                    parts.append(f"{days}d")
                if hours > 0 or days > 0:
                    parts.append(f"{hours:02d}h")
                if minutes > 0 or hours > 0 or days > 0:
                    parts.append(f"{minutes:02d}m")
                parts.append(f"{seconds:02d}s")
                
                return ''.join(parts)
            
            records = []
            for row in rows:
                tipo, region, hora, sitio, alarma, devicename, device_id = row
                records.append({
                    "tipo": tipo.capitalize() if tipo else "Unknown",
                    "region": region,
                    "hora": hora.strftime("%Y-%m-%d %H:%M:%S") if isinstance(hora, datetime) else hora,
                    "duracion": format_duration_compact(hora),
                    "sitio": sitio,
                    "alarma": alarma,
                    "devicename": devicename,
                    "device_id": device_id
                })
            
            return records
            
        except Exception as e:
            logging.error(f"Error obteniendo datos de desconexion: {e}")
            return []
        finally:
            conn.close()




    @staticmethod
    def obtener_datos_completos_v2(db_type, include_anomalias=True):
        eventos = MonitoringService.obtener_eventos_cumplidos(db_type)
        if not include_anomalias: return {"eventos": eventos, "anomalias": []}
        conn = get_db_connection()
        try:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            lim = (datetime.now() - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")
            cur.execute("""
                SELECT sitio, categoria, alarma, COUNT(*) as repeticiones, MAX(hora) as ultima_vez
                FROM (
                    SELECT sitio, categoria, alarma, hora FROM alarmas_activas WHERE tipo=%s AND hora >= %s AND categoria NOT IN ('AC_FAIL', 'BATERIA BAJA', 'BATERIA')
                    UNION ALL
                    SELECT sitio, categoria, alarma, hora FROM alarmas_historicas WHERE tipo=%s AND hora >= %s AND categoria NOT IN ('AC_FAIL', 'BATERIA BAJA', 'BATERIA')
                ) c GROUP BY sitio, categoria, alarma HAVING COUNT(*) > 5
            """, (db_type, lim, db_type, lim))
            anom = []
            for r in cur.fetchall():
                s = r['sitio']
                if db_type == "transport":
                    tc = CameraService.get_transport_cameras_for_site(s)
                    c_info = {"has_camera": len(tc) > 0, "cameras": tc, "available_positions": list(tc.keys())}
                else: c_info = {"has_camera": CameraService.has_camera(s, "access")}
                uv = r['ultima_vez'].strftime("%Y-%m-%d %H:%M:%S") if isinstance(r['ultima_vez'], datetime) else r['ultima_vez']
                anom.append({"sitio": s, "categoria": r['categoria'], "alarmameta": r['alarma'], "veces": r['repeticiones'], 
                             "ultima_vez": uv, "cameras": c_info})
        finally: conn.close()
        return {"eventos": eventos, "anomalias": anom}
