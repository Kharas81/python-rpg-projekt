# Python RPG Projekt

Ein textbasiertes, selbstlaufendes Rollenspiel (RPG) entwickelt in Python.

## Projektübersicht

Das Projekt zielt darauf ab, ein RPG zu erstellen, das:
- Verschiedene Charakterklassen (Krieger, Magier, Schurke, Kleriker) bietet
- Ein rundenbasiertes Kampfsystem implementiert
- Fortschrittssystem mit Leveln und Fähigkeiten beinhaltet
- Zunächst als Kommandozeilen-Interface (CLI) funktioniert
- Perspektivisch durch KI (regelbasiert und Reinforcement Learning) gesteuert werden kann

## Projektstruktur

```
rpg-projekt/
├── src/                          # Quellcode
│   ├── ai/                       # AI-Komponenten
│   ├── definitions/              # Spieldefinitionen
│   │   └── json_data/            # JSON-Dateien für Spielelemente
│   ├── environment/              # RL-Umgebung
│   ├── game_logic/               # Spiellogik
│   └── ui/                       # Benutzeroberfläche
├── tests/                        # Automatisierte Tests
├── tools/                        # Hilfsskripte
├── logs/                         # Logdateien
├── reports/                      # Berichte
└── saves/                        # Spielstände
```

## Installation & Start

1. Repository klonen:
   ```bash
   git clone https://github.com/Kharas81/python-rpg-projekt.git
   cd python-rpg-projekt
   ```

2. Abhängigkeiten installieren:
   ```bash
   pip install -r requirements.txt
   ```

3. Spiel starten:
   ```bash
   python src/main.py
   ```

## Entwicklung mit GitHub Codespaces

Dieses Projekt ist für die Entwicklung mit GitHub Codespaces optimiert.

1. Auf den "Code" Button im Repository klicken
2. "Codespaces" Tab auswählen
3. "Create codespace on main" klicken
4. Sobald der Codespace bereit ist, kannst du direkt mit der Entwicklung beginnen

## Lizenz

[Noch festzulegen]