# src/ai/rl_utils.py
"""
Hilfsfunktionen für RL-Trainingsläufe, z.B. Erstellung von READMEs, Pfadmanagement,
Orchestrierung von Post-Training-Aufgaben.
Kopiert jetzt das beste Modell an einen festen Ort.
"""
import os
import logging
import datetime
import json5
import sys
import shutil # NEU: Für das Kopieren von Dateien
from typing import Dict, Any, Optional, List, Callable, Type

# Benötigte Imports
if True:
    from src.config.user_config_manager import UserConfigManager
    from src.ai import rl_postprocessing_utils
    from src.utils import file_converters

logger = logging.getLogger(__name__)

_PROJECT_ROOT_RL_UTILS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def setup_experiment_paths(
    base_output_dir_config_val: Optional[str],
    project_root_path: str,
    experiment_prefix: str,
    algorithm_name: str,
    hero_id: str,
    start_timestamp: datetime.datetime
) -> Dict[str, str]:
    """
    Erstellt die Verzeichnisstruktur für einen Experimentenlauf und gibt ein Dictionary mit den Pfaden zurück.
    """
    # ... (Diese Funktion bleibt unverändert) ...
    date_str_for_path = start_timestamp.strftime("%Y-%m-%d")
    time_str_for_path = start_timestamp.strftime("%H-%M-%S")
    base_experiment_name_for_path = f"{experiment_prefix}_{algorithm_name.lower()}_{hero_id}"
    run_specific_identifier = f"{time_str_for_path}_{base_experiment_name_for_path}"

    gdrive_project_root_default = "/content/drive/MyDrive/python-rpg-projekt"
    colab_content_dir_check = "/content/drive/MyDrive"

    default_output_base_path = os.path.join(gdrive_project_root_default, "rl_runs_persistent") \
        if os.path.exists(colab_content_dir_check) else \
        os.path.join(project_root_path, "rl_outputs_local")

    final_output_base_dir_resolved = base_output_dir_config_val \
        if base_output_dir_config_val and os.path.isabs(base_output_dir_config_val) else \
        os.path.join(project_root_path, base_output_dir_config_val) \
        if base_output_dir_config_val else default_output_base_path
    
    os.makedirs(final_output_base_dir_resolved, exist_ok=True)

    current_run_dir = os.path.join(final_output_base_dir_resolved, date_str_for_path, run_specific_identifier)
    os.makedirs(current_run_dir, exist_ok=True)

    paths = {
        "current_run_dir": current_run_dir,
        "run_specific_identifier": run_specific_identifier,
        "tensorboard_log_path": os.path.join(current_run_dir, "tensorboard"),
        "monitor_log_path_base": os.path.join(current_run_dir, "monitor"),
        "checkpoint_path": os.path.join(current_run_dir, "checkpoints"),
        "final_model_dir": os.path.join(current_run_dir, "models"),
        "context_file_path": os.path.join(current_run_dir, f"context__{run_specific_identifier}.md"),
        "combat_log_filename_base": f"combat_details__{run_specific_identifier}.txt",
        "agent_action_log_filename_base": f"agent_actions__{run_specific_identifier}.txt",
        "run_summary_filename_base": f"run_summary__{run_specific_identifier}.txt",
        "readme_filename_base": "README_experiment.md",
        "tensorboard_csv_export_dir": os.path.join(current_run_dir, "tensorboard_csv_export"),
        "analysis_package_dir": os.path.join(current_run_dir, "analysis_package"),
        "eval_callback_log_dir": os.path.join(current_run_dir, "eval_callback_logs")
    }
    
    paths["combat_log_file_path"] = os.path.join(current_run_dir, paths["combat_log_filename_base"])
    paths["agent_action_log_file_path"] = os.path.join(current_run_dir, paths["agent_action_log_filename_base"])
    paths["run_summary_file_path"] = os.path.join(current_run_dir, paths["run_summary_filename_base"])
    paths["readme_file_path"] = os.path.join(current_run_dir, paths["readme_filename_base"])
    paths["evaluations_npz_path"] = os.path.join(paths["eval_callback_log_dir"], "evaluations.npz")
    paths["evaluations_summary_txt_path"] = os.path.join(paths["eval_callback_log_dir"], f"evaluations_summary__{run_specific_identifier}.txt")

    for dir_key in ["tensorboard_log_path", "monitor_log_path_base", "checkpoint_path", "final_model_dir", "tensorboard_csv_export_dir", "analysis_package_dir", "eval_callback_log_dir"]:
        os.makedirs(paths[dir_key], exist_ok=True)
        
    return paths

