Dieses Dokument enthält detaillierte Informationen zur physikalischen Struktur unseres Projekts im Dateisystem und der Entwicklungsumgebung.

1. Projektstruktur (Richtlinie)
Wir halten uns an diese Struktur, die im Repository gepflegt wird. Diese Struktur ist eine Richtlinie und kann jederzeit an Projektbedürfnisse angepasst, erweitert oder geändert werden. Es ist wichtig, beim Erstellen von Code-Einheiten den korrekten Platz in dieser Struktur zu finden, um Modularität und Übersichtlichkeit zu gewährleisten.

python-rpg-projekt/
│
├── src/                     # [AKTIV] Hauptverzeichnis für den gesamten Quellcode (modulare Einheiten, SRP)
│   ├── config/              # Konfigurationsdateien (JSON/YAML + Python-Lader)
│   │   ├── __init__.py      # Macht 'config' zu einem Python-Paket
│   │   └── config.py        # Zentrales Config-Objekt lädt Einstellungen (JSON/YAML)
│   ├── definitions/         # Definitionen von Spielobjekten & Daten
│   │   ├── json_data/       # Reine JSON-Daten (Charaktere, Skills, Items, Quests etc.) - **Beachte das spezifische Kommentarformat (`"_comment": "..."`)**
│   │   │   ├── characters.json
│   │   │   ├── opponents.json
│   │   │   ├── skills.json
│   │   │   ├── items.json    # [PLATZHALTER]
│   │   │   ├── npcs.json     # [PLATZHALTER]
│   │   │   └── quests.json   # [PLATZHALTER]
│   │   ├── character.py     # Python-Klasse `Character` (Basis für alle Entitäten mit Stats/Skills)
│   │   ├── skill.py         # Python-Klasse `Skill`
│   │   ├── item.py          # [PLATZHALTER] Python-Klasse `Item`
│   │   ├── loader.py        # Lädt JSON-Daten in Python-Objekte (kleine, spezifische Lader pro Datentyp)
│   │   └── __init__.py      # Macht 'definitions' zu einem Python-Paket
│   ├── environment/         # RL-Umgebung (Gymnasium-kompatibel)
│   │   ├── __init__.py      # Macht 'environment' zu einem Paket
│   │   ├── rpg_env.py       # Hauptklasse `RPGEnv(gym.Env)` - Orchestriert den RL-Durchlauf
│   │   ├── env_state.py     # Verwaltet den Zustand (Liste der Charaktere etc.) für die Env
│   │   ├── observation_manager.py # Definiert/Erstellt Observation Space/Vektor für den Agenten
│   │   ├── action_manager.py  # Definiert/Erstellt Action Space/Masken, mappt Aktionen zu Skill-IDs
│   │   └── reward_calculator.py # Berechnet die Belohnungsfunktion für den RL-Agenten
│   ├── game_logic/          # Kernlogik des Spiels (modulare Einheiten)
│   │   ├── __init__.py      # Macht 'game_logic' zu einem Paket
│   │   ├── combat.py        # Logik für Kampfaktionen (Treffer, Schaden, Skill-Effekte)
│   │   ├── effects.py       # Logik für Statuseffekte (Anwendung, Ticking, Entfernung)
│   │   └── leveling.py      # Logik für Level-Up und XP-Berechnung
│   ├── ui/                  # Benutzeroberfläche (aktuell CLI-Simulation)
│   │   ├── __init__.py      # Macht 'ui' zu einem Paket
│   │   ├── cli_output.py    # Funktionen zur formatierten Ausgabe (Konsole/Logs)
│   │   └── cli_main_loop.py # Steuert die automatische Simulationsschleife für den 'auto' Modus
│   ├── ai/                  # Künstliche Intelligenz (Regelbasiert & RL)
│   │   ├── __init__.py      # Macht 'ai' zu einem Paket
│   │   ├── strategies/      # Einzelne (regelbasierte) AI-Strategien für Gegner/NPCs
│   │   │   ├── __init__.py
│   │   │   ├── default_strategy.py # Fallback-Strategie
│   │   │   └── basic_melee.py    # Beispielstrategie
│   │   ├── ai_dispatcher.py # Wählt die passende AI-Strategie basierend auf Charakterdaten
│   │   ├── rl_training.py   # Skript zum Trainieren von RL-Agenten (nutzt rpg_env.py)
│   │   ├── evaluate_agent.py# Skript zur Evaluierung trainierter RL-Agenten
│   │   └── models/          # Verzeichnis zum Speichern trainierter RL-Modelle (.zip) (in .gitignore)
│   └── main.py              # HAUPTEINSTIEGSPUNKT: Parsed Argumente (--mode) und startet die Simulation/das Training
│
├── tests/                   # [ANGEFANGEN] Verzeichnis für automatisierte Tests (`pytest`). Struktur sollte src/ spiegeln.
│   └── (Unit-Tests für game_logic, definitions etc.)
│
├── logs/                    # [DYN ERSTELT] Verzeichnis für Laufzeitprotokolle (in .gitignore)
│   └── (Struktur für Simulation/Training/Evaluierung mit Datum/Zeit + Kontextdateien)
│
├── reports/                 # [PLATZHALTER] Manuell erstellte oder spezielle Berichte (Analysen, Meilensteine)
│
├── docs/                    # [AKTIV] Dokumentationsverzeichnis
│   ├── ENTSCHEIDUNGEN.md    # Protokoll wichtiger Entscheidungen
│   └── README_DYNAMIC_SETTINGS.md # Anleitung zur Parameteranpassung (verweist auf JSON/YAMLs)
│
├── tools/                   # [AKTIV] Hilfsskripte für Entwicklungsaufgaben
│   ├── context_extractor.py # Skript zur Extraktion des Laufzeit-Kontexts (Code, JSON)
│   ├── generate_report.py   # Skript zum Generieren von Evaluationsberichten
│   └── (Weitere wie create_snapshot.py, profile_env_step.py, run_pipeline.py)
│
├── .gitignore               # [AKTIV] Definiert von Git ignorierte Dateien/Ordner
└── requirements.txt         # [AKTIV] Liste der Python-Paketabhängigkeiten

