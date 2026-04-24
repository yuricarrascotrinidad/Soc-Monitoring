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

@main_bp.route('/access_camera')
def access_camera():
    return render_template('access_camera.html')

@main_bp.route('/transport_camera')
def transport_camera():
    return render_template('transport_camera.html')

@main_bp.route('/edit_camera')
def edit_camera():
    return render_template('edit_camera.html')

@main_bp.route('/show_battery')
def show_battery():
    return render_template('show_battery.html')

@main_bp.route('/rectifier_monitor')
def rectifier_monitor():
    return render_template('rectifier_monitor.html')