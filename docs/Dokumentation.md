# Python RPG Projekt - Dokumentation

Diese Dokumentation bietet eine Übersicht über die Struktur und Funktionalität des Python-RPG-Projekts. Sie soll als Referenz dienen und die Navigation durch den Code erleichtern.

## Projektstruktur
python-rpg-projekt/ ├── docs/ │ ├── ENTSCHEIDUNGEN.md # Protokoll wichtiger Designentscheidungen mit Zeitstempeln ├── src/ │ ├── game_logic/ │ │ ├── entity/ # Entity-Klassen für Spieler, Feinde und NPCs │ │ ├── skills/ # Skill-Effekte und -Mechaniken │ │ ├── combat/ # Kampfsystem-Komponenten │ │ │ ├── actions/ # Aktionsverarbeitung im Kampf │ │ │ ├── initiative/ # Initiative-Management │ │ │ ├── rewards/ # Belohnungssystem │ ├── ui/ # Benutzeroberflächen (CLI, zukünftig eventuell GUI) │ ├── utils/ # Hilfsklassen und -funktionen


## Komponentenübersicht

### Entity-System (`src/game_logic/entity/`)

Das Entity-System verwendet eine modulare Struktur mit Vererbung und Komposition.

| Datei | Beschreibung |
|-------|-------------|
| `base_entity.py` | Basisklasse für alle Spielentitäten mit grundlegenden Attributen und Methoden |
| `player.py` | Implementiert die Spieler-Klasse mit Charakterklassen, Levelsystem und Inventar |
| `enemy.py` | Implementiert die Gegner-Klasse mit KI-Verhalten, Loot-Tabellen und Erfahrungsbelohnungen |
| `npc.py` | Implementiert Nicht-Spieler-Charaktere mit Dialog- und Questsystem |

### Skill-System (`src/game_logic/skills/`)

Das Skill-System verwendet einen modularen Effektbasierten Ansatz.

| Datei | Beschreibung |
|-------|-------------|
| `skill_effect.py` | Basisklasse für alle Skill-Effekte (Schaden, Heilung, Statuseffekte) |
| `damage_effect.py` | Implementiert verschiedene Schadensarten (physisch, magisch) |
| `healing_effect.py` | Implementiert Heilungseffekte |
| `status_effect.py` | Implementiert temporäre Statuseffekte (Buff, Debuff) |
| `skill_manager.py` | Verwaltet Skill-Definitionen und -Anwendung |

### Kampfsystem (`src/game_logic/combat/`)

Das Kampfsystem ist in spezialisierte Komponenten aufgeteilt, die jeweils eine eigene Verantwortung haben.

| Datei | Beschreibung |
|-------|-------------|
| `combat_manager.py` | Hauptkoordinator des Kampfablaufs, orchestriert die anderen Komponenten |

#### Initiative-Management (`src/game_logic/combat/initiative/`)

| Datei | Beschreibung |
|-------|-------------|
| `initiative_manager.py` | Verwaltet die Initiative-Reihenfolge und den Rundenwechsel im Kampf |

#### Aktionsverarbeitung (`src/game_logic/combat/actions/`)

| Datei | Beschreibung |
|-------|-------------|
| `action_resolver.py` | Führt Aktionen (Angriff, Skill, Flucht) aus und verwaltet Kampfstatistiken |

#### Belohnungssystem (`src/game_logic/combat/rewards/`)

| Datei | Beschreibung |
|-------|-------------|
| `reward_calculator.py` | Berechnet und verteilt EP und Beute nach erfolgreichen Kämpfen |

## Hauptfunktionalitäten

### Entity-System

- **Modularer Aufbau**: Entities haben Basisattribute und können mit spezifischen Fähigkeiten erweitert werden
- **Charakterklassen**: Spieler können verschiedene Klassen (Krieger, Magier, Schurke, Kleriker) wählen
- **Attributsystem**: Stärke, Geschicklichkeit, Intelligenz, Weisheit beeinflussen Kampfwerte
- **Levelsystem**: Spieler können durch EP aufsteigen und Attribute verbessern

### Kampfsystem

- **Rundenbasiert**: Kampf läuft in Runden ab, Reihenfolge durch Initiative bestimmt
- **Diverse Aktionen**: Angriff, Skill-Einsatz, Item-Verwendung, Flucht
- **Trefferchance**: Basierend auf Attributen und Modifikatoren
- **Schadensberechnung**: Verschiedene Schadenstypen mit Modifikatoren
- **Statuseffekte**: Buffs und Debuffs beeinflussen Kampfwerte
- **Kampfstatistiken**: Tracking von Schaden, Heilung und Bedrohung
- **Belohnungen**: EP- und Loot-Berechnung nach Kampfende

## Nächste Schritte

1. **UI-Implementierung**: Entwicklung einer CLI oder GUI für die Interaktion mit dem Spiel
2. **Quest-System**: Implementierung von Quests mit Fortschritt und Belohnungen
3. **Item-System**: Erweiterung des Inventarsystems mit verschiedenen Ausrüstungsgegenständen
4. **Speichersystem**: Speichern und Laden von Spielständen
5. **Welt-System**: Implementierung einer Spielwelt mit verschiedenen Bereichen
6. **KI-Verbesserungen**: Erweiterung der Gegner-KI für taktischere Kämpfe
7. **Balancing**: Feinabstimmung von Kampfwerten, EP und Belohnungen

## Entwicklungshinweise

- **Single Responsibility Principle**: Jede Klasse hat eine klare, einzelne Verantwortung
- **Modularität**: Komponenten sind so entworfen, dass sie unabhängig voneinander erweitert werden können
- **Testbarkeit**: Logik ist von UI getrennt, um Unit-Tests zu erleichtern
- **Dokumentation**: Wichtige Entscheidungen in ENTSCHEIDUNGEN.md festhalten mit Datum und Begründung