# SAIA S-Bus Integration for Home Assistant

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)
[![hacs][hacsbadge]][hacs]

![Project Maintenance][maintenance-shield]

**Diese Integration ermöglicht die Kommunikation mit SAIA PCD Steuerungen über das S-Bus Protokoll in Home Assistant.**

## 🌟 Features

- **Multi-Protokoll Support**: 
  - **Ether-S-Bus**: UDP/TCP über Ethernet (Port 5050)
  - **Serial-S-Bus**: RS-232/RS-485 über USB oder TCP-Seriell-Bridge
  - **Profi-S-Bus**: Profibus FDL Gateway-Unterstützung
- **Auto-Discovery**: Automatische Erkennung über mDNS/Zeroconf und SSDP
- **Connection Health Monitoring**: Automatische Wiederverbindung bei Verbindungsabbrüchen
- **Umfassende Datenpunkte**: Register, Flags, Timer, Counter, Data Blocks
- **CRC-16 Validierung**: Sichere Datenübertragung gemäß S-Bus Spezifikation
- **Retry-Logik**: Exponential Backoff bei Netzwerkfehlern
- **Native Integration**: Nahtlose Integration in die Home Assistant UI
- **Async/Await**: Moderne asynchrone Implementierung für beste Performance

## 📋 Unterstützte Geräte

Diese Integration unterstützt SAIA PCD Steuerungen mit S-Bus Schnittstelle, einschließlich:

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
4. Wählen Sie das gewünschte Protokoll:

#### Ether-S-Bus (UDP/TCP)
- **Connection Type**: UDP (Standard) oder TCP
- **Host**: IP-Adresse oder Hostname der PCD Steuerung
- **Port**: UDP/TCP-Port (Standard: 5050)
- **Station Adresse**: S-Bus Stationsadresse (0-253, Standard: 0)
- **Scan Intervall**: Abfrageintervall in Sekunden (Standard: 30)

#### Serial-S-Bus (RS-232/RS-485)
- **Connection Type**: USB/Serial oder TCP-Seriell-Bridge
- **Serial Port**: 
  - USB/Serial: z.B. `/dev/ttyUSB0`, `/dev/ttyAMA0`
  - TCP-Seriell-Bridge: z.B. `192.168.1.100:5050`
- **Baud Rate**: 9600, 19200, 38400, 57600, 115200 (Standard: 9600)
- **Station Adresse**: S-Bus Stationsadresse (0-253, Standard: 0)
- **Scan Intervall**: Abfrageintervall in Sekunden (Standard: 30)

#### Profi-S-Bus (Profibus Gateway)
- **Gateway Host**: IP-Adresse des Profibus-Gateways
- **Gateway Port**: TCP-Port des Gateways
- **Station Adresse**: S-Bus Stationsadresse (0-253)
- **Profibus Adresse**: Profibus-Knotennummer (0-126)
- **Scan Intervall**: Abfrageintervall in Sekunden (Standard: 30)

### Auto-Discovery

Die Integration unterstützt automatische Erkennung von PCD Steuerungen im Netzwerk:

- **mDNS/Zeroconf**: Erkennung über `_http._tcp.local.` und `_sbus._tcp.local.`
- **SSDP**: Erkennung von SAIA-Geräten mit Herstellerinformation

Wenn eine Steuerung gefunden wird, erscheint eine Benachrichtigung in Home Assistant mit vorausgefüllten Verbindungsdaten.

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

### S-Bus Protokoll-Varianten

Diese Integration implementiert alle drei SAIA S-Bus Protokoll-Varianten:

#### Ether-S-Bus (UDP/TCP)
- **Modus**: Ether-S-Bus über UDP Port 5050 (Standard) oder TCP
- **Header**: 8-Byte Ether-S-Bus Header mit Sequenznummern
- **CRC**: CRC-16-CCITT mit 0x0000 Initialwert (Polynom 0x1021)
- **Retry**: 3 Versuche mit exponential backoff (0.5s, 1s, 2s)
- **Discovery**: mDNS/Zeroconf und SSDP Support

#### Serial-S-Bus (RS-232/RS-485)
- **Modus**: Data Mode (SM2) mit 8N1 (8 Datenbits, No Parity, 1 Stopbit)
- **Byte-Stuffing**: Automatische Behandlung von 0xB5/0xC5 Escape-Sequenzen
- **CRC**: CRC-16-CCITT über entstuffte Daten
- **Baudraten**: 1200-115200 Baud (Standard: 9600)
- **Verbindungen**: Direkte USB/Serial oder TCP-Seriell-Bridge (ser2net)

#### Profi-S-Bus (Profibus FDL)
- **Transport**: Profibus FDL Layer 2
- **Gateway**: Benötigt Profibus-zu-Ethernet Gateway
- **Adressierung**: Separate Profibus- und S-Bus-Adressen

### Systemregister

Die Integration liest automatisch Geräte-Informationen aus den Systemregistern:

- **R600-R604**: Seriennummer (ASCII)
- **R605-R611**: Produkttyp (ASCII)
- **R612**: Hardware-Version
- **R614**: Firmware-Version (formatiert als Major.Minor.Patch)
- **R621**: Protokoll-Version

### Architektur

- **Config Flow**: Multi-Step UI-basierte Konfiguration mit Protokollauswahl
- **DataUpdateCoordinator**: Zentrale Datenverwaltung mit Connection Health Monitoring
- **Auto-Reconnect**: Automatische Wiederverbindung bei bis zu 3 aufeinanderfolgenden Fehlern
- **Async/Await**: Nicht-blockierende I/O-Operationen
- **Type Hints**: Vollständige Type-Annotations für bessere Code-Qualität
- **Factory Pattern**: Dynamische Instanziierung der korrekten Protokoll-Implementierung

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
