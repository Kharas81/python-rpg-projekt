import typing

# Typ-Aliase für Klarheit, könnten später in eine zentrale types.py ausgelagert werden
EffectData = typing.Dict[str, typing.Any]
CostData = typing.Dict[str, typing.Any]
StatusEffectApplicationData = typing.Dict[str, typing.Any]

class Skill:
    """
    Repräsentiert einen einzelnen Skill im Spiel mit all seinen Eigenschaften.
    """
    def __init__(self,
                 skill_id: str,
                 name: str,
                 description: str,
                 cost: CostData,
                 target: str,
                 effects: typing.List[EffectData],
                 applies_effects: typing.List[StatusEffectApplicationData],
                 allowed_classes: typing.Optional[typing.List[str]] = None,
                 target_count: typing.Optional[int] = 1):
        """
        Initialisiert ein neues Skill-Objekt.

        Args:
            skill_id: Die eindeutige ID des Skills (z.B. "fireball").
            name: Der Anzeigename des Skills (z.B. "Feuerball").
            description: Eine kurze Beschreibung des Skills.
            cost: Ein Dictionary, das die Kosten des Skills definiert (z.B. {"resource": "MANA", "amount": 10}).
            target: Der Zieltyp des Skills (z.B. "ENEMY", "ALLY", "SELF", "AREA").
            effects: Eine Liste von Dictionaries, die die direkten Effekte des Skills beschreiben (z.B. Schaden, Heilung).
            applies_effects: Eine Liste von Dictionaries, die Status-Effekte beschreiben, die der Skill anwendet.
            allowed_classes: Optionale Liste von Klassen-IDs, die diesen Skill verwenden dürfen.
            target_count: Optionale Anzahl der Ziele (relevant für "AREA" Skills, Standard ist 1).
        """
        self.skill_id: str = skill_id
        self.name: str = name
        self.description: str = description
        self.cost: CostData = cost
        self.target: str = target
        self.effects: typing.List[EffectData] = effects
        self.applies_effects: typing.List[StatusEffectApplicationData] = applies_effects
        self.allowed_classes: typing.List[str] = allowed_classes if allowed_classes is not None else []
        self.target_count: int = target_count if target_count is not None else 1

    def __repr__(self) -> str:
        return f"<Skill(id='{self.skill_id}', name='{self.name}')>"

    def get_cost_resource(self) -> typing.Optional[str]:
        """Gibt die Art der Ressource zurück, die der Skill kostet (z.B. 'MANA', 'STAMINA')."""
        return self.cost.get("resource")

    def get_cost_amount(self) -> int:
        """Gibt die Menge der Ressource zurück, die der Skill kostet."""
        return self.cost.get("amount", 0)

    # Weitere Methoden könnten hier hinzugefügt werden, z.B.:
    # - is_offensive() -> bool
    # - is_healing() -> bool
    # - affects_multiple_targets() -> bool
    # - get_damage_type() -> Optional[str]

if __name__ == '__main__':
    # Beispielhafte Erstellung eines Skill-Objekts für Testzwecke
    # Diese Daten würden normalerweise vom loader.py aus der JSON5-Datei kommen

    # Simuliere geladene Daten für "fireball" (Auszug)
    fireball_data_from_json = {
        "name": "Fireball",
        "description": "Schleudert einen Feuerball, der Feuerschaden verursacht und das Ziel verbrennt.",
        "cost": { "resource": "MANA", "amount": 20 },
        "target": "ENEMY",
        "effects": [
          { "type": "DAMAGE", "damage_type": "FIRE", "base_damage": 10, "attribute": "INT", "multiplier": 2.0 }
        ],
        "applies_effects": [
          { "id": "BURNING", "duration": 2, "potency": 3 }
        ],
        "allowed_classes": ["Magier"],
        "target_count": 1
    }

    fireball_skill = Skill(
        skill_id="fireball",
        name=fireball_data_from_json["name"],
        description=fireball_data_from_json["description"],
        cost=fireball_data_from_json["cost"],
        target=fireball_data_from_json["target"],
        effects=fireball_data_from_json["effects"],
        applies_effects=fireball_data_from_json["applies_effects"],
        allowed_classes=fireball_data_from_json["allowed_classes"],
        target_count=fireball_data_from_json["target_count"]
    )

    print(f"Skill erstellt: {fireball_skill}")
    print(f"  Name: {fireball_skill.name}")
    print(f"  Kosten: {fireball_skill.get_cost_amount()} {fireball_skill.get_cost_resource()}")
    print(f"  Zieltyp: {fireball_skill.target}")
    print(f"  Erster Effekt-Typ: {fireball_skill.effects[0]['type'] if fireball_skill.effects else 'Keine'}")
    print(f"  Verursacht Status-Effekt: {fireball_skill.applies_effects[0]['id'] if fireball_skill.applies_effects else 'Keine'}")

    basic_strike_data = {
        "name": "Basic Strike Phys",
        "description": "Ein einfacher Waffenschlag.",
        "cost": { "resource": "NONE", "amount": 0 },
        "target": "ENEMY",
        "effects": [
            { "type": "DAMAGE", "damage_type": "PHYSICAL", "base_damage": None, "attribute": "STR", "multiplier": 1.0 }
        ],
        "applies_effects": []
    }
    basic_strike_skill = Skill(
        skill_id="basic_strike_phys",
        **basic_strike_data
    )
    print(f"\nSkill erstellt: {basic_strike_skill}")
    print(f"  Kosten: {basic_strike_skill.get_cost_amount()} {basic_strike_skill.get_cost_resource()}")

