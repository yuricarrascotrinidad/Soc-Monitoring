import os
import logging
REGLAS_EVENTOS = {
    "access": {
        "🚪PUERTA_ABIERTA": {"Puerta"},
        "🏢 SHELTER": {"Shelter"},
        "🚨INTRUSION": {"Puerta", "Movimiento"},
        "🚪🚨ROBO P_S": {"Puerta", "Shelter"},
        "🚨🚨ROBO_SHELTER": {"Movimiento", "Shelter"},
        "🚨📷 SABOTAJE": {"Movimiento", "Shelter", "Camara"},
        "🚨🚨ROBO": {"Puerta", "Movimiento", "Shelter"},
        "🚨🚨ROBO_SABOTAJE": {"Puerta", "Movimiento", "Shelter", "Camara"},
        "🪫 BATERIA": {"Bateria Lit. disc."},
    },
    "transport": {
        "🚪PUERTA_Principal": {"Puerta p."},
        "🚪PUERTA_Generador": {"Puerta f."},
        "🚪PUERTA_Equipo": {"Puerta e."},
        "🚨Patio": {"Puerta p.", "M. Patio"},
        "🚨Generador": {"Puerta f.", "M. S.Fz"},
        "🚨Equipo": {"Puerta e.", "M. S.Eq"},
        "🚨📷 SABOTAJE": {"Movimiento", "Camara Prin"},
        "🚨🚨ROBO_SABOTAJE": {"Puerta", "Movimiento", "Camara Prin"},
        "🪫 BATERIA": {"Bateria Lit. disc."},
    }
}

CONFIG_REGIONES = {}
TOKENS_FILE = os.path.join(os.path.dirname(__file__), 'tokens_api.json')

def load_dynamic_tokens():
    """Carga tokens y URLs actualizados desde el archivo JSON si existe, o inicializa con semilla."""
    import json
    global CONFIG_REGIONES
    
    # Semilla de configuración (URLs necesarias para el primer arranque)
    SEED_CONFIG = {
        "access": {
            "Ancash": {"url": "http://10.254.1.135:8090/peim/request/alarm/queryAlarm", "cookies": {"PEIMWEBID": ""}},
            "Arequipa": {"url": "http://10.254.11.135:8090/peim/request/alarm/queryAlarm", "cookies": {"PEIMWEBID": ""}},
            "La Libertad": {"url": "http://10.254.21.135:8090/peim/request/alarm/queryAlarm", "cookies": {"PEIMWEBID": ""}},
            "San Martin": {"url": "http://10.254.31.135:8090/peim/request/alarm/queryAlarm", "cookies": {"PEIMWEBID": ""}},
        },
        "transport": {
            "Ancash": {"url": "http://10.255.1.135:8090/peim/request/alarm/queryAlarm", "cookies": {"PEIMWEBID": ""}},
            "Arequipa": {"url": "http://10.255.11.135:8090/peim/request/alarm/queryAlarm", "cookies": {"PEIMWEBID": ""}},
            "La Libertad": {"url": "http://10.255.21.135:8090/peim/request/alarm/queryAlarm", "cookies": {"PEIMWEBID": ""}},
            "San Martin": {"url": "http://10.255.31.135:8090/peim/request/alarm/queryAlarm", "cookies": {"PEIMWEBID": ""}},
        }
    }

    tokens_file = TOKENS_FILE
    
    if os.path.exists(tokens_file):
        try:
            with open(tokens_file, 'r', encoding='utf-8') as f:
                new_config = json.load(f)
            
            # Update CONFIG_REGIONES in-place to preserve references
            logging.debug(f"🔄 Cargando tokens desde {tokens_file}...")
            for segment, regions in new_config.items():
                if segment not in CONFIG_REGIONES:
                    CONFIG_REGIONES[segment] = {}
                for region, data in regions.items():
                    if region not in CONFIG_REGIONES[segment]:
                        CONFIG_REGIONES[segment][region] = data
                    else:
                        # Deep update: respect existing fields but overwrite with new ones from JSON
                        if isinstance(data, dict):
                            for key, value in data.items():
                                CONFIG_REGIONES[segment][region][key] = value
                        else:
                            CONFIG_REGIONES[segment][region] = data
        except Exception as e:
            # Only use seed if we have absolutely nothing
            if not CONFIG_REGIONES:
                CONFIG_REGIONES.update(SEED_CONFIG)
    else:
        # Si no existe el archivo, guardamos la semilla inicial
        if not CONFIG_REGIONES:
            CONFIG_REGIONES.update(SEED_CONFIG)
        try:
            with open(tokens_file, 'w', encoding='utf-8') as f:
                json.dump(CONFIG_REGIONES, f, indent=4)
        except Exception as e:
            pass

# Cargar tokens al importar el módulo
if not CONFIG_REGIONES:
    load_dynamic_tokens()

DATA_TEMPLATE = {
    "filter_id": "", "station_name": "", "precinct_list": "", "alarm_name": "", "device_id": "",
    "alarm_time": "", "alarm_span_time": "", "device_name": "", "mete_name": "",
    "alarmtype_list": "18_18003001,18_18042001,18_18043001,19_19082001,18_18047001,5_05159001,"
                      "18_18046001,47_47099001,96_96006001,38_38099001,47_47116001,32_32099001",
    "start_time": "", "end_time": "",
    "eliminate_state": "0", "radio_clear": "0",
    "confirm_state": "0", "chk_confirm": "0",
    "alarmlevel_list": "",
    "chk_level_all": "-1", "chk_level": "4",
    "only_major": "1",
    "page_no": 1, "page_size": 500
}

ALARM_TEMPLATE_AC = {
    "filter_id": "",
    "station_name": "",
    "precinct_list": "",
    "alarm_name": "",
    "alarm_desc": "",
    "alarm_time": "",
    "alarm_span_time": "",
    "device_name": "",
    "mete_name": "",
    "alarmtype_list": "6_06101001",  
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
    "page_size": 500
}

SENSORES_INTERES = {
    # Litio (Type 47)
    "0147116001": "soc",      
    "0147106001": "carga",     
    "0147106002": "descarga",  
    "0147099001": "conexion",
    
    # ZTE (Type 32)
    "0132125001": "soc_1",
    "0132125002": "soc_2",
    "0132125003": "soc_3",
    "0132125004": "soc_4",
    "0132123001": "cur_1",
    "0132123002": "cur_2",
    "0132123003": "cur_3",
    "0132123004": "cur_4",
    "0132099001": "conexion",

    # Rectificador (Type 6/8)
    "0106101001": "voltaje",    
    "0106111001": "svoltage",   
    "0106184001": "current1",   
    "0106184002": "current2",   
    "0106099001": "conexion",

    # Generador (Type 5)
    "0105159001": "voltaje_gen",
    "0105158001": "corriente_gen",
}

HEADERS = {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}

POSICIONES_TRANSPORT = ["principal", "patio", "equipo", "generador"]
