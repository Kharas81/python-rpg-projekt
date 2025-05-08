# src/definitions/loader.py

import json5
from pathlib import Path
import sys
from typing import Dict, List, Any, Optional

from .character import CharacterDefinition, PrimaryAttributeSet, BaseCombatValueSet, SkillIdList
from .skill import SkillDefinition, SkillCost, SkillEffectDefinition, BonusVsTypeData # Diese Zeile wird in Schritt 4 angepasst

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = PROJECT_ROOT / "src" / "config"
DEFINITIONS_DATA_DIR = PROJECT_ROOT / "src" / "definitions" / "json_data"

SETTINGS_FILE = CONFIG_DIR / "settings.json5"
CHARACTERS_FILE = DEFINITIONS_DATA_DIR / "characters.json5"
SKILLS_FILE = DEFINITIONS_DATA_DIR / "skills.json5"
OPPONENTS_FILE = DEFINITIONS_DATA_DIR / "opponents.json5"

def _load_json_file(file_path: Path) -> Any:
    if not file_path.exists():
        print(f"FEHLER: Definitionsdatei nicht gefunden: {file_path}", file=sys.stderr)
        return None
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json5.load(f)
        return data
    except json5.JSONDecodeError as e:
        print(f"FEHLER: Fehler beim Parsen der JSON5-Datei {file_path}: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"FEHLER: Ein unerwarteter Fehler ist beim Laden von {file_path} aufgetreten: {e}", file=sys.stderr)
        return None

def load_game_settings() -> Optional[Dict[str, Any]]:
    return _load_json_file(SETTINGS_FILE)

def load_character_definitions() -> Optional[Dict[str, CharacterDefinition]]:
    raw_data_list = _load_json_file(CHARACTERS_FILE)
    if not isinstance(raw_data_list, list):
        print(f"FEHLER: Inhalt von {CHARACTERS_FILE} ist keine Liste.", file=sys.stderr)
        return None

    character_definitions: Dict[str, CharacterDefinition] = {}
    for char_dict in raw_data_list:
        if not isinstance(char_dict, dict):
            print(f"WARNUNG: Eintrag in {CHARACTERS_FILE} ist kein Dictionary: {char_dict}", file=sys.stderr)
            continue
        try:
            char_def = CharacterDefinition(
                id=char_dict['id'],
                name=char_dict['name'],
                description=char_dict['description'],
                primary_attributes=PrimaryAttributeSet(char_dict['primary_attributes']),
                base_combat_values=BaseCombatValueSet(char_dict['base_combat_values']),
                starting_skills=SkillIdList(char_dict['starting_skills'])
            )
            character_definitions[char_def.id] = char_def
        except KeyError as e:
            print(f"WARNUNG: Fehlender Schlüssel {e} in Charakterdaten: {char_dict.get('id', 'UNBEKANNTE ID')}", file=sys.stderr)
        except TypeError as e:
            print(f"WARNUNG: Typfehler beim Erstellen von CharacterDefinition für {char_dict.get('id', 'UNBEKANNTE ID')}: {e}", file=sys.stderr)
            
    return character_definitions if character_definitions else None

def _parse_skill_effect(effect_data: Dict[str, Any]) -> SkillEffectDefinition: # Wird in Schritt 4 angepasst
    bonus_vs_type_dict = effect_data.get("bonus_vs_type")
    bonus_vs_type_obj = None
    if bonus_vs_type_dict:
        bonus_vs_type_obj = BonusVsTypeData(**bonus_vs_type_dict)
    
    effect_kwargs = effect_data.copy()
    if 'bonus_vs_type' in effect_kwargs:
        del effect_kwargs['bonus_vs_type']

    return SkillEffectDefinition(
        **effect_kwargs,
        bonus_vs_type=bonus_vs_type_obj
    )

def _parse_skill_dict_to_definition(skill_data: Dict[str, Any]) -> SkillDefinition: # Wird in Schritt 4 angepasst
    cost_data = skill_data.get("cost", {})
    skill_cost_obj = SkillCost(**cost_data)

    effects_list_data = skill_data.get("effects", [])
    effects_obj_list: List[SkillEffectDefinition] = []
    for effect_data in effects_list_data:
        effects_obj_list.append(_parse_skill_effect(effect_data))

    skill_kwargs = skill_data.copy()
    skill_kwargs['cost'] = skill_cost_obj
    skill_kwargs['effects'] = effects_obj_list
    
    return SkillDefinition(**skill_kwargs)

def load_skill_definitions() -> Optional[Dict[str, SkillDefinition]]: # Wird in Schritt 4 angepasst
    raw_data_list = _load_json_file(SKILLS_FILE)
    if not isinstance(raw_data_list, list):
        print(f"FEHLER: Inhalt von {SKILLS_FILE} ist keine Liste.", file=sys.stderr)
        return None

    skill_definitions: Dict[str, SkillDefinition] = {}
    for skill_dict in raw_data_list:
        if not isinstance(skill_dict, dict):
            print(f"WARNUNG: Eintrag in {SKILLS_FILE} ist kein Dictionary: {skill_dict}", file=sys.stderr)
            continue
        try:
            skill_def = _parse_skill_dict_to_definition(skill_dict)
            skill_definitions[skill_def.id] = skill_def
        except KeyError as e:
            print(f"WARNUNG: Fehlender Schlüssel {e} in Skilldaten: {skill_dict.get('id', 'UNBEKANNTE ID')}", file=sys.stderr)
        except TypeError as e:
            print(f"WARNUNG: Typfehler beim Erstellen von SkillDefinition für {skill_dict.get('id', 'UNBEKANNTE ID')}: {e}", file=sys.stderr)
            print(f"         Skill-Daten: {skill_dict}", file=sys.stderr)

    return skill_definitions if skill_definitions else None

def load_opponent_definitions() -> Optional[Dict[str, Dict[str, Any]]]:
    raw_data_list = _load_json_file(OPPONENTS_FILE)
    if not isinstance(raw_data_list, list):
        print(f"FEHLER: Inhalt von {OPPONENTS_FILE} ist keine Liste.", file=sys.stderr)
        return None
        
    indexed_data: Dict[str, Dict[str, Any]] = {}
    for item in raw_data_list:
        if not isinstance(item, dict):
            print(f"WARNUNG: Eintrag in {OPPONENTS_FILE} ist kein Dictionary: {item}", file=sys.stderr)
            continue
        item_id = item.get("id")
        if not item_id:
            print(f"WARNUNG: Eintrag in {OPPONENTS_FILE} hat keine ID: {item}", file=sys.stderr)
            continue
        indexed_data[item_id] = item
    return indexed_data if indexed_data else None