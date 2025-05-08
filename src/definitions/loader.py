# src/definitions/loader.py

import json5 # type: ignore
from pathlib import Path
from typing import Dict, List, Any

# Importiere die geänderten Skill-Definitionsklassen und andere benötigte Klassen/Exceptions
from .character import CharacterDefinition, PrimaryAttributeSet, BaseCombatValueSet, SkillIdList
from .skill import (
    SkillDefinition, SkillCost, BonusVsTypeData,
    BaseEffectDefinition, DamageEffectDefinition, HealEffectDefinition, ApplyStatusEffectDefinition,
    EffectType, DamageType, AttributeName, StatusEffectId, SkillEffectPotency # Type Aliases
)
from .opponent import OpponentDefinition
from src.utils.exceptions import DefinitionFileNotFoundError, DefinitionParsingError, DefinitionContentError, RPGBaseException


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = PROJECT_ROOT / "src" / "config"
DEFINITIONS_DATA_DIR = PROJECT_ROOT / "src" / "definitions" / "json_data"

SETTINGS_FILE = CONFIG_DIR / "settings.json5"
CHARACTERS_FILE = DEFINITIONS_DATA_DIR / "characters.json5"
SKILLS_FILE = DEFINITIONS_DATA_DIR / "skills.json5"
OPPONENTS_FILE = DEFINITIONS_DATA_DIR / "opponents.json5"

def _load_json_file(file_path: Path) -> Any:
    if not file_path.exists():
        raise DefinitionFileNotFoundError(filepath=str(file_path))
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json5.load(f)
        return data
    except json5.JSONDecodeError as e:
        raise DefinitionParsingError(filepath=str(file_path), original_exception=e)
    except Exception as e:
        raise DefinitionFileError(message=f"Ein unerwarteter Fehler ist beim Laden von {file_path} aufgetreten: {e}", 
                                  filepath=str(file_path))

def load_game_settings() -> Dict[str, Any]:
    data = _load_json_file(SETTINGS_FILE)
    if not isinstance(data, dict):
        raise DefinitionContentError(filepath=str(SETTINGS_FILE), 
                                     message="settings.json5 muss ein Dictionary auf Top-Level sein.")
    return data

def load_character_definitions() -> Dict[str, CharacterDefinition]:
    # Implementierung bleibt gleich wie im vorherigen Schritt
    raw_data_list = _load_json_file(CHARACTERS_FILE)
    if not isinstance(raw_data_list, list):
        raise DefinitionContentError(filepath=str(CHARACTERS_FILE), message=f"Inhalt von {CHARACTERS_FILE.name} ist keine Liste.")
    defs: Dict[str, CharacterDefinition] = {}
    for i, item_dict in enumerate(raw_data_list):
        if not isinstance(item_dict, dict):
            raise DefinitionContentError(filepath=str(CHARACTERS_FILE), message=f"Eintrag #{i} ist kein Dictionary.")
        try:
            defs[item_dict['id']] = CharacterDefinition(**item_dict)
        except (KeyError, TypeError) as e:
            raise DefinitionContentError(filepath=str(CHARACTERS_FILE), message=f"Fehler bei Charakter #{i} (ID: {item_dict.get('id')}): {e}")
    return defs
    
def load_opponent_definitions() -> Dict[str, OpponentDefinition]:
    # Implementierung bleibt gleich wie im vorherigen Schritt
    raw_data_list = _load_json_file(OPPONENTS_FILE)
    if not isinstance(raw_data_list, list):
        raise DefinitionContentError(filepath=str(OPPONENTS_FILE), message=f"Inhalt von {OPPONENTS_FILE.name} ist keine Liste.")
    defs: Dict[str, OpponentDefinition] = {}
    for i, item_dict in enumerate(raw_data_list):
        if not isinstance(item_dict, dict):
            raise DefinitionContentError(filepath=str(OPPONENTS_FILE), message=f"Eintrag #{i} ist kein Dictionary.")
        try:
            # .get für optionale Felder in JSON, die in Dataclass Defaults haben (wie 'tags')
            item_dict['description'] = item_dict.get('description', '') 
            item_dict['skills'] = item_dict.get('skills', [])
            item_dict['tags'] = item_dict.get('tags', [])
            defs[item_dict['id']] = OpponentDefinition(**item_dict)
        except (KeyError, TypeError) as e:
            raise DefinitionContentError(filepath=str(OPPONENTS_FILE), message=f"Fehler bei Gegner #{i} (ID: {item_dict.get('id')}): {e}")
    return defs

