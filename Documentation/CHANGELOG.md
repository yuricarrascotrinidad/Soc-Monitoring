# Changelog: Soc-Monitoring Platform

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.2.0] - 2026-04-21
### Added
- Comprehensive documentation suite (Blueprint, User Manual, Technical Docs, etc.).
- `PROJECT_BLUEPRINT.md` for high-level vision alignment.
- `SECURITY.md` and `DISASTER_RECOVERY.md` for infrastructure resilience.

### Changed
- Refined **Camera Management** module: Improved "Position" field logic in transport cameras.
- Updated **AC Failure** table filtering logic for better performance.

---

## [1.1.0] - 2026-04-14
### Added
- **Camera Management Dashboard**: Support for CRUD operations on Access and Transport cameras.
- Search/Filter feature in the camera list.

### Fixed
- Mapping of ZTE battery data for SOC and Current sensors.
- Sidebar navigation overlap in collapsed mode.

---

## [1.0.0] - 2026-04-01
### Added
- Initial release of the **Soc-Monitoring** platform.
- Real-time dashboard for AC Failures and Battery SOC.
- Background monitoring service with SQLite support.
- Email alert system (SMTP).
- Export to Excel functionality.

---

## [0.1.0] - 2026-03-15
### Added
- Project initialization with Flask.
- Database schema for telemetry storage.
- Basic background loops for data collection.
