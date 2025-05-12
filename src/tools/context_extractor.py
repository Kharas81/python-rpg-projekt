# tools/context_extractor.py
import os
import sys
import json # Für das finale Schreiben als JSON, wenn gewünscht (oder Markdown)
import json5 # Zum Laden der JSON5-Dateien
import inspect 
import datetime
import logging
import importlib # Für import_module
from typing import Dict, Optional, List, Any, Union

# --- Pfad Setup ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")

if SRC_DIR not in sys.path: sys.path.insert(0, SRC_DIR)
if PROJECT_ROOT not in sys.path: sys.path.insert(0, PROJECT_ROOT)

logger = logging.getLogger(__name__) 

# --- Konfiguration für den Extractor ---
# Pfade sind relativ zum Projekt-Root.
_JSON_FILES_TO_EXTRACT_CONFIG = [
    "src/config/settings.json5",
    "src/config/user_preferences.json5",
    "src/definitions/json_data/characters.json5",
    "src/definitions/json_data/opponents.json5",
    "src/definitions/json_data/skills.json5",
]

_CODE_SNIPPETS_TO_EXTRACT_CONFIG = {
    "src.definitions.character": ["CharacterTemplate"], 
    "src.definitions.opponent": ["OpponentTemplate"],
    "src.definitions.skill": ["SkillTemplate", "SkillEffectData", "AppliedEffectData"],
    "src.game_logic.formulas": ["calculate_damage", "calculate_hit_chance", "calculate_xp_for_next_level"],
    "src.game_logic.entities": ["CharacterInstance"], 
    "src.game_logic.effects": ["StatusEffect", "BurningEffect", "StunnedEffect", "ShieldedEffect"], 
    "src.game_logic.combat": ["CombatHandler"], 
    "src.ai.strategies.basic_melee": ["BasicMeleeStrategy"],
    "src.ai.strategies.basic_ranged": ["BasicRangedStrategy"],
    "src.ai.strategies.support_caster": ["SupportCasterStrategy"],
    "src.ai.ai_dispatcher": ["get_ai_strategy_instance"],
    "src.environment.rpg_env": ["RPGEnv"], 
    "src.environment.state_manager": ["EnvStateManager"],
    "src.environment.observation_manager": ["ObservationManager", "get_observation"],
    "src.environment.action_manager": ["ActionManager", "get_action_mask", "get_game_action"],
    "src.environment.reward_manager": ["RewardManager", "calculate_reward_for_hero_action", "get_final_episode_rewards"],
    "src.config.config": ["Config"], 
    "src.config.user_config_manager": ["UserConfigManager"],
}

_FILES_TO_INCLUDE_FULL_CONTENT_CONFIG: List[str] = [] # Standardmäßig leer

# --- Hilfsfunktionen ---
def get_source_code(module_path: str, object_name: str) -> Optional[str]:
    try:
        module = importlib.import_module(module_path)
        obj_to_inspect = None
        if hasattr(module, object_name):
            candidate = getattr(module, object_name)
            if inspect.isfunction(candidate) or inspect.isclass(candidate) or inspect.ismethod(candidate):
                obj_to_inspect = candidate
        if not obj_to_inspect:
            for _, member_class in inspect.getmembers(module, inspect.isclass):
                if member_class.__module__ == module.__name__:
                    if hasattr(member_class, object_name):
                        candidate = getattr(member_class, object_name)
                        if inspect.isfunction(candidate) or inspect.ismethod(candidate):
                            obj_to_inspect = candidate; break
        if obj_to_inspect:
            try:
                if inspect.ismethod(obj_to_inspect): obj_to_inspect = obj_to_inspect.__func__
                return inspect.getsource(obj_to_inspect)
            except (TypeError, OSError) as e:
                logger.warning(f"CE: Quellcode für {module_path}.{object_name} nicht geladen: {e}"); return f"FEHLER: Code nicht ladbar ({type(obj_to_inspect)})"
        else:
            logger.warning(f"CE: Objekt '{object_name}' nicht in '{module_path}' gefunden."); return f"FEHLER: Objekt '{object_name}' nicht gefunden."
    except ImportError: logger.error(f"CE: Modul '{module_path}' nicht importierbar."); return f"FEHLER: Modul '{module_path}' nicht importierbar."
    except Exception as e: logger.error(f"CE: Fehler Extrahieren {module_path}.{object_name}: {e}", exc_info=True); return f"FEHLER: Unerwarteter Fehler."

