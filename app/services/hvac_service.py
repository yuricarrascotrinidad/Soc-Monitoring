import requests
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from collections import defaultdict
import threading
import logging
from app.utils.constants import CONFIG_REGIONES, HEADERS
from app.utils.db import execute_db, query_db

# Configuración de optimización
MAX_WORKERS = 15
BATCH_SIZE = 100
REQUEST_TIMEOUT = 15
DEVICE_TIMEOUT = 10
METE_TIMEOUT = 8

class HvacService:
    _current_hvac_data = []
    _last_update_time = None
    _hvac_lock = threading.Lock()
    
    # Cache thread-safe
    _device_cache = {}
    _device_cache_lock = threading.Lock()

    # Sesiones por IP
    _sessions = {}
    _sessions_lock = threading.Lock()

    # Protección contra hilos duplicados
    _monitoring_started = False
    _monitoring_lock = threading.Lock()

    @classmethod
    def get_current_data(cls):
        """Retorna los últimos datos obtenidos de HVAC."""
        with cls._hvac_lock:
            # Si no hay datos, intentar cargar de DB una vez
            if not cls._current_hvac_data:
                cls._load_from_db()
            return cls._current_hvac_data

    @classmethod
    def get_session_for_ip(cls, ip):
        """Obtiene o crea una sesión HTTP para una IP específica."""
        with cls._sessions_lock:
            if ip not in cls._sessions:
                session = requests.Session()
                retry = Retry(
                    total=3,
                    backoff_factor=0.5,
                    status_forcelist=[500, 502, 503, 504],
                    raise_on_status=False
                )
                adapter = HTTPAdapter(
                    max_retries=retry,
                    pool_connections=200,
                    pool_maxsize=MAX_WORKERS
                )
                session.mount('http://', adapter)
                cls._sessions[ip] = session
            return cls._sessions[ip]

    @classmethod
    def obtener_sitios_de_region_rapido(cls, config, tipo, region):
        """Obtiene TODOS los sitios de una región utilizando la configuración viva (de memoria)."""
        ip = config["url"].split("://")[1].split(":")[0]
        cookies = config["cookies"].copy()
        
        cookies.update({
            "contextPath": "/peim",
            "language": "es_ES",
            "loginUser": "yuri.carrasco",
            "proversion": "null"
        })

        url = f"http://{ip}:8090/peim/request/region/getDeviceTree"
        headers = HEADERS.copy()
        headers["Host"] = f"{ip}:8090"
        
        params = {
            "tree_type": 0,
            "id": "00001005000000000000",
            "node_type_show": 3,
            "_": int(time.time() * 1000)
        }

        try:
            session = cls.get_session_for_ip(ip)
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
            return sitios
        except Exception as e:
            logging.error(f"[HVAC] Error obteniendo sitios para {region}: {e}")
            return []

    @classmethod
    def obtener_dispositivos_de_sitio_con_cache(cls, sitio):
        """Obtiene dispositivos de un sitio utilizando caché para minimizar requests."""
        cache_key = f"{sitio['ip']}_{sitio['precinct_id']}"
        
        with cls._device_cache_lock:
            if cache_key in cls._device_cache:
                return cls._device_cache[cache_key]

        url = f"http://{sitio['ip']}:8090/peim/request/region/getDeviceTree"
        headers = HEADERS.copy()
        headers["Host"] = f"{sitio['ip']}:8090"
        
        params = {
            "tree_type": 0,
            "id": sitio["precinct_id"],
            "node_type_show": 3,
            "_": int(time.time() * 1000)
        }

        try:
            session = cls.get_session_for_ip(sitio['ip'])
            resp = session.get(url, headers=headers, cookies=sitio["cookies"], 
                               params=params, timeout=DEVICE_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()

            dispositivos = []
            if data.get("success"):
                for item in data.get("info", []):
                    if item.get("device_id"):
                        dispositivos.append({
                            "device_id": item.get("device_id"),
                            "device_name": item.get("device_name", ""),
                            "device_type": item.get("device_type"),
                        })
            
            with cls._device_cache_lock:
                cls._device_cache[cache_key] = dispositivos

            return dispositivos
        except Exception as e:
            # Silenciar log excesivo si falla
            return []

    @classmethod
    def obtener_aa_de_sitio(cls, sitio):
        """Busca dispositivos de aire acondicionado dentro del sitio."""
        dispositivos = cls.obtener_dispositivos_de_sitio_con_cache(sitio)
        raw_station_name = sitio.get("station_name", "") or ""
        # Extraer prefijo del sitio (ej: T1002 de T1002_AR_SELVA ALEGRE)
        # Aseguramos strip() para evitar fallos por espacios
        clean_name = raw_station_name.strip()
        site_prefix = ""
        if clean_name and "_" in clean_name:
            site_prefix = clean_name.split("_")[0].strip()
        elif clean_name and " " in clean_name:
            # Si tiene espacios, probamos el primer token
            site_prefix = clean_name.split(" ")[0].strip()
        elif clean_name:
            site_prefix = clean_name
            
        # Refinamiento del prefijo: Ignorar si es muy corto o puramente numérico (ej: "01", "02")
        # que suele ser de casas de guardianía o similares sin AA
        if site_prefix and site_prefix.isdigit() and len(site_prefix) <= 2:
            site_prefix = ""
            
        aires_del_sitio = []
        for d in dispositivos:
            d_name = d.get("device_name", "").strip()
            
            # Filtro base: Tipo 12, contiene 'Aire Acondicionado', no 'Intercambiador'
            if (d.get("device_type") == "12" and 
                "Aire Acondicionado" in d_name and 
                "Intercambiador" not in d_name):
                
                # Aplicar filtro de prefijo si existe
                if site_prefix:
                    # Comparación insensible a espacios y casos
                    if d_name.lower().startswith(site_prefix.lower()):
                        aires_del_sitio.append({
                            "device_id": d["device_id"],
                            "device_name": d_name
                        })
                else:
                    # Si no hay prefijo detectable, somos conservadores (no agregamos todo)
                    # Solo agregamos si el nombre coincide exactamente o tiene un patrón muy claro
                    # Por ahora, si no hay prefijo en el sitio, no agregamos para evitar leaks
                    pass
        # Log si encontramos algo sospechoso (más de 2 aires en un sitio de acceso)
        if len(aires_del_sitio) > 2 and sitio.get("tipo") == "access":
            logging.warning(f"[HVAC] Sitio {clean_name} tiene {len(aires_del_sitio)} aires: {[a['device_name'] for a in aires_del_sitio]}")
            
        return aires_del_sitio, site_prefix

    @classmethod
    def obtener_valor_aa_individual(cls, aa_info, sitio):
        """Consulta los valores telemétricos de un aire acondicionado individual."""
        ip = sitio["ip"]
        device_id = aa_info["device_id"]
        tipo = sitio["tipo"]

        url = f"http://{ip}:8090/peim/request/realtime/getMeteValue"
        headers = HEADERS.copy()
        headers["Host"] = f"{ip}:8090"
        headers["Referer"] = f"http://{ip}:8090/peim/main/realtime/realtimedevice.html?id={device_id}&device_type=12"
        
        payload = f"device_id={device_id}&is_manual=0"

        # Sensores de interes de HVAC
        sensores_aa_acceso = {
            "0112120001": "temperatura",
            "0112099001": "conexion",
        }
        sensores_aa_transporte = {
            "0112099001": "conexion",
            "011205A001": "status",
            "0112166001": "temp1",
            "0112167001": "hum1",
            "0112166002": "temp2",
            "0112167002": "hum2",
        }

        if tipo == "access":
            sensores_map = sensores_aa_acceso
        else:
            sensores_map = sensores_aa_transporte

        valores = {campo: None for campo in sensores_map.values()}
        valores["ultimo_update"] = None
        valores["device_id"] = device_id

        try:
            session = cls.get_session_for_ip(ip)
            resp = session.post(url, headers=headers, cookies=sitio["cookies"], 
                                data=payload, timeout=METE_TIMEOUT)
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
                            try:
                                valores[campo] = float(valor_limpio)
                            except ValueError:
                                valores[campo] = valor_limpio
                    except:
                        pass
                
                if update_time and valores["ultimo_update"] is None:
                    valores["ultimo_update"] = update_time
            
            # Limpiar algunos estados visuales para la api
            if "status" in valores:
                if valores["status"] == 21:
                    valores["status_str"] = "ENCENDIDO"
                elif valores["status"] == 23:
                    valores["status_str"] = "APAGADO"
                else: 
                    valores["status_str"] = f"DESCONOCIDO({valores['status']})" if valores["status"] is not None else "DESCONOCIDO"

            if "conexion" in valores:
                if valores["conexion"] == 0:
                    valores["conexion_str"] = "✅ Conectado"
                    valores["conexion_bool"] = True
                elif valores["conexion"] == 1:
                    valores["conexion_str"] = "❌ Desconectado"
                    valores["conexion_bool"] = False
                else:
                    valores["conexion_str"] = f"⚠️ ({valores['conexion']})" if valores["conexion"] is not None else "❓"
                    valores["conexion_bool"] = False
            else:
                valores["conexion_bool"] = False

            return {
                "device_id": device_id,
                "nombre": aa_info["device_name"],
                "valores": valores,
                "tiene_datos": any(v is not None for k, v in valores.items() if k not in ['device_id', 'ultimo_update'])
            }
        except Exception:
            return None

    @classmethod
    def procesar_lote_de_sitios(cls, sitios_lote):
        """Procesa un lote de sitios de manera concurrente."""
        resultados_lote = []
        sitios_con_aa = []
        
        for sitio in sitios_lote:
            aires, prefix = cls.obtener_aa_de_sitio(sitio)
            sitio_con_prefix = sitio.copy()
            sitio_con_prefix["site_prefix"] = prefix
            
            if aires:
                sitios_con_aa.append({"sitio": sitio_con_prefix, "aires": aires})
            else:
                # El usuario quiere ver todos los sitios (ej: 1523), incluso los que no tienen AA
                sitio_limpio = {k: v for k, v in sitio_con_prefix.items() if k != "cookies"}
                resultados_lote.append({
                    "sitio": sitio_limpio,
                    "aires": []
                })

        if sitios_con_aa:
            todos_los_aa = []
            for item in sitios_con_aa:
                for aa in item["aires"]:
                    todos_los_aa.append({"sitio": item["sitio"], "aa": aa})

            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                futures = {}
                for item in todos_los_aa:
                    future = executor.submit(cls.obtener_valor_aa_individual, item["aa"], item["sitio"])
                    futures[future] = item
                
                # Agrupar por una clave ÚNICA por estación para evitar fugas entre sitios con mismo precinct_id
                valores_por_sitio = defaultdict(list)
                for future in as_completed(futures):
                    try:
                        item = futures[future]
                        resultado = future.result(timeout=METE_TIMEOUT + 2)
                        if resultado:
                            # Clave compuesta: IP + Precinct + Nombre (para unicidad total en el lote)
                            sitio_key = f"{item['sitio']['ip']}_{item['sitio']['precinct_id']}_{item['sitio']['station_name']}"
                            valores_por_sitio[sitio_key].append(resultado)
                    except Exception:
                        pass
                
                for item in sitios_con_aa:
                    sitio_key = f"{item['sitio']['ip']}_{item['sitio']['precinct_id']}_{item['sitio']['station_name']}"
                    aires_con_valores = valores_por_sitio.get(sitio_key, [])
                    
                    if not aires_con_valores:
                        aires_con_valores = [{
                            "device_id": aa["device_id"],
                            "nombre": aa["device_name"],
                            "valores": {},
                            "tiene_datos": False
                        } for aa in item["aires"]]
                    
                    # Remover las cookies antes de guardarlo en cache
                    sitio_limpio = {k: v for k, v in item["sitio"].items() if k != "cookies"}
                    resultados_lote.append({
                        "sitio": sitio_limpio,
                        "aires": aires_con_valores
                    })

        return resultados_lote

    @classmethod
    def actualizar_datos_hvac(cls):
        """Ciclo principal de recolección de datos."""
        logging.info("[HVAC] Iniciando recolección de datos...")
        inicio = time.time()
        
        todos_los_sitios = []
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = []
            for tipo, regiones in CONFIG_REGIONES.items():
                for region, config in regiones.items():
                    # Check if Token exists, because we share CONFIG_REGIONES with TrackingService.
                    if config.get("cookies", {}).get("PEIMWEBID"):
                        futures.append(executor.submit(cls.obtener_sitios_de_region_rapido, config, tipo, region))
            
            for future in as_completed(futures):
                try:
                    sitios = future.result(timeout=30)
                    todos_los_sitios.extend(sitios)
                except Exception as e:
                    logging.warning(f"[HVAC] Expiró o falló la recolección de una región: {e}")
        
        if not todos_los_sitios:
            logging.warning("[HVAC] No se obtuvieron sitios. Reintentando próximo ciclo.")
            return

        resultados_finales = []
        for batch_start in range(0, len(todos_los_sitios), BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, len(todos_los_sitios))
            batch = todos_los_sitios[batch_start:batch_end]
            
            res_lote = cls.procesar_lote_de_sitios(batch)
            resultados_finales.extend(res_lote)

        # Ordenar por el nombre de la estación para consistencia
        resultados_finales.sort(key=lambda x: x["sitio"].get("station_name", ""))
        
        with cls._hvac_lock:
            cls._current_hvac_data = resultados_finales
            cls._last_update_time = datetime.now()
            
        # Persistir en DB de manera eficiente
        cls._save_to_db(resultados_finales)
            
        duracion = time.time() - inicio
        logging.info(f"[HVAC] Recolección terminada en {duracion:.1f}s. {sum(1 for r in resultados_finales if r['aires'])} sitios con AA de {len(resultados_finales)} totales.")

    @classmethod
    def _save_to_db(cls, data):
        """Guarda los datos en la tabla hvac_telemetry usando UPSERT."""
        if not data:
            return
            
        # Deduplicar por device_id para evitar error de PostgreSQL "cannot affect a row a second time"
        dict_registros = {}
        for row in data:
            s = row.get("sitio", {})
            for aa in row.get("aires", []):
                v = aa.get("valores", {})
                device_id = aa.get("device_id")
                if device_id:
                    dict_registros[device_id] = (
                        device_id, s.get("precinct_id"), s.get("station_name"),
                        s.get("region"), s.get("tipo"), aa.get("nombre"),
                        v.get("temperatura"), v.get("conexion"), v.get("conexion_str"),
                        v.get("status"), v.get("status_str"),
                        v.get("temp1"), v.get("hum1"), v.get("temp2"), v.get("hum2"),
                        v.get("ultimo_update"), s.get("site_prefix")
                    )
        
        registros = list(dict_registros.values())
        
        if not registros:
            return

        query = """
        INSERT INTO hvac_telemetry (
            device_id, precinct_id, station_name, region, tipo, device_name,
            temperatura, conexion, conexion_str, status_val, status_str,
            temp1, hum1, temp2, hum2, ultimo_update, site_prefix
        ) VALUES %s
        ON CONFLICT (device_id) DO UPDATE SET
            precinct_id = EXCLUDED.precinct_id,
            station_name = EXCLUDED.station_name,
            region = EXCLUDED.region,
            tipo = EXCLUDED.tipo,
            device_name = EXCLUDED.device_name,
            temperatura = EXCLUDED.temperatura,
            conexion = EXCLUDED.conexion,
            conexion_str = EXCLUDED.conexion_str,
            status_val = EXCLUDED.status_val,
            status_str = EXCLUDED.status_str,
            temp1 = EXCLUDED.temp1,
            hum1 = EXCLUDED.hum1,
            temp2 = EXCLUDED.temp2,
            hum2 = EXCLUDED.hum2,
            ultimo_update = EXCLUDED.ultimo_update,
            site_prefix = EXCLUDED.site_prefix,
            last_updated_db = CURRENT_TIMESTAMP;
        """
        
        try:
            import psycopg2.extras
            from app.utils.db import get_db_connection
            conn = get_db_connection()
            cur = conn.cursor()
            
            # 1. Identificar estaciones únicas en este lote para limpiar el "historial"
            # Esto evita que equipos retirados (ej: baterías cambiadas) se queden como fantasmas
            estaciones_unicas = set()
            for r in registros:
                # r[2] es station_name, r[1] es precinct_id
                estaciones_unicas.add((r[1], r[2]))
            
            if estaciones_unicas:
                # Borrar por lote de estaciones
                # Usamos una clave compuesta (precinct_id, station_name) para mayor seguridad
                for p_id, s_name in estaciones_unicas:
                    cur.execute(
                        "DELETE FROM hvac_telemetry WHERE precinct_id = %s AND station_name = %s",
                        (p_id, s_name)
                    )
            
            # 2. Insertar los nuevos registros
            psycopg2.extras.execute_values(cur, query, registros)
            
            conn.commit()
            rows_affected = cur.rowcount
            cur.close()
            conn.close()
            logging.info(f"[HVAC] DB: {len(registros)} registros procesados. {rows_affected} filas insertadas/actualizadas.")
        except Exception as e:
            if conn: conn.rollback(); conn.close()
            logging.error(f"[HVAC] Error persistiendo en DB ({len(registros)} registros): {e}")

    @classmethod
    def _load_from_db(cls):
        """Carga los últimos datos conocidos de la base de datos."""
        try:
            query = "SELECT * FROM hvac_telemetry ORDER BY station_name"
            rows = query_db(query)
            
            if not rows:
                return
            
            # Reconstruir la estructura sitios -> aires
            sitios_map = {}
            for row in rows:
                p_id = row["precinct_id"]
                s_name = row["station_name"]
                # Clave compuesta para evitar colisiones entre estaciones del mismo recinto
                sitio_key = f"{p_id}_{s_name}"
                
                if sitio_key not in sitios_map:
                    sitios_map[sitio_key] = {
                        "sitio": {
                            "precinct_id": p_id,
                            "station_name": s_name,
                            "region": row["region"],
                            "tipo": row["tipo"],
                            "site_prefix": row.get("site_prefix")
                        },
                        "aires": []
                    }
                
                # Reconstruir el objeto del aire
                v = {
                    "temperatura": row["temperatura"],
                    "conexion": row["conexion"],
                    "conexion_str": row["conexion_str"],
                    "status": row["status_val"],
                    "status_str": row["status_str"],
                    "temp1": row["temp1"],
                    "hum1": row["hum1"],
                    "temp2": row["temp2"],
                    "hum2": row["hum2"],
                    "ultimo_update": row["ultimo_update"],
                    "conexion_bool": row["conexion"] == 0
                }
                
                sitios_map[sitio_key]["aires"].append({
                    "device_id": row["device_id"],
                    "nombre": row["device_name"],
                    "valores": v,
                    "tiene_datos": any(val is not None for k, val in v.items() if k not in ['device_id', 'ultimo_update', 'conexion_bool'])
                })
            
            cls._current_hvac_data = list(sitios_map.values())
            logging.info(f"[HVAC] DB: {len(cls._current_hvac_data)} sitios cargados desde el historial.")
            
        except Exception as e:
            logging.error(f"[HVAC] Error cargando desde DB: {e}")

    @classmethod
    def run_monitoring_loop(cls):
        """Bucle infinito para el Daemon Thread."""
        while True:
            try:
                cls.actualizar_datos_hvac()
            except Exception as e:
                import traceback
                logging.error(f"[HVAC] Error inesperado en el loop principal: {e}")
                traceback.print_exc()
            # Dormir por 5 minutos
            time.sleep(300)

    @classmethod
    def start_hvac_monitoring(cls, app):
        """Inicia el monitoreo de HVAC en un hilo separado de fondo."""
        with cls._monitoring_lock:
            if cls._monitoring_started:
                logging.info("[HVAC] El monitoreo ya está en ejecución. Saltando.")
                return
            cls._monitoring_started = True

        t = threading.Thread(target=cls.run_monitoring_loop, daemon=True, name="HVAC_Monitoring_Thread")
        t.start()
        logging.info("[HVAC] Hilo de monitoreo iniciado.")
