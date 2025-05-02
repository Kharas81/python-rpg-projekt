# Python RPG Projekt

Ein textbasiertes RPG, das in Python entwickelt wird.

## Setup (Lokale Entwicklungsumgebung)

Wenn du dieses Projekt lokal (nicht in Codespaces, das es automatisch macht) einrichten möchtest:

1.  **Klonen:** Klone das Repository auf deinen Computer:
    ```bash
    git clone [https://github.com/Kharas81/python-rpg-projekt.git](https://github.com/Kharas81/python-rpg-projekt.git)
    ```
2.  **Verzeichnis wechseln:** Gehe in das Projektverzeichnis:
    ```bash
    cd python-rpg-projekt
    ```
3.  **Virtuelle Umgebung (Empfohlen):** Erstelle und aktiviere eine virtuelle Umgebung:
    * Windows:
        ```bash
        python -m venv venv
        .\venv\Scripts\activate
        ```
    * macOS / Linux:
        ```bash
        python3 -m venv venv
        source venv/bin/activate
        ```
4.  **Abhängigkeiten installieren:** Installiere die benötigten Pakete:
    ```bash
    pip install -r requirements.txt
    ```
    *(Hinweis: Die `requirements.txt` wird im Laufe des Projekts gefüllt)*

## Ausführen (Zukünftig)

Um das Spiel zu starten (sobald die Hauptdatei existiert):
```bash
python src/main.py

git pull origin main  # Oder der Name deines Haupt-Branches