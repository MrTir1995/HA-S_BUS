# Zusammenfassung der Änderungen - Multi-Protokoll-Unterstützung

## Übersicht
Die SAIA S-Bus Integration wurde erweitert, um alle drei S-Bus-Protokollvarianten zu unterstützen:
- **Ether-S-Bus** (UDP/TCP über Ethernet)
- **Serial-S-Bus** (USB/Serial oder TCP Serial Bridge)
- **Profi-S-Bus** (Profibus Gateway)

## Neue Dateien

### Protokoll-Implementierungen
- **`sbus_protocol_base.py`**: Basisklasse mit gemeinsamer S-Bus-Funktionalität
  - CRC-Berechnung
  - Telegram-Aufbau und -Validierung
  - Register/Flag read/write Operationen
  - Device-Info-Abfrage

- **`ether_sbus.py`**: Ether-S-Bus Implementierung
  - UDP-Kommunikation (Standard)
  - TCP-Kommunikation (optional)
  - Asynchrone Datagram/Stream-Protokolle

- **`serial_sbus.py`**: Serial-S-Bus Implementierung
  - Direkte serielle Verbindung (USB/RS-232/RS-485)
  - TCP Serial Bridge Support (ser2net, socat)
  - Baudrate-Konfiguration (1200-115200)

- **`profi_sbus.py`**: Profi-S-Bus Implementierung
  - Profibus Gateway Kommunikation
  - Profibus-Adressierung
  - Gateway-Protokoll Wrapping/Unwrapping

### Dokumentation
- **`MULTI_PROTOCOL_GUIDE.md`**: Umfassende Anleitung zur Konfiguration aller Protokolle
  - Verbindungstypen und Anwendungsfälle
  - Schritt-für-Schritt-Anleitungen
  - Fehlerbehebung
  - ser2net-Konfigurationsbeispiele

## Geänderte Dateien

### `const.py`
- Neue Konstanten für Protokolltypen
- Connection Type Definitionen
- Serial-Port und Baudrate-Konfiguration
- Erweiterte Fehler-Codes

### `sbus_protocol.py`
- Vollständig überarbeitet als Factory-Modul
- `create_sbus_protocol()` Factory-Funktion
- Legacy-Kompatibilität (`SBusProtocol = EtherSBusProtocol`)
- Zentrale Exports für alle Protokoll-Klassen

### `config_flow.py`
- Multi-Step Configuration Flow
- Protokollauswahl im ersten Schritt
- Spezifische Konfigurationsschritte für jedes Protokoll:
  - `async_step_ether_sbus()`: Ethernet-Konfiguration
  - `async_step_serial_sbus()`: Serial-Konfiguration  
  - `async_step_profi_sbus()`: Profibus-Konfiguration
- Validation für alle Protokolltypen

### `__init__.py`
- Verwendung der `create_sbus_protocol()` Factory
- Dynamische Protokoll-Instanzierung aus Config-Daten
- Verbesserte Fehlerbehandlung mit spezifischen Fehlermeldungen

### `coordinator.py`
- Type-Hint geändert: `SBusProtocol` → `SBusProtocolBase`
- Funktioniert mit allen Protokollvarianten

### `strings.json`
- Neue Übersetzungsstrings für Protokollauswahl
- Separate Konfigurationsschritte mit Beschreibungen
- Erweiterte Fehlermeldungen
- Description Placeholders für kontextabhängige Hilfe

### `manifest.json`
- Version erhöht: `0.1.0` → `0.2.0`
- Abhängigkeit hinzugefügt: `pyserial-asyncio==0.6`

### `requirements.txt`
- `pyserial-asyncio==0.6` hinzugefügt

## Architektur

```
┌─────────────────────────┐
│   Config Flow          │
│   (Protocol Selection)  │
└───────────┬─────────────┘
            │
            ├──→ Ether-S-Bus Config
            ├──→ Serial-S-Bus Config
            └──→ Profi-S-Bus Config
                    │
                    ↓
┌─────────────────────────────────────┐
│   create_sbus_protocol(config)     │
│   (Factory Function)                │
└───────────┬─────────────────────────┘
            │
    ┌───────┴───────┬─────────────┐
    ↓               ↓             ↓
┌─────────┐  ┌──────────┐  ┌──────────┐
│ Ether   │  │ Serial   │  │ Profi    │
│ S-Bus   │  │ S-Bus    │  │ S-Bus    │
└────┬────┘  └────┬─────┘  └────┬─────┘
     │            │             │
     └────────────┴─────────────┘
                  │
          ┌───────┴────────┐
          │ SBusProtocol   │
          │ Base           │
          └────────────────┘
```

## Verwendung

### Für Ether-S-Bus (wie bisher):
```python
config = {
    "protocol_type": "ether_sbus",
    "connection_type": "udp",
    "host": "192.168.1.100",
    "port": 5050,
    "station": 0
}
protocol = create_sbus_protocol(config)
```

### Für Serial-S-Bus (USB):
```python
config = {
    "protocol_type": "serial_sbus",
    "connection_type": "usb",
    "serial_port": "/dev/ttyUSB0",
    "baudrate": 9600,
    "station": 0
}
protocol = create_sbus_protocol(config)
```

### Für Serial-S-Bus (TCP Bridge):
```python
config = {
    "protocol_type": "serial_sbus",
    "connection_type": "tcp_serial",
    "serial_port": "192.168.1.200:5050",
    "baudrate": 9600,
    "station": 0
}
protocol = create_sbus_protocol(config)
```

### Für Profi-S-Bus:
```python
config = {
    "protocol_type": "profi_sbus",
    "host": "192.168.1.150",
    "port": 5050,
    "station": 0,
    "profibus_address": 2
}
protocol = create_sbus_protocol(config)
```

## Abwärtskompatibilität

Die bisherige Verwendung bleibt kompatibel durch Legacy-Alias:
```python
# Alt (funktioniert weiterhin):
from .sbus_protocol import SBusProtocol
protocol = SBusProtocol(host, port, station)

# Neu (empfohlen):
from .sbus_protocol import create_sbus_protocol
protocol = create_sbus_protocol(config)
```

## Nächste Schritte

1. **Testing**: Umfassende Tests für alle Protokollvarianten
2. **Documentation**: README.md aktualisieren
3. **Examples**: Beispielskripte für jedes Protokoll
4. **HACS**: GitHub Release erstellen (v0.2.0)
5. **Home Assistant**: Integration testen

## Bekannte Einschränkungen

- **Serial-S-Bus**: Erfordert `pyserial-asyncio` (automatisch installiert)
- **Profi-S-Bus**: Gateway-spezifische Implementierung ist Platzhalter
- **Tests**: Müssen noch für neue Protokolle erweitert werden
