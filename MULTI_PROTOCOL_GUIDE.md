# Mehrere S-Bus-Protokolle - Konfigurationsanleitung

Die SAIA S-Bus Integration unterstützt jetzt alle drei Hauptvarianten des S-Bus-Protokolls:

## Unterstützte Protokolle

### 1. Ether-S-Bus (UDP/TCP)
Kommunikation über Ethernet-Netzwerk.

**Verbindungstypen:**
- **UDP** (Standard): Schneller, verbindungsloser Modus
- **TCP**: Verbindungsorientierter Modus mit Fehlerkorrektur

**Konfiguration:**
```yaml
Protocol Type: Ether-S-Bus (UDP/TCP)
Connection Type: UDP oder TCP
Host: IP-Adresse des PCD (z.B. 192.168.1.100)
Port: 5050 (Standard)
Station Address: 0-253 (Standard: 0)
Scan Interval: 30 Sekunden (Standard)
```

**Anwendungsfälle:**
- Standard-Ethernet-Verbindung zu PCD-Steuerungen
- Netzwerkbasierte Kommunikation über LAN/WAN
- Schnelle Datenübertragung mit geringer Latenz

---

### 2. Serial-S-Bus (USB/Serial)
Kommunikation über serielle Schnittstellen.

**Verbindungstypen:**
- **USB/Serial**: Direkte serielle Verbindung über USB-Adapter
- **TCP Serial Bridge**: Serieller Port über TCP/IP-Netzwerk (z.B. ser2net)

**Konfiguration für USB/Serial:**
```yaml
Protocol Type: Serial-S-Bus (USB/TCP Serial)
Connection Type: USB/Serial
Serial Port: /dev/ttyUSB0 (Linux) oder COM3 (Windows)
Baud Rate: 9600 (Standard), 19200, 38400, 57600, 115200
Station Address: 0-253
Scan Interval: 30 Sekunden
```

**Konfiguration für TCP Serial Bridge:**
```yaml
Protocol Type: Serial-S-Bus (USB/TCP Serial)
Connection Type: TCP Serial Bridge
Serial Port: 192.168.1.200:5050 (Format: host:port)
Baud Rate: 9600 (Standard)
Station Address: 0-253
Scan Interval: 30 Sekunden
```

**Anwendungsfälle:**
- Direkte RS-232/RS-485 Verbindung zum PCD
- USB-zu-Serial Adapter (FTDI, Prolific, etc.)
- Serieller Fernzugriff über TCP/IP (ser2net, socat)
- Legacy-Systeme ohne Ethernet

**Hinweise:**
- Unter Linux benötigen Sie möglicherweise Berechtigungen für `/dev/ttyUSB*` oder `/dev/ttyACM*`
- Fügen Sie Ihren Benutzer zur Gruppe `dialout` hinzu: `sudo usermod -a -G dialout $USER`
- Für TCP Serial Bridge: Stellen Sie sicher, dass der Serial Server läuft und erreichbar ist

---

### 3. Profi-S-Bus (Profibus)
Kommunikation über Profibus-Gateway.

**Konfiguration:**
```yaml
Protocol Type: Profi-S-Bus (Profibus)
Gateway Host: IP-Adresse des Profibus-Gateways
Gateway Port: 5050 (Standard)
Station Address: 0-253 (S-Bus Station)
Profibus Address: 0-126 (Profibus Knotenadresse)
Scan Interval: 30 Sekunden
```

**Anwendungsfälle:**
- Integration in bestehende Profibus-Netzwerke
- Kommunikation mit PCD über Profibus DP
- Industrielle Automatisierungssysteme mit Profibus-Infrastruktur

**Hinweise:**
- Erfordert Profibus-Gateway oder -Master
- Gateway muss S-Bus-zu-Profibus-Translation unterstützen
- Profibus-Adresse muss korrekt konfiguriert sein

---

## Ersteinrichtung

