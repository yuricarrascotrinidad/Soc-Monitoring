
import sqlite3

def add_camera_access(site, ip):
    conn = sqlite3.connect('monitoring.db')
    try:
        conn.execute("INSERT INTO access_cameras (site, ip) VALUES (?, ?)", (site, ip))
        conn.commit()
        print(f"Added access camera for {site} at {ip}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

def add_camera_transport(site, position, ip):
    # Valid positions: prin, patio, equipo, generador
    conn = sqlite3.connect('monitoring.db')
    try:
        conn.execute("INSERT INTO transport_cameras (site, position, ip) VALUES (?, ?, ?)", (site, position, ip))
        conn.commit()
        print(f"Added transport camera ({position}) for {site} at {ip}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    # Examples:
    # add_camera_access("NUEVO_SITIO_1", "10.0.0.50")
    # add_camera_transport("NUEVO_SITIO_2", "prin", "10.0.0.51")
    pass
