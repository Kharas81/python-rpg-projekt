# tools/context_extractor.py
import os
import sys
import json # Für das finale Schreiben als JSON, wenn gewünscht (oder Markdown)
import json5 # Zum Laden der JSON5-Dateien
import inspect 
import datetime
import logging
from typing import Dict, Optional, List, Any, Union # Union hinzugefügt

# --- Pfad Setup ---
# Annahme: Dieses Skript liegt in tools/
# Das Projekt-Root-Verzeichnis ist eine Ebene höher.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")

# Füge src zum Python-Pfad hinzu, damit src-Module importiert werden können
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)
if PROJECT_ROOT not in sys.path: # Auch Projekt-Root, falls nötig für andere Imports
    sys.path.insert(0, PROJECT_ROOT)

logger = logging.getLogger(__name__) # Logger für dieses Modul

# --- Konfiguration für den Extractor ---
# Pfade sind relativ zum Projekt-Root oder absolut, wenn nötig.
# Die json5-Dateien, deren Inhalt extrahiert werden soll.
_JSON_FILES_TO_EXTRACT_CONFIG = [
    "src/config/settings.json5",
    "src/config/user_preferences.json5", # Kann nützlich sein
    "src/definitions/json_data/characters.json5",
    "src/definitions/json_data/opponents.json5",
    "src/definitions/json_data/skills.json5",
]

# Python-Module und die daraus zu extrahierenden Objekte (Funktionen, Klassen, Methoden).
# Pfade sind Modulpfade (z.B. "src.definitions.character")
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
    # Wichtig: Die Skripte, die den Extractor aufrufen, hier nicht unbedingt einfügen,
    # da das zu Rekursion oder sehr großen Ausgaben führen kann.
    # "src.ai.rl_training": ["train_agent"], 
    # "src.ai.evaluate_agent": ["evaluate_agent_performance"],
}

# Dateien, deren ganzer Inhalt einbezogen werden soll (Pfade relativ zum Projekt-Root).
# Dies wird typischerweise dynamisch von der aufrufenden Funktion (z.B. rl_training.py)
# mit dem Pfad zur spezifischen RL-Konfigurationsdatei gefüllt.
# Hier als leere Liste als Default.
_FILES_TO_INCLUDE_FULL_CONTENT_CONFIG: List[str] = []

# --- Hilfsfunktionen ---
def get_source_code(module_path: str, object_name: str) -> Optional[str]:
    """
    Extrahiert den Quellcode eines Objekts (Funktion/Methode/Klasse) aus einem Modul.
    Sucht auch nach Methoden in Klassen des Moduls.
    """
    try:
        module = importlib.import_module(module_path)
        obj_to_inspect = None
        
        # 1. Versuche, das Objekt direkt im Modul zu finden
        if hasattr(module, object_name):
            candidate = getattr(module, object_name)
            if inspect.isfunction(candidate) or inspect.isclass(candidate) or inspect.ismethod(candidate):
                obj_to_inspect = candidate
                logger.debug(f"ContextExtractor: Objekt '{object_name}' direkt in Modul '{module_path}' gefunden.")

        # 2. Wenn nicht direkt gefunden, suche als Methode in den Klassen des Moduls
        if not obj_to_inspect:
            for _, member_class in inspect.getmembers(module, inspect.isclass):
                # Stelle sicher, dass die Klasse auch in diesem Modul definiert wurde (nicht importiert)
                if member_class.__module__ == module.__name__:
                    if hasattr(member_class, object_name):
                        candidate = getattr(member_class, object_name)
                        if inspect.isfunction(candidate) or inspect.ismethod(candidate):
                            obj_to_inspect = candidate
                            logger.debug(f"ContextExtractor: Objekt '{object_name}' als Methode in Klasse '{member_class.__name__}' von Modul '{module_path}' gefunden.")
                            break # Nimm den ersten Fund
        
        if obj_to_inspect:
            try:
                # Bei Methoden, hole die zugrundeliegende Funktion für getsource
                if inspect.ismethod(obj_to_inspect):
                    obj_to_inspect = obj_to_inspect.__func__
                return inspect.getsource(obj_to_inspect)
            except (TypeError, OSError) as e:
                logger.warning(f"ContextExtractor: Konnte Quellcode für {module_path}.{object_name} nicht laden (Typ={type(obj_to_inspect)}): {e}")
                return f"FEHLER: Quellcode konnte nicht geladen werden (Typ={type(obj_to_inspect)}, Fehler={e})"
        else:
            logger.warning(f"ContextExtractor: Objekt '{object_name}' nicht im Modul '{module_path}' oder dessen Klassen gefunden.")
            return f"FEHLER: Objekt '{object_name}' nicht im Modul '{module_path}' oder dessen Klassen gefunden."

    except ImportError:
        logger.error(f"ContextExtractor: Konnte Modul '{module_path}' nicht importieren.")
        return f"FEHLER: Modul '{module_path}' konnte nicht importiert werden."
    except Exception as e:
        logger.error(f"ContextExtractor: Unerwarteter Fehler beim Extrahieren von {module_path}.{object_name}: {e}", exc_info=True)
        return f"FEHLER: Unerwarteter Fehler beim Extrahieren von {module_path}.{object_name}."

