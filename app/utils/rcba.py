from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt, get_jwt_identity, verify_jwt_in_request
import logging

def admin_required():
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            if claims.get("role") == "admin":
                return fn(*args, **kwargs)
            else:
                return jsonify(msg="Admin required"), 403
        return decorator
    return wrapper

def permission_required(permission):
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            permissions = claims.get("permissions", {})
            if permissions.get(permission):
                return fn(*args, **kwargs)
            else:
                return jsonify(msg=f"Permission '{permission}' required"), 403
        return decorator
    return wrapper

def api_permission_required(api_name):
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            permissions = claims.get("permissions", {})
            
            # For admin, grant all
            if claims.get("role") == "admin":
                return fn(*args, **kwargs)
                
            api_access = permissions.get("api_access", {})
            if api_access.get(api_name):
                return fn(*args, **kwargs)
            else:
                return jsonify(msg=f"API access for '{api_name}' required"), 403
        return decorator
    return wrapper

def filter_response_data(data, permissions):
    """
    Remove keys from JSON data based on user permissions.
    If 'can_view_sensitive' is False, remove some keys.
    """
    if not isinstance(data, (dict, list)):
        return data

    can_view_sensitive = permissions.get("can_view_sensitive", False)
    
    if isinstance(data, list):
        return [filter_response_data(item, permissions) for item in data]
    
    # Define keys to filter if no sensitive access
    sensitive_keys = ["device_id", "url", "ip", "password"] # Examples
    
    filtered_data = {}
    for key, value in data.items():
        if key in sensitive_keys and not can_view_sensitive:
            continue
        
        # Recursive filtering
        if isinstance(value, (dict, list)):
            filtered_data[key] = filter_response_data(value, permissions)
        else:
            filtered_data[key] = value
            
    return filtered_data
