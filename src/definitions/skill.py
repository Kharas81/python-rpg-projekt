# src/definitions/skill.py

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

# --- Type Aliases ---
SkillEffectPotency = Any
EffectType = str
DamageType = str
AttributeName = str
StatusEffectId = str
ResourceType = str
TargetType = str

# --- Nested Dataclasses for Skill Structure ---

@dataclass(frozen=True)
class SkillCost:
    """Definiert die Kosten eines Skills."""
    type: ResourceType
    value: int

@dataclass(frozen=True)
class BonusVsTypeData:
    """Definiert Bonus-Effekte gegen bestimmte Gegnertypen (Tags)."""
    tag: str
    bonus_multiplier: float

@dataclass(frozen=True)
class SkillEffectDefinition:
    """
    Definiert einen einzelnen Effekt, den ein Skill haben kann.
    (Platzhalter bis zur polymorphen Umstellung)
    """
    type: EffectType
    application_chance: float = 1.0
    damage_type: Optional[DamageType] = None
    base_damage: Optional[int] = None
    scaling_attribute: Optional[AttributeName] = None
    attribute_multiplier: Optional[float] = None
    armor_penetration_percent: Optional[float] = None
    bonus_vs_type: Optional[BonusVsTypeData] = None
    base_heal: Optional[int] = None
    flat_heal_bonus_per_attribute_point: Optional[float] = None
    status_effect_id: Optional[StatusEffectId] = None
    duration_rounds: Optional[int] = None
    potency: SkillEffectPotency = None

@dataclass(frozen=True)
class SkillDefinition:
    """
    Repräsentiert die statische Definition eines Skills, geladen aus den JSON-Dateien.
    """
    id: str
    name: str
    description: str
    cost: SkillCost
    target_type: TargetType
    effects: List[SkillEffectDefinition] = field(default_factory=list)