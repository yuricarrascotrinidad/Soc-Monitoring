# app/utils/rbac_utils.py
from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt, verify_jwt_in_request

def admin_required():
    """
    Decorador para verificar que el usuario sea administrador
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            
            # Verificar si es admin
            if claims.get("role") != "admin":
                return jsonify({"msg": "Admin access required"}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def api_permission_required(permission_name):
    """
    Decorador para verificar que el usuario tenga un permiso específico de API
    AHORA ES OPCIONAL - SOLO FILTRA, NO BLOQUEA
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            
            # Admin siempre tiene acceso
            if claims.get("role") == "admin":
                return f(*args, **kwargs)
            
            permissions = claims.get("permissions", {})
            
            # Si no tiene el permiso, devolver datos vacíos en lugar de bloquear
            if not permissions.get(permission_name, False):
                # Para endpoints que devuelven JSON, retornar estructura vacía
                if permission_name == "view_batteries":
                    return jsonify({
                        "summary": {
                            "total": 0, "critical": 0, "caution": 0, 
                            "normal": 0, "no_data": 0, "access_count": 0, "transport_count": 0
                        },
                        "records": []
                    })
                elif permission_name == "view_cameras":
                    return jsonify({'access': [], 'transport': []})
                elif permission_name == "export_data_api":
                    return jsonify({"msg": "No tiene permiso para exportar"}), 403
                elif permission_name == "get_dashboard_state":
                    # Para dashboard, devolver estructura básica sin datos sensibles
                    return jsonify({
                        "access": {"eventos": [], "anomalias": []},
                        "transport": {"eventos": [], "anomalias": []},
                        "ac_failures_count": 0,
                        "battery_alerts_count": 0,
                        "cameras": {"access": [], "transport": []},
                        "timestamp": None,
                        "connection_errors": {}
                    })
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def filter_response_data(data, permissions):
    """
    Filtra datos sensibles según permisos del usuario
    """
    if not permissions:
        return data
    
    # Si es admin, no filtrar nada
    if permissions.get("admin_users", False):
        return data
    
    # Hacer una copia para no modificar el original
    if isinstance(data, dict):
        filtered_data = data.copy()
    else:
        filtered_data = data
    
    # Filtrar según permisos
    if isinstance(filtered_data, dict):
        if not permissions.get('view_batteries', False):
            # Ocultar contadores de baterías
            filtered_data['battery_alerts_count'] = 0
            filtered_data['ac_failures_count'] = 0
            filtered_data['disconnection_count'] = 0
            
            # Ocultar datos de baterías en las secciones
            if 'access' in filtered_data and isinstance(filtered_data['access'], dict):
                if 'anomalias' in filtered_data['access']:
                    filtered_data['access']['anomalias'] = [
                        a for a in filtered_data['access']['anomalias'] 
                        if 'bateria' not in a.get('categoria', '').lower()
                    ]
            if 'transport' in filtered_data and isinstance(filtered_data['transport'], dict):
                if 'anomalias' in filtered_data['transport']:
                    filtered_data['transport']['anomalias'] = [
                        a for a in filtered_data['transport']['anomalias'] 
                        if 'bateria' not in a.get('categoria', '').lower()
                    ]
        
        if not permissions.get('view_cameras', False):
            # Ocultar datos de cámaras
            if 'cameras' in filtered_data:
                filtered_data['cameras'] = {'access': [], 'transport': []}
    
    return filtered_data