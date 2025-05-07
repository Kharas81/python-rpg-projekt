# src/definitions/character.py
"""
Definiert die Basisstruktur für Charakter-Templates.
Diese Klasse repräsentiert die Blaupause eines Charakters, nicht eine Instanz im Spiel.
"""

class CharacterTemplate:
    """
    Grundlegende Vorlage für einen Charakter im Spiel.
    Enthält statische Daten, die aus JSON5-Dateien geladen werden.
    """
    def __init__(self, id: str, name: str, attributes: dict, skills: list[str]):
        """
        Initialisiert ein Charakter-Template.

        Args:
            id (str): Eindeutige ID des Charakter-Templates.
            name (str): Name des Charakters.
            attributes (dict): Ein Wörterbuch mit Attributen (z.B. {"strength": 10, "dexterity": 8}).
            skills (list[str]): Eine Liste von Skill-IDs, die dieser Charakter potenziell lernen kann.
        """
        if not isinstance(id, str) or not id:
            raise ValueError("Character ID muss ein nicht-leerer String sein.")
        if not isinstance(name, str) or not name:
            raise ValueError("Character Name muss ein nicht-leerer String sein.")
        if not isinstance(attributes, dict):
            raise ValueError("Character Attributes muss ein Dictionary sein.")
        if not isinstance(skills, list) or not all(isinstance(skill_id, str) for skill_id in skills):
            raise ValueError("Character Skills muss eine Liste von Skill-IDs (Strings) sein.")

        self.id: str = id
        self.name: str = name
        self.attributes: dict[str, int] = attributes # z.B. {"strength": 10, "health": 100}
        self.skills: list[str] = skills # Liste von Skill-IDs

    def __str__(self) -> str:
        return f"CharacterTemplate(ID: {self.id}, Name: {self.name}, Attributes: {self.attributes}, Skills: {self.skills})"

    def __repr__(self) -> str:
        return f"CharacterTemplate(id='{self.id}', name='{self.name}', attributes={self.attributes!r}, skills={self.skills!r})"

# Beispiel für eine Validierungsfunktion oder Hilfsfunktion, falls benötigt
def validate_character_data(data: dict) -> bool:
    """
    Validiert die Struktur der Daten für ein Charakter-Template.
    Könnte später komplexer werden und z.B. JSON-Schema verwenden.
    """
    required_keys = ["id", "name", "attributes", "skills"]
    for key in required_keys:
        if key not in data:
            # Hier könnte man später ein logging.error() einfügen
            print(f"Fehlender Schlüssel in Charakterdaten: {key}")
            return False

    if not isinstance(data["attributes"], dict):
        print("Schlüssel 'attributes' in Charakterdaten ist kein Dictionary.")
        return False
    if not isinstance(data["skills"], list):
        print("Schlüssel 'skills' in Charakterdaten ist keine Liste.")
        return False
    return True