def format_data_for_markdown(data: Union[Dict, List], indent_level: int = 0) -> str: # Umbenannt für Klarheit
    lines = []
    indent_str = "  " * indent_level
    items_to_iterate = sorted(data.items()) if isinstance(data, dict) else enumerate(data)

    for key_or_idx, value in items_to_iterate:
        display_key = f"[{key_or_idx}]" if isinstance(data, list) else str(key_or_idx)
        
        if isinstance(value, dict):
            lines.append(f"{indent_str}* **{display_key}:**")
            lines.append(format_data_for_markdown(value, indent_level + 1))
        elif isinstance(value, list):
            lines.append(f"{indent_str}* **{display_key}:**")
            if not value or all(not isinstance(item, (dict, list)) for item in value):
                lines.append(f"{indent_str}  * `{[str(v).replace('`', '') for v in value]}`") # Backticks in Strings escapen/entfernen
            else: 
                for i, item in enumerate(value): # Verschachtelte Listen/Dicts in Listen
                    # Zeige Index für Listenelemente
                    lines.append(format_data_for_markdown({f"Item {i}": item}, indent_level + 1))
        else:
            lines.append(f"{indent_str}* **{display_key}:** `{str(value).replace('`', '')}`")
    return "\n".join(lines)

def extract_and_save_context(
    run_identifier: str, # Umbenannt von run_timestamp_or_name für Klarheit
    output_filepath: str,
    additional_full_content_files: Optional[List[str]] = None,
    json_files_to_extract_override: Optional[List[str]] = None,
    code_snippets_to_extract_override: Optional[Dict[str, List[str]]] = None
    ) -> Optional[str]:
    
    logger.info(f"ContextExtractor: Extrahiere Kontext für Lauf '{run_identifier}' nach: {output_filepath}")
    context_data: Dict[str, Any] = {"meta": {"extraction_timestamp": datetime.datetime.now().isoformat(), "run_identifier": run_identifier}}

    json_files = json_files_to_extract_override if json_files_to_extract_override is not None else _JSON_FILES_TO_EXTRACT_CONFIG
    code_snippets = code_snippets_to_extract_override if code_snippets_to_extract_override is not None else _CODE_SNIPPETS_TO_EXTRACT_CONFIG
    
    # Kombiniere Standard-Dateien für vollen Inhalt mit den zusätzlich übergebenen
    full_content_files_to_process = list(_FILES_TO_INCLUDE_FULL_CONTENT_CONFIG) # Kopie
    if additional_full_content_files:
        full_content_files_to_process.extend(additional_full_content_files)

    # 1. Lade JSON5-Dateien
    context_data["json_configurations"] = {} # Umbenannt für bessere Gruppierung
    for file_path_rel_to_project in json_files:
        abs_file_path = os.path.join(PROJECT_ROOT, file_path_rel_to_project)
        file_key = file_path_rel_to_project.replace(os.sep, "_") # Eindeutiger Schlüssel aus Pfad
        
        if os.path.exists(abs_file_path):
            try:
                with open(abs_file_path, 'r', encoding='utf-8') as f:
                    context_data["json_configurations"][file_key] = json5.load(f)
                logger.debug(f"ContextExtractor: Inhalt von '{abs_file_path}' geladen.")
            except Exception as e:
                logger.error(f"ContextExtractor: Fehler beim Laden von JSON5 '{abs_file_path}': {e}")
                context_data["json_configurations"][file_key] = f"FEHLER: Konnte Datei nicht laden - {e}"
        else:
            logger.warning(f"ContextExtractor: JSON5-Datei nicht gefunden: '{abs_file_path}'")
            context_data["json_configurations"][file_key] = "FEHLER: Datei nicht gefunden."

    # 2. Extrahiere Code-Snippets
    context_data["code_snippets"] = {}
    for module_path, object_names in code_snippets.items():
        context_data["code_snippets"][module_path] = {}
        for object_name in object_names:
            source = get_source_code(module_path, object_name)
            context_data["code_snippets"][module_path][object_name] = source if source else "FEHLER: Quelle nicht extrahierbar."

    # 3. Füge ganze Dateiinhalte hinzu
    context_data["full_file_contents"] = {}
    for file_path_rel_to_project_or_abs in full_content_files_to_process:
        abs_file_path_full = file_path_rel_to_project_or_abs
        if not os.path.isabs(file_path_rel_to_project_or_abs):
            abs_file_path_full = os.path.join(PROJECT_ROOT, file_path_rel_to_project_or_abs)
        
        file_key_full = os.path.basename(abs_file_path_full) # Nur Dateiname als Schlüssel
        # Um Duplikate zu vermeiden, wenn der gleiche Dateiname aus verschiedenen Pfaden kommt:
        # file_key_full = file_path_rel_to_project_or_abs.replace(os.sep, "_") # Ganzer relativer Pfad als Key

        if os.path.exists(abs_file_path_full):
            try:
                with open(abs_file_path_full, 'r', encoding='utf-8') as f_full:
                    context_data["full_file_contents"][file_key_full] = f_full.read()
                logger.debug(f"ContextExtractor: Vollständiger Inhalt von '{abs_file_path_full}' geladen.")
            except Exception as e:
                logger.error(f"ContextExtractor: Fehler beim Laden von '{abs_file_path_full}': {e}")
                context_data["full_file_contents"][file_key_full] = f"FEHLER: Konnte Datei nicht laden - {e}"
        else:
            logger.warning(f"ContextExtractor: Datei für vollen Inhalt nicht gefunden: '{abs_file_path_full}'")
            context_data["full_file_contents"][file_key_full] = "FEHLER: Datei nicht gefunden."

    # Schreibe die gesammelten Daten in die Markdown-Datei
    try:
        os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
        with open(output_filepath, 'w', encoding='utf-8') as outfile:
            outfile.write(f"# RPG Projekt Kontext - Lauf: {run_identifier}\n")
            outfile.write(f"Extrahiert am: {context_data['meta']['extraction_timestamp']}\n")
            outfile.write("=" * 40 + "\n\n")

            outfile.write("## 1. JSON-basierte Konfigurationen und Daten\n\n")
            if context_data["json_configurations"]:
                outfile.write(format_data_for_markdown(context_data["json_configurations"], indent_level=0))
            else:
                outfile.write("Keine JSON-Dateien extrahiert.\n")
            outfile.write("\n\n")
            
            outfile.write("## 2. Vollständige Dateiinhalte (z.B. verwendete RL-Setup-Datei)\n\n")
            if context_data["full_file_contents"]:
                for filename, content in context_data["full_file_contents"].items():
                    outfile.write(f"### Datei: `{filename}`\n\n")
                    if isinstance(content, str) and content.startswith("FEHLER:"):
                        outfile.write(f"```\n{content}\n```\n\n")
                    else:
                        lang_hint = "json5" if filename.endswith((".json5", ".json")) else \
                                    "python" if filename.endswith(".py") else \
                                    "markdown" if filename.endswith(".md") else ""
                        outfile.write(f"```{lang_hint}\n{content}\n```\n\n")
            else:
                outfile.write("Keine Dateien für vollständigen Inhalt angegeben oder gefunden.\n\n")

            outfile.write("## 3. Relevante Code Snippets\n")
            outfile.write("=" * 28 + "\n")
            for module_path, objects in context_data["code_snippets"].items():
                outfile.write(f"\n--- Modul: `{module_path}` ---\n")
                for object_name, source_code in objects.items():
                    outfile.write(f"\n### Objekt: `{module_path}.{object_name}`\n\n")
                    if source_code and source_code.startswith("FEHLER:"):
                        outfile.write(f"```\n{source_code}\n```\n\n")
                    elif source_code:
                        outfile.write(f"```python\n{source_code.strip()}\n```\n\n")
                    else:
                        outfile.write(f"*Quelle nicht verfügbar oder leer.*\n\n")
            
            outfile.write("\n" + "=" * 40 + "\nEnde des extrahierten Kontexts.\n")
        
        logger.info(f"ContextExtractor: Kontext-Extraktion nach '{output_filepath}' abgeschlossen.")
        return output_filepath
    except IOError as e:
        logger.error(f"CE: Konnte Kontext-Ausgabedatei '{output_filepath}' nicht schreiben: {e}")
    except Exception as e:
        logger.error(f"CE: Unerwarteter Fehler bei der Kontext-Extraktion: {e}", exc_info=True)
    return None

