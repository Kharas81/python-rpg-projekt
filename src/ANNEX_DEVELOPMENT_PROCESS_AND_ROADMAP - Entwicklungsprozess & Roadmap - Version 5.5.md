Dieses Dokument beschreibt den geplanten Ablauf des Projekts und deine Rolle dabei.
1. Entwicklungsprozess (Orientierung)
Wir folgen dieser Roadmap (flexibel). Die Schritte sind [Ausstehend], falls nicht anders markiert.
Setup (Klonen, Codespace, venv, requirements.txt, .gitignore, Commit) [Ausstehend]
Basis-Definitionen (JSON-Daten & Python-Klassen/Lader in src/definitions/) [Ausstehend]
Konfiguration & Logging Setup (config.py, logging_setup.py) [Ausstehend]
Betriebsmodi (main.py argparse) [Ausstehend]
Kernlogik (src/game_logic/, modular, nutzt JSON) [Ausstehend]
AI (Regelbasiert in src/ai/) [Ausstehend]
CLI-Simulation (src/ui/, cli_main_loop.py, nutzt JSON/Logik) [Ausstehend]
RL-Integration (src/environment/, rl_training.py, evaluate_agent.py, nutzt JSON-Config) [Ausstehend]
Refactoring & Stabilisierung (Code-Qualität, Modularität, Datenstrukturen, DRY) [Ausstehend]
Testen & CI (tests/, GitHub Actions) [Ausstehend]
Weitere Systeme (Neue JSON-Definitionen & Logik - z.B. Items, Quests etc., mit Strukturplanung bei Bedarf) [Ausstehend]
Erweiterte RL-Techniken (Curriculum, Parallele Läufe, JSON-Config) [Ausstehend]
Dokumentation (docs/, README_DYNAMIC_SETTINGS.md verweist auf JSONs) [Ausstehend]
Git (Regelmäßige Commits/Pushes, Branches/PRs) [Ausstehend]
2. Deine Rolle im Prozess
Nach jedem abgeschlossenen Schritt schlägst du proaktiv den nächsten Schritt der Roadmap vor und begründest kurz, warum dieser als Nächstes ansteht. Wir besprechen den vorgeschlagenen Schritt und fahren dann fort. Wenn ein Schritt das Hinzufügen neuer Dateien/Module/JSONs beinhaltet (wie z.B. "Weitere Systeme"), schlagen wir die konkrete Struktur im Rahmen des Kollaborations-Workflows vor und aktualisieren anschließend ANNEX_PROJECT_STRUCTURE_AND_ENV.md.