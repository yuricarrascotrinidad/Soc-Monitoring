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
from app.utils.rbac_utils import filter_response_data, api_permission_required

api_bp = Blueprint('api', __name__)

def obtener_datos_completos(db_type):
    """
    Replica la lógica de 'obtener_datos' del app.py original.
    Devuelve {eventos: [], anomalias: []}
    """
    # This function is now partially replaced by MonitoringService.obtener_datos_completos_v2
    # but kept for compatibility if needed by other local routes not yet updated.
    # However, since we moved the main logic to MonitoringService, we can decide to keep or remove it.
    # For now, let's keep it to avoid breaking other potential local callers, 
    # but the main API uses the cache from MonitoringService.
    return MonitoringService.obtener_datos_completos_v2(db_type)

@api_bp.route('/datos')
def get_data():
    try:
        return get_dashboard_state()
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@api_bp.route('/api/dashboard_state')
@jwt_required()
@api_permission_required('get_dashboard_state')
def get_dashboard_state():
    try:
        data = MonitoringService.get_cached_dashboard_state()
        
        # Si la cache aún no se ha generado (primeros segundos), calcularla on-demand una vez
        if data is None:
            # logging.info("Cache asíncrona vacía, calculando síncronamente por primera vez...")
            from flask import current_app
            data = MonitoringService._calculate_dashboard_state()
            
        # Filtrar datos según permisos del JWT
        claims = get_jwt()
        permissions = claims.get("permissions", {})
        filtered_data = filter_response_data(data, permissions)
        
        return jsonify(filtered_data)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@api_bp.route('/cameras')
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
        
        return jsonify({
            'access': access_cameras,
            'transport': transport_cameras
        })
    finally:
        conn.close()

@api_bp.route('/api/camera_status')
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
    
    try:
        # Use Cached Service
        status = CameraService.get_camera_status(site, camera_type, position)
        return jsonify(status)
    except Exception as e:
        return jsonify({
            'status': 'no_config',
            'ip': None,
            'message': f'Error: {str(e)}'
        }), 500

