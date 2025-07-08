# src/definitions/loader.py
"""
Modul zum Laden von Spieldefinitionen (Charaktere, Skills, Gegner etc.)
aus JSON5-Dateien.
V3: Fügt die Logik zum Laden von Item-Templates hinzu.
"""
import json5 # Wichtig: Benötigt die json5-Bibliothek
import os
from typing import Dict, List, Any, Optional

# Importiere die Template-Klassen aus den anderen Definitionsmodulen
from .character import CharacterTemplate
from .skill import SkillTemplate
from .opponent import OpponentTemplate
from .item import ItemTemplate # NEU: ItemTemplate importieren

# Pfadkonstanten - Sicherstellen, dass sie auf die korrekten Speicherorte zeigen
_JSON_DATA_PATH = os.path.join(os.path.dirname(__file__), 'json_data')
CHARACTERS_FILE = os.path.join(_JSON_DATA_PATH, "characters.json5")
SKILLS_FILE = os.path.join(_JSON_DATA_PATH, "skills.json5")
OPPONENTS_FILE = os.path.join(_JSON_DATA_PATH, "opponents.json5")
ITEMS_FILE = os.path.join(_JSON_DATA_PATH, "items.json5") # NEU: Pfad für Items

# Globale Variablen zum Speichern der geladenen Daten (als Cache)
_character_templates: Optional[Dict[str, CharacterTemplate]] = None
_skill_templates: Optional[Dict[str, SkillTemplate]] = None
_opponent_templates: Optional[Dict[str, OpponentTemplate]] = None
_item_templates: Optional[Dict[str, ItemTemplate]] = None # NEU: Cache für Items

