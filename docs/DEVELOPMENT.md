# Entwicklungsleitfaden für SAIA S-Bus Integration

## Entwicklungsumgebung einrichten

### Voraussetzungen

- [Docker](https://www.docker.com/get-started) installiert
- [Visual Studio Code](https://code.visualstudio.com/) mit der Extension "Dev Containers"
- Git

### Setup

1. **Repository klonen:**
   ```bash
   git clone https://github.com/MrTir1995/S-Bus_HA.git
   cd S-Bus_HA
   ```

2. **In VS Code öffnen:**
   ```bash
   code .
   ```

3. **Dev Container starten:**
   - VS Code wird fragen: "Reopen in Container?" → Klicken Sie auf "Reopen in Container"
   - Der Container wird automatisch eingerichtet (kann einige Minuten dauern)

4. **Home Assistant starten:**
   ```bash
   hass -c config
   ```

5. **Browser öffnen:**
   - Navigieren Sie zu http://localhost:8123
   - Durchlaufen Sie das Onboarding

## Projekt-Struktur

```
S-Bus_HA/
├── custom_components/sbus/      # Die Integration
│   ├── __init__.py              # Setup und Teardown
│   ├── config_flow.py           # UI-Konfiguration
│   ├── const.py                 # Konstanten
│   ├── coordinator.py           # Daten-Koordinator
│   ├── sbus_protocol.py         # S-Bus Protokoll
│   ├── sensor.py                # Sensor-Entitäten
│   ├── binary_sensor.py         # Binary Sensor-Entitäten
│   ├── switch.py                # Switch-Entitäten
│   ├── manifest.json            # Metadaten
│   ├── strings.json             # UI-Texte
│   └── services.yaml            # Service-Definitionen
├── tests/                       # Unit Tests
├── .devcontainer/               # Dev Container Config
├── .github/workflows/           # CI/CD
└── docs/                        # Dokumentation
```

## Development Workflow

### 1. Neue Features entwickeln

```bash
# Neuen Branch erstellen
git checkout -b feature/meine-neue-funktion

# Code ändern
# ...

# Tests ausführen
pytest tests/ -v

# Linting
ruff check .
ruff format .
```

### 2. Integration testen

Nach Änderungen am Code:

1. **Integration neu laden:**
   - In Home Assistant: **Einstellungen → System → Neu laden**
   - Wählen Sie "YAML-Konfiguration"

2. **Oder: Home Assistant neu starten:**
   ```bash
   # Im Terminal: Ctrl+C, dann:
   hass -c config
   ```

### 3. Debugging

VS Code ist für Debugging konfiguriert:

1. **Breakpoints setzen:** Klicken Sie links neben die Zeilennummer
2. **Debug starten:** F5 oder "Run → Start Debugging"
3. **Debug-Konfiguration:** "Home Assistant: Debug"

Logs werden in der VS Code Debug-Konsole angezeigt.

### 4. Logs anzeigen

```bash
# Im config/home-assistant.log
tail -f config/home-assistant.log

# Nur S-Bus Logs (wenn debug aktiviert)
tail -f config/home-assistant.log | grep sbus
```

## Testing

### Unit Tests ausführen

```bash
# Alle Tests
pytest tests/

# Specific Test-Datei
pytest tests/test_sbus_protocol.py

# Mit Coverage
pytest tests/ --cov=custom_components.sbus --cov-report=html
```

### Coverage Report ansehen

```bash
# HTML Report generieren
pytest tests/ --cov=custom_components.sbus --cov-report=html

# Im Browser öffnen
python -m http.server 8000 --directory htmlcov
# Dann: http://localhost:8000
```

## Code-Qualität

### Linting mit Ruff

```bash
# Code prüfen
ruff check .

# Auto-Fix
ruff check --fix .

# Format
ruff format .
```

### Pre-commit Hooks

Pre-commit Hooks sind automatisch installiert und führen bei jedem Commit aus:

```bash
# Manuell ausführen
pre-commit run --all-files
```

## Häufige Aufgaben

### Integration hinzufügen

1. In Home Assistant: **Einstellungen → Geräte & Dienste**
2. **+ Integration hinzufügen**
3. Nach "SAIA S-Bus" suchen
4. IP-Adresse des PCD eingeben

### Services testen

Developer Tools → Services:

```yaml
service: sbus.read_register
data:
  device_id: <your_device_id>
  start_address: 100
  count: 4
```

### Neue Entität hinzufügen

1. Entsprechende Platform-Datei bearbeiten (z.B. `sensor.py`)
2. Neue Entitäts-Klasse erstellen (von `CoordinatorEntity` erben)
3. In `async_setup_entry` zur Entity-Liste hinzufügen
4. Home Assistant neu laden

## Troubleshooting

### "Cannot connect" Fehler

- Prüfen Sie, ob PCD erreichbar ist: `ping <ip>`
- Prüfen Sie Port: `nc -zv <ip> 5050`
- Prüfen Sie Firewall-Einstellungen
- `--network=host` in devcontainer.json für Linux

### "CRC Error"

- Datenkorruption im Netzwerk
- Prüfen Sie Netzwerkqualität
- Erhöhen Sie Timeout in Protocol

### Integration lädt nicht

- Prüfen Sie Logs: `config/home-assistant.log`
- Syntax-Fehler in Python-Dateien
- Fehlende Dependencies in `manifest.json`

### Tests schlagen fehl

- Dependencies installieren: `pip install -r requirements_test.txt`
- Pytest cache löschen: `rm -rf .pytest_cache`
- Neu ausführen: `pytest tests/ -v`

## Nützliche Links

- [Home Assistant Developer Docs](https://developers.home-assistant.io/)
- [S-Bus Protokoll Manual](https://www.dcsmodule.com/js/htmledit/kindeditor/attached/20220712/20220712134948_56336.pdf)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Pytest Documentation](https://docs.pytest.org/)

## Support

Bei Fragen oder Problemen:

- Öffnen Sie ein [Issue auf GitHub](https://github.com/MrTir1995/S-Bus_HA/issues)
- Diskutieren Sie im [Home Assistant Forum](https://community.home-assistant.io/)
