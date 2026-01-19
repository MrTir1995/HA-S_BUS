# Contributing to SAIA S-Bus Integration

Vielen Dank für Ihr Interesse, zu diesem Projekt beizutragen! 🎉

## 🚀 Wie kann ich beitragen?

### Bugs melden

Wenn Sie einen Bug gefunden haben:

1. Prüfen Sie, ob der Bug bereits als [Issue](https://github.com/MrTir1995/HA-S_BUS/issues) gemeldet wurde
2. Falls nicht, erstellen Sie ein neues Issue mit:
   - Klarer Beschreibung des Problems
   - Schritten zur Reproduktion
   - Erwartetes vs. tatsächliches Verhalten
   - Home Assistant Version
   - Relevante Log-Ausgaben

### Features vorschlagen

Feature-Requests sind willkommen! Bitte erstellen Sie ein Issue mit:

- Detaillierter Beschreibung des Features
- Anwendungsfall / Use Case
- Mögliche Implementierungsansätze (optional)

### Code beitragen

1. **Fork das Repository**
2. **Clone Ihren Fork**
   ```bash
   git clone https://github.com/IhrUsername/S-Bus_HA.git
   cd S-Bus_HA
   ```

3. **Öffnen Sie den Dev Container in VS Code**
   - Der Container richtet automatisch die Entwicklungsumgebung ein

4. **Erstellen Sie einen Feature-Branch**
   ```bash
   git checkout -b feature/mein-neues-feature
   ```

5. **Entwickeln Sie Ihr Feature**
   - Schreiben Sie sauberen, gut dokumentierten Code
   - Fügen Sie Type Hints hinzu
   - Folgen Sie dem bestehenden Code-Stil

6. **Testen Sie Ihre Änderungen**
   ```bash
   pytest tests/
   ```

7. **Linting ausführen**
   ```bash
   ruff check .
   ruff format .
   ```

8. **Commit mit aussagekräftiger Message**
   ```bash
   git commit -m "feat: Beschreibung des Features"
   ```
   
   Commit-Message Format:
   - `feat:` Neue Features
   - `fix:` Bugfixes
   - `docs:` Dokumentation
   - `refactor:` Code-Refactoring
   - `test:` Tests hinzufügen/ändern
   - `chore:` Wartungsarbeiten

9. **Push zu Ihrem Fork**
   ```bash
   git push origin feature/mein-neues-feature
   ```

10. **Erstellen Sie einen Pull Request**

## 📋 Code-Standards

### Python Style Guide

- Folgen Sie [PEP 8](https://pep8.org/)
- Verwenden Sie Ruff für Linting und Formatierung
- Maximale Zeilenlänge: 88 Zeichen (Black-kompatibel)
- Verwenden Sie Type Hints für alle Funktionen

### Code-Qualität

- **Type Hints**: Alle Funktionen müssen Type Hints haben
- **Docstrings**: Öffentliche Funktionen benötigen Docstrings
- **Async/Await**: Verwenden Sie async/await für I/O-Operationen
- **Error Handling**: Fangen Sie spezifische Exceptions ab
- **Logging**: Nutzen Sie `_LOGGER` für Debug-Informationen

### Testing

- Schreiben Sie Tests für neue Features
- Stellen Sie sicher, dass alle Tests erfolgreich durchlaufen
- Minimale Code-Coverage: 80%

## 🏗️ Projekt-Struktur

```
S-Bus_HA/
├── custom_components/sbus/
│   ├── __init__.py          # Integration Setup
│   ├── config_flow.py       # UI-Konfiguration
│   ├── const.py             # Konstanten
│   ├── coordinator.py       # Data Update Coordinator
│   ├── sbus_protocol.py     # S-Bus Protokoll-Implementierung
│   ├── sensor.py            # Sensor Entitäten
│   ├── binary_sensor.py     # Binary Sensor Entitäten
│   ├── switch.py            # Switch Entitäten
│   ├── manifest.json        # Metadaten
│   └── strings.json         # UI-Texte
├── tests/                   # Unit Tests
├── .devcontainer/           # Development Container
└── docs/                    # Dokumentation
```

## 🔍 Development Workflow

1. **Starten Sie Home Assistant im Dev Container**
   ```bash
   hass -c config --debug
   ```

2. **Logs beobachten**
   - Logs werden in der Console angezeigt
   - Custom Component Logs: `custom_components.sbus`

3. **Debuggen**
   - Setzen Sie Breakpoints in VS Code
   - Nutzen Sie die Debug-Konfiguration "Home Assistant: Debug"

4. **Hot-Reload**
   - Gehen Sie zu **Einstellungen → System → Neu laden**
   - Oder verwenden Sie den Service `homeassistant.reload_config_entry`

## 📚 Hilfreiche Ressourcen

- [Home Assistant Developer Docs](https://developers.home-assistant.io/)
- [S-Bus Protokoll Dokumentation](https://www.dcsmodule.com/js/htmledit/kindeditor/attached/20220712/20220712134948_56336.pdf)
- [Python asyncio Documentation](https://docs.python.org/3/library/asyncio.html)

## 📝 Pull Request Checklist

Vor dem Erstellen eines Pull Requests:

- [ ] Code folgt dem Projekt-Style Guide
- [ ] Alle Tests laufen erfolgreich durch
- [ ] Neue Tests wurden hinzugefügt (falls zutreffend)
- [ ] Dokumentation wurde aktualisiert
- [ ] Commit-Messages sind aussagekräftig
- [ ] Code wurde von Ruff geprüft
- [ ] Type Hints sind vorhanden

## 🤔 Fragen?

Falls Sie Fragen haben:

- Öffnen Sie ein Issue mit dem Label "question"
- Diskutieren Sie im [Home Assistant Forum](https://community.home-assistant.io/)

## 📄 Lizenz

Durch das Beitragen zu diesem Projekt stimmen Sie zu, dass Ihre Beiträge unter der MIT-Lizenz lizenziert werden.

Vielen Dank für Ihre Beiträge! 🙏