# --- Factory für Skill-Effekte ---
def _parse_skill_effect_from_dict(effect_data: Dict[str, Any]) -> BaseEffectDefinition:
    """
    Factory-Funktion: Erstellt die korrekte SkillEffectDefinition-Subklasse
    basierend auf dem 'type'-Feld in den Daten.
    """
    effect_type_str = effect_data.get("type")
    if not effect_type_str:
        raise DefinitionContentError(message="Skill-Effekt-Daten fehlt das 'type'-Feld.", filepath=str(SKILLS_FILE))

    # Allgemeine Felder, die alle Effekte haben (oder von BaseEffectDefinition geerbt)
    # Wir extrahieren die Basis-Argumente zuerst
    base_args = {
        "type": effect_type_str,
        "application_chance": float(effect_data.get("application_chance", 1.0))
    }
    
    # Entferne Basis-Argumente aus effect_data, damit wir den Rest per **kwargs übergeben können
    specific_args = {k: v for k, v in effect_data.items() if k not in base_args}

    if effect_type_str == "DAMAGE":
        bonus_vs_type_dict = specific_args.pop("bonus_vs_type", None)
        bonus_vs_type_obj = BonusVsTypeData(**bonus_vs_type_dict) if bonus_vs_type_dict else None
        return DamageEffectDefinition(**base_args, **specific_args, bonus_vs_type=bonus_vs_type_obj)
    
    elif effect_type_str == "HEAL":
        return HealEffectDefinition(**base_args, **specific_args)
        
    elif effect_type_str == "APPLY_STATUS_EFFECT":
        return ApplyStatusEffectDefinition(**base_args, **specific_args)
        
    # Hier könnten weitere elif-Blöcke für neue Effekttypen hinzukommen
    else:
        raise DefinitionContentError(
            message=f"Unbekannter Skill-Effekttyp '{effect_type_str}' in Skill-Definitionen.",
            filepath=str(SKILLS_FILE)
        )

def _parse_skill_dict_to_definition(skill_data: Dict[str, Any]) -> SkillDefinition:
    """Wandelt ein Dictionary aus der JSON-Datei in ein SkillDefinition-Objekt um."""
    try:
        cost_data = skill_data.get("cost", {})
        skill_cost_obj = SkillCost(**cost_data)

        effects_list_data = skill_data.get("effects", [])
        effects_obj_list: List[BaseEffectDefinition] = []
        for i, effect_data_dict in enumerate(effects_list_data):
            if not isinstance(effect_data_dict, dict):
                raise DefinitionContentError(message=f"Effekt #{i} für Skill '{skill_data.get('id')}' ist kein Dictionary.", filepath=str(SKILLS_FILE))
            effects_obj_list.append(_parse_skill_effect_from_dict(effect_data_dict))
        
        # Erstelle das SkillDefinition-Objekt, indem alle Felder explizit zugewiesen werden
        # oder indem **skill_data verwendet wird, nachdem 'cost' und 'effects' modifiziert wurden.
        return SkillDefinition(
            id=skill_data['id'],
            name=skill_data['name'],
            description=skill_data['description'],
            cost=skill_cost_obj,
            target_type=skill_data['target_type'],
            effects=effects_obj_list
        )
    except KeyError as e:
        raise DefinitionContentError(message=f"Fehlender Schlüssel {e} in Skill-Daten für ID '{skill_data.get('id', 'UNBEKANNT')}'.", filepath=str(SKILLS_FILE))
    except TypeError as e: # Fängt Fehler beim Entpacken von **kwargs in Dataclasses
        raise DefinitionContentError(message=f"Typfehler beim Parsen von Skill '{skill_data.get('id', 'UNBEKANNT')}': {e}", filepath=str(SKILLS_FILE))
    except DefinitionContentError: # Wenn _parse_skill_effect_from_dict einen Fehler wirft
        raise # Einfach weiterwerfen, da die Nachricht schon spezifisch ist
    except Exception as e: # Fängt andere unerwartete Fehler ab
        raise RPGBaseException(f"Unerwarteter Fehler beim Parsen von Skill '{skill_data.get('id', 'UNBEKANNT')}': {e}")


def load_skill_definitions() -> Dict[str, SkillDefinition]:
    raw_data_list = _load_json_file(SKILLS_FILE)
    if not isinstance(raw_data_list, list):
        raise DefinitionContentError(filepath=str(SKILLS_FILE),
                                     message=f"Inhalt von {SKILLS_FILE.name} ist keine Liste.")

    skill_definitions: Dict[str, SkillDefinition] = {}
    for i, skill_dict in enumerate(raw_data_list):
        if not isinstance(skill_dict, dict):
            raise DefinitionContentError(filepath=str(SKILLS_FILE),
                                         message=f"Eintrag #{i} in {SKILLS_FILE.name} ist kein Dictionary.")
        try:
            skill_def = _parse_skill_dict_to_definition(skill_dict)
            skill_definitions[skill_def.id] = skill_def
        except DefinitionContentError as e: # Fängt Fehler aus _parse_skill_dict_to_definition
            # Hier könnten wir entscheiden, ob wir den Ladevorgang abbrechen oder nur eine Warnung loggen
            # und den fehlerhaften Skill überspringen. Fürs Erste werfen wir den Fehler weiter.
            # print(f"WARNUNG: Skill-Definition fehlerhaft und übersprungen: {e}", file=sys.stderr)
            raise e 
        except RPGBaseException as e: # Fängt andere spezifische Fehler ab
             raise e
             
    return skill_definitions