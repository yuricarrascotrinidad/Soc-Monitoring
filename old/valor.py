import requests
import json
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# -----------------------------
# Configuración de todas las regiones
# -----------------------------
CONFIG_REGIONES = {
    "access": {
        "Ancash": {
            "ip": "10.254.1.135",
            "cookies": {"PEIMWEBID": "339820562C0C15103E985FDD8B0ADBCD"}
        },
        "Arequipa": {
            "ip": "10.254.11.135",
            "cookies": {"PEIMWEBID": "C7DE9EEBE1CB1F2DFCDCE4F67417A20F"}
        },
        "La Libertad": {
            "ip": "10.254.21.135",
            "cookies": {"PEIMWEBID": "40CFAA530E9D7CB50B4E2F816E7AD19D"}
        },
        "San Martin": {
            "ip": "10.254.31.135",
            "cookies": {"PEIMWEBID": "0BF1494AB24E9E41F94F2E68F32F6604"}
        },
    },
    "transport": {
        "Ancash": {
            "ip": "10.255.1.135",
            "cookies": {"PEIMWEBID": "F20646089379E9E163578B13C5280848"}
        },
        "Arequipa": {
            "ip": "10.255.11.135",
            "cookies": {"PEIMWEBID": "7EC9969FBBF0FDE8431E8DC05E07EB24"}
        },
        "La Libertad": {
            "ip": "10.255.21.135",
            "cookies": {"PEIMWEBID": "F3C43E263A35EF2F35FF38CFD42A593A"}
        },
        "San Martin": {
            "ip": "10.255.31.135",
            "cookies": {"PEIMWEBID": "25C76393352BA6DE3659C9440FC44CF6"}
        },
    }
}

# Headers base (comunes para todas las peticiones)
HEADERS_BASE = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "es-419,es-US;q=0.9,es;q=0.8",
    "Connection": "keep-alive",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
    "X-Requested-With": "XMLHttpRequest"
}

# Template para consulta de alarmas
DATA_TEMPLATE = {
    "filter_id": "",
    "station_name": "",
    "precinct_list": "",
    "alarm_name": "",
    "alarm_desc": "",
    "alarm_time": "",
    "alarm_span_time": "",
    "device_name": "",
    "mete_name": "",
    "alarmtype_list": "47_47116001",
    "start_time": "",
    "end_time": "",
    "eliminate_state": "0",
    "radio_clear": "0",
    "confirm_state": "0",
    "chk_confirm": "0",
    "alarmlevel_list": "",
    "chk_level_all": "-1",
    "chk_level": "4",
    "only_major": "1",
    "page_no": 1,
    "page_size": 50
}

# -----------------------------
# Funciones para cada región/servidor
# -----------------------------

def construir_urls(ip):
    """Construye las URLs para una IP dada"""
    return {
        "alarmas": f"http://{ip}:8090/peim/request/alarm/queryAlarm",
        "valores": f"http://{ip}:8090/peim/request/realtime/getMeteValue"
    }

def obtener_alarmas_region(tipo, region, config):
    """Obtiene alarmas para una región específica"""
    ip = config["ip"]
    cookies = config["cookies"].copy()
    
    # Agregar cookies adicionales necesarias
    cookies.update({
        "contextPath": "/peim",
        "language": "es_ES",
        "limit": "8",
        "loginUser": "yuri.carrasco",
        "proversion": "null",
        "sessionUser": "%7B%22retUrl%22%3A%22/peim/views/default_design%22%2C%22fr_use%22%3A%221%22%2C%22user_name%22%3A%22yuri.carrasco%22%2C%22proversion%22%3Anull%2C%22operate_id%22%3A%221%2C2%2C3%2C4%2C5%2C6%2C7%2C8%2C9%2C10%22%2C%22isAdmin%22%3A%22false%22%2C%22userid%22%3A%2200001001000000000047%22%2C%22username%22%3A%22yuri.carrasco%22%7D"
    })
    
    urls = construir_urls(ip)
    headers = HEADERS_BASE.copy()
    headers["Host"] = f"{ip}:8090"
    headers["Origin"] = f"http://{ip}:8090"
    headers["Referer"] = f"http://{ip}:8090/peim/main/realtime/realtimedevice.html"
    
    data = {"queryObjStr": json.dumps(DATA_TEMPLATE)}
    
    try:
        resp = requests.post(urls["alarmas"], headers=headers, cookies=cookies, 
                            data=data, timeout=15)
        resp.raise_for_status()
        datos = resp.json()
        
        if datos.get("success"):
            alarmas = datos["info"]["data"]
            # Agregar metadatos de región a cada alarma
            for alarm in alarmas:
                alarm["_region"] = region
                alarm["_tipo"] = tipo
                alarm["_ip"] = ip
            return alarmas
        else:
            print(f"⚠️ [{tipo} - {region}] Error: {datos.get('msg', 'Unknown error')}")
            return []
    except Exception as e:
        print(f"❌ [{tipo} - {region}] Error de conexión: {e}")
        return []