if __name__ == '__main__':
    if not logging.getLogger().hasHandlers():
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    logger.info("Starte Context Extractor Testlauf...")
    test_output_dir = os.path.join(PROJECT_ROOT, "logs", "context_extractor_tests")
    os.makedirs(test_output_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(test_output_dir, f"test_context_output_{timestamp}.md")

    dummy_rl_config_path_rel = "src/config/rl_setups/dummy_test_rl_config_for_extractor.json5"
    dummy_rl_config_path_abs = os.path.join(PROJECT_ROOT, dummy_rl_config_path_rel)
    os.makedirs(os.path.dirname(dummy_rl_config_path_abs), exist_ok=True)
    with open(dummy_rl_config_path_abs, 'w', encoding='utf-8') as f_dummy:
        json5.dump({"test_param": "extractor_test_value", "description": "Dummy RL Config für Extractor Test"}, f_dummy, indent=2)

    # Wichtig: Pfade für additional_full_content_files sollten relativ zum Projekt-Root sein,
    # da der Extractor sie so erwartet, wenn sie in _FILES_TO_INCLUDE_FULL_CONTENT_CONFIG wären.
    additional_files_for_test = [dummy_rl_config_path_rel] 

    result_path = extract_and_save_context(
        run_identifier=f"test_run_{timestamp}", 
        output_filepath=output_file,
        additional_full_content_files=additional_files_for_test
    )

    if result_path: print(f"Context Extractor Test erfolgreich. Ausgabe in: {result_path}")
    else: print("Context Extractor Test fehlgeschlagen.")

    if os.path.exists(dummy_rl_config_path_abs): os.remove(dummy_rl_config_path_abs)
