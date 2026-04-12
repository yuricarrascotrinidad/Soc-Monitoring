from flask import Blueprint, jsonify, send_file
from app.services.monitoring_service import MonitoringService
from app.services.camera_service import CameraService
from app.services.export_service import ExportService
from app.utils.db import get_db_connection
from app.utils.constants import REGLAS_EVENTOS
from app.utils.helpers import filtrar_eventos_generales
from datetime import datetime, timedelta
import json
import re
from flask_jwt_extended import jwt_required, get_jwt
from app.utils.rbac_utils import filter_response_data

api_bp = Blueprint('api', __name__)

@api_bp.route('/datos')
def get_data():
    try:
        return get_dashboard_state()
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@api_bp.route('/api/dashboard_state')
@jwt_required()  # Solo requiere autenticación, NO permisos específicos
def get_dashboard_state():
    try:
        data = MonitoringService.get_cached_dashboard_state()
        
        # Si la cache aún no se ha generado (primeros segundos), calcularla on-demand una vez
        if data is None:
            from flask import current_app
            data = MonitoringService._calculate_dashboard_state()
            
        # Filtrar datos según permisos del JWT (solo oculta módulos, NO bloquea)
        claims = get_jwt()
        permissions = claims.get("permissions", {})
        filtered_data = filter_response_data(data, permissions)
        
        return jsonify(filtered_data)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@api_bp.route('/cameras')
