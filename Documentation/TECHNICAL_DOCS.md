# Technical Documentation: SoC Monitoring Architecture

## 1. System Architecture
The system follows a monolithic architecture based on Flask with background service threads for data collection.

### Components
- **Web Application (Flask)**: Handles HTTP requests, JWT authentication, and provides user interface templates.

- **Monitoring Service (`app/services/monitoring_service.py`)**: An engine that captures alarms and sends emails when events are generated based on alarm correlation.

- **Monitoring Service (`app/services/battery_service.py`)**: A multithreaded engine that runs polling loops for battery telemetry and AC power status.

- **Camera Service (`app/services/camera_service.py`)**: Manages camera metadata and visualizations.

- **Data Layer**:
- **Development**: Local PostgreSQL (`monitoring.db`).

- **Production**: PostgreSQL (configured in the `Config` class).

-

## 2. API Design
The API is organized into templates in `app/routes/`. Most endpoints require a valid JWT.

### Main Endpoints
| Endpoint | Method | Parameters | Description |

| :--- | :--- | :--- | :--- |

| `/api/dashboard_state` | `GET` | N/A | Full status of the alarm monitoring dashboard (cached). |

| `/api/battery_data` | `GET` | N/A | Real-time battery charge status (battery below 50%) and discharge telemetry. |

`/api/ac_data` | `GET` | N/A | Filtered list of sites with active AC power outages. |

`/api/disconnection_data` | `GET` | N/A | List of disconnected batteries. |

`/api/hvac_data` | `GET` | N/A | Telemetry from the air conditioning humidity and temperature sensors. |

`/api/cameras/manage` | `POST` | `action`, `site`, `ip` | CRUD operations exclusive to camera administrators. |

---

## 3. Data Models
### `battery_telemetry` (PostgreSQL/SQLite)
Stores the latest readings from all batteries.

- `device_id`: Unique identifier.

- `soc`: Charge status (0.0 - 100.0).

- `upload/download`: Current amperage readings.

- `ultimo_update`: Timestamp of the last successful query.

### `active_alarms`: Captures alarms, allowing correlation analysis.

- `category`: Classification (`AC_FAIL`, `LOW BATTERY`, etc.)
- `status`: `on` if active, `off` if deactivated.

- ## 4. Query Mechanism
The `MonitoringService` starts threads when the application initializes.

1. **Loop 1 (Fast)**: Synchronizes activated alarms every 15-30 seconds.

2. **Loop 2 (Standard)**: Updates battery telemetry (SOC/Voltage) every 2-5 minutes per site.

3. **Queuing System**: Uses thread-safe collections to update the `dashboard_state` cache, ensuring the user interface remains responsive.

-
## 5. Technologies Used
- **Languages**: Python 3.9+, JavaScript (Vanilla ES6).

- **Backend Framework**: Flask.

- **Authentication**: Flask-JWT-Extended.

- **Database**: Native SQL with psycopg2 (PostgreSQL).

- **Frontend**: Bootstrap 5 + jQuery (legacy components). - **Communication**: Ngrok (for local server tunneling), SMTP (email alerts).