def obtener_valores_dispositivo(ip, device_id, cookies_base):
    """
    Obtiene todos los valores importantes para un dispositivo:
    - SOC (0147116001)
    - Corriente de Carga (0147106001)
    - Corriente de Descarga (0147106002)
    """
    urls = construir_urls(ip)
    headers = HEADERS_BASE.copy()
    headers["Host"] = f"{ip}:8090"
    headers["Origin"] = f"http://{ip}:8090"
    
    cookies = cookies_base.copy()
    cookies.update({
        "contextPath": "/peim",
        "language": "es_ES",
        "limit": "8",
        "loginUser": "yuri.carrasco",
        "proversion": "null"
    })
    
    payload = f"device_id={device_id}&is_manual=0"
    
    valores = {
        'soc': None,
        'carga': None,
        'descarga': None
    }
    
    try:
        resp = requests.post(urls["valores"], headers=headers, cookies=cookies,
                            data=payload, timeout=10)
        resp.raise_for_status()
        sensores = resp.json()
        
        for sensor in sensores:
            mete_id = sensor.get("meteId", "")
            mete_value = sensor.get("meteValue")
            
            if mete_id == "0147116001":  # SOC
                try:
                    valores['soc'] = float(mete_value) if mete_value else None
                except (ValueError, TypeError):
                    pass
            elif mete_id == "0147106001":  # Corriente de Carga
                try:
                    valores['carga'] = float(mete_value) if mete_value else None
                except (ValueError, TypeError):
                    pass
            elif mete_id == "0147106002":  # Corriente de Descarga
                try:
                    valores['descarga'] = float(mete_value) if mete_value else None
                except (ValueError, TypeError):
                    pass
        
        return valores
    except Exception as e:
        return valores

def obtener_estado_emoji(soc_actual, umbral):
    """Determina el emoji de estado basado en SOC y umbral"""
    if soc_actual is None:
        return "⚪"
    if soc_actual < umbral:
        return "🔴"
    elif soc_actual <= umbral * 1.2 or soc_actual == umbral:
        return "🟡"
    else:
        return "🟢"

def procesar_alarma_con_valores(alarma, cache_valores):
    """Procesa una alarma individual y devuelve una línea de texto"""
    device_id = alarma.get("device_id")
    ip = alarma.get("_ip")
    cookies = CONFIG_REGIONES[alarma["_tipo"]][alarma["_region"]]["cookies"].copy()
    
    # Usar cache o consultar
    cache_key = f"{ip}_{device_id}"
    if cache_key not in cache_valores:
        cache_valores[cache_key] = obtener_valores_dispositivo(ip, device_id, cookies)
    
    valores = cache_valores[cache_key]
    soc_actual = valores['soc']
    carga = valores['carga']
    descarga = valores['descarga']
    
    # Extraer datos de la alarma
    alarm_time = alarma.get("alarm_time", "Fecha desconocida")
    device_name = alarma.get("device_name", "Desconocido")
    alarm_desc = alarma.get("alarm_desc", "Alarma")
    station_name = alarma.get("station_name", "N/A")
    
    try:
        umbral = float(alarma.get("alarm_value", 0))
    except (ValueError, TypeError):
        umbral = 0.0
    
    # Formatear salida
    tipo_emoji = "📡" if alarma["_tipo"] == "access" else "🚛"
    region = alarma["_region"]
    
    # Formatear valores de corriente (con 2 decimales)
    carga_str = f"{carga:.2f}A" if carga is not None else "N/A"
    descarga_str = f"{descarga:.2f}A" if descarga is not None else "N/A"
    
    # Obtener emoji de estado
    estado_emoji = obtener_estado_emoji(soc_actual, umbral)
    
    if soc_actual is not None:
        if umbral == 1.0:
            diferencia = round(soc_actual, 2)
        else:
            diferencia = round(soc_actual - umbral, 2)
        
        # Formatear diferencia con signo explícito
        if diferencia > 0:
            diff_str = f"+{diferencia:.1f}"
        elif diferencia < 0:
            diff_str = f"{diferencia:.1f}"
        else:
            diff_str = "0.0"
        
        # UNA SOLA LÍNEA con todos los datos
        return (f"{tipo_emoji} [{alarm_time}] {device_name} | {alarm_desc} | "
                f"{station_name} | {region}| {umbral}| "
                f"SOC: {soc_actual:.1f}% | Dif: {diff_str} | "
                f"Carga: {carga_str} | Descarga: {descarga_str} {estado_emoji}")
    else:
        return (f"{tipo_emoji} [{alarm_time}] {device_name} | {alarm_desc} | "
                f"{station_name} | {region} | {umbral}| "
                f"SOC: N/A | Dif: N/A | "
                f"Carga: {carga_str} | Descarga: {descarga_str} ⚪")

