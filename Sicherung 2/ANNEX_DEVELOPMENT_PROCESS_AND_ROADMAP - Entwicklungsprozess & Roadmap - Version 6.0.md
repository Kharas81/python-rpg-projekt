Dieses Dokument beschreibt den geplanten Ablauf des Projekts und deine Rolle dabei.
1. Entwicklungsprozess (Orientierung)
Wir folgen dieser Roadmap (flexibel). Die Schritte sind logische Meilensteine oder kohärente Aufgabenblöcke, nicht notwendigerweise atomare, sequentielle Aktionen. Die Schritte sind [Ausstehend], falls nicht anders markiert.
Setup (Klonen, Codespace, venv, requirements.txt [jetzt mit json5], .gitignore, Commit) [Ausstehend]
Basis-Definitionen (JSON5-Daten & Python-Klassen/Lader in src/definitions/, src/config/settings.json5) [Ausstehend]
Konfiguration & Logging Setup (config.py [lädt settings.json5], src/utils/logging_setup.py) [Ausstehend]
Betriebsmodi (main.py argparse) [Ausstehend]
Kernlogik (src/game_logic/ Module wie formulas.py, entities.py, effects.py, leveling.py, combat.py, modular, nutzt JSON5/Config) [Ausstehend]
AI (Regelbasiert in src/ai/) [Ausstehend]
CLI-Simulation (src/ui/, cli_main_loop.py, nutzt JSON5/Logik) [Ausstehend]
RL-Integration (src/environment/, rl_training.py, evaluate_agent.py, nutzt JSON5-Config) [Ausstehend]
Refactoring & Stabilisierung: Dieser Punkt repräsentiert dedizierte, größere Aufräumarbeiten oder Code-Qualitätsprojekte. Basis-Refactoring (Verbesserung bestehenden Codes, Aufteilen langer Funktionen, Entkopplung von Logik wie Leveling/Status-Effekte) ist jedoch ein KONTINUIERLICHER Teil jedes Schritts, insbesondere bei der Code-Erstellung. (Code-Qualität, Modularität, Datenstrukturen [in JSON5], DRY) [Ausstehend für dedizierten Schritt]
Testen & CI (tests/ mit pytest und pytest-monkeypatch, GitHub Actions) [Ausstehend]
Weitere Systeme (Neue JSON5-Definitionen & Logik - z.B. Items, Quests etc., mit Strukturplanung bei Bedarf) [Ausstehend]
Erweiterte RL-Techniken (Curriculum, Parallele Läufe, JSON5-Config) [Ausstehend]
Dokumentation (docs/, README_DYNAMIC_SETTINGS.md verweist auf JSON5) [Ausstehend]
Git (Regelmäßige Commits/Pushes, Branches/PRs) [Ausstehend]
2. Deine Rolle im Prozess
Nachdem ein Aufgabenblock abgeschlossen ist, schlägst du proaktiv den nächsten Schritt der Roadmap (logischer Meilenstein oder kohärenter Aufgabenblock) vor und begründest kurz, warum dieser als Nächstes ansteht. Wir besprechen den vorgeschlagenen Schritt und fahren dann fort. Wenn ein Schritt das Hinzufügen neuer Dateien/Module/JSON5s beinhaltet (wie z.B. "Weitere Systeme"), schlagen wir die konkrete Struktur im Rahmen des Kollaborations-Workflows vor und aktualisieren anschließend ANNEX_PROJECT_STRUCTURE_AND_ENV.md. Achte bei der Implementierung und bei der Überarbeitung bestehenden Codes auf kontinuierliches Refactoring, um die Code-Qualität und Wartbarkeit fortlaufend zu verbessern (z.B. durch Aufteilen von Funktionen, Entkopplung von Verantwortlichkeiten).