# Configuration and Deployment Guide: Soc-Monitoring

## 1. Setting up the local development environment
Follow these steps to set up the environment on your machine.

### Prerequisites
- Python 3.9+
- PostgreSQL
### Installation
1. **Locate the file containing the code**

2. **Install dependencies**:
```bash
`pip install -r requirements.txt
```
3. **Environment configuration**:
Create a `.env` file based on the modifications to `app/config.py`.

5. **Run the application**:
```bash
python run.py
```
*The application will be available at `http://localhost:8005`.*

---

## 2. Production Deployment
### Database Migration
1. Configure your PostgreSQL server and create a database named `monitoring`.

2. Run the migration script:
```bash
python old/migrate_to_pg.py
```
## 3. Remote Access (Ngrok)
If the server is behind a NAT, use Ngrok:
```bash
./ngrok.exe http 8000 --auth="username:password"
```