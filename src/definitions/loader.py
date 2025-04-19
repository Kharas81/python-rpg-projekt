import json
import os

def load_json(file_path):
    """
    Lädt eine JSON-Datei und gibt die Daten zurück.

    :param file_path: Pfad zur JSON-Datei
    :return: Inhalt der JSON-Datei als Dictionary
    :raises FileNotFoundError: Wenn die Datei nicht existiert
    :raises ValueError: Wenn die Datei kein gültiges JSON ist
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Die Datei {file_path} wurde nicht gefunden.")
    
    with open(file_path, "r", encoding="utf-8") as json_file:
        try:
            data = json.load(json_file)
        except json.JSONDecodeError as e:
            raise ValueError(f"Fehler beim Laden der JSON-Datei {file_path}: {e}")
    
    return data


def validate_json(data, required_keys):
    """
    Validiert, ob die JSON-Daten alle erforderlichen Schlüssel enthalten.

    :param data: Das zu validierende JSON-Daten-Dictionary
    :param required_keys: Liste der erforderlichen Schlüssel
    :return: True, wenn die Validierung erfolgreich ist
    :raises KeyError: Wenn ein erforderlicher Schlüssel fehlt
    """
    missing_keys = [key for key in required_keys if key not in data]
    if missing_keys:
        raise KeyError(f"Die folgenden Schlüssel fehlen in den JSON-Daten: {missing_keys}")
    
    return True


if __name__ == "__main__":
    # Beispiel: JSON-Dateien laden und validieren
    from config.config import SKILLS_JSON, CHARACTERS_JSON

    try:
        # Skills laden und validieren
        skills = load_json(SKILLS_JSON)
        validate_json(skills, required_keys=["name", "type", "power"])

        # Charakterdaten laden und validieren
        characters = load_json(CHARACTERS_JSON)
        validate_json(characters, required_keys=["name", "class", "attributes"])

        print("JSON-Daten erfolgreich geladen und validiert.")
    except (FileNotFoundError, ValueError, KeyError) as e:
        print(f"Fehler: {e}")
