# src/definitions/character.py
"""
Definiert die Datenstruktur für Charakter-Templates, die aus JSON5-Dateien geladen werden.
"""

from typing import List, Dict, Optional

class CharacterTemplate:
    """
    Repräsentiert die Definition einer Charakterklasse (Template),
    wie sie in characters.json5 definiert ist.
    """
    def __init__(self,
                 id: str,
                 name: str,
                 description: str,
                 base_hp: int,
                 primary_attributes: Dict[str, int], # z.B. {"STR": 10, "DEX": 12, ...}
                 combat_values: Dict[str, int],      # z.B. {"base_stamina": 100, "armor": 5, ...}
                 starting_skills: List[str],         # Liste von Skill-IDs
                 resource_type: str):                # Hauptressource (z.B. "STAMINA", "MANA", "ENERGY")
        
        self.id: str = id
        self.name: str = name
        self.description: str = description
        self.base_hp: int = base_hp # Basis-Lebenspunkte vor Modifikatoren

        # Primärattribute (STR, DEX, INT, CON, WIS)
        self.primary_attributes: Dict[str, int] = primary_attributes
        
        # Basis-Kampfwerte (Ressourcen, Rüstung, etc.)
        # z.B. base_stamina, base_mana, base_energy, armor, magic_resist
        self.combat_values: Dict[str, int] = combat_values

        self.starting_skills: List[str] = starting_skills # Liste der IDs der Start-Skills
        self.resource_type: str = resource_type # Typ der Hauptressource des Charakters

    def __repr__(self) -> str:
        return (f"CharacterTemplate(id='{self.id}', name='{self.name}', "
                f"base_hp={self.base_hp}, attributes={self.primary_attributes}, "
                f"resource='{self.resource_type}')")

    # Zukünftige Methoden könnten hier hinzugefügt werden,
    # z.B. Hilfsfunktionen, um bestimmte Werte abzurufen oder zu validieren.

if __name__ == '__main__':
    # Beispielhafte Erstellung eines CharacterTemplate-Objekts (nur zu Testzwecken)
    krieger_template_data = {
        "id": "krieger_test",
        "name": "Test Krieger",
        "description": "Ein Test-Krieger.",
        "base_hp": 50,
        "primary_attributes": {"STR": 14, "DEX": 10, "INT": 8, "CON": 12, "WIS": 8},
        "combat_values": {"base_stamina": 100, "armor": 5, "magic_resist": 1},
        "starting_skills": ["basic_strike_phys", "power_strike"],
        "resource_type": "STAMINA"
    }
    
    krieger = CharacterTemplate(**krieger_template_data)
    print(krieger)
    print(f"Stärke des Test-Kriegers: {krieger.primary_attributes.get('STR')}")
    print(f"Rüstung des Test-Kriegers: {krieger.combat_values.get('armor')}")