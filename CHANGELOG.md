# Changelog

Alle bemerkenswerten Änderungen an diesem Projekt werden in dieser Datei dokumentiert.

Das Format basiert auf [Keep a Changelog](https://keepachangelog.com/de/1.0.0/),
und dieses Projekt folgt [Semantic Versioning](https://semver.org/lang/de/).

## [Unreleased]

### Geplant
- YAML-Konfiguration für Entitäten
- Automatische Erkennung aller verfügbaren Datenpunkte
- Unterstützung für Timer und Counter Entitäten
- Diagnostics Support
- Serielle S-Bus Unterstützung (RS-485)

## [0.1.0] - 2026-01-19

### Hinzugefügt
- Initiale Release der S-Bus Integration
- Ether-S-Bus Support (UDP Port 5050)
- UI-basierte Konfiguration (Config Flow)
- Sensor-Entitäten für Register
- Binary Sensor-Entitäten für Flags
- Switch-Entitäten für schreibbare Flags
- DataUpdateCoordinator für zentrale Datenverwaltung
- CRC-16-CCITT Validierung
- Services:
  - `sbus.read_register` - Register lesen
  - `sbus.write_register` - Register schreiben
  - `sbus.read_flag` - Flags lesen
  - `sbus.write_flag` - Flag schreiben
- Automatische Device-Identifikation über Systemregister
- Device Registry Integration
- Reconfigure Flow für Änderung von Verbindungseinstellungen
- Options Flow für Scan-Intervall Anpassung
- Vollständige Async/Await Implementierung
- Dev Container für VS Code
- GitHub Actions CI/CD
- Unit Tests mit pytest
- Linting mit Ruff
- Pre-commit Hooks
- Umfassende Dokumentation

### Technische Details
- Python 3.13 Support
- Home Assistant 2024.1.0+
- Nicht-blockierende UDP-Kommunikation
- Type Hints für alle Funktionen
- Logging und Error Handling

[Unreleased]: https://github.com/MrTir1995/S-Bus_HA/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/MrTir1995/S-Bus_HA/releases/tag/v0.1.0
