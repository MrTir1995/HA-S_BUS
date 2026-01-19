# SAIA S-Bus Integration for Home Assistant

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)
[![hacs][hacsbadge]][hacs]

![Project Maintenance][maintenance-shield]

**Diese Integration ermöglicht die Kommunikation mit SAIA PCD Steuerungen über das S-Bus Protokoll in Home Assistant.**

## 🌟 Features

- **Ether-S-Bus Support**: Volle Unterstützung für S-Bus über UDP (Port 5050)
- **Auto-Discovery**: Automatische Erkennung von PCD Steuerungen im Netzwerk
- **Umfassende Datenpunkte**: Unterstützung für Register, Flags, Timer, Counter und mehr
- **CRC-16 Validierung**: Sichere Datenübertragung mit Prüfsummen-Validierung
- **Native Integration**: Nahtlose Integration in die Home Assistant UI
- **Async/Await**: Moderne asynchrone Implementierung für beste Performance

## 📋 Unterstützte Geräte

Diese Integration unterstützt SAIA PCD Steuerungen mit Ether-S-Bus Schnittstelle, einschließlich:

- PCD1.M2120, PCD1.M2160
- PCD2.M480, PCD2.M5540
- PCD3.M5560, PCD3.M6860
- E-Line Serie (PCD1.E1000, etc.)
- Und weitere PCD-Modelle mit S-Bus Support

## 🚀 Installation

### HACS (Empfohlen)

1. Öffnen Sie HACS in Home Assistant
2. Klicken Sie auf "Integrations"
3. Klicken Sie auf das Menü (⋮) in der oberen rechten Ecke
4. Wählen Sie "Custom repositories"
5. Fügen Sie die Repository-URL hinzu: `https://github.com/MrTir1995/HA-S_BUS`
6. Wählen Sie die Kategorie "Integration"
7. Klicken Sie auf "ADD"
8. Suchen Sie nach "SAIA S-Bus"
9. Klicken Sie auf "Download"

### Manuelle Installation

1. Kopieren Sie den Ordner `custom_components/sbus` in Ihr `config/custom_components/` Verzeichnis
2. Starten Sie Home Assistant neu

## ⚙️ Konfiguration

### UI-Konfiguration

1. Navigieren Sie zu **Einstellungen** → **Geräte & Dienste**
2. Klicken Sie auf **+ Integration hinzufügen**
3. Suchen Sie nach **SAIA S-Bus**
4. Folgen Sie dem Einrichtungsassistenten:
   - **Host**: IP-Adresse oder Hostname der PCD Steuerung
   - **Port**: UDP-Port (Standard: 5050)
   - **Station Adresse**: S-Bus Stationsadresse (0-253, Standard: 0)
   - **Scan Intervall**: Abfrageintervall in Sekunden (Standard: 30)

### Auto-Discovery

Die Integration unterstützt automatische Erkennung von PCD Steuerungen im Netzwerk. Wenn eine Steuerung gefunden wird, erscheint eine Benachrichtigung in Home Assistant.

## 📖 Verwendung

### Entitäten

Nach der Konfiguration werden automatisch Entitäten für die erkannten Datenpunkte erstellt:

- **Sensor**: Register-Werte (R0-R9999), Timer, Counter
- **Binary Sensor**: Flags, Inputs, Outputs (Bit-Werte)
- **Switch**: Outputs, Flags (schreibbar)

### Beispiel-Automation

```yaml
automation:
  - alias: "Temperatur überwachen"
    trigger:
      - platform: numeric_state
        entity_id: sensor.sbus_register_100
        above: 25
    action:
      - service: notify.notify
        data:
          message: "Temperatur überschreitet 25°C!"
```

### Services

Die Integration bietet Custom Services für direkten Zugriff:

#### `sbus.read_register`
Liest ein oder mehrere Register aus.

```yaml
service: sbus.read_register
data:
  device_id: <device_id>
  start_address: 100
  count: 4
```

#### `sbus.write_register`
Schreibt einen Wert in ein Register.

```yaml
service: sbus.write_register
data:
  device_id: <device_id>
  address: 100
  value: 12345
```

## 🔧 Technische Details

### S-Bus Protokoll

Diese Integration implementiert das SAIA S-Bus Protokoll:

- **Modus**: Data Mode (SM2) für Ether-S-Bus
- **Port**: UDP 5050 (Standard)
- **CRC**: CRC-16-CCITT mit 0x1021 Polynom
- **Byte-Stuffing**: Automatische Behandlung von 0xB5/0xC5 Sequenzen
- **Systemregister**: R600-R621 für Geräte-Identifikation

### Architektur

- **Config Flow**: UI-basierte Konfiguration
- **DataUpdateCoordinator**: Zentrale Datenverwaltung
- **Async/Await**: Nicht-blockierende I/O-Operationen
- **Type Hints**: Vollständige Type-Annotations für bessere Code-Qualität

## 🤝 Beiträge

Beiträge sind willkommen! Bitte lesen Sie [CONTRIBUTING.md](CONTRIBUTING.md) für Details.

### Development Setup

1. Clone das Repository
2. Öffnen Sie den Ordner in VS Code
3. Wenn Sie dazu aufgefordert werden, öffnen Sie den Ordner im Dev Container
4. Der Container wird automatisch eingerichtet mit allen Dependencies

```bash
# Starten Sie Home Assistant im Debug-Modus
hass -c config --debug
```

## 📝 Lizenz

Dieses Projekt ist unter der MIT-Lizenz lizenziert - siehe [LICENSE](LICENSE) für Details.

## 🙏 Danksagung

- [SAIA-Burgess Controls](https://www.saia-pcd.com/) für das S-Bus Protokoll
- [Home Assistant Community](https://www.home-assistant.io/) für das großartige Framework
- [digimat.saia](https://github.com/digimat/digimat-saia) für die Python S-Bus Referenzimplementierung

## 📞 Support

Bei Problemen oder Fragen:

- Öffnen Sie ein [Issue auf GitHub](https://github.com/MrTir1995/HA-S_BUS/issues)
- Diskutieren Sie im [Home Assistant Forum](https://community.home-assistant.io/)

---

[commits-shield]: https://img.shields.io/github/commit-activity/y/MrTir1995/HA-S_BUS.svg?style=for-the-badge
[commits]: https://github.com/MrTir1995/HA-S_BUS/commits/main
[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[license-shield]: https://img.shields.io/github/license/MrTir1995/HA-S_BUS.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-MrTir1995-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/MrTir1995/HA-S_BUS.svg?style=for-the-badge
[releases]: https://github.com/MrTir1995/HA-S_BUS/releases
