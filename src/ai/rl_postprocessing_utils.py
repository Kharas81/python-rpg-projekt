# src/ai/rl_postprocessing_utils.py
"""
Hilfsfunktionen für Aufgaben nach dem RL-Training, primär zur Erstellung
von Analyse-Artefakten wie CSV-Exporten von TensorBoard-Daten und
dem Zusammenstellen eines Analyse-Pakets.
"""
import os
import logging
import subprocess
import sys
import glob
import shutil
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

def export_tensorboard_to_csv(
    tensorboard_log_path: str,
    csv_output_dir: str,
    project_root_path: str,
    python_executable: str = sys.executable
) -> bool:
    """
    Exportiert TensorBoard Event-Dateien in CSV-Dateien.
    (Diese Funktion bleibt wie zuvor definiert)
    """
    logger.info(f"Starte Export von TensorBoard-Daten aus '{tensorboard_log_path}' nach CSV in '{csv_output_dir}'...")
    
    tb_event_files_pattern = os.path.join(tensorboard_log_path, "events.out.tfevents.*")
    tb_event_files = glob.glob(tb_event_files_pattern)

    if not tb_event_files:
        logger.warning(f"Keine TensorBoard Event-Dateien in '{tensorboard_log_path}' gefunden (Muster: {tb_event_files_pattern}). CSV-Export übersprungen.")
        return False

    os.makedirs(csv_output_dir, exist_ok=True)
    tb_to_csv_script_path = os.path.join(project_root_path, "tools", "tensorboard_to_csv.py")

    if not os.path.exists(tb_to_csv_script_path):
        logger.error(f"Skript 'tools/tensorboard_to_csv.py' nicht gefunden unter '{tb_to_csv_script_path}'. CSV-Export abgebrochen.")
        return False

    processed_at_least_one_event_file_successfully = False
    for event_file_to_process in tb_event_files:
        logger.info(f"Verarbeite TensorBoard Event-Datei: {event_file_to_process}")
        try:
            process = subprocess.run(
                [python_executable, tb_to_csv_script_path, event_file_to_process, "--output_dir", csv_output_dir],
                capture_output=True, text=True, check=False, cwd=project_root_path
            )
            if process.returncode == 0:
                logger.info(f"TensorBoard zu CSV Export für '{os.path.basename(event_file_to_process)}' erfolgreich. Ausgabe in: {csv_output_dir}")
                if process.stdout: logger.debug(f"tensorboard_to_csv.py STDOUT:\n{process.stdout}")
                processed_at_least_one_event_file_successfully = True
            else:
                logger.error(f"Fehler beim Ausführen von tensorboard_to_csv.py für '{os.path.basename(event_file_to_process)}'. RC: {process.returncode}")
                if process.stderr: logger.error(f"tensorboard_to_csv.py STDERR:\n{process.stderr}")
                if process.stdout: logger.error(f"tensorboard_to_csv.py STDOUT:\n{process.stdout}")
        except Exception as e_tb_csv:
            logger.error(f"Fehler beim Aufrufen des tensorboard_to_csv.py Skripts für '{os.path.basename(event_file_to_process)}': {e_tb_csv}", exc_info=True)
            
    if processed_at_least_one_event_file_successfully:
        logger.info(f"TensorBoard CSV-Export nach '{csv_output_dir}' abgeschlossen.")
    else:
        logger.warning(f"TensorBoard CSV-Export konnte keine Event-Dateien erfolgreich verarbeiten.")
        
    return processed_at_least_one_event_file_successfully


