# Dynamische Einstellungen

Diese Dokumentation beschreibt, wie und wo wichtige Parameter und Konfigurationen im Projekt angepasst werden können.

## Allgemeine Konfigurationen

Die allgemeinen Konfigurationen werden in JSON-Dateien im Verzeichnis `src/definitions/json_data/` gespeichert.

### Spieler-Klassen und Attribute

Datei: `src/definitions/json_data/characters.json`
- Definiert die verschiedenen Spielerklassen
- Konfiguriert Basisattribute und Ressourcen
- Legt die bekannten Skills fest

### Skills und Fähigkeiten

Datei: `src/definitions/json_data/skills.json`
- Definiert die verschiedenen Fähigkeiten im Spiel
- Konfiguriert Kosten, Ziele und Effekte
- Legt Grundschaden und andere Parameter fest

### Gegner

Datei: `src/definitions/json_data/enemies.json`
- Definiert die verschiedenen Gegnertypen
- Konfiguriert Attribute und Fähigkeiten
- Legt XP-Belohnungen fest

## Logging-Einstellungen

Die Logging-Konfiguration kann in `src/utils/logging_setup.py` angepasst werden.