#@jwt_required()  # Comentado para pruebas
def get_cameras_list():
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        
        # Access Cameras
        cur.execute("SELECT site, ip FROM access_cameras")
        access_cameras = [{"site": row[0], "ip": row[1]} for row in cur.fetchall()]
        
        # Transport Cameras
        cur.execute("SELECT site, position, ip FROM transport_cameras")
        transport_cameras = [{"site": row[0], "position": row[1], "ip": row[2]} for row in cur.fetchall()]
        
        # ✅ ELIMINAR TODA LA LÓGICA DE JWT
        # Simplemente devolver todas las cámaras sin filtrar
        result = {
            'access': access_cameras,
            'transport': transport_cameras
        }
        
        return jsonify(result)
    except Exception as e:
        print(f"Error en get_cameras_list: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@api_bp.route('/api/camera_status')
@jwt_required()  # Solo requiere autenticación
def check_camera_status():
    """
    Check camera connectivity status.
    Query params: site, type (access/transport), position (optional, for transport)
    """
    from flask import request
    
    site = request.args.get('site')
    camera_type = request.args.get('type', 'access')
    position = request.args.get('position', 'principal')
    
    if not site:
        return jsonify({'error': 'Site parameter required'}), 400
    
    # Verificar permiso para ver cámaras
    claims = get_jwt()
    permissions = claims.get("permissions", {})
    if not permissions.get('view_cameras', False):
        return jsonify({
            'status': 'no_permission',
            'ip': None,
            'message': 'No tiene permiso para ver cámaras'
        }), 403
    
    try:
        status = CameraService.get_camera_status(site, camera_type, position)
        return jsonify(status)
    except Exception as e:
        return jsonify({
            'status': 'no_config',
            'ip': None,
            'message': f'Error: {str(e)}'
        }), 500

@api_bp.route('/api/camera_status/batch', methods=['POST'])
@jwt_required()  # Solo requiere autenticación
def check_camera_status_batch():
    """
    Check multiple cameras. Expects JSON: { "cameras": [ {site, type, position}, ... ] }
    """
    from flask import request
    
    data = request.json
    results = []
    
    if not data or 'cameras' not in data:
        return jsonify({'error': 'Invalid data'}), 400
    
    # Verificar permiso para ver cámaras
    claims = get_jwt()
    permissions = claims.get("permissions", {})
    can_view_cameras = permissions.get('view_cameras', False)
    
    for cam in data['cameras']:
        site = cam.get('site')
        ctype = cam.get('type', 'access')
        pos = cam.get('position', 'principal')
        
        # Si no tiene permiso, devolver estado denegado para todas
        if not can_view_cameras:
            results.append({
                'site': site,
                'type': ctype,
                'position': pos,
                'status': {
                    'status': 'no_permission',
                    'ip': None,
                    'message': 'No tiene permiso para ver cámaras'
                }
            })
            continue
            
        try:
            status = CameraService.get_camera_status(site, ctype, pos)
            results.append({
                'site': site,
                'type': ctype,
                'position': pos,
                'status': status
            })
        except Exception:
            results.append({
                'site': site,
                'type': ctype,
                'position': pos,
                'status': {'status': 'error', 'message': 'Unknown error'}
            })
            
    return jsonify({'results': results})

@api_bp.route('/exportar/<tipo>')
@jwt_required()  # Solo requiere autenticación
def exportar_excel(tipo):
    try:
        # Verificar permiso para exportar
        claims = get_jwt()
        permissions = claims.get("permissions", {})
        if not permissions.get('export_data', False):
            return jsonify({'error': 'No tiene permiso para exportar datos'}), 403
            
        output = ExportService.generar_excel(tipo)
        filename = f"{tipo}_report.xlsx"
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/api/battery_data')
@jwt_required()  # Solo requiere autenticación
def get_battery_data():
    conn = get_db_connection()
    try:
        # Verificar permiso para ver baterías
        claims = get_jwt()
        permissions = claims.get("permissions", {})
        if not permissions.get('view_batteries', False):
            return jsonify({
                "summary": {
                    "total": 0, "critical": 0, "caution": 0, 
                    "normal": 0, "no_data": 0, "access_count": 0, "transport_count": 0
                },
                "records": []
            })
        
        # ✅ Forzar modo READ ONLY para evitar locks
        conn.set_session(readonly=True)
        cur = conn.cursor()
        
        cur.execute("""
            WITH site_disc_alarms AS (
                SELECT sitio, COUNT(*) as disc_count
                FROM alarmas_activas
                WHERE estado = 'on' AND categoria LIKE 'Bateria%%disc.'
                GROUP BY sitio
            ),
            battery_alarm_counts AS (
                SELECT device_id, COUNT(*) as counts
                FROM alarmas_activas
                WHERE estado = 'on' AND (categoria LIKE 'Bateria%%')
                GROUP BY device_id
            )
            SELECT MAX(a.hora), a.tipo, a.region, a.sitio, 
                   COALESCE(NULLIF(a.deviceName, ''), t.nombre, 'Batería de Litio') as dispositivo,
                   a.alarma, t.soc, t.carga, t.descarga, t.ultimo_update, a.device_id,
                   COALESCE(bac.counts, 0) as active_battery_alarms,
                   CASE WHEN sda.disc_count > 0 THEN 1 ELSE 0 END as conexion
            FROM alarmas_activas a
            LEFT JOIN battery_telemetry t ON a.device_id = t.device_id AND a.sitio = t.sitio
                AND (LOWER(t.nombre) LIKE '%%bater%%' OR LOWER(t.nombre) LIKE '%%litio%%' OR LOWER(t.nombre) LIKE '%%lithium%%' OR LOWER(t.nombre) LIKE '%%bat%%')
            LEFT JOIN battery_alarm_counts bac ON a.device_id = bac.device_id
            LEFT JOIN site_disc_alarms sda ON a.sitio = sda.sitio
            WHERE a.estado = 'on' AND a.categoria = 'BATERIA BAJA'
            GROUP BY a.device_id, a.tipo, a.region, a.sitio, a.deviceName, t.nombre, a.alarma, t.soc, t.carga, t.descarga, t.ultimo_update, bac.counts, sda.disc_count
            ORDER BY MAX(a.hora) DESC
        """)
        rows = cur.fetchall()
        cur.close()  # ✅ Cerrar cursor antes de procesar
        
        records = []
        summary = {
            "total": 0,
            "critical": 0,
            "caution": 0,
            "normal": 0,
            "no_data": 0,
            "access_count": 0,
            "transport_count": 0
        }
        
        for row in rows:
            hora, tipo, region, sitio, dispositivo, alarma_desc, soc, carga, descarga, ultimo_update, device_id, active_battery_alarms, conexion = row
            
            umbral = 0.0
            if alarma_desc and "muy baja" in alarma_desc.lower():
                umbral = 29.0
            elif alarma_desc and "baja" in alarma_desc.lower():
                umbral = 49.0
            else:
                umbral = 30.0
            
            estado_label = "IDLE"
            if soc is None:
                estado_label = "NO DATA"
                summary["no_data"] += 1
            elif (carga or 0) > 0:
                estado_label = "CHARGING"
                summary["normal"] += 1
            elif (descarga or 0) > 0:
                estado_label = "DISCHARGING"
                summary["critical"] += 1
            else:
                estado_label = "IDLE"
                summary["caution"] += 1
            
            summary["total"] += 1
            if tipo == "access": 
                summary["access_count"] += 1
            else: 
                summary["transport_count"] += 1
            
            records.append({
                "hora": hora.strftime("%Y-%m-%d %H:%M:%S") if isinstance(hora, datetime) else hora,
                "tipo": tipo.capitalize() if tipo else "Unknown",
                "region": region,
                "sitio": sitio,
                "dispositivo": dispositivo,
                "alarma": alarma_desc,
                "umbral": umbral,
                "soc": soc,
                "estado": estado_label,
                "has_battery_alarm": active_battery_alarms > 0 if active_battery_alarms else False,
                "conexion": 1 if (conexion == 1 or conexion is True) else 0,
                "carga": carga,
                "descarga": descarga,
                "ultimo_update": ultimo_update.strftime("%Y-%m-%d %H:%M:%S") if isinstance(ultimo_update, datetime) else ultimo_update
            })

        return jsonify({
            "summary": summary,
            "records": records
        })
    except Exception as e:
        print(f"Error en get_battery_data: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e), "summary": {}, "records": []}), 500
    finally:
        conn.close()

@api_bp.route('/api/ac_data')
@jwt_required()
def get_ac_data():
    conn = get_db_connection()
    try:
        claims = get_jwt()
        permissions = claims.get("permissions", {})
        if not permissions.get('view_batteries', False):
            return jsonify({"records": [], "count": 0})

        # ✅ IMPORTANTE: Forzar modo READ ONLY para evitar locks
        conn.set_session(readonly=True)
        cur = conn.cursor()

        # 1️⃣ Traer todas las alarmas AC_FAIL/GE activas con priorización
        cur.execute("""
            SELECT 
                MAX(a.hora) AS max_hora, 
                a.tipo, 
                a.region, 
                a.sitio, 
                (ARRAY_AGG(a.deviceName ORDER BY CASE WHEN a.categoria = 'AC_FAIL' THEN 1 ELSE 2 END, a.hora DESC))[1] as deviceName,
                string_agg(DISTINCT a.alarma, ',') AS all_alarms,
                (ARRAY_AGG(a.device_id ORDER BY CASE WHEN a.categoria = 'AC_FAIL' THEN 1 ELSE 2 END, a.hora DESC))[1] as device_id,
                MAX(a.valor) AS max_valor
            FROM alarmas_activas a
            WHERE a.estado = 'on' AND a.categoria IN ('AC_FAIL', 'AC_FAIL_GE')
            GROUP BY a.sitio, a.tipo, a.region
            ORDER BY max_hora DESC
        """)
        alarm_rows = cur.fetchall()

        sitios = [row[3] for row in alarm_rows]
        if not sitios:
            return jsonify({"records": [], "count": 0})

        # ✅ CORRECCIÓN: Usar IN en lugar de ANY para evitar error de array
        if len(sitios) == 1:
            sitios_param = (sitios[0],)  # Tuple de un elemento requiere coma
        else:
            sitios_param = tuple(sitios)

        # 2️⃣ Traer toda la telemetría en una sola consulta usando IN
        cur.execute("""
            SELECT t.device_id, t.sitio, t.nombre, t.soc, t.carga, t.descarga, t.ultimo_update,
                   t.voltaje, t.svoltage, t.current1, t.current2, t.conexion
            FROM battery_telemetry t
            WHERE t.sitio IN %s
        """, (sitios_param,))
        telemetry_rows = cur.fetchall()

        # ✅ Cerrar cursor explícitamente antes de procesar (liberar recursos)
        cur.close()

        # 3️⃣ Procesar en memoria (ya sin conexión activa a DB)
        telemetry_by_sitio = {}
        for row in telemetry_rows:
            t_id, sitio, nombre, soc, carga, descarga, ultimo_update, voltaje, svolt, current1, current2, conexion = row
            if sitio not in telemetry_by_sitio:
                telemetry_by_sitio[sitio] = []
            
            # Manejar fechas None
            ultimo_update_str = None
            if ultimo_update and isinstance(ultimo_update, datetime):
                ultimo_update_str = ultimo_update.strftime("%Y-%m-%d %H:%M:%S")
            
            telemetry_by_sitio[sitio].append({
                "device_id": t_id,
                "nombre": nombre,
                "soc": soc,
                "carga": carga,
                "descarga": descarga,
                "ultimo_update": ultimo_update_str,
                "voltaje": voltaje,
                "svolt": svolt,
                "current1": current1,
                "current2": current2,
                "conexion": conexion
            })

        records = []
        for row in alarm_rows:
            hora, tipo, region, sitio, deviceName, all_alarms, device_id, max_valor = row
            
            # Formatear hora
            hora_str = hora.strftime("%Y-%m-%d %H:%M:%S") if isinstance(hora, datetime) else str(hora)

            site_telemetry = telemetry_by_sitio.get(sitio, [])
            baterias = []
            todos_los_voltajes = []
            site_svolt, site_current1, site_current2 = None, None, None
            site_volt_gen = None
            site_corriente_gen = None

            for b in site_telemetry:
                if b["voltaje"] is not None and b["voltaje"] > 0:
                    todos_los_voltajes.append(b["voltaje"])

                # Valores del sitio (primera batería que tenga valores)
                if site_svolt is None or (b["svolt"] is not None and b["svolt"] > 0):
                    site_svolt = b["svolt"]
                if site_current1 is None or (b["current1"] is not None and b["current1"] != 0):
                    site_current1 = b["current1"]
                if site_current2 is None or (b["current2"] is not None and b["current2"] != 0):
                    site_current2 = b["current2"]

                # Búsqueda selectiva: Identificar voltajes y corrientes de Grupo Electrógeno
                if b["nombre"] and 'Grupo Electrógeno' in b["nombre"]:
                    site_volt_gen = b["voltaje"]
                    site_corriente_gen = b["carga"]

                # Filtrar solo baterías (evitar rectificadores u otros equipos)
                # Mejorado: Chequear nombre del dispositivo o tipo si estuviera disponible
                nombre_bat = (b["nombre"] or "").lower()
                is_battery = any(word in nombre_bat for word in ['bater', 'lithium', 'litio', 'bat'])
                
                if is_battery:
                    # Para baterías ZTE, usar current1 para determinar carga/descarga si carga/descarga son None
                    # (El nuevo hilo de telemetría ya debería traer valores normalizados, pero mantenemos compatibilidad)
                    carga_val = b["carga"]
                    descarga_val = b["descarga"]
                    
                    if 'zte' in nombre_bat:
                        # Si current1 está presente, derivamos carga/descarga
                        if b["current1"] is not None:
                            if b["current1"] < 0:
                                descarga_val = abs(b["current1"])
                                carga_val = 0
                            elif b["current1"] > 0:
                                carga_val = b["current1"]
                                descarga_val = 0
                            else:
                                carga_val = 0
                                descarga_val = 0
                    
                    # Determinar estado
                    estado = "IDLE"
                    if b["soc"] is None:
                        estado = "NO DATA"
                    elif (carga_val or 0) > 0:
                        estado = "CHARGING"
                    elif (descarga_val or 0) > 0:
                        estado = "DISCHARGING"

                    baterias.append({
                        "device_id": b["device_id"],
                        "nombre": b["nombre"],
                        "soc": b["soc"],
                        "carga": carga_val,
                        "descarga": descarga_val,
                        "estado": estado,
                        "conexion": 1 if (b["conexion"] == 1 or b["conexion"] is True) else 0,
                        "ultimo_update": b["ultimo_update"]
                    })

            # Determinar voltaje final
            voltaje_final = None
            if max_valor is not None:
                try:
                    voltaje_final = float(max_valor)
                except:
                    pass

            if voltaje_final is None and all_alarms:
                matches = re.findall(r'(?:\()?\b(\d+(?:\.\d+)?)\s*V?\b(?:\))?', all_alarms)
                valores_encontrados = [float(v) for v in matches if 0 <= float(v) <= 500]
                if valores_encontrados:
                    voltaje_final = 0.0 if 0.0 in valores_encontrados else valores_encontrados[0]

            if todos_los_voltajes:
                voltaje_final = max(todos_los_voltajes)

            # Fallback final: Usar el voltaje del bus de sitio si no hay valor de alarma ni equipos soporte específicos
            if voltaje_final is None:
                voltaje_final = site_svolt

            alarma_display = f"{voltaje_final}V" if voltaje_final is not None else "N/A"

            records.append({
                "hora": hora_str,
                "tipo": tipo.capitalize() if tipo else "Unknown",
                "region": region,
                "sitio": sitio,
                "voltaje": alarma_display,
                "svoltaje": site_svolt,
                "voltaje_gen": site_volt_gen,
                "corriente_gen": site_corriente_gen,
                "current1": site_current1,
                "current2": site_current2,
                "baterias": baterias
            })

        return jsonify({
            "records": records,
            "count": len(records)
        })

    except Exception as e:
        # Loggear el error
        print(f"Error en get_ac_data: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e), "records": [], "count": 0}), 500
    finally:
        conn.close()

@api_bp.route('/api/hvac_data')
@jwt_required()
def get_hvac_data():
    try:
        claims = get_jwt()
        permissions = claims.get("permissions", {})
        
        # Deny access if user is not admin and lacks view_hvac permission
        if not (claims.get("role") == "admin" or permissions.get("view_hvac", False)):
            return jsonify({"msg": "Forbidden: Requires view_hvac permission"}), 403

        from app.services.hvac_service import HvacService
        data = HvacService.get_current_data()
        return jsonify({"records": data, "count": len(data)})
    except Exception as e:
        import traceback
        logging.error(f"Error en get_hvac_data: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": str(e), "records": [], "count": 0}), 500
@api_bp.route('/api/disconnection_data')
@jwt_required()
def get_disconnection_data():
    from flask import request
    """
    Obtiene las alarmas de baterías desconectadas (Bateria Lit. disc.)
    Query params opcionales: region, tipo
    """
    try:
        # Verificar permiso para ver baterías
        claims = get_jwt()
        permissions = claims.get("permissions", {})
        if not permissions.get('view_batteries', False):
            return jsonify({"records": [], "count": 0})
        
        # Obtener filtros de query string
        filtro_region = request.args.get('region')
        filtro_tipo = request.args.get('tipo')
        
        # Obtener datos
        records = MonitoringService.obtener_datos_desconexion(filtro_region, filtro_tipo)
        
        return jsonify({
            "records": records,
            "count": len(records)
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e), "records": [], "count": 0}), 500


@api_bp.route('/exportar/disconnection')
@jwt_required()
def exportar_excel_desconexion():
    """
    Exporta a Excel las alarmas de baterías desconectadas
    Query params opcionales: region, tipo
    """
    from flask import request
    try:
        # Verificar permiso para exportar
        claims = get_jwt()
        permissions = claims.get("permissions", {})
        if not permissions.get('export_data', False):
            return jsonify({'error': 'No tiene permiso para exportar datos'}), 403
        
        # Obtener filtros de query string
        filtro_region = request.args.get('region')
        filtro_tipo = request.args.get('tipo')
        
        # Generar Excel
        output = ExportService.generar_excel_desconexion(filtro_region, filtro_tipo)
        filename = f"baterias_desconectadas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500