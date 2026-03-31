from flask import Blueprint, render_template, redirect, url_for

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    return redirect(url_for('main.login_page'))

@main_bp.route('/login')
def login_page():
    return render_template('login.html')

@main_bp.route('/dashboard')
def protected_dashboard():
    # El dashboard real que requiere login
    return render_template('dashboard.html')

@main_bp.route('/settings')
def settings_page():
    return render_template('settings.html')

@main_bp.route('/camera_list')
def camera_list():
    return render_template('camera_list.html')

@main_bp.route('/battery')
def battery_dashboard():
    return render_template('battery.html')

@main_bp.route('/falla_ac')
def falla_ac_dashboard():
    return render_template('falla_ac.html')

@main_bp.route('/estado')
def system_status():
    # Placeholder for status page
    return "System Status OK" 

@main_bp.route('/hvac')
def hvac_dashboard():
    return render_template('hvac.html')
@main_bp.route('/disconection')
def disconection_page():
    return render_template('disconection.html')