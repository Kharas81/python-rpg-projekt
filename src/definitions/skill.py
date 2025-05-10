# src/definitions/skill.py
"""
Definiert die Datenstruktur für Skill-Templates, die aus JSON5-Dateien geladen werden,
basierend auf der überarbeiteten Struktur (Objekt mit Skill-IDs als Schlüssel).
"""

from typing import List, Dict, Any, Optional

class SkillEffectData:
    """
    Daten für einen direkten Effekt eines Skills (Schaden oder Heilung).
    Entspricht dem 'effects'-Objekt in skills.json5.
    """
    def __init__(self,
                 base_damage: Optional[int] = None,
                 base_healing: Optional[int] = None,
                 scaling_attribute: Optional[str] = None,
                 damage_type: Optional[str] = None, # PHYSICAL, MAGIC, FIRE, ICE, HOLY, etc.
                 multiplier: float = 1.0,
                 healing_multiplier: float = 1.0,
                 bonus_crit_chance: float = 0.0,
                 critical_multiplier: float = 1.5, # Standard Krit-Multiplikator, falls nicht anders angegeben
                 bonus_damage_vs_tags: Optional[List[Dict[str, Any]]] = None, # z.B. [{"tag": "UNDEAD", "multiplier": 1.5}]
                 area_type: Optional[str] = None): # z.B. CLEAVE, SPLASH
        self.base_damage = base_damage
        self.base_healing = base_healing
        self.scaling_attribute = scaling_attribute
        self.damage_type = damage_type
        self.multiplier = multiplier
        self.healing_multiplier = healing_multiplier # Eigener Multiplikator für Heilung
        self.bonus_crit_chance = bonus_crit_chance
        self.critical_multiplier = critical_multiplier
        self.bonus_damage_vs_tags = bonus_damage_vs_tags if bonus_damage_vs_tags else []
        self.area_type = area_type

    def __repr__(self) -> str:
        details = []
        if self.base_damage is not None: details.append(f"Dmg: {self.base_damage}")
        if self.base_healing is not None: details.append(f"Heal: {self.base_healing}")
        if self.scaling_attribute: details.append(f"Scales: {self.scaling_attribute}")
        if self.damage_type: details.append(f"Type: {self.damage_type}")
        return f"SkillEffectData({', '.join(details)})"

class AppliedEffectData:
    """
    Daten für einen Status-Effekt, der durch einen Skill angewendet wird.
    Entspricht einem Objekt in der 'applies_effects'-Liste in skills.json5.
    """
    def __init__(self,
                 effect_id: str, # ID des Status-Effekts (z.B. STUNNED, BURNING)
                 potency: float, # Stärke/Wert des Effekts
                 duration_rounds: int, # Dauer in Runden
                 application_chance: float = 1.0, # Wahrscheinlichkeit der Anwendung (0.0 bis 1.0)
                 scales_with_attribute: Optional[str] = None, # Attribut, mit dem die Potenz skaliert
                 attribute_potency_multiplier: float = 1.0): # Multiplikator für die Skalierung der Potenz
        self.effect_id = effect_id
        self.potency = potency
        self.duration_rounds = duration_rounds
        self.application_chance = application_chance
        self.scales_with_attribute = scales_with_attribute
        self.attribute_potency_multiplier = attribute_potency_multiplier

    def __repr__(self) -> str:
        return (f"AppliedEffectData(id='{self.effect_id}', pot={self.potency}, "
                f"dur={self.duration_rounds}r, chance={self.application_chance:.0%})")

class SkillCostData:
    """Daten für die Kosten eines Skills."""
    def __init__(self, value: int, type: str): # z.B. type = "MANA", "STAMINA", "ENERGY", "NONE"
        self.value = value
        self.type = type

    def __repr__(self) -> str:
        return f"SkillCostData(val={self.value}, type='{self.type}')"