def format_dict_for_markdown(data: Union[Dict, List], indent_level: int = 0) -> str:
    """Formatiert ein Dictionary oder eine Liste für Markdown-Ausgabe."""
    lines = []
    indent_str = "  " * indent_level
    
    if isinstance(data, dict):
        # Sortiere Schlüssel für konsistente Ausgabe, außer es ist eine Liste von Dingen ohne natürliche Ordnung
        # Hier sortieren wir immer, um Vorhersagbarkeit zu gewährleisten.
        items_to_iterate = sorted(data.items())
    elif isinstance(data, list):
        items_to_iterate = enumerate(data)
    else: # Sollte nicht passieren, wenn der Input ein Dict oder eine List ist
        return f"{indent_str}{data}"

    for key_or_idx, value in items_to_iterate:
        display_key = f"[{key_or_idx}]" if isinstance(data, list) else str(key_or_idx)
        
        if isinstance(value, dict):
            lines.append(f"{indent_str}* **{display_key}:**")
            lines.append(format_dict_for_markdown(value, indent_level + 1))
        elif isinstance(value, list):
            lines.append(f"{indent_str}* **{display_key}:**")
            # Wenn die Liste leer ist oder nur Primitive enthält, gib sie direkt aus
            if not value or all(not isinstance(item, (dict, list)) for item in value):
                lines.append(f"{indent_str}  * `{[str(v) for v in value]}`") # Kompakte Darstellung für einfache Listen
            else: # Liste enthält verschachtelte Strukturen
                for i, item in enumerate(value):
                    lines.append(format_dict_for_markdown({i: item}, indent_level + 1)) # Behandle Listenelemente wie Dict-Einträge
        else:
            lines.append(f"{indent_str}* **{display_key}:** `{value}`") # Primitive Werte in Backticks
    return "\n".join(lines)


