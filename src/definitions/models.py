import sys
import dataclasses # Importiere das Modul selbst
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Union

# --- Basis-Definitionen ---
@dataclass(frozen=True)
class AttributeDefinition:
    id: str
    name: str
    description: str

@dataclass(frozen=True)
class CombatStatDefinition:
    id: str
    name: str
    description: str

# --- Skill-Definitionen ---
@dataclass(frozen=True)
class SkillCost:
    resource: Optional[str]
    amount: int

@dataclass(frozen=True)
class SkillAreaDetails:
    max_targets: int
    secondary_modifier: float

@dataclass(frozen=True)
class SkillBonusVsType:
    type: str
    modifier: float

@dataclass(frozen=True)
class SkillEffectDefinition:
    type: str
    damage_type: Optional[str] = None
    base_value: Union[int, str, None] = None
    scaling_attribute: Optional[str] = None
    multiplier: Optional[float] = 1.0
    ignores_armor_percentage: Optional[float] = 0.0
    bonus_vs_type: Optional[SkillBonusVsType] = None
    scaling_factor: Optional[int] = None
    duration: Optional[int] = None
    status_effect: Optional[str] = None
    chance: Optional[float] = 1.0
    magnitude: Optional[int] = None

@dataclass(frozen=True)
class SkillDefinition:
    id: str
    name: str
    description: str
    cost: SkillCost
    target_type: str
    area_details: Optional[SkillAreaDetails] = None
    effects: List[SkillEffectDefinition] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

# --- Charakter/Gegner Attribute ---
@dataclass(frozen=True)
class AttributesSet:
    STR: int = 0
    DEX: int = 0
    INT: int = 0
    CON: int = 0
    WIS: int = 0

# --- Definitionen für verschachtelte Typen ZUERST ---
@dataclass(frozen=True)
class EnemyCombatStats:
    base_hp: int
    max_stamina: Optional[int] = None
    max_energy: Optional[int] = None
    max_mana: Optional[int] = None
    base_armor: int = 0
    base_magic_resist: int = 0

@dataclass(frozen=True)
class ClassCombatStats:
    base_armor: int
    base_magic_resist: int
    max_stamina: Optional[int] = None
    max_energy: Optional[int] = None
    max_mana: Optional[int] = None


# --- Gegner-Definitionen ---
@dataclass(frozen=True)
class EnemyDefinition:
    id: str
    name: str
    level: int
    attributes: AttributesSet
    combat_stats: EnemyCombatStats
    xp_reward: int
    tags: List[str] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)


# --- Klassen-Definitionen ---
@dataclass(frozen=True)
class ClassDefinition:
    id: str
    name: str
    description: str
    starting_attributes: AttributesSet
    starting_combat_stats: ClassCombatStats
    primary_resource: Optional[str] = None
    starting_skills: List[str] = field(default_factory=list)
    key_attributes: List[str] = field(default_factory=list)


# --- Helfende Funktion zur Deserialisierung ---
def dict_to_dataclass(data: Dict[str, Any], cls: type):
    """
    Versucht, ein Dictionary in eine Instanz der gegebenen Dataclass umzuwandeln.
    Behandelt verschachtelte Dataclasses (einfache Fälle).
    """
    if not isinstance(data, dict):
        return data

    field_types = {f.name: f.type for f in cls.__dataclass_fields__.values()}
    init_args = {}
    processed_keys = set()

    try:
        # Felder ohne Default-Wert
        # KORREKTUR: Verwende dataclasses.MISSING statt field.MISSING
        non_default_fields = {f.name for f in cls.__dataclass_fields__.values()
                              if f.default is dataclasses.MISSING and f.default_factory is dataclasses.MISSING}
        for key in non_default_fields:
             if key in data:
                 field_type = field_types[key]
                 value = data[key]
                 init_args[key] = _convert_value(value, field_type, cls)
                 processed_keys.add(key)
             else:
                 # Wenn ein Pflichtfeld im JSON fehlt (und nicht Optional ist), fehlt hier noch Fehlerbehandlung
                 # Fürs Erste gehen wir davon aus, dass die JSONs valide sind bzgl. Pflichtfeldern
                 pass


        # Felder mit Default-Wert (nur wenn im JSON vorhanden, sonst wird der Default verwendet)
        # KORREKTUR: Verwende dataclasses.MISSING statt field.MISSING
        default_fields = {f.name for f in cls.__dataclass_fields__.values()
                           if f.default is not dataclasses.MISSING or f.default_factory is not dataclasses.MISSING}
        for key in default_fields:
            if key in data:
                field_type = field_types[key]
                value = data[key]
                init_args[key] = _convert_value(value, field_type, cls)
                processed_keys.add(key)

        # Ignoriere Schlüssel im JSON, die nicht im Dataclass sind
        # ...

        # Erstelle die Instanz mit den gesammelten Argumenten
        return cls(**init_args)

    except TypeError as e:
        # Spezifischere Fehlermeldung bei fehlenden Pflichtargumenten
        missing_args = non_default_fields - set(init_args.keys())
        if missing_args:
             print(f"Error converting dict to {cls.__name__}: Missing required arguments: {missing_args}", file=sys.stderr)
        else:
             print(f"TypeError converting dict to {cls.__name__}: {e}", file=sys.stderr)

        print(f"Data: {data}", file=sys.stderr)
        print(f"Processed Init Args: {init_args}", file=sys.stderr)
        raise # Fehler weitergeben
    except Exception as e:
        print(f"Unexpected error converting dict to {cls.__name__}: {e}", file=sys.stderr)
        print(f"Data: {data}", file=sys.stderr)
        raise

def _convert_value(value: Any, field_type: type, parent_cls: type):
    """Hilfsfunktion zur Konvertierung von Werten für dict_to_dataclass."""
    origin_type = getattr(field_type, '__origin__', None)
    type_args = getattr(field_type, '__args__', ())

    # Behandlung für Optional[T] -> T oder None
    is_optional = origin_type is Union and len(type_args) == 2 and type(None) in type_args
    if is_optional:
        if value is None:
            return None
        actual_type = next(t for t in type_args if t is not type(None))
        origin_type = getattr(actual_type, '__origin__', None)
        type_args = getattr(actual_type, '__args__', ())
        field_type = actual_type

    # Behandlung für List[T]
    is_list = origin_type is list or origin_type is List
    if is_list:
        if not isinstance(value, list):
             return []

        list_item_type = type_args[0] if type_args else Any
        if hasattr(list_item_type, '__dataclass_fields__'):
             return [dict_to_dataclass(item, list_item_type) for item in value if isinstance(item, dict)] # Stelle sicher, dass item ein dict ist
        else:
             # Konvertiere Elemente in der Liste, falls nötig (z.B. List[int])
             try:
                return [list_item_type(item) for item in value if item is not None]
             except (TypeError, ValueError):
                return value # Fallback

    # Behandlung für verschachtelte Dataclasses
    elif hasattr(field_type, '__dataclass_fields__'):
         if isinstance(value, dict):
             return dict_to_dataclass(value, field_type)
         else:
             return None # Fehler oder None?

    # Einfache Typkonvertierung (int, float, str, bool)
    else:
        # Prüfe auf bool explizit, da bool eine Subklasse von int ist
        if field_type is bool and isinstance(value, int):
             return bool(value)
        try:
            if value is not None and not isinstance(value, field_type):
                return field_type(value)
            else:
                return value
        except (TypeError, ValueError):
             return value # Fallback