def initialize_run_logging_and_context(
    config_file_path_str: str,
    paths: Dict[str, str],
    logging_setup_module: Optional[Any], 
    context_extractor_fn: Optional[Callable] 
):
    # ... (Diese Funktion bleibt unverändert) ...
    if logging_setup_module:
        if hasattr(logging_setup_module, 'set_combat_log_path'):
            logging_setup_module.set_combat_log_path(paths["combat_log_file_path"])
        if hasattr(logging_setup_module, 'set_agent_action_log_path'):
            logging_setup_module.set_agent_action_log_path(paths["agent_action_log_file_path"])
    else:
        logger.warning("logging_setup_module nicht übergeben. Spezifische Logpfade nicht gesetzt.")

    if context_extractor_fn:
        logger.info("Starte Context Extractor (via rl_utils)...")
        abs_config_path_for_extractor = os.path.abspath(config_file_path_str)
        additional_files_for_ctx = [abs_config_path_for_extractor]
        try:
            extracted_path = context_extractor_fn(
                run_identifier=paths["run_specific_identifier"],
                output_filepath=paths["context_file_path"],
                additional_full_content_files=additional_files_for_ctx
            )
            if extracted_path: logger.info(f"Kontext erfolgreich nach '{extracted_path}' extrahiert.")
            else: logger.warning("Context Extractor konnte Kontext nicht erstellen.")
        except Exception as e_extract:
            logger.error(f"Fehler beim Aufrufen des Context Extractors: {e_extract}", exc_info=True)
    else:
        logger.warning("context_extractor_fn nicht übergeben. Kontext wird nicht extrahiert.")


def create_experiment_readme(
    paths: Dict[str, str],
    run_specific_identifier: str,
    description_from_config: str,
    config_path_str: str,
    hero_id: str,
    rl_algorithm_name: str,
    policy_to_use: str,
    total_timesteps: int,
    start_timestamp_obj: Any,
    end_timestamp_obj: Any,
    checkpoint_interval_sb3_model_save: int
) -> Optional[str]:
    # ... (Diese Funktion bleibt unverändert) ...
    readme_content = f"""# RL Experiment Run: {run_specific_identifier}
## 1. Übersicht
* **Beschreibung des Laufs:** {description_from_config}
* **RL-Algorithmus:** {rl_algorithm_name} ({policy_to_use})
* **Verwendete RL-Setup-Konfiguration:** `{os.path.basename(config_path_str)}`
(Details auch in `{os.path.basename(paths["context_file_path"])}`)
## 2. Wichtige Ausgabedateien
* **`{paths["readme_filename_base"]}`**: Diese Datei.
* **`{paths["run_summary_filename_base"]}`**: Zusammenfassende Metadaten (als .txt, Inhalt JSON5).
* **`{os.path.basename(paths["context_file_path"])}`**: Kontext-Extrakt.
* **`{paths["agent_action_log_filename_base"]}`**: Detailliertes Log jeder Agentenaktion.
* **`{paths["combat_log_filename_base"]}`**: Detailliertes Kampfprotokoll.
* **`tensorboard/`**: TensorBoard Event-Dateien.
* **`tensorboard_csv_export/all_scalars_combined.csv`**: Kombinierte CSV der TensorBoard Skalare.
* **`eval_callback_logs/evaluations.npz`**: Rohdaten der EvalCallback.
* **`eval_callback_logs/{os.path.basename(paths["evaluations_summary_txt_path"])}`**: Textuelle Zusammenfassung der EvalCallback-Daten.
* **`models/`**: Finale und beste Modelle dieses Laufs.
* **`checkpoints/`**: Modell-Checkpoints.
* **`analysis_package/`**: Kuratierte Auswahl wichtiger Dateien.
... (Rest des README-Inhalts) ...
"""
    readme_filepath = paths["readme_file_path"]
    try:
        with open(readme_filepath, "w", encoding="utf-8") as f_readme:
            f_readme.write(readme_content)
        logger.info(f"README_experiment.md erfolgreich in '{paths['current_run_dir']}' erstellt.")
        return readme_filepath
    except Exception as e_readme:
        logger.error(f"Fehler beim Erstellen der README_experiment.md: {e_readme}", exc_info=True)
        return None