def extract_and_save_context(
    run_timestamp_or_name: str, 
    output_filepath: str,
    additional_full_content_files: Optional[List[str]] = None, # Liste von Pfaden zu Dateien für vollen Inhalt
    json_files_to_extract_override: Optional[List[str]] = None, # Option, die Standardliste zu überschreiben
    code_snippets_to_extract_override: Optional[Dict[str, List[str]]] = None
    ) -> Optional[str]:
    """
    Extrahiert den definierten Kontext und speichert ihn in einer Markdown-Datei.
    """
    logging.info(f"ContextExtractor: Extrahiere Kontext für Lauf '{run_timestamp_or_name}' nach: {output_filepath}")
    context_data: Dict[str, Any] = {"meta": {"extraction_timestamp": datetime.datetime.now().isoformat()}}

    # Verwende Overrides oder Defaults
    json_files = json_files_to_extract_override if json_files_to_extract_override is not None else _JSON_FILES_TO_EXTRACT_CONFIG
    code_snippets = code_snippets_to_extract_override if code_snippets_to_extract_override is not None else _CODE_SNIPPETS_TO_EXTRACT_CONFIG
    full_content_files = additional_full_content_files if additional_full_content_files is not None else []
    # Füge die Standard-Dateien für vollen Inhalt hinzu, falls definiert
    full_content_files.extend(_FILES_TO_INCLUDE_FULL_CONTENT_CONFIG)


    # 1. Lade JSON5-Dateien
    context_data["json_files"] = {}
    for file_path_rel_or_abs in json_files:
        # Mache den Pfad absolut, wenn er relativ ist (relativ zum PROJECT_ROOT)
        file_path = file_path_rel_or_abs
        if not os.path.isabs(file_path_rel_or_abs):
            file_path = os.path.join(PROJECT_ROOT, file_path_rel_or_abs)
        
        file_key = os.path.basename(file_path)
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    context_data["json_files"][file_key] = json5.load(f)
                logger.debug(f"ContextExtractor: Inhalt von '{file_path}' geladen.")
            except Exception as e:
                logger.error(f"ContextExtractor: Fehler beim Laden von JSON5 '{file_path}': {e}")
                context_data["json_files"][file_key] = f"FEHLER: Konnte Datei nicht laden - {e}"
        else:
            logger.warning(f"ContextExtractor: JSON5-Datei nicht gefunden: '{file_path}'")
            context_data["json_files"][file_key] = "FEHLER: Datei nicht gefunden."

    # 2. Extrahiere Code-Snippets
    context_data["code_snippets"] = {}
    for module_path, object_names in code_snippets.items():
        context_data["code_snippets"][module_path] = {}
        for object_name in object_names:
            source = get_source_code(module_path, object_name)
            context_data["code_snippets"][module_path][object_name] = source if source else "FEHLER: Quelle nicht extrahierbar."

    # 3. Füge ganze Dateiinhalte hinzu
    context_data["full_file_contents"] = {}
    for file_path_rel_or_abs in full_content_files:
        file_path_full = file_path_rel_or_abs
        if not os.path.isabs(file_path_rel_or_abs):
            file_path_full = os.path.join(PROJECT_ROOT, file_path_rel_or_abs)
        
        file_key_full = os.path.basename(file_path_full)
        if os.path.exists(file_path_full):
            try:
                with open(file_path_full, 'r', encoding='utf-8') as f_full:
                    context_data["full_file_contents"][file_key_full] = f_full.read()
                logger.debug(f"ContextExtractor: Vollständiger Inhalt von '{file_path_full}' geladen.")
            except Exception as e:
                logger.error(f"ContextExtractor: Fehler beim Laden des vollständigen Inhalts von '{file_path_full}': {e}")
                context_data["full_file_contents"][file_key_full] = f"FEHLER: Konnte Datei nicht laden - {e}"
        else:
            logger.warning(f"ContextExtractor: Datei für vollen Inhalt nicht gefunden: '{file_path_full}'")
            context_data["full_file_contents"][file_key_full] = "FEHLER: Datei nicht gefunden."


    # Schreibe die gesammelten Daten in die Markdown-Datei
    try:
        os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
        with open(output_filepath, 'w', encoding='utf-8') as outfile:
            outfile.write(f"# RPG Projekt Kontext - Lauf: {run_timestamp_or_name}\n")
            outfile.write(f"Extrahiert am: {context_data['meta']['extraction_timestamp']}\n")
            outfile.write("=" * 40 + "\n\n")

            outfile.write("## 1. JSON5-Konfigurationsdateien\n\n")
            for filename, content in context_data["json_files"].items():
                outfile.write(f"### `{filename}`\n\n")
                if isinstance(content, str) and content.startswith("FEHLER:"):
                    outfile.write(f"```\n{content}\n```\n\n")
                else:
                    outfile.write("```json5\n")
                    # Nutze json.dumps für einheitliches und hübsches JSON-Format, auch wenn es json5 war
                    outfile.write(json.dumps(content, indent=2, ensure_ascii=False))
                    outfile.write("\n```\n\n")
            
            outfile.write("## 2. Vollständige Dateiinhalte\n\n")
            if context_data["full_file_contents"]:
                for filename, content in context_data["full_file_contents"].items():
                    outfile.write(f"### `{filename}`\n\n")
                    if isinstance(content, str) and content.startswith("FEHLER:"):
                        outfile.write(f"```\n{content}\n```\n\n")
                    else:
                        # Versuche, die Sprache für Syntaxhervorhebung zu erraten
                        lang_hint = "json5" if filename.endswith(".json5") else "python" if filename.endswith(".py") else ""
                        outfile.write(f"```{lang_hint}\n")
                        outfile.write(content)
                        outfile.write("\n```\n\n")
            else:
                outfile.write("Keine Dateien für vollständigen Inhalt angegeben oder gefunden.\n\n")


            outfile.write("\n" + "=" * 40 + "\n")
            outfile.write("## 3. Relevante Code Snippets\n")
            outfile.write("=" * 28 + "\n")
            for module_path, objects in context_data["code_snippets"].items():
                outfile.write(f"\n--- Modul: `{module_path}` ---\n")
                for object_name, source_code in objects.items():
                    outfile.write(f"\n### Objekt: `{module_path}.{object_name}`\n\n")
                    if source_code and source_code.startswith("FEHLER:"):
                        outfile.write(f"```\n{source_code}\n```\n\n")
                    elif source_code:
                        outfile.write("```python\n")
                        outfile.write(source_code.strip())
                        outfile.write("\n```\n\n")
                    else:
                        outfile.write(f"*Quelle nicht verfügbar oder leer.*\n\n")
                outfile.write("-" * 20 + "\n")
            
            outfile.write("\n" + "=" * 40 + "\n")
            outfile.write("Ende des extrahierten Kontexts.\n")
        
        logger.info(f"ContextExtractor: Kontext-Extraktion nach '{output_filepath}' abgeschlossen.")
        return output_filepath
    except IOError as e:
        logger.error(f"ContextExtractor: Konnte Kontext-Ausgabedatei '{output_filepath}' nicht schreiben: {e}")
        return None
    except Exception as e:
        logger.error(f"ContextExtractor: Unerwarteter Fehler bei der Kontext-Extraktion: {e}", exc_info=True)
        return None