Use code with caution.
(Statusmarkierungen wie [AKTIV]/[PLATZHALTER] dienen nur zur Orientierung.)

.gitignore Beispiele (sollten in der Datei so oder ähnlich stehen):
venv/
__pycache__/
*.pyc
saves/
logs/
src/ai/models/
*.prof
.pytest_cache/
reports/ # Ignoriert alle Reports, falls gewünscht
Use code with caution.

2. GitHub/Codespaces Workflow & Umgebung
Versionskontrolle: Nutze Git konsequent (add, commit, push, pull). Feature-Branches und Pull Requests sind empfohlen. Repo: https://github.com/Kharas81/python-rpg-projekt
Entwicklungsumgebung: Primär GitHub Codespaces oder VS Code (mit GitHub).
Virtuelle Umgebung: Codespaces stellt oft eine Umgebung bereit. Stelle sicher, dass pip install -r requirements.txt im Terminal ausgeführt wird.
.gitignore: Wichtig! Stelle sicher, dass sensible oder temporäre Dateien/Ordner ignoriert werden (siehe Beispiele oben).
Dateierstellung/Aktualisierung: Die Erstellung/das Überschreiben ganzer Dateien oder das Liefern von Code-Snippets erfolgt immer per cat << 'EOF' > pfad/zur/datei.py im Terminal (siehe Absolute Prioritäten im Master-Core). Ich werde diese Befehle direkt ausführen und danach im Editor überprüfen.
Ausführung: Im Terminal (im Projekt-Root), z.B. python src/main.py --mode manual oder python src/main.py --mode auto.