# Project Plan: SOC Monitoring

## 1. Vision and Purpose
**SOC Monitoring** is a platform designed for real-time surveillance and alarm monitoring of various sensors located at access and transport nodes, as well as the status of energy infrastructure (batteries), air conditioning, and security assets (IP access/transport cameras) in various regions.

The system functions as a "Unified Control Panel" for the Security Operations Center (SOC), enabling proactive monitoring and rapid response to any abnormal situation.

-
## 2. Objectives
### Key Objectives
- **Centralized Monitoring**: Consolidate diverse data sources (SNMP, HTTP, database exports) into a unified dashboard.

- **Predictive Alerts**: Identify battery degradation (low SOC) before site shutdown occurs.

- **Audit**: Maintain a historical record of all alarm events and system changes.

### Key Performance Indicators
| Metric | Target | Description |

| **System Uptime** | > 99.9% | Availability of the monitoring control panel. |

| **Data Latency** | < 60 s | Maximum delay for site telemetry updates. |

| **False Positive Rate** | < 5% | Minimization of "noise" on critical alarm channels. |

-

## 3. Scope and Limitations
### Scope
- Panel where alarms are displayed and event correlations are performed, allowing identification of open door conditions (in transport: main door, yard, equipment, and power room; in access: main door and shelter), as well as potential intrusion, sabotage, or theft situations.

- Real-time dashboard for AC power failures and battery status (percentage, charge/discharge).

- CRUD management for access and transportation camera networks.

- Export of operational reports to Excel.

- Automated monitoring service for background status checks.

### Out of Scope (No Targets)
- **Direct Remote Control**: The system monitors, but does not perform remote reboots or hardware configuration changes.

- **Video Storage**: The system provides routes/links to camera feeds, but does not host or record video feeds.

- **Inventory Management**: This is not an asset tracking tool; it only tracks active monitoring nodes.

--

## 4. Restrictions and Assumptions
### Technical Restrictions
- **Hardware Diversity**: This aspect does not represent a direct restriction, since integration is performed through an API that unifies battery information, regardless of the manufacturer (e.g., ZTE or Huawei/Lithium). This eliminates the complexity of handling different telemetry formats or protocols.

- **Network Bandwidth**: Monitoring threads should perform lightweight polls to avoid saturating low-bandwidth site links.

- **Storage**: The system already uses PostgreSQL in the current environment, which adequately supports concurrent write operations and the handling of larger data volumes.

### Assumptions
- Devices are accessible via a dedicated VPN or static IP management.

- A reliable SMTP server is available for alert distribution.

- Users authenticate using JWT to ensure internal security.