def _load_json5_file(file_path: str) -> Any:
    """
    Hilfsfunktion zum Laden und Parsen einer JSON5-Datei.
    Gibt den geparsten Inhalt zurück.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json5.load(f)
        return data
    except FileNotFoundError:
        print(f"FEHLER: Datei nicht gefunden: {file_path}")
        raise
    except Exception as e:
        print(f"FEHLER beim Laden/Parsen von {file_path}: {e}")
        raise

def load_character_templates() -> Dict[str, CharacterTemplate]:
    """
    Lädt die Charakter-Templates aus der characters.json5 Datei.
    Die Templates werden unter ihrer ID in einem Dictionary gespeichert.
    """
    global _character_templates
    if _character_templates is None:
        data = _load_json5_file(CHARACTERS_FILE)
        templates = {}
        if "character_classes" in data and isinstance(data["character_classes"], list):
            for char_data in data["character_classes"]:
                try:
                    required_fields = ["id", "name", "description", "base_hp", "primary_attributes", "combat_values", "starting_skills", "resource_type"]
                    for field in required_fields:
                        if field not in char_data:
                            raise ValueError(f"Fehlendes Feld '{field}' in Charakter-Template Daten: {char_data.get('id', 'UNKNOWN_ID')}")
                    templates[char_data["id"]] = CharacterTemplate(**char_data)
                except Exception as e:
                    print(f"FEHLER beim Erstellen des CharacterTemplate für ID {char_data.get('id', 'FEHLENDE_ID')}: {e}")
            _character_templates = templates
        else:
            _character_templates = {}
            raise ValueError("Ungültige Struktur in characters.json5: 'character_classes' nicht gefunden oder keine Liste.")
    return _character_templates

def load_skill_templates() -> Dict[str, SkillTemplate]:
    """
    Lädt die Skill-Templates aus der skills.json5 Datei.
    Die Templates werden unter ihrer ID (dem Schlüssel im JSON-Objekt) gespeichert.
    """
    global _skill_templates
    if _skill_templates is None:
        data = _load_json5_file(SKILLS_FILE)
        templates = {}
        # Veraltete Struktur ("skills": {...}) und neue Struktur ({...}) unterstützen
        skill_definitions = data.get("skills", data) if isinstance(data, dict) else {}
        if not isinstance(skill_definitions, dict):
             _skill_templates = {}
             raise ValueError("Ungültige Struktur in skills.json5: Muss ein Objekt sein, das Skill-IDs auf Skill-Definitionen mappt.")

        for skill_id, skill_data in skill_definitions.items():
            try:
                required_fields_skill = ["name", "description", "cost", "target_type"]
                for field in required_fields_skill:
                    if field not in skill_data:
                         raise ValueError(f"Fehlendes Feld '{field}' in Skill-Template Daten für ID: {skill_id}")
                templates[skill_id] = SkillTemplate(skill_id=skill_id, **skill_data)
            except Exception as e:
                print(f"FEHLER beim Erstellen des SkillTemplate für ID {skill_id}: {e}")
        _skill_templates = templates
    return _skill_templates

def load_opponent_templates() -> Dict[str, OpponentTemplate]:
    """
    Lädt die Gegner-Templates aus der opponents.json5 Datei.
    """
    global _opponent_templates
    if _opponent_templates is None:
        data = _load_json5_file(OPPONENTS_FILE)
        templates = {}
        if "opponents" in data and isinstance(data["opponents"], list):
            for opp_data in data["opponents"]:
                try:
                    required_fields_opp = [
                        "id", "name", "description", "level", "base_hp",
                        "primary_attributes", "combat_values", "skills", "xp_reward"
                    ]
                    for field in required_fields_opp:
                        if field not in opp_data:
                            raise ValueError(f"Fehlendes Feld '{field}' in Gegner-Template Daten für ID: {opp_data.get('id', 'UNKNOWN_ID')}")
                    templates[opp_data["id"]] = OpponentTemplate(**opp_data)
                except Exception as e:
                    print(f"FEHLER beim Erstellen des OpponentTemplate für ID {opp_data.get('id', 'FEHLENDE_ID')}: {e}")
            _opponent_templates = templates
        else:
            _opponent_templates = {}
            raise ValueError("Ungültige Struktur in opponents.json5: 'opponents' nicht gefunden oder keine Liste.")
    return _opponent_templates

# NEU: Funktion zum Laden der Item-Templates
def load_item_templates() -> Dict[str, ItemTemplate]:
    """
    Lädt die Item-Templates aus der items.json5 Datei.
    """
    global _item_templates
    if _item_templates is None:
        data = _load_json5_file(ITEMS_FILE)
        templates = {}
        if "items" in data and isinstance(data["items"], dict):
            for item_id, item_data in data["items"].items():
                try:
                    # Hier könnten wir auch eine Validierung der Pflichtfelder einbauen
                    templates[item_id] = ItemTemplate(item_id=item_id, **item_data)
                except Exception as e:
                    print(f"FEHLER beim Erstellen des ItemTemplate für ID {item_id}: {e}")
            _item_templates = templates
        else:
            _item_templates = {}
            raise ValueError("Ungültige Struktur in items.json5: 'items' nicht gefunden oder kein Objekt.")
    return _item_templates

def load_all_definitions():
    """Lädt alle bekannten Definitionstypen."""
    print("Lade Charakter-Templates...")
    load_character_templates()
    print("Lade Skill-Templates...")
    load_skill_templates()
    print("Lade Gegner-Templates...")
    load_opponent_templates()
    print("Lade Item-Templates...") # HINZUGEFÜGT
    load_item_templates()          # HINZUGEFÜGT
    print("Alle Basis-Definitionen geladen (oder aus Cache bezogen).")

if __name__ == '__main__':
    print(f"Erwarteter Pfad für CHARACTERS_FILE: {os.path.abspath(CHARACTERS_FILE)}")
    print(f"Erwarteter Pfad für SKILLS_FILE: {os.path.abspath(SKILLS_FILE)}")
    print(f"Erwarteter Pfad für OPPONENTS_FILE: {os.path.abspath(OPPONENTS_FILE)}")
    print(f"Erwarteter Pfad für ITEMS_FILE: {os.path.abspath(ITEMS_FILE)}") # HINZUGEFÜGT

    try:
        # Bestehende Tests bleiben unverändert
        char_templates = load_character_templates()
        print(f"\n--- Geladene Charakter-Templates ({len(char_templates)}) ---")
        for char_id, char_template in char_templates.items():
            print(char_template)

        skill_templates = load_skill_templates()
        print(f"\n--- Geladene Skill-Templates ({len(skill_templates)}) ---")
        for skill_id, skill_template in skill_templates.items():
            print(f"{skill_template} - Direct: {skill_template.direct_effects}, Applies: {skill_template.applied_status_effects}")

        opponent_templates = load_opponent_templates()
        print(f"\n--- Geladene Gegner-Templates ({len(opponent_templates)}) ---")
        for opp_id, opp_template in opponent_templates.items():
            print(opp_template)

        # HINZUGEFÜGT: Test für Item-Templates
        item_templates = load_item_templates()
        print(f"\n--- Geladene Item-Templates ({len(item_templates)}) ---")
        for item_id, item_template in item_templates.items():
            print(item_template)
            print(f"  Direct Effects: {item_template.direct_effects}")

        print("\n--- Erneutes Laden (sollte aus Cache kommen) ---")
        load_all_definitions()

    except Exception as e:
        print(f"\nEin Fehler ist während des Testlaufs aufgetreten: {e}")
        import traceback
        traceback.print_exc()