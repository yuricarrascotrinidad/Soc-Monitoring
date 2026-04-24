from flask import Blueprint, jsonify, send_file
import logging
from psycopg2 import extras
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
        cur.execute("SELECT id, site, ip FROM access_cameras")
        access_cameras = [{"id": row[0], "site": row[1], "ip": row[2]} for row in cur.fetchall()]
        
        # Transport Cameras
        cur.execute("SELECT id, site, position, ip FROM transport_cameras")
        transport_cameras = [{"id": row[0], "site": row[1], "position": row[2], "ip": row[3]} for row in cur.fetchall()]
        
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
            
            # Filtro Global: Omitir dispositivos virtuales/agregados (_Battery)
            if dispositivo and str(dispositivo).strip().endswith('_Battery'):
                continue

            
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

        # 2️⃣ Traer toda la telemetría de todas las fuentes posibles (Prioridad, Rectificadores, Global)
        cur.execute("""
            SELECT t.device_id, t.sitio, t.nombre, t.soc, t.carga, t.descarga, t.ultimo_update,
                   t.voltaje, t.svoltage, t.current1, t.current2, t.conexion,
                   t.tipo_dispositivo, t.voltaje_gen, t.corriente_gen, 1 as source_priority
            FROM battery_telemetry t
            WHERE t.sitio IN %s
            UNION ALL
            SELECT r.device_id, r.sitio, r.nombre, NULL as soc, NULL as carga, NULL as descarga, r.ultimo_update,
                   r.voltaje, r.svoltage, r.current1, r.current2, r.conexion,
                   r.tipo_dispositivo, NULL as voltaje_gen, NULL as corriente_gen, 2 as source_priority
            FROM rectifier_telemetry r
            WHERE r.sitio IN %s
            UNION ALL
            SELECT g.device_id, g.sitio, g.nombre, g.soc, NULL as carga, NULL as descarga, g.ultimo_update,
                   NULL as voltaje, NULL as svoltage, NULL as current1, NULL as current2, g.conexion,
                   g.tipo_dispositivo, NULL as voltaje_gen, NULL as corriente_gen, 3 as source_priority
            FROM battery_telemetry_global g
            WHERE g.sitio IN %s
            ORDER BY source_priority ASC
        """, (sitios_param, sitios_param, sitios_param))
        telemetry_rows = cur.fetchall()

        # ✅ Cerrar cursor explícitamente antes de procesar (liberar recursos)
        cur.close()

        # 3️⃣ Procesar en memoria (ya sin conexión activa a DB)
        telemetry_by_sitio = {}
        dispositivos_procesados = set() # (sitio, device_id, nombre)

        for row in telemetry_rows:
            t_id, sitio, nombre, soc, carga, descarga, ultimo_update, voltaje, svolt, current1, current2, conexion, td, v_gen, c_gen, _prio = row
            
            # Evitar duplicados: Si ya tenemos este equipo de una fuente con mayor prioridad, ignorar el resto
            key = (sitio, t_id, nombre)
            if key in dispositivos_procesados:
                continue
            dispositivos_procesados.add(key)

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
                "conexion": conexion,
                "tipo_dispositivo": td,
                "voltaje_gen": v_gen,
                "corriente_gen": c_gen
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
                # Omitir registros agregados _Battery en la lista de baterías individuales
                if b["nombre"] and b["nombre"].strip().endswith('_Battery'):
                    continue

                # Priorizar valores del Rectificador para el Encabezado del Sitio
                if b["tipo_dispositivo"] == 'Rectificador':
                    # site_svolt debe ser lo que el dashboard muestra como "Voltaje" o "Svoltaje"
                    if site_svolt is None or (b["svolt"] is not None and b["svolt"] > 0):
                        site_svolt = b["svolt"]
                    
                    if site_current1 is None or (b["current1"] is not None and b["current1"] != 0):
                        site_current1 = b["current1"]
                    if site_current2 is None or (b["current2"] is not None and b["current2"] != 0):
                        site_current2 = b["current2"]
                    
                    # Para el voltaje principal del sitio (en la columna "Voltaje")
                    if b["voltaje"] is not None:
                        todos_los_voltajes.append(b["voltaje"])
                    elif b["svolt"] is not None and b["svolt"] > 0:
                        todos_los_voltajes.append(b["svolt"])

                # Priorizar valores del Generador
                if b["tipo_dispositivo"] == 'Generador':
                    site_volt_gen = b["voltaje_gen"]
                    site_corriente_gen = b["corriente_gen"]

                # Identificar Baterías
                if b["tipo_dispositivo"] in ['Litio', 'ZTE']:
                    baterias.append({
                        "device_id": b["device_id"],
                        "nombre": b["nombre"],
                        "soc": b["soc"],
                        "carga": b["carga"],
                        "descarga": b["descarga"],
                        "estado": "DISCHARGING" if (b["descarga"] or 0) > 0 else "CHARGING" if (b["carga"] or 0) > 0 else "IDLE" if b["soc"] is not None else "NO DATA",
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

@api_bp.route('/api/cameras/manage', methods=['POST'])
@jwt_required()
def manage_cameras():
    from flask import request
    try:
        claims = get_jwt()
        if claims.get("role") != "admin":
            return jsonify({"error": "Forbidden: Requires admin role"}), 403

        data = request.json
        action = data.get('action')
        c_type = data.get('type')
        c_id = data.get('id')
        site = data.get('site')
        ip = data.get('ip')
        position = data.get('position')

        if not action or c_type not in ['access', 'transport']:
            return jsonify({'error': 'Invalid payload'}), 400

        conn = get_db_connection()
        cur = conn.cursor()

        try:
            if action == 'delete':
                if not c_id: return jsonify({'error': 'ID required for deletion'}), 400
                table = 'access_cameras' if c_type == 'access' else 'transport_cameras'
                cur.execute(f"DELETE FROM {table} WHERE id = %s", (c_id,))
                
            elif action == 'create':
                if not site or not ip: return jsonify({'error': 'Missing fields'}), 400
                if c_type == 'access':
                    cur.execute("INSERT INTO access_cameras (site, ip) VALUES (%s, %s)", (site, ip))
                else:
                    cur.execute("INSERT INTO transport_cameras (site, position, ip) VALUES (%s, %s, %s)", (site, position or '', ip))
                    
            elif action == 'edit':
                if not c_id or not site or not ip: return jsonify({'error': 'Missing fields'}), 400
                if c_type == 'access':
                    cur.execute("UPDATE access_cameras SET site = %s, ip = %s WHERE id = %s", (site, ip, c_id))
                else:
                    cur.execute("UPDATE transport_cameras SET site = %s, position = %s, ip = %s WHERE id = %s", (site, position or '', ip, c_id))
            else:
                return jsonify({'error': 'Invalid action'}), 400

            conn.commit()
            return jsonify({'success': True})
        except Exception as query_error:
            conn.rollback()
            raise query_error
        finally:
            cur.close()
            conn.close()

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@api_bp.route('/api/battery_show_data')
@jwt_required()
def get_battery_show_data():
    """
    Endpoint para show_battery.html - Los datos vienen del nuevo BatteryService
    """
    conn = get_db_connection()
    try:
        claims = get_jwt()
        permissions = claims.get("permissions", {})
        if not permissions.get('view_batteries', False):
            return jsonify({
                "summary": {"total": 0, "critical": 0, "caution": 0, "normal": 0, "no_data": 0, "access_count": 0, "transport_count": 0},
                "records": []
            })
        
        conn.set_session(readonly=True)
        cur = conn.cursor(cursor_factory=extras.RealDictCursor)
        
        # Obtener telemetría de todos los sitios (Modo Global - 1h)
        cur.execute("""
            SELECT 
                t.*,
                (SELECT COUNT(*) FROM alarmas_activas a WHERE a.device_id = t.device_id AND a.sitio = t.sitio AND a.estado = 'on') as alarm_count
            FROM battery_telemetry_global t
            ORDER BY t.ultimo_update DESC
        """)
        rows = cur.fetchall()
        cur.close()
        
        records = []
        summary = {
            "total": 0, "critical": 0, "caution": 0, "normal": 0, "no_data": 0,
            "access_count": 0, "transport_count": 0, "rectifiers": 0, "litio": 0, "zte": 0
        }
        
        for row in rows:
            # Filtrar dispositivos con nombre terminado en _Battery (ej: A3444_Battery)
            if row['nombre'] and row['nombre'].strip().endswith('_Battery'):
                continue

            # Determinación de estado simplificada para el dashboard
            estado_label = "IDLE"
            soc = row['soc'] if 'soc' in row else None
            carga = row['carga'] if 'carga' in row else None
            descarga = row['descarga'] if 'descarga' in row else None
            tipo_dispositivo = row['tipo_dispositivo'] if 'tipo_dispositivo' in row else None
            
            if soc is None:
                if tipo_dispositivo == 'Rectificador':
                    estado_label = "NORMAL" # Rectificadores no tienen SOC
                else:
                    estado_label = "NO DATA"
            elif (carga or 0) > 0:
                estado_label = "CHARGING"
            elif (descarga or 0) > 0:
                estado_label = "DISCHARGING"
            else:
                estado_label = "IDLE"

            # Actualizar summary
            summary["total"] += 1
            if estado_label == "DISCHARGING": summary["critical"] += 1
            elif estado_label == "CHARGING": summary["normal"] += 1
            elif estado_label == "IDLE": summary["caution"] += 1
            elif estado_label == "NO DATA": summary["no_data"] += 1
            
            if 'tipo_sistema' in row and row['tipo_sistema'] == "access": summary["access_count"] += 1
            else: summary["transport_count"] += 1

            if tipo_dispositivo == 'Rectificador': summary["rectifiers"] += 1
            elif tipo_dispositivo == 'Litio': summary["litio"] += 1
            elif tipo_dispositivo == 'ZTE': summary["zte"] += 1
            
            records.append({
                "hora": row['ultimo_update'].strftime("%Y-%m-%d %H:%M:%S") if ('ultimo_update' in row and row['ultimo_update']) else "N/A",
                "tipo": row['tipo_sistema'].capitalize() if ('tipo_sistema' in row and row['tipo_sistema']) else "Unknown",
                "region": row['region'] if 'region' in row else None,
                "sitio": row['sitio'] if 'sitio' in row else None,
                "dispositivo": row['nombre'] if 'nombre' in row else None,
                "tipo_dispositivo": tipo_dispositivo,
                "soc": soc,
                "capacidad": f"{row['capacidad']:.1f} Ah" if ('capacidad' in row and row['capacidad']) else None,
                "estado": estado_label,
                "has_battery_alarm": (row['alarm_count'] if 'alarm_count' in row else 0) > 0,
                "conexion": 1 if ('conexion' in row and row['conexion'] == 1) else 0,
                "carga": carga,
                "descarga": descarga,
                "voltaje": row['voltaje'] if 'voltaje' in row else None,
                "svoltage": row['svoltage'] if 'svoltage' in row else None,
                "current1": row['current1'] if 'current1' in row else None,
                "current2": row['current2'] if 'current2' in row else None,
                "voltaje_gen": row['voltaje_gen'] if 'voltaje_gen' in row else None,
                "corriente_gen": row['corriente_gen'] if 'corriente_gen' in row else None
            })

        return jsonify({
            "summary": summary,
            "records": records
        })
    except Exception as e:
        import traceback
        logging.error(f"Error en get_battery_show_data: {str(e)}")
        traceback.print_exc()
        return jsonify({"error": str(e), "summary": {}, "records": []}), 500
    finally:
        conn.close()

@api_bp.route('/api/rectifier_data')
@jwt_required()
def get_rectifier_data():
    """
    Endpoint para rectifier_monitor.html
    """
    conn = get_db_connection()
    try:
        claims = get_jwt()
        permissions = claims.get("permissions", {})
        if not permissions.get('view_batteries', False):
            return jsonify({"records": [], "summary": {}})
        
        conn.set_session(readonly=True)
        cur = conn.cursor(cursor_factory=extras.RealDictCursor)
        
        cur.execute("""
            SELECT * FROM rectifier_telemetry 
            ORDER BY sitio ASC, nombre ASC
        """)
        rows = cur.fetchall()
        cur.close()
        
        records = []
        summary = {"total": 0, "access": 0, "transport": 0, "low_voltage": 0}
        
        for row in rows:
            # Filtrar dispositivos con nombre terminado en _Battery (ej: A3444_Battery)
            if row['nombre'] and row['nombre'].strip().endswith('_Battery'):
                continue
                
            summary["total"] += 1
            if row['tipo_sistema'] == 'access': summary["access"] += 1
            else: summary["transport"] += 1
            
            v1 = row['voltaje'] if ('voltaje' in row and row['voltaje'] is not None) else None
            v2 = row['svoltage'] if ('svoltage' in row and row['svoltage'] is not None) else None
            
            # Alerta si el voltaje es menor a 48V (incluyendo 0V que es falla total)
            if (v1 is not None and v1 < 48) or (v2 is not None and v2 < 48):
                summary["low_voltage"] += 1
                
            records.append({
                "hora": row['ultimo_update'].strftime("%Y-%m-%d %H:%M:%S") if row['ultimo_update'] else "N/A",
                "sitio": row['sitio'],
                "dispositivo": row['nombre'],
                "region": row['region'],
                "tipo": row['tipo_sistema'].capitalize() if row['tipo_sistema'] else "Unknown",
                "v1": row['voltaje'],
                "v2": row['svoltage'],
                "c1": row['current1'],
                "c2": row['current2'],
                "conexion": row['conexion']
            })
            
        return jsonify({"records": records, "summary": summary})
    except Exception as e:
        import traceback
        logging.error(f"Error en get_rectifier_data: {e}")
        traceback.print_exc()
        return jsonify({"records": [], "summary": {}}), 500
    finally:
        conn.close()