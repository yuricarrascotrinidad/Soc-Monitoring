# Security Policy: Soc-Monitoring
## 1. Authentication and Authorization
### JWT Management
Access to the API and administrative functions is protected using **JSON Web Tokens (JWTs)**.

- **Expiration**: 24 hours (`JWT_ACCESS_TOKEN_EXPIRES = 86400`).

- **Storage**: Tokens must be stored in secure HttpOnly cookies or on secure local storage.

### RBAC (Role-Based Access Control)
The system distinguishes between the roles of **Administrator** and **Standard User**.

- `admin`: Can perform CRUD operations on cameras and modify system settings.

- `Soc`: Can view dashboards and export reports.

---

## 2. Secret Management
- **Environment Variables**: Confidential data (database passwords, JWT keys, SMTP credentials) must be stored in a `.env` file and **never** uploaded to Git.

- **Example of `.env`:
```bash
PG_PASSWORD=your_secure_password
SECRET_KEY=generated_random_string
EMAIL_PASSWORD=application_specific_password
```

---

## 3. Infrastructure Security
- **Network Isolation**: The monitoring server must reside on a management VLAN with restricted access to the necessary site IPs (SNMP/HTTP).


- **Ngrok Security**: If using Ngrok for remote access, always use the `--auth` option to add a password layer over the tunnel.

- **Database Access**: PostgreSQL must be configured to allow connections only from the application server's IP address using `db.py`.

-

## 4. Incident Response
In case of a security breach:
1. **Key Rotation**: Immediately generate a new `JWT_SECRET_KEY` in `.env` to invalidate all active sessions.

2. **Password Update**: Change the root database password.