if __name__ == '__main__':
    # Setup basic logging for direct script execution
    if not logging.getLogger().hasHandlers():
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    logger.info("Starte Context Extractor Testlauf...")
    
    # Erstelle ein temporäres Verzeichnis für die Ausgabe
    test_output_dir = os.path.join(PROJECT_ROOT, "logs", "context_extractor_tests")
    os.makedirs(test_output_dir, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(test_output_dir, f"test_context_output_{timestamp}.md")

    # Beispiel: Eine spezifische RL-Konfig-Datei für diesen Testlauf hinzufügen
    # Erstelle eine Dummy-RL-Konfig für den Test
    dummy_rl_config_path_rel = "src/config/rl_setups/dummy_test_rl_config.json5"
    dummy_rl_config_path_abs = os.path.join(PROJECT_ROOT, dummy_rl_config_path_rel)
    os.makedirs(os.path.dirname(dummy_rl_config_path_abs), exist_ok=True)
    with open(dummy_rl_config_path_abs, 'w', encoding='utf-8') as f_dummy:
        json5.dump({"test_param": "extractor_test_value"}, f_dummy, indent=2)

    # Die relative Pfadangabe ist wichtig, wenn man sie in der Konfig des Extractors hätte
    # oder wenn man sie relativ zum Projekt-Root speichert.
    additional_files = [dummy_rl_config_path_rel] 

    # Test mit expliziten Override-Listen (optional)
    # test_json_files = ["src/config/settings.json5"]
    # test_code_snippets = {"src.game_logic.formulas": ["calculate_damage"]}

    result_path = extract_and_save_context(
        run_timestamp_or_name=f"test_run_{timestamp}", 
        output_filepath=output_file,
        additional_full_content_files=additional_files
        # json_files_to_extract_override=test_json_files, # Beispiel für Override
        # code_snippets_to_extract_override=test_code_snippets # Beispiel für Override
    )

    if result_path:
        print(f"Context Extractor Test erfolgreich. Ausgabe in: {result_path}")
    else:
        print("Context Extractor Test fehlgeschlagen.")

    # Aufräumen der Dummy-Datei
    if os.path.exists(dummy_rl_config_path_abs):
        os.remove(dummy_rl_config_path_abs)
