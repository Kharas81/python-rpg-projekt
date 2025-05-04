#!/usr/bin/env python3
"""
Context Extractor Tool

Dieses Tool extrahiert relevante Kontextinformationen aus dem Projekt für
Analysen oder Dokumentationszwecke.
"""

import os
import json
from pathlib import Path

# Konfiguration der zu extrahierenden Dateien
JSON_FILES_TO_EXTRACT = [
    "src/definitions/json_data/characters.json",
    "src/definitions/json_data/skills.json",
    "src/definitions/json_data/enemies.json",
]

CODE_SNIPPETS_TO_EXTRACT = [
    "src/main.py",
    "src/game_logic/combat/combat_manager.py",
]

FILES_TO_INCLUDE_FULL_CONTENT = [
    "docs/ENTSCHEIDUNGEN.md",
]

def extract_context(output_file="extracted_context.md"):
    """Extrahiert Kontextinformationen und schreibt sie in eine Markdown-Datei."""
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("# Extrahierter Projektkontext\n\n")
        
        # JSON-Dateien extrahieren
        f.write("## JSON-Definitionen\n\n")
        for json_file in JSON_FILES_TO_EXTRACT:
            if os.path.exists(json_file):
                try:
                    with open(json_file, "r", encoding="utf-8") as jf:
                        data = json.load(jf)
                    f.write(f"### {os.path.basename(json_file)}\n\n")
                    f.write("```json\n")
                    json.dump(data, f, indent=2, ensure_ascii=False)
                    f.write("\n```\n\n")
                except Exception as e:
                    f.write(f"Fehler beim Lesen von {json_file}: {str(e)}\n\n")
            else:
                f.write(f"Datei nicht gefunden: {json_file}\n\n")
        
        # Code-Snippets extrahieren
        f.write("## Code-Snippets\n\n")
        for code_file in CODE_SNIPPETS_TO_EXTRACT:
            if os.path.exists(code_file):
                try:
                    with open(code_file, "r", encoding="utf-8") as cf:
                        code = cf.read()
                    f.write(f"### {os.path.basename(code_file)}\n\n")
                    f.write("```python\n")
                    f.write(code)
                    f.write("\n```\n\n")
                except Exception as e:
                    f.write(f"Fehler beim Lesen von {code_file}: {str(e)}\n\n")
            else:
                f.write(f"Datei nicht gefunden: {code_file}\n\n")
        
        # Vollständige Dateien einbeziehen
        f.write("## Vollständige Dateien\n\n")
        for full_file in FILES_TO_INCLUDE_FULL_CONTENT:
            if os.path.exists(full_file):
                try:
                    with open(full_file, "r", encoding="utf-8") as ff:
                        content = ff.read()
                    f.write(f"### {os.path.basename(full_file)}\n\n")
                    f.write("```\n")
                    f.write(content)
                    f.write("\n```\n\n")
                except Exception as e:
                    f.write(f"Fehler beim Lesen von {full_file}: {str(e)}\n\n")
            else:
                f.write(f"Datei nicht gefunden: {full_file}\n\n")


if __name__ == "__main__":
    extract_context()
    print(f"Kontext wurde erfolgreich extrahiert.")