def obtener_todas_las_alarmas():
    """Obtiene alarmas de todas las regiones en paralelo"""
    todas_alarmas = []
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = []
        
        # Lanzar peticiones para todas las regiones
        for tipo, regiones in CONFIG_REGIONES.items():
            for region, config in regiones.items():
                futures.append(
                    executor.submit(obtener_alarmas_region, tipo, region, config)
                )
        
        # Recoger resultados
        for future in as_completed(futures):
            alarmas = future.result()
            todas_alarmas.extend(alarmas)
    
    return todas_alarmas

# -----------------------------
# Ejecución principal
# -----------------------------
if __name__ == "__main__":
    print("=" * 120)
    print("🚀 MONITOR MULTIREGIÓN DE BATERÍAS DE LITIO")
    print("=" * 120)
    print("📡 Access | 🚛 Transport")
    print("📊 Mostrando: SOC, Corriente de Carga (0147106001) y Descarga (0147106002)")
    print(f"Iniciado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 120)
    
    MODO_CONTINUO = True
    INTERVALO_SEGUNDOS = 60  # 1 minuto
    
    if MODO_CONTINUO:
        print(f"🔄 Modo: MONITOREO CONTINUO (cada {INTERVALO_SEGUNDOS} segundos)")
        print("Presiona Ctrl+C para detener\n")
        
        try:
            ciclo = 1
            while True:
                print(f"\n📊 CICLO #{ciclo} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print("-" * 120)
                
                # Obtener todas las alarmas
                todas_alarmas = obtener_todas_las_alarmas()
                
                if todas_alarmas:
                    print(f"✅ Total alarmas encontradas: {len(todas_alarmas)}")
                    
                    # Procesar alarmas con cache compartido
                    cache_valores = {}
                    lineas_salida = []
                    
                    # Procesar todas las alarmas
                    for alarma in todas_alarmas:
                        linea = procesar_alarma_con_valores(alarma, cache_valores)
                        lineas_salida.append(linea)
                    
                    # Ordenar por fecha (más reciente primero)
                    lineas_salida.sort(reverse=True)
                    
                    # Mostrar resultados (UNA LÍNEA POR ALARMA)
                    for linea in lineas_salida:
                        print(linea)
                    
                    print(f"\n✅ Ciclo #{ciclo} completado. Próximo ciclo en {INTERVALO_SEGUNDOS} segundos...")
                else:
                    print("📭 No se encontraron alarmas en ninguna región")
                
                ciclo += 1
                time.sleep(INTERVALO_SEGUNDOS)
                
        except KeyboardInterrupt:
            print("\n\n👋 Monitor detenido por el usuario")
            print(f"Total de ciclos completados: {ciclo-1}")
    else:
        # Ejecución única
        print("\n📋 Modo: EJECUCIÓN ÚNICA\n")
        todas_alarmas = obtener_todas_las_alarmas()
        
        if todas_alarmas:
            print(f"✅ Total alarmas: {len(todas_alarmas)}")
            print("-" * 120)
            
            cache_valores = {}
            for alarma in todas_alarmas:
                linea = procesar_alarma_con_valores(alarma, cache_valores)
                print(linea)
        else:
            print("📭 No se encontraron alarmas")