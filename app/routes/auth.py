from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt
from werkzeug.security import check_password_hash, generate_password_hash
from app.utils.db import get_db_connection
from app.utils.rbac_utils import admin_required
import logging

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    username = request.json.get('username')
    password = request.json.get('password')
    
    if not username or not password:
        return jsonify({"msg": "Missing username or password"}), 400
    
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT password_hash, role, permissions FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        
        if user and check_password_hash(user[0], password):
            # Create token with additional claims
            role = user[1]
            permissions = user[2]
            
            access_token = create_access_token(
                identity=username,
                additional_claims={"role": role, "permissions": permissions}
            )
            return jsonify(access_token=access_token, role=role, permissions=permissions)
        
        return jsonify({"msg": "Bad username or password"}), 401
    finally:
        cur.close()
        conn.close()

@auth_bp.route('/admin/users', methods=['GET'])
@admin_required()
def list_users():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, username, role, permissions, created_at, first_name, last_name FROM users ORDER BY id ASC")
        users = cur.fetchall()
        user_list = []
        for u in users:
            user_list.append({
                "id": u[0],
                "username": u[1],
                "role": u[2],
                "permissions": u[3],
                "created_at": u[4].isoformat() if u[4] else None,
                "first_name": u[5],
                "last_name": u[6]
            })
        return jsonify(user_list)
    except Exception as e:
        return jsonify({"msg": f"Error: {str(e)}"}), 500
    finally:
        cur.close()
        conn.close()

@auth_bp.route('/admin/users', methods=['POST'])
@admin_required()
def create_user():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    role_name = data.get('role', 'viewer')
    permissions = data.get('permissions')
    
    if not username or not password:
        return jsonify({"msg": "Missing username or password"}), 400
        
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # If no perms provided, fetch from roles table
        if permissions is None:
            cur.execute("SELECT permissions FROM roles WHERE name = %s", (role_name,))
            role_data = cur.fetchone()
            permissions = role_data[0] if role_data else {}

        password_hash = generate_password_hash(password)
        cur.execute("""
            INSERT INTO users (username, password_hash, role, permissions, first_name, last_name)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (username) DO NOTHING
            RETURNING id;
        """, (username, password_hash, role_name, json.dumps(permissions), first_name, last_name))
        
        result = cur.fetchone()
        if not result:
            return jsonify({"msg": "User already exists"}), 409
            
        conn.commit()
        return jsonify({"msg": "User created successfully", "id": result[0]}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"msg": f"Error: {str(e)}"}), 500
    finally:
        cur.close()
        conn.close()

@auth_bp.route('/admin/users/<int:user_id>', methods=['PUT'])
@admin_required()
def update_user(user_id):
    data = request.json
    username = data.get('username')
    password = data.get('password')
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    role_name = data.get('role')
    permissions = data.get('permissions')
    
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        updates = []
        params = []
        
        if username:
            updates.append("username = %s")
            params.append(username)
        if password: # Password Reset logic
            updates.append("password_hash = %s")
            params.append(generate_password_hash(password))
        if first_name:
            updates.append("first_name = %s")
            params.append(first_name)
        if last_name:
            updates.append("last_name = %s")
            params.append(last_name)
        if role_name:
            updates.append("role = %s")
            params.append(role_name)
            
            # If role is updated but no perms provided, fetch new role defaults
            if permissions is None:
                cur.execute("SELECT permissions FROM roles WHERE name = %s", (role_name,))
                role_data = cur.fetchone()
                if role_data:
                    permissions = role_data[0]

        if permissions is not None:
            updates.append("permissions = %s")
            params.append(json.dumps(permissions))
            
        if not updates:
            return jsonify({"msg": "No data to update"}), 400
            
        params.append(user_id)
        query = f"UPDATE users SET {', '.join(updates)} WHERE id = %s"
        cur.execute(query, tuple(params))
        
        if cur.rowcount == 0:
            return jsonify({"msg": "User not found"}), 404
            
        conn.commit()
        return jsonify({"msg": "User updated successfully"})
    except Exception as e:
        conn.rollback()
        return jsonify({"msg": f"Error: {str(e)}"}), 500
    finally:
        cur.close()
        conn.close()

@auth_bp.route('/admin/users/<int:user_id>', methods=['DELETE'])
@admin_required()
def delete_user(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM users WHERE id = %s AND username != 'admin'", (user_id,))
        if cur.rowcount == 0:
            return jsonify({"msg": "User not found or cannot delete admin"}), 404
        conn.commit()
        return jsonify({"msg": "User deleted successfully"})
    except Exception as e:
        conn.rollback()
        return jsonify({"msg": f"Error: {str(e)}"}), 500
    finally:
        cur.close()
        conn.close()

# --- New Roles CRUD ---

@auth_bp.route('/admin/roles', methods=['GET'])
@admin_required()
def list_roles():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, name, permissions FROM roles ORDER BY name ASC")
        roles = cur.fetchall()
        return jsonify([{"id": r[0], "name": r[1], "permissions": r[2]} for r in roles])
    finally:
        cur.close()
        conn.close()

@auth_bp.route('/admin/roles', methods=['POST'])
@admin_required()
def create_role():
    data = request.json
    name = data.get('name')
    permissions = data.get('permissions', {})
    if not name: return jsonify({"msg": "Missing role name"}), 400
    
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO roles (name, permissions) VALUES (%s, %s) RETURNING id", 
                    (name, json.dumps(permissions)))
        conn.commit()
        return jsonify({"msg": "Role created", "id": cur.fetchone()[0]}), 201
    except Exception as e:
        return jsonify({"msg": str(e)}), 500
    finally:
        cur.close()
        conn.close()

@auth_bp.route('/admin/roles/<int:role_id>', methods=['PUT'])
@admin_required()
def update_role(role_id):
    data = request.json
    name = data.get('name')
    permissions = data.get('permissions')
    
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        if name:
            cur.execute("UPDATE roles SET name = %s WHERE id = %s", (name, role_id))
        if permissions is not None:
            cur.execute("UPDATE roles SET permissions = %s WHERE id = %s", (json.dumps(permissions), role_id))
        conn.commit()
        return jsonify({"msg": "Role updated"})
    finally:
        cur.close()
        conn.close()

@auth_bp.route('/admin/roles/<int:role_id>', methods=['DELETE'])
@admin_required()
def delete_role(role_id):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM roles WHERE id = %s", (role_id,))
        conn.commit()
        return jsonify({"msg": "Role deleted"})
    finally:
        cur.close()
        conn.close()

import json # For json.dumps
