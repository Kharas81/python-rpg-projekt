import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any

# Importiere die Datenmodelle
from .models import (
    AttributeDefinition, CombatStatDefinition, SkillDefinition, EnemyDefinition,
    ClassDefinition, SkillCost, SkillAreaDetails, SkillBonusVsType,
    SkillEffectDefinition, AttributesSet, EnemyCombatStats, ClassCombatStats,
    dict_to_dataclass
)

# --- Globale Speicher für geladene Definitionen ---
# Wir verwenden Dictionaries, wobei der Schlüssel die ID ist (z.B. "STR", "fireball")
# und der Wert die Dataclass-Instanz.
ATTRIBUTES: Dict[str, AttributeDefinition] = {}
COMBAT_STATS: Dict[str, CombatStatDefinition] = {}
SKILLS: Dict[str, SkillDefinition] = {}
ENEMIES: Dict[str, EnemyDefinition] = {}
CLASSES: Dict[str, ClassDefinition] = {}

# Pfad zum Verzeichnis mit den JSON-Definitionen
# Geht davon aus, dass loader.py in src/definitions/ liegt
# Passt den Pfad an, falls die Struktur anders ist.
DEFINITIONS_DIR = Path(__file__).parent / 'json_data'

# --- Ladefunktionen ---

def _load_json_file(filename: str) -> Optional[Dict[str, Any]]:
    """Lädt eine einzelne JSON-Datei und gibt ihren Inhalt als Dict zurück."""
    filepath = DEFINITIONS_DIR / filename
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not isinstance(data, dict):
            print(f"Error: JSON file '{filename}' does not contain a dictionary.", file=sys.stderr)
            return None
        return data
    except FileNotFoundError:
        print(f"Error: JSON file '{filename}' not found at '{filepath}'.", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON file '{filename}': {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"An unexpected error occurred loading '{filename}': {e}", file=sys.stderr)
        return None

def _parse_attributes(data: Dict[str, Any]) -> Dict[str, AttributeDefinition]:
    """Wandelt Rohdaten in AttributeDefinition-Objekte um."""
    definitions = {}
    for attr_id, definition_data in data.items():
        try:
            definitions[attr_id] = AttributeDefinition(
                id=attr_id,
                name=definition_data.get("name", "N/A"),
                description=definition_data.get("description", "")
            )
        except Exception as e:
            print(f"Error parsing attribute '{attr_id}': {e}\nData: {definition_data}", file=sys.stderr)
    return definitions

def _parse_combat_stats(data: Dict[str, Any]) -> Dict[str, CombatStatDefinition]:
    """Wandelt Rohdaten in CombatStatDefinition-Objekte um."""
    definitions = {}
    for stat_id, definition_data in data.items():
         try:
            definitions[stat_id] = CombatStatDefinition(
                id=stat_id,
                name=definition_data.get("name", "N/A"),
                description=definition_data.get("description", "")
            )
         except Exception as e:
            print(f"Error parsing combat stat '{stat_id}': {e}\nData: {definition_data}", file=sys.stderr)
    return definitions

def _parse_skills(data: Dict[str, Any]) -> Dict[str, SkillDefinition]:
    """Wandelt Rohdaten in SkillDefinition-Objekte um."""
    definitions = {}
    for skill_id, definition_data in data.items():
        try:
            # Füge die ID zum Dictionary hinzu, bevor es konvertiert wird
            definition_data['id'] = skill_id
            skill_def = dict_to_dataclass(definition_data, SkillDefinition)
            if skill_def:
                 definitions[skill_id] = skill_def
        except Exception as e:
            print(f"Error parsing skill '{skill_id}': {e}\nData: {definition_data}", file=sys.stderr)
    return definitions

def _parse_enemies(data: Dict[str, Any]) -> Dict[str, EnemyDefinition]:
    """Wandelt Rohdaten in EnemyDefinition-Objekte um."""
    definitions = {}
    for enemy_id, definition_data in data.items():
         try:
            # Füge die ID zum Dictionary hinzu, bevor es konvertiert wird
            definition_data['id'] = enemy_id
            enemy_def = dict_to_dataclass(definition_data, EnemyDefinition)
            if enemy_def:
                 definitions[enemy_id] = enemy_def
         except Exception as e:
            print(f"Error parsing enemy '{enemy_id}': {e}\nData: {definition_data}", file=sys.stderr)
    return definitions

def _parse_classes(data: Dict[str, Any]) -> Dict[str, ClassDefinition]:
    """Wandelt Rohdaten in ClassDefinition-Objekte um."""
    definitions = {}
    for class_id, definition_data in data.items():
        try:
             # Füge die ID zum Dictionary hinzu, bevor es konvertiert wird
            definition_data['id'] = class_id
            class_def = dict_to_dataclass(definition_data, ClassDefinition)
            if class_def:
                 definitions[class_id] = class_def
        except Exception as e:
            print(f"Error parsing class '{class_id}': {e}\nData: {definition_data}", file=sys.stderr)
    return definitions

# --- Haupt-Ladefunktion ---
def load_definitions():
    """
    Lädt alle JSON-Definitionen aus dem json_data-Verzeichnis
    und speichert sie in den globalen Dictionaries.
    Sollte beim Programmstart aufgerufen werden.
    """
    global ATTRIBUTES, COMBAT_STATS, SKILLS, ENEMIES, CLASSES

    print("Loading game definitions...")

    attr_data = _load_json_file("primary_attributes.json")
    if attr_data:
        ATTRIBUTES = _parse_attributes(attr_data)
        print(f"  - Loaded {len(ATTRIBUTES)} attributes.")

    stat_data = _load_json_file("combat_stats.json")
    if stat_data:
        COMBAT_STATS = _parse_combat_stats(stat_data)
        print(f"  - Loaded {len(COMBAT_STATS)} combat stats.")

    skill_data = _load_json_file("skills.json")
    if skill_data:
        SKILLS = _parse_skills(skill_data)
        print(f"  - Loaded {len(SKILLS)} skills.")

    enemy_data = _load_json_file("enemies.json")
    if enemy_data:
        ENEMIES = _parse_enemies(enemy_data)
        print(f"  - Loaded {len(ENEMIES)} enemies.")

    class_data = _load_json_file("classes.json")
    if class_data:
        CLASSES = _parse_classes(class_data)
        print(f"  - Loaded {len(CLASSES)} classes.")

    print("Definitions loaded successfully.")

# --- Zugriffsmethoden (optional, aber sauber) ---
def get_attribute(attribute_id: str) -> Optional[AttributeDefinition]:
    return ATTRIBUTES.get(attribute_id)

def get_combat_stat(stat_id: str) -> Optional[CombatStatDefinition]:
    return COMBAT_STATS.get(stat_id)

def get_skill(skill_id: str) -> Optional[SkillDefinition]:
    return SKILLS.get(skill_id)

def get_enemy(enemy_id: str) -> Optional[EnemyDefinition]:
    return ENEMIES.get(enemy_id)

def get_class(class_id: str) -> Optional[ClassDefinition]:
    return CLASSES.get(class_id)

def get_all_skills() -> Dict[str, SkillDefinition]:
    return SKILLS

def get_all_classes() -> Dict[str, ClassDefinition]:
    return CLASSES
# etc.

# Beispielhafte Nutzung (kann entfernt werden):
if __name__ == "__main__":
    load_definitions()

    print("\n--- Example Access ---")
    warrior_class = get_class("warrior")
    if warrior_class:
        print(f"Warrior starting STR: {warrior_class.starting_attributes.STR}")
        print(f"Warrior primary resource: {warrior_class.primary_resource}")
        first_skill_id = warrior_class.starting_skills[0]
        first_skill = get_skill(first_skill_id)
        if first_skill:
            print(f"Warrior first skill: {first_skill.name} (Cost: {first_skill.cost.amount} {first_skill.cost.resource or 'N/A'})")

    fireball_skill = get_skill("fireball")
    if fireball_skill:
        print(f"\nFireball details:")
        print(f"  Target: {fireball_skill.target_type}")
        for effect in fireball_skill.effects:
            print(f"  Effect Type: {effect.type}")
            if effect.type == "DAMAGE":
                 print(f"    Damage: {effect.base_value} * {effect.multiplier} (scaling: {effect.scaling_attribute}, type: {effect.damage_type})")
            elif effect.type == "APPLY_STATUS":
                 print(f"    Status: {effect.status_effect} (duration: {effect.duration})")

