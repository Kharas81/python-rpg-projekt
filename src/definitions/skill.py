# src/definitions/skill.py
"""
Definiert die Basisstruktur für Skill-Templates.
Diese Klasse repräsentiert die Blaupause eines Skills, nicht dessen Anwendung oder Zustand.
"""

class SkillTemplate:
    """
    Grundlegende Vorlage für eine Fähigkeit (Skill) im Spiel.
    Enthält statische Daten, die aus JSON5-Dateien geladen werden.
    """
    def __init__(self, id: str, name: str, description: str, cost: int, effects: list[dict]):
        """
        Initialisiert ein Skill-Template.

        Args:
            id (str): Eindeutige ID des Skill-Templates.
            name (str): Name des Skills.
            description (str): Beschreibung des Skills.
            cost (int): Kosten (z.B. Mana, Energie) für die Anwendung des Skills.
            effects (list[dict]): Eine Liste von Effekt-Definitionen,
                                   die dieser Skill bei Anwendung auslöst.
                                   z.B. [{"type": "damage", "amount": 10, "element": "fire"},
                                         {"type": "heal", "amount": 5}]
        """
        if not isinstance(id, str) or not id:
            raise ValueError("Skill ID muss ein nicht-leerer String sein.")
        if not isinstance(name, str) or not name:
            raise ValueError("Skill Name muss ein nicht-leerer String sein.")
        if not isinstance(description, str): # Beschreibung kann leer sein
            raise ValueError("Skill Description muss ein String sein.")
        if not isinstance(cost, int) or cost < 0:
            raise ValueError("Skill Cost muss eine nicht-negative Ganzzahl sein.")
        if not isinstance(effects, list) or not all(isinstance(effect, dict) for effect in effects):
            raise ValueError("Skill Effects muss eine Liste von Dictionaries sein.")

        self.id: str = id
        self.name: str = name
        self.description: str = description
        self.cost: int = cost # z.B. Manakosten, Energiepunkte etc.
        self.effects: list[dict] = effects # Liste von Effekt-Definitionen

    def __str__(self) -> str:
        return f"SkillTemplate(ID: {self.id}, Name: {self.name}, Cost: {self.cost}, Effects: {len(self.effects)}x)"

    def __repr__(self) -> str:
        return (f"SkillTemplate(id='{self.id}', name='{self.name}', description='{self.description}', "
                f"cost={self.cost}, effects={self.effects!r})")

# Beispiel für eine Validierungsfunktion oder Hilfsfunktion, falls benötigt
def validate_skill_data(data: dict) -> bool:
    """
    Validiert die Struktur der Daten für ein Skill-Template.
    """
    required_keys = ["id", "name", "description", "cost", "effects"]
    for key in required_keys:
        if key not in data:
            # Hier könnte man später ein logging.error() einfügen
            print(f"Fehlender Schlüssel in Skilldaten: {key}")
            return False

    if not isinstance(data["cost"], int) or data["cost"] < 0:
        print("Schlüssel 'cost' in Skilldaten ist keine nicht-negative Ganzzahl.")
        return False
    if not isinstance(data["effects"], list):
        print("Schlüssel 'effects' in Skilldaten ist keine Liste.")
        return False
    # Man könnte hier noch tiefer validieren, z.B. die Struktur der einzelnen Effekte
    return True