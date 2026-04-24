# Runbooks: Operating Procedures for SoC Monitoring

## 1. Incident: Control Panel Troubleshooting
**Symptoms**: The control panel displays "Connection Error" or takes more than 10 seconds to load.

1. Check the `run.py` process:

```bash

ps aux | grep run.py

```
2. Check the logs for the message "Database is locked":

- **Solution**: Restart the application to release file locks.

3. Check if the size of `monitoring.db` has exceeded disk limits.

-

## 2. Incident: Monitoring Thread Failure
**Symptoms**: No new data timestamps appear in the "Last Updated" columns.

1. Check the logs for error traces related to `MonitoringService`.

2. Common Cause: Network timeout during an SNMP/HTTP call without proper exception handling.

3. Action: Restart the service. If the problem persists, isolate the IP address of the site causing the block and temporarily remove it from the configuration.

--

## 3. Incident: No SMTP alerts sent
Symptoms: A completed event occurs, but no emails are received.

1. Check `EMAIL_ADDRESS` and `EMAIL_PASSWORD` in `config.py`.

2. Check if the Gmail/SMTP account is locked or requires a new application password. 3. Connectivity Test:

```bash

python -c "import smtplib; s = smtplib.SMTP('smtp.gmail.com', 587); s.starttls(); s.login('user', 'pass')"

```

---

## 4. Procedure: Adding a New Batch of Cameras
**Context**: Adding more than 50 new sites.

1. Prepare an Excel file with the columns: `site`, `position`, `ip`.

2. Use the `old/add_camera.py` script or import it directly into the `transport_cameras` table using SQL:

```sql

INSERT INTO transport_cameras (site, position, ip) VALUES ('SITE_NAME', 'EQUIPO', '10.x.x.x');

```

---

## 5. Procedure: Database Cleanup
**Context**: The `alarmas_activas` table is growing too large.

1. Archive old alarms (status = 'deactivated' and age > 30 days).

2. Cleanup:

```sql

DELETE FROM alarmas_activas WHERE estado = 'off' AND hora < NOW() - INTERVAL '30 days';

``