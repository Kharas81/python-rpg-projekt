# src/definitions/skill.py

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from abc import ABC # Wir verwenden ABC nicht aktiv für @abstractmethod, aber es kennzeichnet die Absicht

# --- Type Aliases (bleiben nützlich) ---
SkillEffectPotency = Any
EffectType = str          # z.B. "DAMAGE", "HEAL", "APPLY_STATUS_EFFECT"
DamageType = str          # z.B. "PHYSICAL", "MAGICAL_FIRE", "HOLY"
AttributeName = str       # z.B. "STR", "INT"
StatusEffectId = str      # z.B. "STUNNED", "BURNING"
ResourceType = str        # z.B. "MANA", "STAMINA", "ENERGY", "NONE"
TargetType = str          # z.B. "ENEMY_SINGLE", "SELF"

# --- Gemeinsame Datenstrukturen ---
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

# --- Polymorphe Effektdefinitionen ---
@dataclass(frozen=True)
class BaseEffectDefinition(ABC): # ABC als Marker für eine Basisklasse im Vererbungsbaum
    """
    Abstrakte Basisklasse für alle Skill-Effekt-Definitionen.
    Enthält Felder, die für die meisten oder alle Effekte relevant sind.
    """
    # Der 'type' wird vom Loader verwendet, um die korrekte Subklasse zu instanziieren.
    # Er bleibt auch für Debugging-Zwecke und potenzielle spätere Logik nützlich.
    type: EffectType
    application_chance: float = 1.0 # Standardmäßig 100% Anwendungschance

@dataclass(frozen=True)
class DamageEffectDefinition(BaseEffectDefinition):
    """Spezifische Definition für Schaden verursachende Effekte."""
    damage_type: DamageType
    base_damage: Optional[int] = None               # Basisschaden, null falls Waffenbasis
    scaling_attribute: Optional[AttributeName] = None # Attribut für Skalierung
    attribute_multiplier: Optional[float] = None    # Multiplikator für Skalierung
    armor_penetration_percent: Optional[float] = None # Rüstungsdurchdringung (0.0 bis 1.0)
    bonus_vs_type: Optional[BonusVsTypeData] = None   # Bonus gegen bestimmte Typen

@dataclass(frozen=True)
class HealEffectDefinition(BaseEffectDefinition):
    """Spezifische Definition für Heilungseffekte."""
    base_heal: int
    scaling_attribute: Optional[AttributeName] = None # Attribut für Skalierung
    # Multiplikator für Heilskalierung könnte hier sein, oder flacher Bonus:
    flat_heal_bonus_per_attribute_point: Optional[float] = None

@dataclass(frozen=True)
class ApplyStatusEffectDefinition(BaseEffectDefinition):
    """Spezifische Definition für Effekte, die Statusveränderungen hervorrufen."""
    status_effect_id: StatusEffectId # ID des anzuwendenden Status-Effekts
    duration_rounds: int             # Dauer des Effekts in Runden
    potency: SkillEffectPotency = None # Stärke/Wert des Status-Effekts (kann variieren)
    # Beispiel potency: für DOTs int (Schaden), für Buffs/Debuffs dict {"STAT_UP": wert} oder int (Wert der Änderung)

# --- Haupt-Skilldefinition ---
@dataclass(frozen=True)
class SkillDefinition:
    """
    Repräsentiert die statische Definition eines Skills.
    Nutzt jetzt eine Liste von BaseEffectDefinition für polymorphe Effekte.
    """
    id: str
    name: str
    description: str
    cost: SkillCost
    target_type: TargetType
    effects: List[BaseEffectDefinition] = field(default_factory=list)