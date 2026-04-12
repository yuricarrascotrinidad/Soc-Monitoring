import re

def convertir_duracion(texto):
    if not texto:
        return 0
    m = re.search(r'(\d+)m', texto)
    s = re.search(r'(\d+)s', texto)
    total = 0
    if m:
        total += int(m.group(1)) * 60
    if s:
        total += int(s.group(1))
    return total

def clasificar_evento_access(alarma):
    # Patrones robustos para AC_FAIL
    AC_FAIL_PATTERNS = ["ingresa", "voltaje fase", "falla de red", "falla red", "mains failure", "mainsvoltage", "level one upper alarm", "low dc voltage"]
    
    CLASIFICACIONES = [
        (["fin de carrera"], "Shelter"),
        (["servicios datos"], "NVR"),
        (["nvr"], "NVR"),
        (["fsu"], "Fsu"),
        (["cam. ", "cam ", "cámara ", "camera "], "Camara"),
        (["puerta ", "magnético", "magnetico", "p.p s.magnetico"], "Puerta"),
        (["puerta ", "s.en s.magnetico", "s.eq s.magnetico"], "Puerta Equipo"),
        (["puerta ", "s.fz s.magnetico"], "Puerta Fz"),
        (["movimiento", "infra", "tamper", "masking"], "Movimiento"),
        (["soc"], "BATERIA BAJA"),
        (["interruption alarm"], "Bateria Lit. disc."),
        (AC_FAIL_PATTERNS, "AC_FAIL"),
    ]
    
    texto = (alarma.get("alarm_name", "") + " " +
             alarma.get("device_name", "")).lower()
             
    for patrones, categoria in CLASIFICACIONES:
        for patron in patrones:
            if patron in texto:
                return categoria
    return "No clasificado"

def clasificar_evento_transport(alarma):
    CLASIFICACIONES = [
        (["cam p.prin", "cam. p.prin"], "Camara Prin"),
        (["cam patio", "cam. patio"], "Camara Patio"),
        (["cam s.fz", "cam. s.fz"], "Camara S.Fz"),
        (["cam s.eq", "cam. s.eq"], "Camara S.Eq"),
        (["p.p s.magnetico", "p.p-s.magnetico"], "Puerta p."),
        (["s.fz s.magnetico", "s.fz-s.magnetico"], "Puerta f."),
        (["s.eq s.magnetico", "s.eq-s.magnetico", "s.en s.magnetico", "s.en-s.magnetico"], "Puerta e."),
        (["patio s.movimiento", "patio-s.movimiento"], "M. Patio"),
        (["s.fz s.movimiento", "s.fz-s.movimiento"], "M. S.Fz"),
        (["s.eq s.movimiento", "s.eq-s.movimiento", "s.en s.movimiento", "s.en-s.movimiento"], "M. S.Eq"),
        (["fsu"], "Fsu"),
        (["nvr", "servicios datos"], "NVR"),
        (["interruption alarm"], "Bateria Lit. disc."),
        (["soc"], "BATERIA BAJA"),
        (["ac ingresa voltaje fase xx ua"], "AC_FAIL"),
        (["vmainsvoltagelxxn"], "AC_FAIL_GE"),
    ]
    
    texto = (alarma.get("alarm_name", "") + " " + 
             alarma.get("device_name", "")).lower()
    
    for patrones, categoria in CLASIFICACIONES:
        for patron in patrones:
            if patron in texto:
                return categoria
    return "No clasificado"

def determinar_tipo_evento(eventos_lista):
    if not eventos_lista:
        return "Desconocido"
    return ", ".join(eventos_lista)

def filtrar_eventos_generales(eventos, reglas):
    if not eventos:
        return []
    
    eventos_filtrados = []
    for e in eventos:
        es_subconjunto = False
        reps_e = reglas.get(e, set())
        
        for e2 in eventos:
            if e == e2:
                continue
            
            reps_e2 = reglas.get(e2, set())
            if reps_e.issubset(reps_e2):
                if len(reps_e) < len(reps_e2):
                    es_subconjunto = True
                    break
        
        if not es_subconjunto:
            eventos_filtrados.append(e)
            
    return eventos_filtrados