@api_bp.route('/api/camera_status/batch', methods=['POST'])
def check_camera_status_batch():
    """
    Check multiple cameras. Expects JSON: { "cameras": [ {site, type, position}, ... ] }
    """
    from flask import request
    
    data = request.json
    results = []
    
    if not data or 'cameras' not in data:
        return jsonify({'error': 'Invalid data'}), 400
        
    for cam in data['cameras']:
        site = cam.get('site')
        ctype = cam.get('type', 'access')
        pos = cam.get('position', 'principal')
        
        try:
             # Fast cached lookup
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
@jwt_required()
@api_permission_required('export_data_api')
def exportar_excel(tipo):
    try:
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
@jwt_required()
@api_permission_required('get_battery_history')
def get_battery_data():
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        # Join alarmas with battery_telemetry to get real-time info
        # Also check if there are other active alarms of category 'Bateria' for the same device
        # Use CTE to pre-calculate active battery alarm counts to avoid N+1 subquery overhead
        # This is strictly necessary for large databases (1.5M+ rows)
        # Use MAX(a.hora) and GROUP BY device_id to ensure only one row per battery is returned
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
            LEFT JOIN battery_telemetry t ON a.device_id = t.device_id
            LEFT JOIN battery_alarm_counts bac ON a.device_id = bac.device_id
            LEFT JOIN site_disc_alarms sda ON a.sitio = sda.sitio
            WHERE a.estado = 'on' AND a.categoria = 'BATERIA BAJA'
            GROUP BY a.device_id, a.tipo, a.region, a.sitio, a.deviceName, t.nombre, a.alarma, t.soc, t.carga, t.descarga, t.ultimo_update, bac.counts, sda.disc_count
            ORDER BY MAX(a.hora) DESC
        """)
        rows = cur.fetchall()
        
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
            
            # Use SOC threshold only for reference metadata, but base Status on current flow
            umbral = 0.0
            if "muy baja" in alarma_desc.lower():
                umbral = 29.0
            elif "baja" in alarma_desc.lower():
                umbral = 49.0
            else:
                umbral = 30.0
            
            # Status Logic matched with Dashboard expectations
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
            if tipo == "access": summary["access_count"] += 1
            else: summary["transport_count"] += 1
            
            records.append({
                "hora": hora.strftime("%Y-%m-%d %H:%M:%S") if isinstance(hora, datetime) else hora,
                "tipo": tipo.capitalize(),
                "region": region,
                "sitio": sitio,
                "dispositivo": dispositivo,
                "alarma": alarma_desc,
                "umbral": umbral,
                "soc": soc,
                "estado": estado_label,
                "has_battery_alarm": active_battery_alarms > 0,
                "conexion": conexion,
                "carga": carga,
                "descarga": descarga,
                "ultimo_update": ultimo_update.strftime("%Y-%m-%d %H:%M:%S") if isinstance(ultimo_update, datetime) else ultimo_update
            })
            
        # Filtrar datos según permisos del JWT
        claims = get_jwt()
        permissions = claims.get("permissions", {})
        filtered_records = filter_response_data(records, permissions)

        return jsonify({
            "summary": summary,
            "records": filtered_records
        })
    finally:
        conn.close()

@api_bp.route('/api/ac_data')
@jwt_required()
@api_permission_required('get_ac_data')
def get_ac_data():
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        # Obtener fallas de AC activas agrupadas por sitio
        # Incluimos el valor de voltaje en el agrupamiento para mostrarlo
        cur.execute("""
            SELECT MAX(a.hora), a.tipo, a.region, a.sitio, a.deviceName, 
                   string_agg(DISTINCT a.alarma, ',') as all_alarms, 
                   a.device_id,
                   MAX(a.valor) as max_valor
            FROM alarmas_activas a
            WHERE a.estado = 'on' AND a.categoria = 'AC_FAIL'
            GROUP BY a.sitio, a.tipo, a.region, a.deviceName, a.device_id
            ORDER BY MAX(a.hora) DESC
        """)
        rows = cur.fetchall()
        
        records = []
        for row in rows:
            hora, tipo, region, sitio, deviceName, alarma, device_id, max_valor = row
            
            # Buscar todos los dispositivos asociados a este sitio para obtener el voltaje real
            cur.execute("""
                SELECT t.device_id, t.nombre, t.soc, t.carga, t.descarga, t.ultimo_update, t.voltaje, t.svoltage, t.current1, t.current2, t.conexion
                FROM battery_telemetry t
                WHERE t.sitio = %s
            """, (sitio,))
            all_telemetry_rows = cur.fetchall()
            
            baterias = []
            todos_los_voltajes = []
            
            # Inicializar valores de telemetría del sitio
            site_svolt, site_current1, site_current2 = None, None, None
            
            for b_row in all_telemetry_rows:
                b_id, b_nombre, b_soc, b_carga, b_descarga, b_update, b_volt, b_svolt, b_current1, b_current2, b_conexion = b_row
                
                # Recolectar voltajes para el cálculo global del sitio
                if b_volt is not None and b_volt > 0: todos_los_voltajes.append(b_volt)
                
                # Actualizar valores del sitio (preferir rectificador o primer valor no nulo)
                if site_svolt is None or (b_svolt is not None and b_svolt > 0): site_svolt = b_svolt
                if site_current1 is None or (b_current1 is not None and b_current1 != 0): site_current1 = b_current1
                if site_current2 is None or (b_current2 is not None and b_current2 != 0): site_current2 = b_current2
                
                # Solo agregar a la lista visible si es una batería (según pedido previo del usuario)
                if b_nombre and any(word in b_nombre.lower() for word in ['bater', 'lithium', 'litio']):
                    # Determinar estado de la batería
                    estado = "IDLE"
                    if b_soc is None: estado = "NO DATA"
                    elif (b_carga or 0) > 0: estado = "CHARGING"
                    elif (b_descarga or 0) > 0: estado = "DISCHARGING"
                    
                    baterias.append({
                        "device_id": b_id,
                        "nombre": b_nombre,
                        "soc": b_soc,
                        "carga": b_carga,
                        "descarga": b_descarga,
                        "ultimo_update": b_update,
                        "estado": estado,
                        "conexion": b_conexion
                    })
            
            # Extraer voltaje de forma robusta
            voltaje_final = None
            
            # 1. Prioridad: Usar el campo valor de la alarma (ya que viene directo del meteValue de la API original)
            if max_valor is not None:
                try: voltaje_final = float(max_valor)
                except: pass
            
            # 2. Respaldo: Intentar extraer desde la cadena de alarmas (regex)
            if voltaje_final is None and alarma:
                # Buscar patrones como (220.0V), 220.0V, (0.0), etc.
                matches = re.findall(r'(?:\()?\b(\d+(?:\.\d+)?)\s*V?\b(?:\))?', alarma)
                if matches:
                    valores_encontrados = [float(v) for v in matches if 0 <= float(v) <= 500]
                    if valores_encontrados:
                        if 0.0 in valores_encontrados: voltaje_final = 0.0
                        else: voltaje_final = valores_encontrados[0]
            
            # 3. Prioridad Máxima: Si tenemos un voltaje real (> 0) en telemetría (baterías o rectificadores), usarlo
            if todos_los_voltajes:
                # Si hay voltajes reales, preferimos el más alto (generalmente el de bus/rectificador si AC falló)
                voltaje_final = max(todos_los_voltajes)
            elif (voltaje_final is None or voltaje_final == 0) and any(r[6] == 0 for r in all_telemetry_rows):
                # Si no hay voltajes positivos, pero algún sensor dice 0 explícitamente
                voltaje_final = 0.0
 
            # Formatear el resultado final
            if voltaje_final is not None:
                alarma_display = f"{voltaje_final}V"
            else:
                # No hay voltaje numérico. Nunca mostrar el texto crudo de la alarma.
                alarma_display = "N/A"
 
            records.append({
                "hora": hora.strftime("%Y-%m-%d %H:%M:%S") if isinstance(hora, datetime) else hora,
                "tipo": tipo.capitalize(),
                "region": region,
                "sitio": sitio,
                "voltaje": alarma_display,
                "svoltaje": site_svolt,
                "current1": site_current1,
                "current2": site_current2,
                "baterias": [
                    {
                        "device_id": b["device_id"],
                        "nombre": b["nombre"],
                        "soc": b["soc"],
                        "carga": b["carga"],
                        "descarga": b["descarga"],
                        "estado": b["estado"],
                        "conexion": b["conexion"],
                        "ultimo_update": b["ultimo_update"].strftime("%Y-%m-%d %H:%M:%S") if isinstance(b["ultimo_update"], datetime) else b["ultimo_update"]
                    } for b in baterias
                ]
            })
            
        # Filtrar datos según permisos del JWT
        claims = get_jwt()
        permissions = claims.get("permissions", {})
        filtered_records = filter_response_data(records, permissions)

        return jsonify({
            "records": filtered_records,
            "count": len(filtered_records)
        })
    finally:
        conn.close()
