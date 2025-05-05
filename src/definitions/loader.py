import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any

# Importiere die Datenmodelle (inkl. ItemDefinition)
from .models import (
    AttributeDefinition, CombatStatDefinition, SkillDefinition, EnemyDefinition,
    ClassDefinition, ItemDefinition,
    SkillCost, SkillAreaDetails, SkillBonusVsType,
    SkillEffectDefinition, AttributesSet, EnemyCombatStats, ClassCombatStats,
    ItemStats,
    dict_to_dataclass
)

# Globale Speicher
ATTRIBUTES: Dict[str, AttributeDefinition] = {}
COMBAT_STATS: Dict[str, CombatStatDefinition] = {}
SKILLS: Dict[str, SkillDefinition] = {}
ENEMIES: Dict[str, EnemyDefinition] = {}
CLASSES: Dict[str, ClassDefinition] = {}
ITEMS: Dict[str, ItemDefinition] = {}

DEFINITIONS_DIR = Path(__file__).parent / 'json_data'

# --- Ladefunktionen ---
def _load_json_file(filename: str) -> Optional[Dict[str, Any]]:
    filepath = DEFINITIONS_DIR / filename
    try:
        with open(filepath, 'r', encoding='utf-8') as f: data = json.load(f)
        if not isinstance(data, dict): print(f"Error: '{filename}' no dict.", file=sys.stderr); return None
        return data
    except FileNotFoundError: print(f"Error: '{filename}' not found at {filepath}.", file=sys.stderr); return None
    except json.JSONDecodeError as e: print(f"Error decoding '{filename}': {e}", file=sys.stderr); return None
    except Exception as e: print(f"Error loading '{filename}': {e}", file=sys.stderr); return None

def _parse_attributes(data: Dict[str, Any]) -> Dict[str, AttributeDefinition]:
    definitions = {}
    for attr_id, definition_data in data.items():
        # Kein komplexes Parsing, try...except hier optional, aber sicherheitshalber
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
    definitions = {}
    for skill_id, definition_data in data.items():
        try: # *** KORREKTUR: try Block beginnt hier ***
            # Füge ID hinzu, falls nicht im JSON (obwohl sie sein sollte)
            if 'id' not in definition_data: definition_data['id'] = skill_id
            skill_def = dict_to_dataclass(definition_data, SkillDefinition)
            if skill_def:
                 definitions[skill_id] = skill_def
        # *** KORREKTUR: except Block für diesen try ***
        except Exception as e:
            print(f"Error parsing skill '{skill_id}': {e}\nData: {definition_data}", file=sys.stderr)
    return definitions

def _parse_enemies(data: Dict[str, Any]) -> Dict[str, EnemyDefinition]:
    definitions = {}
    for enemy_id, definition_data in data.items():
         try: # *** KORREKTUR: try Block beginnt hier ***
            if 'id' not in definition_data: definition_data['id'] = enemy_id
            enemy_def = dict_to_dataclass(definition_data, EnemyDefinition)
            if enemy_def:
                 definitions[enemy_id] = enemy_def
         # *** KORREKTUR: except Block für diesen try ***
         except Exception as e:
            print(f"Error parsing enemy '{enemy_id}': {e}\nData: {definition_data}", file=sys.stderr)
    return definitions

def _parse_classes(data: Dict[str, Any]) -> Dict[str, ClassDefinition]:
    definitions = {}
    for class_id, definition_data in data.items():
        try: # *** KORREKTUR: try Block beginnt hier ***
             if 'id' not in definition_data: definition_data['id'] = class_id
             class_def = dict_to_dataclass(definition_data, ClassDefinition)
             if class_def:
                 definitions[class_id] = class_def
        # *** KORREKTUR: except Block für diesen try ***
        except Exception as e:
            print(f"Error parsing class '{class_id}': {e}\nData: {definition_data}", file=sys.stderr)
    return definitions

def _parse_items(data: Dict[str, Any]) -> Dict[str, ItemDefinition]:
    definitions = {}
    for item_id, definition_data in data.items():
         try: # *** KORREKTUR: try Block beginnt hier ***
            if 'id' not in definition_data: definition_data['id'] = item_id
            item_def = dict_to_dataclass(definition_data, ItemDefinition)
            if item_def:
                 definitions[item_id] = item_def
         # *** KORREKTUR: except Block für diesen try ***
         except Exception as e:
            print(f"Error parsing item '{item_id}': {e}\nData: {definition_data}", file=sys.stderr)
    return definitions

# --- Haupt-Ladefunktion ---
def load_definitions():
    global ATTRIBUTES, COMBAT_STATS, SKILLS, ENEMIES, CLASSES, ITEMS
    print("Loading game definitions...")
    attr_data = _load_json_file("primary_attributes.json"); ATTRIBUTES = _parse_attributes(attr_data) if attr_data else {}; print(f"  - Loaded {len(ATTRIBUTES)} attributes.")
    stat_data = _load_json_file("combat_stats.json"); COMBAT_STATS = _parse_combat_stats(stat_data) if stat_data else {}; print(f"  - Loaded {len(COMBAT_STATS)} combat stats.")
    skill_data = _load_json_file("skills.json"); SKILLS = _parse_skills(skill_data) if skill_data else {}; print(f"  - Loaded {len(SKILLS)} skills.")
    enemy_data = _load_json_file("enemies.json"); ENEMIES = _parse_enemies(enemy_data) if enemy_data else {}; print(f"  - Loaded {len(ENEMIES)} enemies.")
    class_data = _load_json_file("classes.json"); CLASSES = _parse_classes(class_data) if class_data else {}; print(f"  - Loaded {len(CLASSES)} classes.")
    item_data = _load_json_file("items.json"); ITEMS = _parse_items(item_data) if item_data else {}; print(f"  - Loaded {len(ITEMS)} items.")
    print("Definitions loaded successfully.")

# --- Zugriffsmethoden ---
def get_attribute(id: str): return ATTRIBUTES.get(id)
def get_combat_stat(id: str): return COMBAT_STATS.get(id)
def get_skill(id: str): return SKILLS.get(id)
def get_enemy(id: str): return ENEMIES.get(id)
def get_class(id: str): return CLASSES.get(id)
def get_all_classes(): return CLASSES
def get_item(item_id: str) -> Optional[ItemDefinition]: return ITEMS.get(item_id)

# Beispielhafte Nutzung
if __name__ == "__main__":
    load_definitions()
    print("\nExample Item Load:")
    print(get_item("short_sword"))
    print("\nExample Skill Load (Fireball Effects):")
    fb = get_skill("fireball")
    if fb: [print(e) for e in fb.effects]

