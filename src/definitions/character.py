import typing

# Typ-Aliase für bessere Lesbarkeit
AttributesData = typing.Dict[str, int]  # z.B. {"STR": 10, "DEX": 12, ...}
CombatValuesData = typing.Dict[str, typing.Any] # z.B. {"base_hp": 50, "armor": 3, ...}

class Character:
    """
    Repräsentiert die Definition einer Charakterklasse oder eines Gegnertyps.
    Dient als Basis für alle Entitäten mit Attributen, Skills und Kampfwerten.
    """
    def __init__(self,
                 entity_id: str,
                 name: str,
                 description: str,
                 attributes: AttributesData,
                 combat_values: CombatValuesData,
                 skill_ids: typing.List[str],
                 level: typing.Optional[int] = 1, # Hauptsächlich für Gegner-Templates relevant
                 primary_resource: typing.Optional[str] = None, # Hauptsächlich für Spielerklassen relevant
                 xp_reward: typing.Optional[int] = 0, # Für Gegner
                 icon: typing.Optional[str] = None, # Für Spielerklassen
                 ai_strategy: typing.Optional[str] = None, # Für Gegner
                 tags: typing.Optional[typing.List[str]] = None):
        """
        Initialisiert eine neue Charakter-Definition.

        Args:
            entity_id: Die eindeutige ID der Entität (z.B. "krieger", "goblin_lv1").
            name: Der Anzeigename (z.B. "Krieger", "Goblin (Level 1)").
            description: Eine kurze Beschreibung.
            attributes: Ein Dictionary der Basis-Attribute (STR, DEX, CON, INT, WIS).
            combat_values: Ein Dictionary der Basis-Kampfwerte (base_hp, armor, etc.).
            skill_ids: Eine Liste von Skill-IDs, die diese Entität verwenden kann.
            level: Das Level der Entität (Standard: 1).
            primary_resource: Die primäre Ressource der Entität (z.B. "MANA", "STAMINA").
            xp_reward: XP, die für das Besiegen dieser Entität gewährt werden.
            icon: Ein optionales Icon für die UI (hauptsächlich Spielerklassen).
            ai_strategy: Die zu verwendende AI-Strategie (hauptsächlich Gegner).
            tags: Optionale Tags zur Kategorisierung (z.B. ["UNDEAD", "SKELETON"]).
        """
        self.entity_id: str = entity_id
        self.name: str = name
        self.description: str = description
        self.attributes: AttributesData = attributes
        self.combat_values: CombatValuesData = combat_values # Beinhaltet base_hp, armor, etc.
        self.skill_ids: typing.List[str] = skill_ids
        self.level: int = level if level is not None else 1
        self.primary_resource: typing.Optional[str] = primary_resource
        self.xp_reward: int = xp_reward if xp_reward is not None else 0
        self.icon: typing.Optional[str] = icon
        self.ai_strategy: typing.Optional[str] = ai_strategy
        self.tags: typing.List[str] = tags if tags is not None else []

        # Die tatsächlichen HP werden später bei der Instanziierung einer konkreten Spielfigur
        # basierend auf CON und base_hp berechnet (z.B. base_hp + attributes.get('CON', 0) * 5)
        # Hier speichern wir nur die Rohdaten aus der Definition.

    def __repr__(self) -> str:
        return f"<Character(id='{self.entity_id}', name='{self.name}', level={self.level})>"

    def get_attribute(self, attr_name: str) -> int:
        """Gibt den Wert eines spezifischen Attributs zurück."""
        return self.attributes.get(attr_name.upper(), 0) # Stellt sicher, dass der Key großgeschrieben wird

    def get_combat_value(self, value_name: str) -> typing.Any:
        """Gibt einen spezifischen Basis-Kampfwert zurück."""
        return self.combat_values.get(value_name, 0)


if __name__ == '__main__':
    # Beispielhafte Erstellung eines Character-Objekts für Testzwecke
    # Diese Daten würden normalerweise aus den JSON5-Dateien via loader.py kommen
    # und dann zur Erstellung von Character-Objekten verwendet.

    # Simuliere Daten für eine Krieger-Klasse
    krieger_class_data = {
        "entity_id": "krieger",
        "name": "Krieger",
        "description": "Ein robuster Nahkämpfer.",
        "attributes": {"STR": 14, "DEX": 10, "INT": 8, "CON": 12, "WIS": 8},
        "combat_values": {"base_hp": 50, "base_stamina": 100, "armor": 5, "magic_resist": 1},
        "skill_ids": ["basic_strike_phys", "power_strike"],
        "primary_resource": "STAMINA",
        "icon": "🛡️"
    }
    krieger_definition = Character(**krieger_class_data)

    print(f"Charakter-Definition erstellt: {krieger_definition}")
    print(f"  Name: {krieger_definition.name}")
    print(f"  STR: {krieger_definition.get_attribute('STR')}")
    print(f"  CON: {krieger_definition.get_attribute('CON')}")
    print(f"  Base HP (aus combat_values): {krieger_definition.get_combat_value('base_hp')}")
    print(f"  Primärressource: {krieger_definition.primary_resource}")
    print(f"  Skills: {krieger_definition.skill_ids}")

    # Simuliere Daten für einen Goblin-Gegner
    goblin_opponent_data = {
        "entity_id": "goblin_lv1",
        "name": "Goblin (Level 1)",
        "description": "Ein kleiner, fieser Goblin.",
        "attributes": {"STR": 8, "DEX": 12, "INT": 5, "CON": 9, "WIS": 6},
        "combat_values": {"base_hp": 50, "armor": 2, "magic_resist": 0},
        "skill_ids": ["basic_strike_phys"],
        "level": 1,
        "xp_reward": 50,
        "ai_strategy": "basic_melee",
        "tags": ["GOBLINOID", "HUMANOID"]
    }
    goblin_definition = Character(**goblin_opponent_data)
    print(f"\nGegner-Definition erstellt: {goblin_definition}")
    print(f"  Name: {goblin_definition.name}")
    print(f"  Level: {goblin_definition.level}")
    print(f"  CON: {goblin_definition.get_attribute('CON')}")
    print(f"  XP: {goblin_definition.xp_reward}")
    print(f"  AI: {goblin_definition.ai_strategy}")

