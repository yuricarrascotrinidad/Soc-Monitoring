# Disaster Recovery Plan: Soc-Monitoring

## 1. Recovery Objectives
- **RPO (Recovery Point Objective)**: 24 hours (Maximum data loss).

- **RTO (Recovery Time Objective)**: 4 hours (Maximum downtime).

--

## 2. Backup Strategy
### Configuration and Code

Ensure that all secret keys are replicated to a secure password manager (e.g., LastPass/Vault) and not just stored in `.env` files on the server.

--

## 3. Disaster Scenarios and Recovery Steps
### Scenario A: Server Hardware Failure
1. Set up a new VPS or server.

2. Follow the instructions in `SETUP_DEPLOYMENT.md` to install Python and its dependencies.

### Scenario B: Database Corruption
1. Stop the application service.

2. Rename the current `monitoring.db` file to `monitoring.db.corrupt`.

3. Restore the most recent, healthy backup.

4. Restart the service.

-
## 3. Continuous Resilience
- **Replication**: For multi-region resilience, consider real-time replication of PostgreSQL to a hot standby server.

- **Monitoring**: Configure a heartbeat monitor to alert the team if the dashboard URL becomes unavailable.