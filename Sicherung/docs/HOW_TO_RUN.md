# Ausführen der Anwendung und einzelner Module

Dieses Dokument beschreibt, wie die Hauptanwendung gestartet und wie einzelne Module (z.B. für Tests oder Debugging) korrekt ausgeführt werden.

## Voraussetzungen

Stelle sicher, dass du dich im Hauptverzeichnis des Projekts (`python-rpg-projekt/`) befindest und deine virtuelle Umgebung (z.B. in GitHub Codespaces oder lokal via `venv`) aktiviert ist.

Die notwendigen Python-Pakete müssen installiert sein:
```bash
pip install -r requirements.txt

Standardmodus ('auto') starten:
python src/main.py
Manuellen Modus starten:
python src/main.py --mode manual
Trainingsmodus starten (Kurzform):
python src/main.py -m train
Hilfe anzeigen (zeigt alle Optionen):
python src/main.py --help

Teste die verschiedenen Modi:
Führe python src/main.py aus (sollte den Default-Modus starten, wahrscheinlich "auto").
Führe python src/main.py --mode manual aus.
Führe python src/main.py --mode train aus.
Führe python src/main.py --mode evaluate aus.
Führe python src/main.py --help aus, um die Hilfe anzuzeigen.
