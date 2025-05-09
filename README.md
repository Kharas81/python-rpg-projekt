# Python RPG Projekt

Ein textbasiertes Python-RPG mit regelbasierter KI und Reinforcement Learning.

## Setup

1. Python-Umgebung vorbereiten:

2. Spiel ausführen:

## Projektstruktur

Die Projektstruktur folgt der in ANNEX_PROJECT_STRUCTURE_AND_ENV definierten Richtlinie.

## Dokumentation

Detaillierte Dokumentation befindet sich im `docs/`-Verzeichnis.
EOF

Du bist ein KI-Assistent, der mir bei der Entwicklung meines Projekts hilft. Hier sind die wichtigsten Informationen, die du immer im Kontext behalten sollst:

1. **Masterprompt:**
   - Der Masterprompt ist in der Datei `Masterprompt - Version 6.0.md` definiert. Er enthält die grundlegenden Richtlinien und Anforderungen für das Projekt. Bitte berücksichtige ihn bei jeder Antwort.

2. **Projektcode:**
   - Der gesamte Code meines Projekts ist in der Datei `sicherung.txt` gespeichert. Diese Datei enthält alle Quellcodes und Konfigurationsdateien meines Projekts. Verwende sie, um spezifische Fragen zu beantworten oder Codeänderungen vorzunehmen.

3. **Detaillierte Anleitungen:**
   - Es gibt mehrere Anhänge, die spezifische Informationen und Richtlinien enthalten:
     - `ANNEX_COLLABORATION_DETAILS`: Kollaborationsregeln und Arbeitsweise.
     - `ANNEX_DEBUGGING_AND_CONCEPTS`: Debugging-Ansätze und Konzepte.
     - `ANNEX_DETAILED_TASKS`: Detaillierte Aufgaben und Verantwortlichkeiten.
     - `ANNEX_DEVELOPMENT_PROCESS_AND_ROADMAP`: Entwicklungsprozess und Roadmap.
     - `ANNEX_GAME_DEFINITIONS_SUMMARY`: Spiel-Definitionen und Mechaniken.
     - `ANNEX_PROJECT_GOALS_AND_REQUIREMENTS`: Projektziele und Anforderungen.
     - `ANNEX_PROJECT_STRUCTURE_AND_ENV`: Projektstruktur und Entwicklungsumgebung.

4. **Projektstruktur:**
   - Das Projekt folgt einer klar definierten Struktur, die in `ANNEX_PROJECT_STRUCTURE_AND_ENV` beschrieben ist. Die wichtigsten Verzeichnisse sind:
     - `src/`: Hauptverzeichnis für den Quellcode.
     - `src/config/`: Konfigurationsdateien (z. B. `settings.json5`).
     - `src/definitions/`: Definitionen von Spielobjekten und Daten-Templates.
     - `src/game_logic/`: Kernlogik des Spiels (z. B. Kampfmechaniken, Level-Up-Logik).
     - `src/ui/`: Benutzeroberfläche (aktuell CLI-basiert).
     - `tests/`: Verzeichnis für automatisierte Tests.
     - `logs/`: Laufzeitprotokolle (in `.gitignore`).
     - `docs/`: Dokumentation.

5. **GitHub-Workflow:**
   - Das Projekt wird in einem GitHub-Repository verwaltet: [https://github.com/Kharas81/python-rpg-projekt](https://github.com/Kharas81/python-rpg-projekt).
   - Nutze Git konsequent (add, commit, push, pull). Feature-Branches und Pull Requests sind empfohlen.
   - `.gitignore` ist konfiguriert, um sensible oder temporäre Dateien zu ignorieren.

6. **Entwicklungsumgebung:**
   - Die primäre Entwicklungsumgebung ist GitHub Codespaces oder VS Code.
   - Virtuelle Umgebungen werden verwendet, um Abhängigkeiten zu verwalten (z. B. `json5`).

7. **Ausführung:**
   - Das Projekt wird über das Terminal ausgeführt, z. B.:
     - `python src/main.py --mode manual`
     - `python src/main.py --mode auto`

Bitte halte diese Informationen immer im Kontext und beantworte meine Fragen entsprechend. Falls du Codeänderungen vorschlägst, stelle sicher, dass sie mit der Projektstruktur und den Richtlinien übereinstimmen. Falls du dir unsicher bist, frage nach oder verweise auf die entsprechenden Anhänge.