def create_analysis_package(
    paths: Dict[str, str],
    run_summary_data: Dict[str, Any],
    # tb_csv_output_dir wird jetzt aus paths["tensorboard_csv_export_dir"] genommen
) -> Optional[str]:
    """
    Erstellt ein Analyse-Paket mit den wichtigsten Artefakten eines Trainingslaufs.
    """
    analysis_package_dir = paths.get("analysis_package_dir")
    if not analysis_package_dir:
        logger.error("Pfad für Analyse-Paket nicht in 'paths' gefunden.")
        return None
        
    logger.info(f"Erstelle/Aktualisiere Analyse-Paket in: {analysis_package_dir}")
    os.makedirs(analysis_package_dir, exist_ok=True)

    run_id = paths.get("run_specific_identifier", "unknown_run")

    # Zu kopierende Dateien und ihre Zielnamen (falls abweichend)
    # Quelle ist entweder aus 'paths' oder 'run_summary_data'
    files_to_process = []

    # 1. combat_details__{RUN_ID}.txt
    if paths.get("combat_log_file_path") and os.path.exists(paths["combat_log_file_path"]):
        files_to_process.append({
            "source": paths["combat_log_file_path"],
            "dest_name": os.path.basename(paths["combat_log_file_path"])
        })
    else:
        logger.warning(f"Kampf-Log-Datei nicht gefunden: {paths.get('combat_log_file_path')}")

    # 2. context__{RUN_ID}.txt (Quelle .md, Ziel .txt)
    context_md_path = paths.get("context_file_path")
    if context_md_path and os.path.exists(context_md_path):
        files_to_process.append({
            "source": context_md_path,
            "dest_name": f"context__{run_id}.txt"
        })
    else:
        logger.warning(f"Kontext-MD-Datei nicht gefunden: {context_md_path}")

    # 3. agent_actions__{RUN_ID}.txt
    if paths.get("agent_action_log_file_path") and os.path.exists(paths["agent_action_log_file_path"]):
        files_to_process.append({
            "source": paths["agent_action_log_file_path"],
            "dest_name": os.path.basename(paths["agent_action_log_file_path"])
        })
    else:
        logger.warning(f"Agenten-Aktions-Log-Datei nicht gefunden: {paths.get('agent_action_log_file_path')}")

    # 4. all_scalars_combined.csv
    tb_csv_export_dir = paths.get("tensorboard_csv_export_dir")
    if tb_csv_export_dir and os.path.exists(tb_csv_export_dir):
        all_scalars_path = os.path.join(tb_csv_export_dir, "all_scalars_combined.csv")
        if os.path.exists(all_scalars_path):
            files_to_process.append({
                "source": all_scalars_path,
                "dest_name": "all_scalars_combined.csv"
            })
        else:
            logger.warning(f"Datei 'all_scalars_combined.csv' nicht in '{tb_csv_export_dir}' gefunden.")
    else:
        logger.warning(f"TensorBoard CSV Export Verzeichnis nicht gefunden oder nicht angegeben: {tb_csv_export_dir}")

    # 5. run_summary__{RUN_ID}.txt
    run_summary_txt_path = paths.get("run_summary_file_path") # Sollte jetzt auf .txt enden
    if run_summary_txt_path and os.path.exists(run_summary_txt_path):
        files_to_process.append({
            "source": run_summary_txt_path,
            "dest_name": os.path.basename(run_summary_txt_path)
        })
    else:
        logger.warning(f"Run Summary Datei nicht gefunden: {run_summary_txt_path}")
        
    # 6. Monitor Eval CB CSV
    eval_cb_log_dir = paths.get("eval_callback_log_dir")
    if eval_cb_log_dir and os.path.exists(eval_cb_log_dir):
        # Der genaue Name des Monitor-Files kann variieren, falls mehr als eine Eval-Umgebung (unwahrscheinlich)
        # oder wenn das Suffix nicht exakt passt. Wir suchen nach *monitor*{run_id}*_eval_cb.csv
        eval_monitor_pattern = os.path.join(eval_cb_log_dir, f"monitor_{run_id}_eval_cb.csv")
        eval_monitor_files = glob.glob(eval_monitor_pattern)
        if eval_monitor_files:
            files_to_process.append({
                "source": eval_monitor_files[0], # Nimm die erste gefundene Datei
                "dest_name": f"monitor_eval_cb__{run_id}.csv"
            })
        else:
            logger.warning(f"Keine Eval-Callback-Monitor-CSV-Datei gefunden (Muster: {eval_monitor_pattern}).")
            
    # 7. Monitor Train CSV(s)
    monitor_train_base_path = paths.get("monitor_log_path_base")
    if monitor_train_base_path and os.path.exists(monitor_train_base_path):
        train_monitor_files = glob.glob(os.path.join(monitor_train_base_path, "monitor_*.csv"))
        for train_monitor_file in train_monitor_files:
            # Suffix anpassen, um _main oder _train_parallel_X zu erhalten
            original_basename = os.path.basename(train_monitor_file)
            # Entferne run_id und gemeinsames Präfix, um das Suffix zu extrahieren
            suffix_part = original_basename.replace(f"monitor_{run_id}", "").replace(".csv","")
            dest_monitor_train_name = f"monitor_train{suffix_part}__{run_id}.csv"
            files_to_process.append({
                "source": train_monitor_file,
                "dest_name": dest_monitor_train_name
            })
        if not train_monitor_files:
            logger.warning(f"Keine Trainings-Monitor-Dateien in '{monitor_train_base_path}' gefunden.")


    # 8. evaluations_summary__{RUN_ID}.txt
    eval_summary_txt_path_from_data = run_summary_data.get("evaluations_summary_txt_path") # Pfad aus run_summary_data
    if eval_summary_txt_path_from_data and os.path.exists(eval_summary_txt_path_from_data):
        files_to_process.append({
            "source": eval_summary_txt_path_from_data,
            "dest_name": os.path.basename(eval_summary_txt_path_from_data)
        })
    else:
        logger.warning(f"Evaluations Summary TXT-Datei nicht gefunden: {eval_summary_txt_path_from_data}")

    # 9. RL Run Config File (als .txt)
    original_rl_config_path = run_summary_data.get("config_file_path")
    if original_rl_config_path and os.path.exists(original_rl_config_path):
        files_to_process.append({
            "source": original_rl_config_path,
            "dest_name": f"rl_config__{run_id}.txt" # Original .json5 als .txt speichern
        })
    else:
        logger.warning(f"Original RL-Konfigurationsdatei nicht gefunden: {original_rl_config_path}")

    # 10. README_experiment.md
    readme_md_path = run_summary_data.get("readme_path")
    if readme_md_path and os.path.exists(readme_md_path):
        files_to_process.append({
            "source": readme_md_path,
            "dest_name": os.path.basename(readme_md_path) # Behält .md Endung
        })
    else:
        logger.warning(f"Experiment README-Datei nicht gefunden: {readme_md_path}")

    # 11. Modell-Datei (bestes oder finales)
    model_to_copy_path = run_summary_data.get("best_model_path_callback") or run_summary_data.get("final_model_path")
    if model_to_copy_path and os.path.exists(model_to_copy_path):
        files_to_process.append({
            "source": model_to_copy_path,
            "dest_name": os.path.basename(model_to_copy_path)
        })
    else:
        logger.warning(f"Modell-Datei (bestes/finales) nicht gefunden: {model_to_copy_path}")

    # Kopiere alle gesammelten Dateien
    copied_files_count = 0
    for item in files_to_process:
        src = item["source"]
        dest = os.path.join(analysis_package_dir, item["dest_name"])
        try:
            shutil.copy2(src, dest)
            logger.debug(f"Datei '{os.path.basename(src)}' nach '{dest}' ins Analyse-Paket kopiert.")
            copied_files_count +=1
        except Exception as e:
            logger.error(f"Fehler beim Kopieren von '{src}' nach '{dest}' ins Analyse-Paket: {e}")

    if copied_files_count > 0 :
        logger.info(f"Analyse-Paket mit {copied_files_count} Datei(en) erfolgreich erstellt/aktualisiert: {analysis_package_dir}")
        return analysis_package_dir
    else:
        logger.warning(f"Keine Dateien konnten ins Analyse-Paket kopiert werden für: {analysis_package_dir}")
        return None


if __name__ == '__main__':
    # (Der Testblock bleibt im Wesentlichen gleich, müsste aber die neuen
    # Dateinamen und -pfade in den Asserts berücksichtigen)
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger.info("--- Teste rl_postprocessing_utils.py direkt (Ausschnitt) ---")
    # ... (Dummy-Pfade und Aufrufe wie zuvor, aber mit den neuen Erwartungen an die Dateiliste)
    # Es ist wichtig, dass der Test-Dummy für run_summary_data die neuen Pfade (z.B. evaluations_summary_txt_path) enthält.
    logger.info("--- Tests für rl_postprocessing_utils.py (Ausschnitt) abgeschlossen ---")