import sys
import dataclasses
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Union

# --- Basis-Definitionen ---
# ... (AttributeDefinition, CombatStatDefinition unverändert) ...
@dataclass(frozen=True)
class AttributeDefinition: id: str; name: str; description: str
@dataclass(frozen=True)
class CombatStatDefinition: id: str; name: str; description: str

# --- Item-Definitionen ---
# *** NEU: ItemStats und ItemDefinition ***
@dataclass(frozen=True)
class ItemStats:
    damage: Optional[int] = None
    armor: Optional[int] = None
    magic_resist: Optional[int] = None
    # TODO: Weitere Stats wie Attributboni etc. könnten hier hinzukommen
    # str_bonus: Optional[int] = None

@dataclass(frozen=True)
class ItemDefinition:
    id: str
    name: str
    description: str
    item_type: str # z.B. WEAPON, ARMOR, POTION
    slot: Optional[str] = None # z.B. WEAPON_MAIN, CHEST, FINGER, null für Verbrauchsgüter
    stats: ItemStats = field(default_factory=ItemStats) # Hält die Werte des Items
    allowed_classes: Optional[List[str]] = None # Welche Klassen können es benutzen? (None = alle)
    # TODO: Weitere Felder wie Wert, Gewicht, Voraussetzungen etc.

# --- Skill-Definitionen ---
# ... (SkillCost, SkillAreaDetails, SkillBonusVsType, SkillEffectDefinition, SkillDefinition unverändert) ...
@dataclass(frozen=True)
class SkillCost: resource: Optional[str]; amount: int
@dataclass(frozen=True)
class SkillAreaDetails: max_targets: int; secondary_modifier: float
@dataclass(frozen=True)
class SkillBonusVsType: type: str; modifier: float
@dataclass(frozen=True)
class SkillEffectDefinition:
    type: str; damage_type: Optional[str] = None; base_value: Union[int, str, None] = None
    scaling_attribute: Optional[str] = None; multiplier: Optional[float] = 1.0
    ignores_armor_percentage: Optional[float] = 0.0; bonus_vs_type: Optional[SkillBonusVsType] = None
    scaling_factor: Optional[int] = None; duration: Optional[int] = None
    status_effect: Optional[str] = None; chance: Optional[float] = 1.0
    magnitude: Optional[Any] = None
@dataclass(frozen=True)
class SkillDefinition:
    id: str; name: str; description: str; cost: SkillCost; target_type: str
    area_details: Optional[SkillAreaDetails] = None
    effects: List[SkillEffectDefinition] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

# --- Charakter/Gegner Attribute ---
# ... (AttributesSet unverändert) ...
@dataclass(frozen=True)
class AttributesSet: STR: int = 0; DEX: int = 0; INT: int = 0; CON: int = 0; WIS: int = 0

# --- Definitionen für verschachtelte Typen ZUERST ---
# ... (EnemyCombatStats, ClassCombatStats unverändert) ...
@dataclass(frozen=True)
class EnemyCombatStats: base_hp: int; max_stamina: Optional[int] = None; max_energy: Optional[int] = None; max_mana: Optional[int] = None; base_armor: int = 0; base_magic_resist: int = 0
@dataclass(frozen=True)
class ClassCombatStats: base_armor: int; base_magic_resist: int; max_stamina: Optional[int] = None; max_energy: Optional[int] = None; max_mana: Optional[int] = None

# --- Gegner-Definitionen ---
# ... (EnemyDefinition unverändert) ...
@dataclass(frozen=True)
class EnemyDefinition: id: str; name: str; level: int; attributes: AttributesSet; combat_stats: EnemyCombatStats; xp_reward: int; tags: List[str] = field(default_factory=list); skills: List[str] = field(default_factory=list)

# --- Klassen-Definitionen ---
# ... (ClassDefinition unverändert) ...
@dataclass(frozen=True)
class ClassDefinition: id: str; name: str; description: str; starting_attributes: AttributesSet; starting_combat_stats: ClassCombatStats; primary_resource: Optional[str] = None; starting_skills: List[str] = field(default_factory=list); key_attributes: List[str] = field(default_factory=list)

# --- Helfende Funktion zur Deserialisierung ---
# ... (dict_to_dataclass, _convert_value unverändert) ...
def dict_to_dataclass(data: Dict[str, Any], cls: type):
    if not isinstance(data, dict): return data
    field_types = {f.name: f.type for f in cls.__dataclass_fields__.values()}
    init_args = {}
    try:
        non_default_fields = {f.name for f in cls.__dataclass_fields__.values() if f.default is dataclasses.MISSING and f.default_factory is dataclasses.MISSING}
        for key in non_default_fields:
             if key in data: init_args[key] = _convert_value(data[key], field_types[key], cls)
             # else: Fehlendes Pflichtfeld?
        default_fields = {f.name for f in cls.__dataclass_fields__.values() if f.default is not dataclasses.MISSING or f.default_factory is not dataclasses.MISSING}
        for key in default_fields:
            if key in data: init_args[key] = _convert_value(data[key], field_types[key], cls)
        return cls(**init_args)
    except TypeError as e:
        missing_args = non_default_fields - set(init_args.keys()); msg = f"Missing: {missing_args}" if missing_args else str(e)
        print(f"TypeError converting to {cls.__name__}: {msg}\nData: {data}\nArgs: {init_args}", file=sys.stderr); raise
    except Exception as e: print(f"Error converting to {cls.__name__}: {e}\nData: {data}", file=sys.stderr); raise

def _convert_value(value: Any, field_type: type, parent_cls: type):
    origin_type = getattr(field_type, '__origin__', None); type_args = getattr(field_type, '__args__', ())
    is_optional = origin_type is Union and len(type_args) == 2 and type(None) in type_args
    if is_optional:
        if value is None: return None
        actual_type = next(t for t in type_args if t is not type(None)); origin_type = getattr(actual_type, '__origin__', None); type_args = getattr(actual_type, '__args__', ()); field_type = actual_type
    is_list = origin_type is list or origin_type is List
    if is_list:
        if not isinstance(value, list): return []
        list_item_type = type_args[0] if type_args else Any
        if hasattr(list_item_type, '__dataclass_fields__'): return [dict_to_dataclass(item, list_item_type) for item in value if isinstance(item, dict)]
        else:
             try: return [list_item_type(item) for item in value if item is not None]
             except (TypeError, ValueError): return value
    elif hasattr(field_type, '__dataclass_fields__'):
         if isinstance(value, dict): return dict_to_dataclass(value, field_type)
         else: return None
    else:
        if field_type is bool and isinstance(value, int): return bool(value)
        try:
            if value is not None and not isinstance(value, field_type): return field_type(value)
            else: return value
        except (TypeError, ValueError): return value

