import logging
import os
import time

# Configurar logging: root en INFO para ver API y renovaciones
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logging.getLogger('werkzeug').setLevel(logging.INFO)
logging.getLogger('urllib3').setLevel(logging.WARNING)

from app import create_app
import threading


app = create_app()

if __name__ == '__main__':
    import sqlite3

    # Solo ejecutar monitoreo en el proceso hijo del reloader
    app.debug = True
    is_reloader_main = os.environ.get('WERKZEUG_RUN_MAIN') == 'true'

    if is_reloader_main or not app.debug:
        from app.services.monitoring_service import MonitoringService
        from app.services.hvac_service import HvacService
        from app.services.battery_service import BatteryService
        time.sleep(1)
        MonitoringService.start_monitoring_threads(app)
        HvacService.start_hvac_monitoring(app)
        BatteryService.start_battery_monitoring(app)

    app.run(host='0.0.0.0', port=8000, debug=app.debug)