1. **Home Assistant öffnen**
2. **Einstellungen** → **Geräte & Dienste**
3. **Integration hinzufügen** → **SAIA S-Bus** suchen
4. **Protokolltyp auswählen**:
   - Ether-S-Bus für Ethernet-Verbindungen
   - Serial-S-Bus für serielle Verbindungen
   - Profi-S-Bus für Profibus-Gateways
5. **Verbindungsdetails eingeben** (siehe oben)
6. **Verbindung testen** und **Gerät hinzufügen**

---

## Fehlerbehebung

### Ether-S-Bus
- **Timeout-Fehler**: Prüfen Sie Netzwerkverbindung und Firewall-Einstellungen
- **Verbindung fehlgeschlagen**: Stellen Sie sicher, dass der PCD erreichbar ist (Ping testen)
- **Falscher Port**: Standardport ist 5050, prüfen Sie PCD-Konfiguration

### Serial-S-Bus
- **Serial Port nicht gefunden**: 
  - Prüfen Sie den Pfad: `ls -l /dev/ttyUSB*` oder `ls -l /dev/ttyACM*`
  - Prüfen Sie Berechtigungen: `sudo chmod 666 /dev/ttyUSB0`
  - Fügen Sie Benutzer zur dialout-Gruppe hinzu
- **Timeout bei USB-Verbindung**:
  - Überprüfen Sie Baudrate (muss mit PCD übereinstimmen)
  - Prüfen Sie Verkabelung (TX/RX richtig verbunden?)
  - Testen Sie mit einem Terminal-Programm (minicom, screen)
- **TCP Serial Bridge verbindet nicht**:
  - Prüfen Sie, ob ser2net oder ähnlicher Service läuft
  - Testen Sie mit: `telnet 192.168.1.200 5050`
  - Prüfen Sie Firewall auf dem Serial-Server

### Profi-S-Bus
- **Gateway nicht erreichbar**: Prüfen Sie Gateway-IP und -Port
- **Profibus-Kommunikationsfehler**: 
  - Prüfen Sie Profibus-Adresse
  - Stellen Sie sicher, dass PCD am Profibus-Netzwerk angeschlossen ist
  - Prüfen Sie Profibus-Terminierung

---

## Beispiele für ser2net-Konfiguration

Für TCP Serial Bridge mit ser2net erstellen Sie `/etc/ser2net.conf`:

```
# Format: port:telnet:timeout:device:options
5050:raw:0:/dev/ttyUSB0:9600 8DATABITS 1STOPBIT EVEN LOCAL
```

Starten Sie ser2net:
```bash
sudo systemctl enable ser2net
sudo systemctl start ser2net
```

In der Integration verwenden Sie dann:
- Serial Port: `192.168.1.100:5050` (IP des Servers mit ser2net)
- Connection Type: TCP Serial Bridge

---

## Erweiterte Konfiguration

### Mehrere Geräte
Sie können mehrere PCD-Steuerungen mit unterschiedlichen Protokollen verbinden:
- PCD1 über Ether-S-Bus (UDP)
- PCD2 über Serial-S-Bus (USB)
- PCD3 über Ether-S-Bus (TCP)

### Station-Adressen
- Station Address 0 ist oft der Broadcast oder Standard
- Für Multidrop-Verbindungen (mehrere PCDs an einer Leitung) verwenden Sie eindeutige Station-Adressen
- RS-485 unterstützt bis zu 32 Geräte (Station 0-31)

### Scan-Intervall
- Niedrigere Werte (5-10s) für schnelle Updates
- Höhere Werte (30-60s) für geringere Netzwerklast
- Für serielle Verbindungen: längere Intervalle empfohlen (>30s)

---

## Weitere Informationen

- [S-Bus Protocol Documentation](docs/PROTOCOL.md)
- [Development Guide](docs/DEVELOPMENT.md)
- [GitHub Issues](https://github.com/MrTir1995/HA-S_BUS/issues)
