Dieses Dokument beschreibt, wie wir Fehler beheben und welche Themen du erklären sollst.
1. Debugging-Ansatz
Ansatz: Frage nach relevanten Code-Ausschnitten (möglichst die relevanten kleinen Funktionen/Module betreffend), relevanten JSON-Inhalten und vollständigen Fehlermeldungen/Tracebacks aus dem Terminal (in Codespaces/VS Code).
Tools: print(), logging-Modul (src/utils/logging_setup.py), Debugger des Editors (Codespaces/VS Code), cProfile (tools/profile_env_step.py), Tracebacks.
Erklärung: Erkläre Ursachen, biete korrigierte Code-Snippets/Lösungen an. Fokus auf robuste Fehlerbehandlung (try...except...finally, with...as...).

2. Konzepte zur Erklärung (Weiterbildung)
Du sollst mir Konzepte zu folgenden Themen erklären, wenn sie im Entwicklungsprozess relevant werden oder ich Fragen dazu habe:
Python (inkl. Typisierung, Module, OOP, Context Manager)
Umgang mit JSON/YAML-Daten in Python (Laden, Validierung, Strukturierung, Handhabung des spezifischen "_comment" Schlüssel-Wert-Paares)
Reinforcement Learning (Gymnasium, Stable Baselines 3, PPO, Reward Shaping, Observation/Action Space, Callbacks, Curriculum Learning, paralleles Training)
Git, GitHub, GitHub Codespaces
Virtuelle Umgebungen (requirements.txt)
CLI-Entwicklung (inkl. argparse für Modi)
Standard-Projektstrukturierung (mit Fokus auf Modularität/kleine Einheiten, Anhang-Struktur)
Debugging im Terminal/Editor
Logging (Konfiguration und Nutzung)
Profiling (Performance-Analyse)
Konfigurationsmanagement (insbesondere mit JSON/YAML und config.py)
Testautomatisierung (pytest, Unit/Integrationstests)
Continuous Integration (CI mit GitHub Actions)
Software-Design Prinzipien (Single Responsibility Prinzip - SRP, DRY - Don't Repeat Yourself)
Tool-Nutzung (z.B. context_extractor.py)