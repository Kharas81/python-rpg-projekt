Dieses Dokument beschreibt die übergeordnete Vision, die Ziele und die qualitativen sowie funktionalen Anforderungen an das Projekt. Diese leiten die Entwicklung und Designentscheidungen.
1. Projektvision & Ziele
Entwicklung eines selbstlaufenden, textbasierten Python-RPGs.
Beginnt als CLI-Simulation, soll aber erweiterbar sein für zukünftige Features (Quests, Items, NPCs, Crafting, Web-UI etc.).
Einbindung von KI (regelbasiert und Reinforcement Learning).
Fokus auf Zukunftssicherheit, gute Softwarearchitektur und Wartbarkeit, nicht nur auf die schnellste Implementierung.
2. Funktionale Anforderungen (Was das System tun soll)
Unterstützung verschiedener Betriebsmodi über src/main.py (--mode manual, --mode auto).
Implementierung der Kern-RPG-Mechaniken (definiert in ANNEX_GAME_DEFINITIONS_SUMMARY.md und umgesetzt in src/game_logic/, src/definitions/ etc.): Kampf, Status-Effekte, Attribut- und Skill-Berechnungen, XP-Vergabe (Level-Up-Mechanik noch zu implementieren).
Integration von Regelbasierter KI für Nicht-Spieler-Charaktere (src/ai/strategies/).
Integration von Reinforcement Learning:
Gymnasium-kompatible Umgebung (src/environment/rpg_env.py).
Training mit stable-baselines3 (MaskablePPO, Action Masking).
Möglichkeit für Curriculum Learning und paralleles Training (Konfiguration über JSON/YAML in src/config/).
Grundlegende CLI-Simulation für den auto-Modus (src/ui/cli_main_loop.py).
Persistenz: Speicherung von Code (Git), RL-Modellen (src/ai/models/), Logs und Berichten (logs/, reports/), optional Spielfortschritte (saves/).
3. Qualitative Anforderungen (Wie das System sein soll)
Code-Qualität: PEP8 (wo sinnvoll), Single Responsibility Prinzip (SRP), DRY (Don't Repeat Yourself), gut dokumentiert (Typisierung, Docstrings, Kommentare).
Modularität: Konsequente Aufteilung in kleine, fokussierte Code-Einheiten (Funktionen, Klassen, Module). Klare Schnittstellen zwischen Modulen. Code-Dateien in src/ sollen typischerweise klein und spezifisch sein.
Wartbarkeit: Code muss leicht verständlich und änderbar sein.
Erweiterbarkeit: Das Design sollte die spätere Integration neuer Features ermöglichen.
Datenhaltung: Spieldaten und wichtige Konfigurationen in gut strukturierten und leicht wartbaren JSON/YAML-Dateien (src/definitions/json_data/, src/config/).
Testbarkeit: Gut testbar. Definition und Implementierung einer Teststrategie (pytest in tests/). Ziel ist gute Testabdeckung.
CI: Einfache Continuous Integration Pipeline (GitHub Actions) für Linting und Tests.
Konfiguration: Zentralisiert und flexibel (src/config/).
Logging: Strukturiertes und konfigurierbares Logging (src/utils/logging_setup.py).
Dokumentation: Klare Code-Dokumentation und zentrale Anleitung zur Konfiguration und Nutzung (docs/README_DYNAMIC_SETTINGS.md verweist auf JSONs).