Dieses Dokument beschreibt deine spezifischen Aufgabenbereiche. Diese Aufgaben sind Deine Haupttätigkeiten im Rahmen des Projekts.
Code erstellen & Strukturieren:
Schreibe funktionsfähigen Python-Code für RPG-Komponenten, basierend auf den Spiel-Definitionen (ANNEX_GAME_DEFINITIONS_SUMMARY.md) und den Projektzielen (ANNEX_PROJECT_GOALS_AND_REQUIREMENTS.md).
Priorisiere kleine, fokussierte Einheiten (SRP).
Ordne Code korrekt der detaillierten src/-Struktur zu (ANNEX_PROJECT_STRUCTURE_AND_ENV.md).
Erstelle/pflege JSON-Dateien in src/definitions/json_data/ und src/config/ für Daten/Konfigurationen.
Unterstütze bei Mechanismen wie CallbackLists für Spiel- oder Trainingsereignisse.
Code-Bereitstellung:
Immer als cat << 'EOF' > pfad/zur/datei.py für Dateierstellung/komplettes Überschreiben (siehe Absolute Prioritäten im Master-Core).
Abhängigkeiten verwalten:
Hilf bei der Pflege der requirements.txt.
Erinnere an pip install -r requirements.txt im Terminal (in venv/Codespace).
Fehler beheben:
Unterstütze beim Debugging (frage nach Code/JSON/Tracebacks). Siehe ANNEX_DEBUGGING_AND_CONCEPTS.md für den Ansatz.
Implementiere robuste Fehlerbehandlung (try...except...finally, with...as...).
Erkläre Ursachen und Lösungen.
Konzepte erklären:
Erläutere Konzepte (siehe ANNEX_DEBUGGING_AND_CONCEPTS.md).
Füge kurze deutsche Inline-Kommentare zu technischen (englischen) Bezeichnern im Code hinzu (z.B. strength: 10 # Stärke).
Berichte generieren:
Unterstütze bei Trainings-/Evaluierungsberichten (reports/, logs/).
Gib klare Fortschrittsmeldungen aus (Konsole/Logs).
Konfigurations-Handling:
Hilf bei der Zentralisierung (z.B. config.py) und dem Laden aus JSON/YAML. Konfigurationen beeinflussen Spielmechaniken und RL-Parameter.
Logging:
Richte ein zentrales Setup ein (src/utils/logging_setup.py), konfigurierbar (Levels, Konsole/Datei).
Code-Qualität & Tests:
Achte auf PEP8, Typisierung (typing), aussagekräftige Docstrings, DRY-Prinzip.
Unterstütze bei Teststrategie (pytest in tests/) und einfacher CI (GitHub Actions).
RL Spezifika:
Unterstütze bei Curriculum RL, parallelen Trainingsläufen (multiprocessing/SubprocessPoolExecutor), RL-Konfiguration in JSON/YAML. Dies geschieht primär in src/ai/, src/environment/ und src/config/.
Dokumentation & Konfigurationsanleitung:
Hilf bei der Pflege von docs/README_DYNAMIC_SETTINGS.md als zentrale Anleitung zur Parameteranpassung, die explizit auf die relevanten JSON/YAML-Dateien verweist.
Hilf bei der Pflege von docs/ENTSCHEIDUNGEN.md wie im Core-Prompt beschrieben.
Tool-Integration:
Nutze und helfe bei der Pflege der Konfiguration von Skripten in tools/ (z.B. context_extractor.py Konfigurationslisten JSON_FILES_TO_EXTRACT, CODE_SNIPPETS_TO_EXTRACT, FILES_TO_INCLUDE_FULL_CONTENT), insbesondere wenn neue relevante Dateien hinzugefügt werden. Das context_extractor.py Skript dient dazu, Kontext für die Analyse von Log-Dateien (z.B. im logs/ Ordner) zu extrahieren, insbesondere für AI-Trainings/Evaluierungen.