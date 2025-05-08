# src/definitions/opponent.py

from dataclasses import dataclass, field
from typing import List, Dict, Optional

# Wir können die bereits in character.py definierten Typ-Aliase hier wiederverwenden,
# um Konsistenz zu gewährleisten und Wiederholungen zu vermeiden.
# Dies schafft eine kleine Abhängigkeit, ist aber für solch grundlegende Typen oft sinnvoll.
# Alternativ könnten diese Typen in eine gemeinsame `common_types.py` ausgelagert werden.
try:
    from .character import PrimaryAttributeSet, BaseCombatValueSet, SkillIdList
except ImportError:
    # Fallback, falls der direkte Import nicht klappt (z.B. bei isolierter Ausführung)
    # In einer strukturierten Projektausführung sollte der obere Import funktionieren.
    PrimaryAttributeSet = Dict[str, int]
    BaseCombatValueSet = Dict[str, int]
    SkillIdList = List[str]

@dataclass(frozen=True)
class OpponentDefinition:
    """
    Repräsentiert die statische Definition eines Gegnertyps,
    geladen aus den JSON-Dateien (opponents.json5).
    """
    id: str                     # Eindeutige ID des Gegners, z.B. "goblin_lv1"
    name: str                   # Anzeigename, z.B. "Goblin (Lv. 1)"
    description: str            # Kurze Beschreibung des Gegners
    level: int                  # Stufe des Gegners

    primary_attributes: PrimaryAttributeSet   # Startwerte der Primärattribute
                                              # z.B. {"STR": 8, "DEX": 12, ...}

    base_combat_values: BaseCombatValueSet    # Basis-Kampfwerte (HP, Ressourcen, Rüstung etc.)
                                              # z.B. {"base_hp": 50, "armor": 2, ...}
                                              # Enthält typischerweise base_hp, base_mana, base_stamina, base_energy, armor, magic_resist

    skills: SkillIdList                       # Liste der IDs der Skills, die der Gegner nutzen kann
                                              # z.B. ["basic_strike_phys"]

    xp_reward: int                            # Erfahrungspunkte, die der Spieler für das Besiegen erhält
    
    tags: List[str] = field(default_factory=list) # Tags zur Kategorisierung (z.B. "GOBLINOID", "UNDEAD")

    # __post_init__ könnte für Validierungen verwendet werden, falls nötig.
    # z.B. sicherstellen, dass 'level' > 0 ist oder 'xp_reward' nicht negativ.