def perform_post_training_tasks(
    rl_config_dict: Dict[str, Any],
    config_file_path_str: str,
    paths: Dict[str, str],
    start_timestamp: datetime.datetime,
    total_timesteps_trained: int,
    policy_used: str,
    hero_id_for_readme: str,
    algo_name_for_readme: str,
    chkpt_interval_for_readme: int,
    project_root_path: str,
    user_config_manager_class: Optional[Type[UserConfigManager]] = None
):
    end_timestamp_obj = datetime.datetime.now()

    # Schritte 1-7 bleiben unverändert...
    readme_filepath = create_experiment_readme(
        paths, paths["run_specific_identifier"], rl_config_dict.get("description", ""),
        config_file_path_str, hero_id_for_readme, algo_name_for_readme, policy_used,
        total_timesteps_trained, start_timestamp, end_timestamp_obj, chkpt_interval_for_readme
    )
    eval_npz_path = paths.get("evaluations_npz_path")
    eval_summary_txt_path = paths.get("evaluations_summary_txt_path")
    npz_conversion_status = "Nicht durchgeführt (NPZ-Datei nicht gefunden oder Pfad fehlt)"
    if eval_npz_path and eval_summary_txt_path and file_converters and os.path.exists(eval_npz_path):
        conversion_successful = file_converters.convert_npz_to_txt(eval_npz_path, eval_summary_txt_path)
        npz_conversion_status = "Erfolgreich" if conversion_successful else "Fehlgeschlagen"
    
    final_model_path_on_disk = os.path.join(paths["final_model_dir"], f"{paths['run_specific_identifier']}_final_{total_timesteps_trained}steps.zip")
    best_model_zip_cb_on_disk = os.path.join(paths["final_model_dir"], "best_model_via_callback", "best_model.zip")
    
    run_summary_data = {
        "experiment_name": paths["run_specific_identifier"], "description": rl_config_dict.get("description", "Keine Beschreibung"),
        "config_file_path": os.path.abspath(config_file_path_str), "hero_id": hero_id_for_readme,
        "rl_algorithm": algo_name_for_readme, "policy_used": policy_used, "total_timesteps_trained": total_timesteps_trained,
        "final_model_path": os.path.abspath(final_model_path_on_disk) if os.path.exists(final_model_path_on_disk) else None,
        "best_model_path_callback": os.path.abspath(best_model_zip_cb_on_disk) if os.path.exists(best_model_zip_cb_on_disk) else None,
        "readme_path": os.path.abspath(readme_filepath) if readme_filepath and os.path.exists(readme_filepath) else None,
        "tensorboard_log_path": os.path.abspath(paths["tensorboard_log_path"]),
        "npz_to_txt_conversion_status": npz_conversion_status,
        "training_start_time_iso": start_timestamp.isoformat(), "training_end_time_iso": end_timestamp_obj.isoformat(),
        "tensorboard_csv_export_status": "Noch nicht ausgeführt", "analysis_package_creation_status": "Noch nicht ausgeführt"
    }
    
    with open(paths["run_summary_file_path"], 'w', encoding='utf-8') as f_summary:
        json5.dump(run_summary_data, f_summary, indent=2, quote_keys=True, trailing_commas=False)

    csv_export_success = rl_postprocessing_utils.export_tensorboard_to_csv(paths["tensorboard_log_path"], paths["tensorboard_csv_export_dir"], project_root_path)
    run_summary_data["tensorboard_csv_export_status"] = "Erfolgreich" if csv_export_success else "Fehlgeschlagen"

    analysis_pkg_path = rl_postprocessing_utils.create_analysis_package(paths, run_summary_data)
    run_summary_data["analysis_package_creation_status"] = "Erfolgreich" if analysis_pkg_path else "Fehlgeschlagen"

    with open(paths["run_summary_file_path"], 'w', encoding='utf-8') as f_summary:
        json5.dump(run_summary_data, f_summary, indent=2, quote_keys=True, trailing_commas=False)

    # Schritt 8 (User Preferences) wird entfernt, da wir jetzt einen festen Pfad haben.

    # NEUER SCHRITT: Bestes Modell an einen festen Ort kopieren
    try:
        model_to_copy_src = run_summary_data.get("best_model_path_callback") or run_summary_data.get("final_model_path")
        if model_to_copy_src and os.path.exists(model_to_copy_src):
            latest_models_dir = os.path.join(project_root_path, "latest_models")
            os.makedirs(latest_models_dir, exist_ok=True)
            
            hero_id = run_summary_data.get("hero_id", "unknown_hero")
            destination_filename = f"{hero_id}_latest_model.zip"
            destination_path = os.path.join(latest_models_dir, destination_filename)
            
            shutil.copy2(model_to_copy_src, destination_path)
            logger.info(f"Bestes Modell für '{hero_id}' erfolgreich nach '{destination_path}' kopiert.")
        else:
            logger.warning("Kein gültiges Modell zum Kopieren gefunden (weder 'best_model_callback' noch 'final_model').")
    except Exception as e_copy:
        logger.error(f"Fehler beim Kopieren des besten Modells an den festen Ort: {e_copy}", exc_info=True)


if __name__ == '__main__':
    # ... (Test-Block bleibt unverändert) ...
    pass