class SkillTemplate:
    """
    Repräsentiert die Definition eines Skills, wie sie in skills.json5 definiert ist.
    Der 'id'-Parameter wird hier explizit übergeben, da er in der neuen JSON-Struktur
    der Schlüssel des Objekts ist.
    """
    def __init__(self,
                 skill_id: str, # Der Schlüssel aus der JSON-Datei
                 name: str,
                 description: str,
                 cost: Dict[str, Any], # Wird zu SkillCostData Objekt
                 target_type: str, # z.B. ENEMY_SINGLE, ALLY_SINGLE, SELF, ENEMY_CLEAVE, ENEMY_SPLASH
                 effects: Optional[Dict[str, Any]] = None, # Wird zu SkillEffectData Objekt
                 applies_effects: Optional[List[Dict[str, Any]]] = None): # Liste von AppliedEffectData Objekten
        
        self.id: str = skill_id
        self.name: str = name
        self.description: str = description
        self.cost: SkillCostData = SkillCostData(**cost)
        self.target_type: str = target_type
        
        self.direct_effects: Optional[SkillEffectData] = SkillEffectData(**effects) if effects and isinstance(effects, dict) else None
        
        self.applied_status_effects: List[AppliedEffectData] = []
        if applies_effects:
            for effect_data in applies_effects:
                # Stelle sicher, dass 'effect_id' aus 'id' gelesen wird, falls so in JSON vorhanden
                # Und 'duration' zu 'duration_rounds' gemappt wird
                processed_effect_data = dict(effect_data) # Kopie, um Original nicht zu ändern
                if 'id' in processed_effect_data and 'effect_id' not in processed_effect_data:
                    processed_effect_data['effect_id'] = processed_effect_data.pop('id')
                if 'duration' in processed_effect_data and 'duration_rounds' not in processed_effect_data:
                    processed_effect_data['duration_rounds'] = processed_effect_data.pop('duration')
                
                self.applied_status_effects.append(AppliedEffectData(**processed_effect_data))

    def __repr__(self) -> str:
        return (f"SkillTemplate(id='{self.id}', name='{self.name}', cost={self.cost}, "
                f"target='{self.target_type}')")

if __name__ == '__main__':
    # Beispielhafte Erstellung eines SkillTemplate-Objekts (nur zu Testzwecken)
    # Basierend auf der neuen Struktur von skills.json5
    
    fireball_data_from_json = {
        "name": "Feuerball",
        "description": "Ein explodierender Feuerball, der den Gegner verbrennt.",
        "cost": {"value": 20, "type": "MANA"},
        "target_type": "ENEMY_SINGLE",
        "effects": {
            "base_damage": 8,
            "scaling_attribute": "INT",
            "damage_type": "FIRE",
            "multiplier": 1.5
        },
        "applies_effects": [
            {"effect_id": "BURNING", "potency": 3, "duration_rounds": 2, "application_chance": 0.9}
        ]
    }
    
    fireball_skill = SkillTemplate(skill_id="fireball", **fireball_data_from_json)
    print(fireball_skill)
    if fireball_skill.direct_effects:
        print(f"  Direct Effects: {fireball_skill.direct_effects}")
    if fireball_skill.applied_status_effects:
        for applied_effect in fireball_skill.applied_status_effects:
            print(f"  Applies: {applied_effect}")

    arcane_barrier_data = {
        "name": "Arkane Barriere",
        "description": "Eine magische Barriere, die Schaden absorbiert.",
        "cost": { "value": 30, "type": "MANA" },
        "target_type": "SELF",
        "effects": {}, # In JSON als leeres Objekt {}  <-- KORRIGIERTER PYTHON-KOMMENTAR
        "applies_effects": [
          { "effect_id": "SHIELDED", "potency": 15, "duration_rounds": 3 }
        ]
    }
    arcane_barrier_skill = SkillTemplate(skill_id="arcane_barrier", **arcane_barrier_data)
    print(arcane_barrier_skill)
    if arcane_barrier_skill.direct_effects: # Sollte jetzt None oder ein leeres SkillEffectData sein
         print(f"  Direct Effects: {arcane_barrier_skill.direct_effects}") 
    if arcane_barrier_skill.applied_status_effects:
        for applied_effect in arcane_barrier_skill.applied_status_effects:
            print(f"  Applies: {applied_effect}")

    area_fire_blast_data = {
        "name": "Flächenbrand",
        "description": "Eine Explosion aus Feuer, die mehrere Gegner trifft.",
        "cost": {"value": 25, "type": "MANA"},
        "target_type": "ENEMY_SPLASH",
        "effects": {
            "base_damage": 6, "scaling_attribute": "INT", "damage_type": "FIRE", "multiplier": 1.0
        },
        "applies_effects": [
            # Hier wurde 'id' und 'duration' in der JSON-Vorlage verwendet,
            # der Konstruktor von SkillTemplate sollte das mappen.
            {"id": "BURNING", "duration": 1, "potency": 2} 
        ]
    }
    area_fire_blast_skill = SkillTemplate(skill_id="area_fire_blast", **area_fire_blast_data)
    print(area_fire_blast_skill)
    if area_fire_blast_skill.applied_status_effects:
        for ap_effect in area_fire_blast_skill.applied_status_effects:
            print(f"  Applies: {ap_effect}") 
            assert ap_effect.effect_id == "BURNING" 
            assert ap_effect.duration_rounds == 1