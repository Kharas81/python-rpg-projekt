# -*- coding: utf-8 -*-
# Generated/Overwritten on: 2025-04-17 07:30:00 # Zeitpunkt aktualisiert
# rpg_training_utils.py
# V24: Moved N_FIGHTS_PER_OPPONENT constant definition to module level.
# V25: Korrektur für AttributeError in evaluate_agent_and_summarize
# V26: Added Output Widget support for evaluate_agent_and_summarize

import os, sys, time, datetime, math, traceback, importlib, inspect
import numpy as np
import pandas as pd
import csv
from collections import defaultdict
from typing import Optional, Dict, List, Any, Set, Tuple
import gymnasium as gym
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.monitor import Monitor
from stable_baselines3.common.results_plotter import load_results
import html

# *** Widget Import hinzugefügt ***
import ipywidgets as widgets
from IPython.display import display

# Globale Imports
try:
    from rpg_env import RPGEnv
    from rpg_game_logic import Character, Skill # Character wird für Type Hinting benötigt
    import rpg_config
    import rpg_definitions
except ImportError:
    print("FEHLER (rpg_training_utils V26): Globale Modul-Imports fehlgeschlagen! Definiere Dummies.")
    # (Fallback Dummies wie vorher)
    class RPGEnv: pass
    class Character: pass # Dummy für Type Hinting
    class Skill: pass
    class rpg_config: DEFAULT_PPO_PARAMS={'policy': "MlpPolicy", 'verbose': 0}; MAX_TURNS=100; MODEL_DIR_BASE="./models_fallback/"; SUMMARY_SAVE_DIR="./summaries_fallback/"; LOG_DIR_BASE="./logs_fallback/"
    class rpg_definitions: CHAR_PARAMS={}; ALL_SKILLS_MAP={}; PRIMARY_SKILLS={}; CLASS_MAIN_RESOURCE={}; ALL_BUFFS_DEBUFFS_NAMES=[]; MAX_BUFF_DURATION=5; MAX_STACKS=3 # Added missing definitions for eval


# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# Callback mit IPyWidgets für Fortschrittsanzeige (Unverändert)
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# (Code unverändert)
class IPyWidgetProgressCallback(BaseCallback):
    """ Custom callback for progress display using IPyWidgets. (Unchanged) """
    def __init__(self, total_timesteps: int, verbose: int = 0):
         super().__init__(verbose); self.target_total_timesteps = total_timesteps; self.progress_bar=None; self.step_label=None; self.time_label=None; self.widget_container=None; self.start_time=0; self.initial_model_num_timesteps=0; self.update_freq=max(100,total_timesteps//100)
    def _on_training_start(self) -> None:
        self.initial_model_num_timesteps=self.num_timesteps; self.start_time=time.time(); max_val=float(max(1.0,self.target_total_timesteps)); self.progress_bar=widgets.FloatProgress(value=float(self.initial_model_num_timesteps),min=0.0,max=max_val,description='Training:',bar_style='info',orientation='horizontal',layout=widgets.Layout(width='70%')); self.step_label=widgets.Label(value=f"{self.initial_model_num_timesteps}/{self.target_total_timesteps} Steps",layout=widgets.Layout(margin='0 0 0 10px')); self.time_label=widgets.Label(value="Dauer: 00:00:00 | Restzeit: ??:??:??"); progress_line=widgets.HBox([self.progress_bar,self.step_label]); self.widget_container=widgets.VBox([progress_line,self.time_label]); display(self.widget_container)
    def _on_step(self) -> bool:
        if self.n_calls%self.update_freq==0:
            if self.progress_bar and self.step_label and self.time_label:
                current_steps=self.num_timesteps; self.progress_bar.max=float(max(self.target_total_timesteps,current_steps)); self.progress_bar.value=float(current_steps); self.step_label.value=f"{current_steps}/{self.target_total_timesteps} Steps"; elapsed_time=time.time()-self.start_time; steps_done_in_run=current_steps-self.initial_model_num_timesteps; remaining_steps=max(0,self.target_total_timesteps-current_steps); estimated_remaining_time=float('inf')
                if steps_done_in_run>self.update_freq and elapsed_time>1: time_per_step=elapsed_time/steps_done_in_run; estimated_remaining_time=remaining_steps*time_per_step
                elapsed_str=time.strftime("%H:%M:%S",time.gmtime(elapsed_time)); remaining_str=time.strftime("%H:%M:%S",time.gmtime(estimated_remaining_time)) if estimated_remaining_time!=float('inf') else "??:??:??"; self.time_label.value=f"Dauer: {elapsed_str} | Restzeit: {remaining_str}"
                if self.progress_bar.bar_style=='info' and current_steps>self.initial_model_num_timesteps: self.progress_bar.bar_style='success'
        return True
    def _on_training_end(self) -> None:
         if self.progress_bar and self.step_label and self.time_label:
            final_steps=self.num_timesteps; self.progress_bar.value=float(final_steps); self.step_label.value=f"{final_steps}/{self.target_total_timesteps} Steps"; elapsed_time=time.time()-self.start_time; elapsed_str=time.strftime("%H:%M:%S",time.gmtime(elapsed_time)); self.time_label.value=f"Dauer: {elapsed_str} | Abgeschlossen."; self.progress_bar.bar_style='success' if final_steps>=self.target_total_timesteps else 'warning'

# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# Funktion zum Trainieren eines Agenten für eine Klasse (Unverändert)
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# (Code unverändert)
def train_agent_for_class(
        env_instance: RPGEnv, class_name: str, total_timesteps: int,
        log_dir_base: str, model_dir_base: str, load_existing: bool = True,
        ppo_params: Optional[dict] = None, progress_callback_cls: type = IPyWidgetProgressCallback
        ) -> Optional[PPO]:
    """ Trains a PPO agent for a specific hero class. (Unchanged) """
    print(f"\n--- Setup Training für Klasse: {class_name} ---"); os.makedirs(log_dir_base, exist_ok=True); os.makedirs(model_dir_base, exist_ok=True)
    timestamp=datetime.datetime.now().strftime("%Y%m%d_%H%M%S"); model_fname_base=f"ppo_{class_name.lower()}_agent"; latest_model_path=os.path.join(model_dir_base,f"{model_fname_base}.zip"); save_model_path_timestamp=os.path.join(model_dir_base,f"{model_fname_base}_{timestamp}.zip")
    model=None; current_steps=0
    try: env_instance.set_fixed_class(class_name); print(f"Umgebung für Klasse '{class_name}' eingestellt.")
    except Exception as e: print(f"FEHLER beim Einstellen der Klasse '{class_name}': {e}"); return None
    if load_existing and os.path.exists(latest_model_path):
        try: print(f"Lade existierendes Modell: {latest_model_path}"); model=PPO.load(latest_model_path,env=env_instance); current_steps=getattr(model,'num_timesteps',0); print(f"  Modell geladen. Bisherige Schritte: {current_steps}")
        except Exception as e: print(f"FEHLER beim Laden {latest_model_path}: {e}. Erstelle neues Modell."); model=None; current_steps=0
    if model is None:
        print("Erstelle neues PPO-Modell.")
        if 'rpg_config' not in sys.modules: import rpg_config
        params_to_use = (ppo_params or rpg_config.DEFAULT_PPO_PARAMS).copy();
        params_to_use.pop('tensorboard_log', None) # Remove tensorboard_log if present
        try:
            if 'policy' not in params_to_use: print("FEHLER: 'policy' fehlt! Verwende Fallback 'MlpPolicy'."); params_to_use['policy'] = params_to_use.get('policy', "MlpPolicy")
            model=PPO(env=env_instance,**params_to_use); current_steps=0
            print(f"  Neues Modell erstellt mit Policy: {params_to_use.get('policy', 'Unbekannt')}")
        except Exception as e: print(f"FATALER FEHLER beim Erstellen des PPO-Modells: {e}"); traceback.print_exc(); return None
    if current_steps>=total_timesteps: print(f"Ziel-Timesteps ({total_timesteps}) bereits erreicht ({current_steps}). Überspringe Training.")
    else:
        print(f"Starte Training von {current_steps} bis {total_timesteps}..."); callback_instance=None
        if progress_callback_cls:
             try: callback_instance=progress_callback_cls(total_timesteps=total_timesteps)
             except Exception as e: print(f"WARNUNG: Konnte Progress Callback nicht erstellen: {e}")
        remaining_timesteps=total_timesteps-current_steps
        try:
            # Ensure tensorboard_log is NOT passed if it was in the original params
            learn_params = {'total_timesteps': remaining_timesteps, 'reset_num_timesteps': False, 'log_interval': 10, 'callback': callback_instance, 'progress_bar': False}
            # Check if the model instance itself expects tensorboard_log (some SB3 versions might)
            # However, usually it's passed during PPO initialization if needed.
            # It's safer to assume it's not needed in learn() if not explicitly documented for the method.
            model.learn(**learn_params);
            print("\nTraining abgeschlossen.")
        except Exception as e: print(f"\nFEHLER während des Trainings für Klasse {class_name}: {e}"); traceback.print_exc()
        finally:
             latest_path = latest_model_path
             try: print(f"Speichere Modell mit Zeitstempel: {save_model_path_timestamp}"); model.save(save_model_path_timestamp); print("  Timestamp-Modell gespeichert.")
             except Exception as e: print(f"\nFEHLER beim Speichern (Timestamp) für {class_name}: {e}")
             try: print(f"Speichere/Überschreibe neuestes Modell: {latest_path}"); model.save(latest_path); print("  Neuestes Modell gespeichert.")
             except Exception as e: print(f"\nFEHLER beim Speichern (Latest) für {class_name}: {e}")
    print(f"--- Training für Klasse: {class_name} beendet ---"); return model


# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# Funktion zum Generieren des verständlichen Trainingsberichts (Unverändert)
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
def generate_layperson_log(
    log_dir: str, output_filepath: str, class_name: str, total_timesteps: int,
    config_params: dict = None, intervals: list = None, window_size: int = 100
    ):
    """
    Generiert einen leicht verständlichen Textbericht über den Trainingsfortschritt
    basierend auf den Daten einer monitor.csv-Datei. (Unchanged)
    """
    # (Code der Funktion wie in V23/V25, unverändert)
    print(f"Versuche, verständlichen Trainingsbericht für '{class_name}' zu erstellen...")
    print(f"Lese Monitor-Daten aus: {log_dir}")
    print(f"Speichere Bericht nach: {output_filepath}")
    monitor_file_path = os.path.join(log_dir, "monitor.csv")
    if not os.path.exists(monitor_file_path): #... (Restlicher Code der Funktion) ...
        print(f"FEHLER: Monitor-Datei nicht gefunden: {monitor_file_path}")
        # ... (Fehlerbehandlung) ...
        report_lines = [f"# FEHLER Trainingsbericht: {class_name}-Agent", f"Monitor-Datei nicht gefunden: {monitor_file_path}"]
        try:
            os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
            with open(output_filepath, "w", encoding="utf-8") as f: f.write("\n".join(report_lines))
        except Exception as e_save: print(f"FEHLER beim Speichern der Fehlermeldung: {e_save}")
        return
    try:
        data = pd.read_csv(monitor_file_path, skiprows=1)
        if data.empty: # ... (Warnungsbehandlung) ...
            print(f"WARNUNG: Monitor-Datei {monitor_file_path} ist leer.")
            report_lines = [f"# WARNUNG Trainingsbericht: {class_name}-Agent", f"Monitor-Datei ist leer: {monitor_file_path}"]
            try:
                os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
                with open(output_filepath, "w", encoding="utf-8") as f: f.write("\n".join(report_lines))
            except Exception as e_save: print(f"FEHLER beim Speichern der Warnung: {e_save}")
            return

        data.columns = [col.strip('# ').strip() for col in data.columns] # Added strip() for safety
        report_lines = []; now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        report_lines.append(f"# Trainingsbericht: {class_name}-Agent"); report_lines.append("") # ... (Header Aufbau) ...
        report_lines.append(f"**Ziel:** Ein KI-{class_name} soll lernen, Kämpfe möglichst gut zu bestehen.")
        report_lines.append(f"**Trainingsdauer:** {total_timesteps} Lernschritte (Ziel)")
        report_lines.append(f"**Bericht vom:** {now}")
        if config_params: report_lines.append("**Trainings-Parameter (Auszug):**"); lr = config_params.get('learning_rate', 'N/A'); bs = config_params.get('batch_size', 'N/A'); gamma = config_params.get('gamma', 'N/A'); report_lines.append(f"  - Lernrate: {lr}"); report_lines.append(f"  - Batch Größe: {bs}"); report_lines.append(f"  - Gamma (Discount): {gamma}")
        report_lines.append("---"); report_lines.append("**Wie liest man das?**"); report_lines.append(f"* **Avg Belohnung (Trend):** Zeigt, wie gut der Agent *im Durchschnitt* pro Kampf abschneidet (höher ist besser). Trend über letzte ~{window_size} Kämpfe."); report_lines.append(f"* **Gewinnrate (%):** Prozent gewonnener Kämpfe (letzte ~{window_size}). Benötigt 'is_success'."); report_lines.append(f"* **Kampfdauer (Trend):** Durchschnittliche Rundenzahl pro Kampf (letzte ~{window_size})."); report_lines.append(f"* **Strategie:** Qualitative Einschätzung."); report_lines.append("---"); report_lines.append("**Beobachtungen während des Trainings:**"); report_lines.append("")

        if intervals is None: intervals = [int(p * total_timesteps) for p in [0.1, 0.25, 0.5, 0.75, 1.0]]; intervals = sorted([i for i in intervals if i > 0]);
        if total_timesteps not in intervals: intervals.append(total_timesteps); intervals = sorted(list(set(i for i in intervals if i <= total_timesteps)))

        # Check required columns
        required_cols = ['r', 'l', 't']
        missing_cols = [col for col in required_cols if col not in data.columns]
        if missing_cols:
            raise KeyError(f"Fehlende Spalten in monitor.csv: {', '.join(missing_cols)}")

        # Ensure numeric types, handle potential errors
        try:
            data['r'] = pd.to_numeric(data['r'], errors='coerce')
            data['l'] = pd.to_numeric(data['l'], errors='coerce')
            data['t'] = pd.to_numeric(data['t'], errors='coerce') # Assuming 't' is cumulative time
            # Drop rows where essential numeric conversion failed
            data.dropna(subset=['r', 'l', 't'], inplace=True)
            if data.empty:
                 print("WARNUNG: Keine gültigen numerischen Daten in monitor.csv nach Bereinigung.")
                 report_lines.append("WARNUNG: Keine gültigen Datenpunkte in der Monitor-Datei gefunden.")
                 # Save the partial report and return
                 final_report = "\n".join(report_lines); os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
                 with open(output_filepath, "w", encoding="utf-8") as f: f.write(final_report);
                 return
            cumulative_timesteps = data['t'] # Use 't' directly if it's cumulative seconds/steps
            # OR if 't' is time per episode and 'l' is steps per episode:
            # cumulative_timesteps = data['l'].cumsum() # Choose the correct column for cumulative steps
        except Exception as e:
            print(f"FEHLER bei Konvertierung/Berechnung kumulativer Timesteps: {e}")
            raise e

        last_avg_reward = -float('inf'); reported_intervals = 0
        for step_threshold in intervals:
            # Find the index corresponding to the step_threshold
            # This assumes cumulative_timesteps is monotonically increasing
            relevant_indices = cumulative_timesteps[cumulative_timesteps <= step_threshold].index
            if relevant_indices.empty: continue
            last_relevant_index = relevant_indices[-1]

            # Define the window for calculating stats, ensuring it doesn't go out of bounds
            window_start_index = max(0, last_relevant_index - window_size + 1)
            window_data = data.iloc[window_start_index : last_relevant_index + 1]

            if window_data.empty: continue

            try:
                avg_reward = window_data['r'].mean()
                avg_length = window_data['l'].mean()
            except Exception as e:
                print(f"FEHLER bei Statistikberechnung für Intervall {step_threshold}: {e}")
                continue # Skip this interval if basic stats fail

            win_rate = np.nan
            has_success_col = 'is_success' in window_data.columns
            win_rate_desc = "(Nicht verfügbar)" # Default description

            if has_success_col:
                 try:
                     # Attempt conversion, coercing errors to NaN, then fill NaN with 0
                     success_numeric = pd.to_numeric(window_data['is_success'], errors='coerce').fillna(0)
                     # Ensure boolean interpretation (1.0 -> True, 0.0 -> False)
                     success_bool = success_numeric.astype(bool)
                     win_rate = success_bool.mean() * 100
                     if not np.isnan(win_rate):
                         if win_rate > 75: win_rate_desc = "Sehr Hoch"
                         elif win_rate > 50: win_rate_desc = "Hoch"
                         elif win_rate > 25: win_rate_desc = "Mittel"
                         else: win_rate_desc = "Niedrig"
                         win_rate_desc += f" ({win_rate:.0f}%)"
                     else:
                         win_rate_desc = "(Berechnung fehlgeschlagen)"
                 except Exception as e:
                     print(f"WARNUNG: Konnte 'is_success' nicht zuverlässig interpretieren bei Schritt {step_threshold}: {e}")
                     has_success_col = False # Treat as unavailable if conversion fails
                     win_rate_desc = "(Fehler bei Interpretation)"

            report_lines.append(f"* **Nach ca. {step_threshold} Schritten:**")
            reward_desc = "Eher schlecht"
            if not np.isnan(avg_reward):
                if avg_reward > 10: reward_desc = "Sehr gut"
                elif avg_reward > 5: reward_desc = "Gut"
                elif avg_reward > 0: reward_desc = "Okay / Verbessert"
                reward_desc += f" (Avg. Belohnung: {avg_reward:.2f})"
            else:
                reward_desc = "(Berechnung fehlgeschlagen)"

            report_lines.append(f"  * **Ergebnis:** {reward_desc}")
            report_lines.append(f"  * **Gewinnrate:** {win_rate_desc}")

            length_desc = "Eher lang"
            if not np.isnan(avg_length):
                # Ensure rpg_config is available or use a default
                max_turns_ref = 100 # Default if not available
                if 'rpg_config' in sys.modules and hasattr(rpg_config, 'MAX_TURNS'):
                    max_turns_ref = rpg_config.MAX_TURNS

                if avg_length < max_turns_ref * 0.3: length_desc = "Sehr kurz"
                elif avg_length < max_turns_ref * 0.6: length_desc = "Kurz"
                elif avg_length < max_turns_ref * 0.9: length_desc = "Mittel"
                length_desc += f" (ca. {avg_length:.0f} Runden)"
            else:
                 length_desc = "(Berechnung fehlgeschlagen)"

            report_lines.append(f"  * **Kampfdauer:** {length_desc}")

            # Simplified strategy description based on reward trend
            strategy_desc = "Noch unklar."
            if not np.isnan(avg_reward) and not np.isinf(last_avg_reward):
                 if avg_reward > last_avg_reward + 1.0: strategy_desc = "Verbessert sich deutlich."
                 elif avg_reward > last_avg_reward: strategy_desc = "Verbessert sich leicht."
                 elif avg_reward < last_avg_reward - 1.0: strategy_desc = "Verschlechtert sich."
                 else: strategy_desc = "Stagniert / Stabil."

            report_lines.append(f"  * **Strategie:** {strategy_desc} *(Hinweis: Genaue Aktionsanalyse erfordert separate Daten)*"); report_lines.append("")
            last_avg_reward = avg_reward if not np.isnan(avg_reward) else last_avg_reward
            reported_intervals += 1

        if reported_intervals == 0:
            print("WARNUNG: Keine Berichtsintervalle erstellt.")
            report_lines.append("FEHLER: Keine Datenpunkte für Berichtsintervalle gefunden.")

        report_lines.append("---"); report_lines.append("**Fazit (vereinfacht):**"); # ... (Fazit logic) ...

        # Calculate final stats using the last window_size episodes/rows
        final_window_data = data.iloc[-window_size:]
        final_avg_reward = np.nan
        final_win_rate = np.nan
        if not final_window_data.empty:
            final_avg_reward = final_window_data['r'].mean()
            if 'is_success' in final_window_data.columns:
                try:
                    final_success_numeric = pd.to_numeric(final_window_data['is_success'], errors='coerce').fillna(0)
                    final_success_bool = final_success_numeric.astype(bool)
                    final_win_rate = final_success_bool.mean() * 100
                except Exception as e:
                     print(f"WARNUNG: Konnte 'is_success' für Fazit nicht interpretieren: {e}")

        # --- HIER IST DIE KORRIGIERTE EINRÜCKUNG ---
        if not np.isnan(final_avg_reward) and final_avg_reward > 10 and (np.isnan(final_win_rate) or final_win_rate > 75):
            # KORREKTUR: Eingerückt für bessere Lesbarkeit und gemäß der ursprünglichen Fehlermeldung.
            report_lines.append(f"Der {class_name}-Agent hat erfolgreich gelernt und die Kriterien erfüllt (Avg Reward > 10, Win Rate > 75% oder NaN).") # Original comment: # ... (Rest Fazit) ...
        elif not np.isnan(final_avg_reward) and final_avg_reward > 5:
             report_lines.append(f"Der {class_name}-Agent zeigt gute Fortschritte (Avg Reward > 5), hat aber die Top-Kriterien noch nicht ganz erreicht.")
        elif reported_intervals > 0:
             report_lines.append(f"Der {class_name}-Agent hat das Training durchlaufen, aber die Leistung stagniert oder ist noch nicht optimal (Avg Reward: {final_avg_reward:.2f}).")
        else:
             report_lines.append(f"Der {class_name}-Agent hat das Training abgeschlossen, aber es konnten keine aussagekräftigen Daten für ein Fazit gewonnen werden.")

        report_lines.append("---"); final_report = "\n".join(report_lines); os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
        with open(output_filepath, "w", encoding="utf-8") as f: f.write(final_report); print(f"Verständlicher Bericht erfolgreich gespeichert: {output_filepath}")

    except pd.errors.EmptyDataError: print(f"FEHLER: Monitor-Datei {monitor_file_path} enthält keine Daten nach Header.")
    except FileNotFoundError: print(f"FEHLER: Monitor-Datei nicht gefunden: {monitor_file_path}") # Should be caught earlier, but good practice
    except KeyError as e: print(f"FEHLER: Erwartete Spalte '{e}' nicht in {monitor_file_path} gefunden oder Datenproblem.")
    except Exception as e: print(f"FEHLER beim Generieren des Berichts: {e}"); traceback.print_exc()


# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# Funktion zur detaillierten Evaluierung (V26 - Mit Widget-Unterstützung)
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

# Konstante auf Modulebene definieren
N_FIGHTS_PER_OPPONENT = 50

# Hilfsfunktion zum sicheren Abrufen von Modul-Infos (unverändert)
def get_module_info(module_name: str) -> str:
    # (Code unverändert)
    try:
        module = sys.modules.get(module_name)
        if not module: return "Nicht geladen"
        version = getattr(module, '__version__', None)
        timestamp_str = "N/A"; filepath = getattr(module, '__file__', None)
        if filepath and os.path.exists(filepath):
            timestamp = os.path.getmtime(filepath); mod_time = datetime.datetime.fromtimestamp(timestamp); timestamp_str = mod_time.strftime('%Y-%m-%d %H:%M:%S')
        version_comment = "N/A"
        if filepath and os.path.exists(filepath):
             try:
                 with open(filepath, 'r', encoding='utf-8') as f:
                     first_line = f.readline()
                     if '#' in first_line and 'V' in first_line.split('#')[-1]:
                          potential_version = first_line.split('#')[-1].strip()
                          if potential_version.startswith('V') and len(potential_version) > 1 and potential_version[1].isdigit(): version_comment = potential_version
             except Exception: pass # Ignore file reading errors
        info_parts = []
        if version_comment != "N/A": info_parts.append(f"{version_comment}")
        elif version: info_parts.append(f"v{version}")
        if timestamp_str != "N/A": info_parts.append(f"({timestamp_str})")
        return " ".join(info_parts) if info_parts else "Info nicht verfügbar"
    except Exception as e: return f"Fehler beim Abrufen ({e})"


# *** HIER DIE ÄNDERUNG: Neue Parameter für Widgets ***
def evaluate_agent_and_summarize(
        class_name: str,
        model_dir_base: str,
        summary_dir: str,
        deterministic: bool = True,
        max_turns_per_episode: int = 100,
        training_params: Optional[dict] = None,
        output_format: str = 'txt_single',
        combat_log_widget: Optional[widgets.Output] = None, # NEU
        info_output_widget: Optional[widgets.Output] = None    # NEU
        ) -> None:
    """
    Evaluates a trained agent, generates summary statistics, saves detailed
    step logs and summary reports into daily subfolders within summary_dir.
    Redirects combat log and info messages to optional Output widgets.
    V26: Added Output Widget support.
    """
    # Helper function to print to console OR widget
    def print_info(msg):
        if info_output_widget:
            with info_output_widget:
                print(msg)
        else:
            print(msg)

    print_info(f"\n--- Starte Evaluierung für Klasse: {class_name} (Format: {output_format}) ---")
    aktionswahl_str = 'Festgelegt' if deterministic else 'Zufällig (mit Erkundung)'
    print_info(f"  Kämpfe pro Gegner: {N_FIGHTS_PER_OPPONENT}, Aktionswahl: {aktionswahl_str}, Max Züge: {max_turns_per_episode}")

    # Täglichen Unterordner erstellen
    today_str = datetime.date.today().strftime('%Y-%m-%d')
    daily_summary_dir = os.path.join(summary_dir, today_str)
    os.makedirs(daily_summary_dir, exist_ok=True)
    print_info(f"  Tagesordner für Berichte: {daily_summary_dir}")

    # --- 1. Modell laden & Eigene Eval-Env erstellen ---
    model_fname_base = f"ppo_{class_name.lower()}_agent"; model_path = os.path.join(model_dir_base, f"{model_fname_base}.zip")
    if not os.path.exists(model_path): print_info(f"FEHLER: Modell '{model_path}' nicht gefunden."); return

    eval_env = None # Initialize eval_env to None
    model = None # Initialize model to None
    try:
        # Lokale Imports (wie in V15) - ensure they are accessible
        try:
            import rpg_env
            import rpg_definitions
            import rpg_config
            import rpg_game_logic
        except ImportError as import_err:
            print_info(f"FEHLER: Kritische Module für Evaluierung nicht gefunden: {import_err}")
            return # Cannot proceed without env and definitions

        eval_env = rpg_env.RPGEnv(
             char_param_definitions=rpg_definitions.CHAR_PARAMS,
             all_buffs_debuffs_names=rpg_definitions.ALL_BUFFS_DEBUFFS_NAMES,
             max_buff_duration=rpg_definitions.MAX_BUFF_DURATION,
             max_stacks=rpg_definitions.MAX_STACKS)
        # Set max_episode_steps if the env supports it (Gymnasium style)
        if hasattr(eval_env, 'spec') and eval_env.spec is not None:
             eval_env.spec.max_episode_steps = max_turns_per_episode
        elif hasattr(eval_env, '_max_episode_steps'): # Older gym style
             eval_env._max_episode_steps = max_turns_per_episode

        model = PPO.load(model_path, env=eval_env);
        print_info(f"Modell geladen: {model_fname_base}.zip")
    except Exception as e:
        print_info(f"FEHLER beim Laden/Erstellen der Umgebung/Modell: {e}");
        if info_output_widget: # Log traceback to widget if available
             with info_output_widget: traceback.print_exc()
        else: traceback.print_exc();
        if eval_env: eval_env.close(); # Close env if it was created before error
        return # Stop execution if loading failed

    # --- 2. Gegnerliste definieren ---
    hero_classes = ["Krieger", "Magier", "Schurke", "Kleriker"]
    if not hasattr(rpg_definitions, 'CHAR_PARAMS') or not rpg_definitions.CHAR_PARAMS:
        print_info("FEHLER: rpg_definitions.CHAR_PARAMS ist nicht verfügbar oder leer.")
        if eval_env: eval_env.close()
        return
    ENEMY_TYPES_TO_TEST = list(set(k for k in rpg_definitions.CHAR_PARAMS if k not in hero_classes))
    if not ENEMY_TYPES_TO_TEST: print_info("FEHLER: Keine Gegner zum Testen gefunden."); eval_env.close(); return
    opponent_types_to_test = sorted(ENEMY_TYPES_TO_TEST)
    total_episodes_planned = len(opponent_types_to_test) * N_FIGHTS_PER_OPPONENT
    print_info(f"  Gegner: {opponent_types_to_test} ({len(opponent_types_to_test)} Typen)")
    print_info(f"  Geplante Gesamtepisoden: {total_episodes_planned}")

    # --- 3. Ergebnis-Speicher initialisieren ---
    # (Unverändert)
    total_reward_list: List[float] = []; total_turns_list: List[int] = []
    skill_usage_count: Dict[str, int] = defaultdict(int); skill_type_usage_count: Dict[str, int] = defaultdict(int)
    total_reward_components: Dict[str, float] = defaultdict(float)
    win_hero_hp_ratio_list: List[float] = []; win_hero_mana_ratio_list: List[float] = []
    loss_hero_mana_ratio_list: List[float] = []
    loss_hero_hp_ratio_list: List[float] = []
    total_damage_dealt_list: List[int] = []; total_damage_taken_list: List[int] = []
    total_healing_done_list: List[int] = []
    results_by_opponent: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
        'wins': 0, 'losses': 0, 'timeouts': 0, 'total_episodes': 0,
        'win_turns': [], 'loss_turns': [], 'timeout_turns': [],
        'win_hp_ratios': [], 'loss_hp_ratios': [],
        'win_mana_ratios': [], 'loss_mana_ratios': [],
        'damage_dealt': [], 'damage_taken': [], 'healing_done': [],
        'hero_skill_usage': defaultdict(int)
    })
    enemy_actions_per_opponent: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    pass_count_total = 0; pass_count_skill_usable = 0; pass_resource_levels: List[float] = []
    ba_count_total = 0; ba_count_skill_usable = 0; ba_resource_levels: List[float] = []

    # --- 4. Infos aus der Umgebung holen ---
    action_map = getattr(eval_env, 'action_to_name_map', {})
    pass_idx = getattr(eval_env, '_pass_action_idx', -1)
    basic_attack_idx = getattr(eval_env, '_basic_attack_idx', -1)
    all_skills_in_env = getattr(eval_env, 'all_skill_objects_list', [])
    initialized_skills_dict = getattr(eval_env, 'initialized_skills', {})
    primary_skill_name = rpg_definitions.PRIMARY_SKILLS.get(class_name) if hasattr(rpg_definitions, 'PRIMARY_SKILLS') else None
    primary_skill_obj: Optional[Skill] = initialized_skills_dict.get(primary_skill_name) if primary_skill_name and initialized_skills_dict else None
    main_resource_name = rpg_definitions.CLASS_MAIN_RESOURCE.get(class_name) if hasattr(rpg_definitions, 'CLASS_MAIN_RESOURCE') else None
    class_skill_names = rpg_definitions.ALL_SKILLS_MAP.get(class_name, []) if hasattr(rpg_definitions, 'ALL_SKILLS_MAP') else []
    # (Warnings for missing info are omitted here for brevity, but could be added back using print_info)

    # --- Schritt-Log Datei vorbereiten ---
    step_log_filename = f"evaluation_steps_{class_name.lower()}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    step_log_filepath = os.path.join(daily_summary_dir, step_log_filename)
    step_log_file = None; csv_writer = None
    step_log_header = [
        "EpisodeID", "OpponentType", "Turn",
        "HeroHP", "HeroMaxHP", "HeroMana", "HeroMaxMana", "HeroStamina", "HeroMaxStamina", "HeroEnergy", "HeroMaxEnergy",
        "HeroBuffs", "HeroDebuffs",
        "EnemyHP", "EnemyMaxHP", "EnemyMana", "EnemyMaxMana",
        "EnemyBuffs", "EnemyDebuffs",
        "HeroActionName", "HeroActionIndex", "EnemyActionName",
        "StepReward", "RewardComponents"
    ]
    try:
        step_log_file = open(step_log_filepath, 'w', newline='', encoding='utf-8')
        csv_writer = csv.writer(step_log_file)
        csv_writer.writerow(step_log_header)
        print_info(f"  Detailliertes Schritt-Log wird geschrieben nach: {step_log_filepath}")
    except Exception as e: print_info(f"FEHLER beim Öffnen/Schreiben des Schritt-Log Headers: {e}"); step_log_file = None; csv_writer = None

    # --- 5. Evaluierungs-Schleifen ---
    start_time = time.time(); print_info(f"  Starte Evaluierungs-Schleifen...")
    episodes_run = 0; current_episode_global = 0
    try:
        for opponent_type in opponent_types_to_test:
            opponent_results = results_by_opponent[opponent_type]
            print_info(f"    Starte Kämpfe gegen: {opponent_type}")
            for ep_vs_opp in range(N_FIGHTS_PER_OPPONENT):
                current_episode_global += 1; episode_id = f"{class_name}_vs_{opponent_type}_{ep_vs_opp+1}"

                # *** HIER DIE ÄNDERUNG: Kampf-Log Widget leeren ***
                if combat_log_widget:
                    combat_log_widget.clear_output(wait=True)
                # **************************************************

                try:
                     eval_env.set_fixed_class(class_name)
                     eval_env.set_fixed_opponent(opponent_type)
                     obs, info = eval_env.reset()
                     if not hasattr(eval_env, 'hero') or not eval_env.hero or not hasattr(eval_env, 'enemy') or not eval_env.enemy:
                         raise RuntimeError("Held und/oder Gegner nicht korrekt nach reset initialisiert.")
                     episodes_run += 1
                except Exception as e:
                    print_info(f"FEHLER beim env.reset() für Ep {current_episode_global} ({episode_id}): {e}");
                    if info_output_widget: # Log traceback to info widget
                         with info_output_widget: traceback.print_exc()
                    continue # Skip episode

                terminated, truncated = False, False; episode_reward, episode_turns = 0.0, 0;
                episode_reward_components = defaultdict(float); ep_damage_dealt = 0; ep_damage_taken = 0; ep_healing_done = 0

                # --- Episoden-Schleife (Turns) ---
                # *** HIER DIE ÄNDERUNG: Kampf-Log im Widget-Kontext ausführen ***
                with combat_log_widget if combat_log_widget else contextlib.nullcontext():
                    if combat_log_widget: # Print header inside the widget
                        print(f"--- Kampf-Log: {episode_id} ---")

                    while not terminated and not truncated:
                        hero = eval_env.hero; enemy = eval_env.enemy
                        if not hero or not enemy:
                            print(f"FEHLER: Held oder Gegner verschwunden in Ep {episode_id}, Turn {episode_turns+1}");
                            break

                        hp_before_step = hero.current_hp; enemy_hp_before_step = enemy.current_hp

                        try:
                            action_array, _ = model.predict(obs, deterministic=deterministic);
                            action = int(action_array.item());
                            action_name = action_map.get(action, f"Unbekannt({action})")

                            # Track Action Usage (bleibt gleich)
                            skill_usage_count[action_name] += 1;
                            opponent_results['hero_skill_usage'][action_name] += 1

                            # Track Pass/BA Details (mit V25 Korrektur)
                            is_primary_skill_usable = False
                            current_resource_percentage = -1.0
                            if primary_skill_obj and main_resource_name and hero:
                                try:
                                    is_primary_skill_usable = hero.can_use_skill(primary_skill_obj)
                                    resource_attr = f"current_{main_resource_name.lower()}"
                                    max_resource_attr = f"max_{main_resource_name.lower()}"
                                    if hasattr(hero, resource_attr) and hasattr(hero, max_resource_attr) and getattr(hero, max_resource_attr) > 0:
                                        current_resource_percentage = (getattr(hero, resource_attr) / getattr(hero, max_resource_attr)) * 100
                                except Exception as e_can_use_skill:
                                    print(f"FEHLER (can_use_skill): {e_can_use_skill}") # Fehler wird jetzt im Widget angezeigt
                                    is_primary_skill_usable = False

                            if action == pass_idx:
                                pass_count_total += 1;
                                if is_primary_skill_usable: pass_count_skill_usable += 1
                                if current_resource_percentage >= 0: pass_resource_levels.append(current_resource_percentage)
                            elif action == basic_attack_idx:
                                ba_count_total += 1;
                                if is_primary_skill_usable: ba_count_skill_usable += 1
                                if current_resource_percentage >= 0: ba_resource_levels.append(current_resource_percentage)

                            # Environment Step (Ausgaben hieraus landen im Widget)
                            obs, reward, terminated, truncated, info = eval_env.step(action)

                            # Get Info from Step
                            enemy_action = info.get('enemy_action_name', 'Unbekannt');
                            enemy_actions_per_opponent[opponent_type][enemy_action] += 1

                            # Determine skill type
                            skill_type = "Unbekannt";
                            if action == pass_idx: skill_type = "Passen"
                            elif action == basic_attack_idx: skill_type = "Basis-Angriff"
                            elif 0 <= action < len(all_skills_in_env):
                                skill_obj = all_skills_in_env[action];
                                if isinstance(skill_obj, Skill) and hasattr(skill_obj, 'effect_type'):
                                    skill_type = skill_obj.effect_type
                            skill_type_usage_count[skill_type] += 1

                            # Accumulate Episode Stats
                            episode_reward += reward; episode_turns += 1
                            step_reward_components = info.get('reward_components', {});
                            if isinstance(step_reward_components, dict):
                                for key, value in step_reward_components.items():
                                    episode_reward_components[key] += value
                            if hero and enemy:
                                ep_damage_dealt += max(0, enemy_hp_before_step - enemy.current_hp);
                                step_damage_taken = max(0, hp_before_step - hero.current_hp);
                                ep_damage_taken += step_damage_taken
                                if step_damage_taken == 0 and hero.current_hp > hp_before_step:
                                    ep_healing_done += (hero.current_hp - hp_before_step)

                            # Log Step Details (CSV)
                            if csv_writer and hero and enemy:
                                try:
                                    def get_effects_str(char_obj, type='buff'):
                                        effects_dict = getattr(char_obj, 'active_effects', {})
                                        filtered_effects = {}
                                        if type == 'buff':
                                            filtered_effects = {k: v for k, v in effects_dict.items() if any(m.startswith('mod_') and mv > 0 for m, mv in v.get('modifiers', {}).items()) or v.get('modifiers', {}).get('dot_heal', 0) > 0}
                                        elif type == 'debuff':
                                            filtered_effects = {k: v for k, v in effects_dict.items() if any(m.startswith('mod_') and mv < 0 for m, mv in v.get('modifiers', {}).items()) or v.get('modifiers', {}).get('dot_damage', 0) > 0}
                                        return "; ".join([f"{name}({eff.get('duration', '?')}/{eff.get('stacks', '?')})" for name, eff in filtered_effects.items()])

                                    log_row = [
                                        episode_id, opponent_type, episode_turns,
                                        int(hero.current_hp), int(hero.max_hp), int(hero.current_mana), int(hero.max_mana),
                                        int(getattr(hero, 'current_stamina', 0)), int(getattr(hero, 'max_stamina', 0)),
                                        int(getattr(hero, 'current_energy', 0)), int(getattr(hero, 'max_energy', 0)),
                                        get_effects_str(hero, 'buff'), get_effects_str(hero, 'debuff'),
                                        int(enemy.current_hp), int(enemy.max_hp),
                                        int(getattr(enemy, 'current_mana', 0)), int(getattr(enemy, 'max_mana', 0)),
                                        get_effects_str(enemy, 'buff'), get_effects_str(enemy, 'debuff'),
                                        action_name, action, enemy_action,
                                        f"{reward:.4f}", str(step_reward_components)
                                    ]
                                    csv_writer.writerow(log_row)
                                except Exception as log_e:
                                    print(f"FEHLER (CSV Log): {log_e}") # Fehler im Widget

                        except Exception as e:
                            print(f"FEHLER in predict/step loop (Ep {episode_id}, T {episode_turns}): {e}");
                            traceback.print_exc(); # Traceback im Widget
                            terminated = True;
                            continue
                # *************************************************************

                # --- Nachbearbeitung der Episode ---
                total_reward_list.append(episode_reward); total_turns_list.append(episode_turns);
                for key, value in episode_reward_components.items(): total_reward_components[key] += value
                total_damage_dealt_list.append(ep_damage_dealt); total_damage_taken_list.append(ep_damage_taken); total_healing_done_list.append(ep_healing_done)

                opponent_results['total_episodes'] += 1;
                opponent_results['damage_dealt'].append(ep_damage_dealt);
                opponent_results['damage_taken'].append(ep_damage_taken);
                opponent_results['healing_done'].append(ep_healing_done);

                hero = eval_env.hero
                hero_won = info.get('is_success', False) if isinstance(info, dict) else False
                hero_mana_ratio = 0.0; hero_hp_ratio = 0.0
                if hero:
                    if hasattr(hero, 'max_mana') and hero.max_mana > 0: hero_mana_ratio = getattr(hero, 'current_mana', 0) / hero.max_mana
                    if hasattr(hero, 'max_hp') and hero.max_hp > 0: hero_hp_ratio = getattr(hero, 'current_hp', 0) / hero.max_hp

                if hero_won:
                    opponent_results['wins'] += 1; opponent_results['win_turns'].append(episode_turns);
                    win_hero_hp_ratio_list.append(hero_hp_ratio); win_hero_mana_ratio_list.append(hero_mana_ratio);
                    opponent_results['win_hp_ratios'].append(hero_hp_ratio); opponent_results['win_mana_ratios'].append(hero_mana_ratio);
                elif truncated and not terminated:
                    opponent_results['timeouts'] += 1; opponent_results['timeout_turns'].append(episode_turns);
                    loss_hero_hp_ratio_list.append(hero_hp_ratio); loss_hero_mana_ratio_list.append(hero_mana_ratio);
                    opponent_results['loss_hp_ratios'].append(hero_hp_ratio); opponent_results['loss_mana_ratios'].append(hero_mana_ratio);
                elif terminated:
                    opponent_results['losses'] += 1; opponent_results['loss_turns'].append(episode_turns);
                    loss_hero_hp_ratio_list.append(hero_hp_ratio); loss_hero_mana_ratio_list.append(hero_mana_ratio);
                    opponent_results['loss_hp_ratios'].append(hero_hp_ratio); opponent_results['loss_mana_ratios'].append(hero_mana_ratio);
                # (Else case omitted)

            # --- Ende Opponent Fight Loop ---
            print_info(f"    Kämpfe gegen {opponent_type} abgeschlossen.")
        # --- Ende Opponent Type Loop ---
    except Exception as loop_err:
        print_info(f"\n!!! FATALER FEHLER in Evaluierungs-Schleifen: {loop_err} !!!");
        if info_output_widget: # Log traceback to info widget
             with info_output_widget: traceback.print_exc()
        else: traceback.print_exc()
    finally:
        if step_log_file:
            try: step_log_file.close(); print_info(f"  Schritt-Log Datei geschlossen: {step_log_filepath}")
            except Exception as e: print_info(f"FEHLER beim Schließen der Schritt-Log Datei: {e}")
        if eval_env:
            try: eval_env.close(); print_info("  Evaluierungsumgebung geschlossen.")
            except Exception as e: print_info(f"FEHLER beim Schließen der Evaluierungsumgebung: {e}")

    eval_duration = time.time() - start_time
    print_info(f"  Evaluierung für {class_name} abgeschlossen (oder abgebrochen). Dauer: {eval_duration:.2f} Sek.")
    if episodes_run == 0: print_info("WARNUNG: Keine Evaluierungs-Episoden erfolgreich abgeschlossen."); return

    # --- 6. Statistiken berechnen ---
    # *** HIER DIE ÄNDERUNG: print-Ausgaben in Widget umleiten ***
    with info_output_widget if info_output_widget else contextlib.nullcontext():
        print("Berechne Statistiken...")
        report_data = None
        try:
            # (Statistikberechnungen bleiben gleich wie in V25)
            total_wins = sum(d['wins'] for d in results_by_opponent.values()); total_losses = sum(d['losses'] for d in results_by_opponent.values()); total_timeouts = sum(d['timeouts'] for d in results_by_opponent.values());
            valid_episodes_run = max(1, episodes_run);
            win_rate = (total_wins / valid_episodes_run) * 100; loss_rate = (total_losses / valid_episodes_run) * 100; timeout_rate = (total_timeouts / valid_episodes_run) * 100;
            avg_reward = np.mean(total_reward_list) if total_reward_list else 0; std_reward = np.std(total_reward_list) if total_reward_list else 0; avg_turns = np.mean(total_turns_list) if total_turns_list else 0;
            avg_win_hp_perc = np.mean(win_hero_hp_ratio_list) * 100 if win_hero_hp_ratio_list else 0;
            avg_win_mana_perc = np.mean(win_hero_mana_ratio_list) * 100 if win_hero_mana_ratio_list else 0;
            avg_loss_hp_perc = np.mean(loss_hero_hp_ratio_list) * 100 if loss_hero_hp_ratio_list else -1;
            avg_loss_mana_perc = np.mean(loss_hero_mana_ratio_list) * 100 if loss_hero_mana_ratio_list else -1;
            avg_dmg_dealt = np.mean(total_damage_dealt_list) if total_damage_dealt_list else 0;
            avg_dmg_taken = np.mean(total_damage_taken_list) if total_damage_taken_list else 0;
            avg_healing_done = np.mean(total_healing_done_list) if total_healing_done_list else 0;
            avg_reward_components = {k: v / valid_episodes_run for k, v in total_reward_components.items()};
            total_actions = sum(skill_usage_count.values()); action_percentages = {k: (v / total_actions) * 100 for k, v in skill_usage_count.items()} if total_actions > 0 else {};
            total_types = sum(skill_type_usage_count.values()); type_percentages = {k: (v / total_types) * 100 for k, v in skill_type_usage_count.items()} if total_types > 0 else {};
            opponent_summary_stats = {}
            for opp_class, data_opp in results_by_opponent.items(): # Renamed 'data' variable
                opp_total = data_opp['total_episodes'];
                if opp_total > 0:
                    all_turns_vs = data_opp['win_turns'] + data_opp['loss_turns'] + data_opp['timeout_turns'];
                    total_hero_actions_vs = sum(data_opp['hero_skill_usage'].values())
                    opponent_summary_stats[opp_class] = {
                        'total_episodes': opp_total, 'win_rate': (data_opp['wins']/opp_total)*100, 'loss_rate': (data_opp['losses']/opp_total)*100, 'timeout_rate': (data_opp['timeouts']/opp_total)*100,
                        'avg_win_turns': np.mean(data_opp['win_turns']) if data_opp['win_turns'] else 0, 'avg_loss_turns': np.mean(data_opp['loss_turns']) if data_opp['loss_turns'] else 0, 'avg_timeout_turns': np.mean(data_opp['timeout_turns']) if data_opp['timeout_turns'] else 0,
                        'avg_overall_turns': np.mean(all_turns_vs) if all_turns_vs else 0, 'avg_win_hp_perc': np.mean(data_opp['win_hp_ratios'])*100 if data_opp['win_hp_ratios'] else 0, 'avg_loss_hp_perc': np.mean(data_opp['loss_hp_ratios'])*100 if data_opp['loss_hp_ratios'] else -1,
                        'avg_win_mana_perc': np.mean(data_opp['win_mana_ratios'])*100 if data_opp['win_mana_ratios'] else 0, 'avg_loss_mana_perc': np.mean(data_opp['loss_mana_ratios'])*100 if data_opp['loss_mana_ratios'] else -1,
                        'avg_dmg_dealt': np.mean(data_opp['damage_dealt']) if data_opp['damage_dealt'] else 0, 'avg_dmg_taken': np.mean(data_opp['damage_taken']) if data_opp['damage_taken'] else 0, 'avg_healing_done': np.mean(data_opp['healing_done']) if data_opp['healing_done'] else 0,
                        'hero_skill_usage': {k: (v / total_hero_actions_vs * 100) if total_hero_actions_vs > 0 else 0 for k,v in data_opp['hero_skill_usage'].items()}
                     }
            perc_pass_total = action_percentages.get('Passen', 0)
            perc_ba_total = action_percentages.get('Basis-Angriff', 0)
            perc_pass_skill_usable = (pass_count_skill_usable / pass_count_total * 100) if pass_count_total > 0 else 0;
            avg_pass_resource = np.mean(pass_resource_levels) if pass_resource_levels else -1;
            perc_ba_skill_usable = (ba_count_skill_usable / ba_count_total * 100) if ba_count_total > 0 else 0;
            avg_ba_resource = np.mean(ba_resource_levels) if ba_resource_levels else -1

            print("Statistiken berechnet.")
            print("Generiere Berichtsdaten...")
            report_data = { # Structure remains the same
                "class_name": class_name, "model_path": model_path, "eval_timestamp": datetime.datetime.now(),
                "code_versions": { name: get_module_info(name) for name in ['rpg_definitions', 'rpg_env', 'rpg_game_logic', 'rpg_training_utils', 'rpg_config']},
                "training_params": training_params or {}, "eval_params": {"fights_per_opponent": N_FIGHTS_PER_OPPONENT, "deterministic": deterministic, "max_turns": max_turns_per_episode, "opponents": opponent_types_to_test},
                "overall_stats": {"episodes_run": episodes_run, "win_rate": win_rate, "loss_rate": loss_rate, "timeout_rate": timeout_rate, "avg_reward": avg_reward, "std_reward": std_reward, "avg_turns": avg_turns, "avg_win_hp_perc": avg_win_hp_perc, "avg_loss_hp_perc": avg_loss_hp_perc, "avg_win_mana_perc": avg_win_mana_perc, "avg_loss_mana_perc": avg_loss_mana_perc, "avg_dmg_dealt": avg_dmg_dealt, "avg_dmg_taken": avg_dmg_taken, "avg_healing_done": avg_healing_done},
                "avg_reward_components": avg_reward_components, "action_percentages": action_percentages, "type_percentages": type_percentages,
                "pass_ba_details": {"pass_perc": perc_pass_total, "pass_count": pass_count_total, "pass_skill_usable_perc": perc_pass_skill_usable, "pass_skill_usable_count": pass_count_skill_usable, "pass_avg_res_perc": avg_pass_resource, "ba_perc": perc_ba_total, "ba_count": ba_count_total, "ba_skill_usable_perc": perc_ba_skill_usable, "ba_skill_usable_count": ba_count_skill_usable, "ba_avg_res_perc": avg_ba_resource, "primary_skill": primary_skill_name, "main_resource": main_resource_name},
                "opponent_stats": opponent_summary_stats, "enemy_actions": enemy_actions_per_opponent, "class_skill_names": class_skill_names, "step_log_path": step_log_filepath
            }
            print("Berichtsdaten generiert.")
        except Exception as stats_err:
            print(f"FEHLER bei Statistikberechnung/Berichtsdatenerstellung: {stats_err}"); traceback.print_exc();
            report_data = None # Ensure no report is saved on error
    # ******************************************************************

    # --- Speicherlogik basierend auf output_format ---
    # *** HIER DIE ÄNDERUNG: print-Ausgaben in Widget umleiten ***
    with info_output_widget if info_output_widget else contextlib.nullcontext():
        if report_data:
            print(f"Versuche Bericht im Format '{output_format}' zu speichern...")
            try:
                # Choose saving function based on format
                if output_format == 'txt_single' or output_format == 'txt_append':
                    _save_report_txt(report_data, daily_summary_dir, append=(output_format == 'txt_append'))
                elif output_format == 'csv':
                    _save_report_csv(report_data, summary_dir) # CSV goes to base summary dir
                elif output_format == 'html':
                    _save_report_html(report_data, daily_summary_dir)
                else:
                    print(f"WARNUNG: Unbekanntes Ausgabeformat '{output_format}'. Speichere als 'txt_single'.")
                    _save_report_txt(report_data, daily_summary_dir, append=False)
                print("Bericht speichern abgeschlossen.")
            except Exception as save_e:
                print(f"FEHLER beim Aufruf der Speicherfunktion '{output_format}': {save_e}"); traceback.print_exc()
        else:
            print("WARNUNG: Keine Berichtsdaten zum Speichern vorhanden aufgrund vorheriger Fehler.")
    # ******************************************************************

    print_info(f"--- Evaluierung für Klasse: {class_name} Ende ---")


# --- Hilfsfunktionen zum Speichern der Berichte ---
# (Code für _save_report_txt, _save_report_csv, _save_report_html unverändert)
# ... (Code für _save_report_txt) ...
# ... (Code für _save_report_csv) ...
# ... (Code für _save_report_html) ...
def _save_report_txt(data: dict, target_dir: str, append: bool):
    """ Speichert den detaillierten Bericht als formatierte TXT-Datei. """
    class_name = data['class_name']; now_str = data['eval_timestamp'].strftime("%Y%m%d_%H%M%S"); date_str = data['eval_timestamp'].strftime("%Y-%m-%d");
    base_filename = f"evaluation_summary_{class_name.lower()}";
    filename = f"{base_filename}_{now_str}.txt" if not append else f"{base_filename}_daily_{date_str}.txt";
    filepath = os.path.join(target_dir, filename)
    summary_lines = []; title_sep = "#"*75; section_sep = "="*60; sub_sep = "-"*50;
    # --- Header ---
    summary_lines.extend([title_sep, f" Agenten-Evaluierungsbericht: {class_name} ".center(75), title_sep]);
    summary_lines.append(f"Bericht generiert am: {data['eval_timestamp'].strftime('%Y-%m-%d %H:%M:%S')}\n")
    summary_lines.append("**1. Kopfzeilen / Metadaten**");
    summary_lines.append(f"   - Heldenklasse:         {class_name}");
    summary_lines.append(f"   - Getestetes Modell:    {data['model_path']}");
    summary_lines.append("   - Code-Versionen:");
    [summary_lines.append(f"     - {name}.py: {info}") for name, info in data['code_versions'].items()]
    if data['training_params']:
        summary_lines.append("   - Trainingsparameter (Auszug):");
        summary_lines.append(f"     - Learning Rate:      {data['training_params'].get('learning_rate', 'N/A')}");
        summary_lines.append(f"     - Batch Size:         {data['training_params'].get('batch_size', 'N/A')}");
        summary_lines.append(f"     - Gamma:              {data['training_params'].get('gamma', 'N/A')}")
    summary_lines.append("   - Evaluierungsparameter:");
    summary_lines.append(f"     - Kämpfe pro Gegner:  {data['eval_params']['fights_per_opponent']}");
    summary_lines.append(f"     - Aktionswahl:        {'Festgelegt' if data['eval_params']['deterministic'] else 'Zufällig (mit Erkundung)'}");
    summary_lines.append(f"     - Max. Runden:        {data['eval_params']['max_turns']}");
    summary_lines.append(f"     - Getestete Gegner:   {', '.join(data['eval_params']['opponents'])}"); # Join list
    summary_lines.append("\n")
    # --- Fazit ---
    summary_lines.extend([section_sep, " 2. Fazit / Executive Summary ".center(60), section_sep]);
    stats = data['overall_stats']; ap = data['action_percentages']; rc = data['avg_reward_components']; os_stats = data['opponent_stats']; pb = data['pass_ba_details']
    fazit_lines = [];
    fazit_lines.append(f"* Leistung: {stats['win_rate']:.1f}% Siege über {stats['episodes_run']} Kämpfe.")
    problem_flags = []; pass_perc = pb.get('pass_perc', 0); ba_perc = pb.get('ba_perc', 0)
    if pass_perc > 15: problem_flags.append(f"hohe Passen-Rate ({pass_perc:.1f}%)")
    if ba_perc > 30: problem_flags.append(f"hohe Basis-Angriff-Rate ({ba_perc:.1f}%)")
    # Check mana on loss (ensure key exists and value is valid)
    avg_loss_mana = stats.get('avg_loss_mana_perc', -1)
    if avg_loss_mana >= 0 and avg_loss_mana < 10: problem_flags.append("oft Mana-leer bei Niederlagen")
    fehler_reward = rc.get('Skill Nutzung (Fehler)', 0) # Check if key exists
    if fehler_reward < -0.5: problem_flags.append(f"deutliche Skill-Fehler (Reward {fehler_reward:.2f})")
    if problem_flags: fazit_lines.append(f"* Hauptproblem(e): {', '.join(problem_flags)}.")
    else: fazit_lines.append("* Strategie wirkt aktuell relativ ausbalanciert (basierend auf einfachen Metriken).")
    # Find major weakness
    major_weakness = None; min_win_rate = 101
    for opp, opp_data in os_stats.items():
        # Check if enough episodes were run against this opponent
        if opp_data.get('total_episodes', 0) >= data['eval_params']['fights_per_opponent'] // 2 :
            if opp_data.get('win_rate', 100) < min_win_rate:
                 min_win_rate = opp_data['win_rate']; major_weakness = opp
    if major_weakness and min_win_rate < 40: fazit_lines.append(f"* Größte Schwäche: Sehr anfällig gegen {major_weakness} ({min_win_rate:.0f}% Sieg).")
    summary_lines.extend(fazit_lines); summary_lines.append("\n")
    # --- Gesamtleistung ---
    summary_lines.extend([section_sep, " 3. Gesamtleistung des Helden ".center(60), section_sep]);
    summary_lines.append(f"- Erfolgsquote: {stats['win_rate']:.1f}% Siege / {stats['loss_rate']:.1f}% Niederl. / {stats['timeout_rate']:.1f}% Timeout ({stats['episodes_run']} Episoden)");
    summary_lines.append(f"- Ø Gesamtbelohnung pro Kampf: {stats['avg_reward']:.2f} (StdAbw: {stats['std_reward']:.2f})")
    # Calculate avg win/loss turns safely
    win_t = []; loss_t = []; timeout_t = []
    [ (win_t.extend(opp_d.get('win_turns',[])), loss_t.extend(opp_d.get('loss_turns',[])), timeout_t.extend(opp_d.get('timeout_turns',[]))) for opp_d in data['opponent_stats'].values() ]
    summary_lines.append(f"- Ø Kampfdauer: {stats['avg_turns']:.1f} Runden (Sieg: {np.mean(win_t) if win_t else 0:.1f}, Niederl.: {np.mean(loss_t) if loss_t else 0:.1f}, Timeout: {np.mean(timeout_t) if timeout_t else 0:.1f})");
    summary_lines.append(f"- Ø Rest-HP bei Siegen: {stats['avg_win_hp_perc']:.1f}%");
    summary_lines.append(f"- Ø Rest-HP bei Niederl./Timeout: {stats['avg_loss_hp_perc']:.1f}%"); # Added loss HP
    summary_lines.append(f"- Ø Rest-Mana bei Siegen: {stats['avg_win_mana_perc']:.1f}%");
    summary_lines.append(f"- Ø Rest-Mana bei Niederl./Timeout: {stats['avg_loss_mana_perc']:.1f}%");
    summary_lines.append(f"- Ø Verursachter Schaden pro Kampf: {stats['avg_dmg_dealt']:.1f}");
    summary_lines.append(f"- Ø Erlittener Schaden pro Kampf: {stats['avg_dmg_taken']:.1f}");
    summary_lines.append(f"- Ø Gewirkte Heilung pro Kampf: {stats['avg_healing_done']:.1f}");
    summary_lines.append("\n")
    # --- Belohnungsanalyse ---
    summary_lines.extend([section_sep, " 4. Belohnungsanalyse (Gesamt, Ø pro Kampf) ".center(60), section_sep]);
    reward_name_map = {'Sieg': 'Für Siege', 'Niederlage': 'Für Niederlagen','Schaden verursacht Bonus': 'Für verursachten Schaden', 'Level Up Bonus': 'Für Level Ups','Zeit Malus': 'Für lange Kämpfe (Zeit)', 'Rest-HP Bonus (Sieg)': 'Für Rest-HP bei Sieg','Skill Nutzung (Erfolg)': 'Für erfolgreiche Skill-Nutzung', 'Timeout Malus': 'Für Timeouts','Basis-Angriff Nutzung': 'Für Nutzung Basis-Angriff', 'Skill Nutzung (Fehler)': 'Für Fehlversuche (Skill)','Passen': 'Für Passen', 'Ungültige Aktion': 'Für ungültige Aktionen', 'Aktiver Buff Bonus': 'Bonus für aktive Buffs', 'Debuff Angewendet Bonus': 'Bonus für Debuff-Anwendung', 'Basis-Angriff Malus': 'Malus für Basis-Angriff'} # Example map
    sorted_rewards = sorted(rc.items(), key=lambda item: abs(item[1]), reverse=True)
    if not sorted_rewards: summary_lines.append("  (Keine Reward-Daten)")
    else:
        summary_lines.append("* Top Positive Komponenten:"); count_pos = 0;
        for key, value in sorted_rewards:
            if value > 0.01 and count_pos < 5:
                 summary_lines.append(f"    - {reward_name_map.get(key, key)}: {value:+.2f}"); count_pos += 1
        if count_pos == 0: summary_lines.append("    (Keine nennenswert positiven)")
        summary_lines.append("* Top Negative Komponenten:"); count_neg = 0;
        for key, value in sorted(sorted_rewards, key=lambda item: item[1]): # Sort ascending for negative
            if value < -0.01 and count_neg < 5:
                 summary_lines.append(f"    - {reward_name_map.get(key, key)}: {value:+.2f}"); count_neg += 1
        if count_neg == 0: summary_lines.append("    (Keine nennenswert negativen)")
    summary_lines.append("\n")
    # --- Strategie-Analyse ---
    summary_lines.extend([section_sep, " 5. Strategie-Analyse des Helden (Gesamt) ".center(60), section_sep]);
    summary_lines.append("* Aktionstypen-Verteilung:"); tp = data['type_percentages']
    if tp: sorted_types = sorted(tp.items(), key=lambda item: item[1], reverse=True); [summary_lines.append(f"    - {type_name.replace('_', ' ').capitalize()}: {perc:.1f}%") for type_name, perc in sorted_types if perc > 0.1]
    else: summary_lines.append("    (Keine Daten zu Aktionstypen)")
    summary_lines.append("\n* Spezifische Aktions-Verteilung (Alle Klassenskills + Andere):"); ap = data['action_percentages']; csn = data['class_skill_names'] # Class skill names from data
    if ap:
        # Separate class skills from others based on csn list
        class_skills_used = {k:v for k,v in ap.items() if k in csn}
        other_actions_used = {k:v for k,v in ap.items() if k not in csn}
        sorted_class_skills = sorted(class_skills_used.items(), key=lambda item: item[1], reverse=True)
        sorted_other_actions = sorted(other_actions_used.items(), key=lambda item: item[1], reverse=True)

        if sorted_class_skills: summary_lines.append("  **Klassenskills:**"); [summary_lines.append(f"    - {skill_name}: {perc:.1f}%") for skill_name, perc in sorted_class_skills if perc > 0.01]
        else: summary_lines.append("  (Keine definierten Klassenskills genutzt?)")
        if sorted_other_actions: summary_lines.append("  **Andere Aktionen:**"); [summary_lines.append(f"    - {action_name}: {perc:.1f}%") for action_name, perc in sorted_other_actions if perc > 0.01]
        else: summary_lines.append("  (Keine anderen Aktionen genutzt)")
    else: summary_lines.append("    (Keine Daten zu Aktionen)")
    summary_lines.append("\n");
    # --- Pass/BA Detail ---
    summary_lines.extend([sub_sep, " Detail: Passen / Basis-Angriff (Held) ".center(50), sub_sep]); pb = data['pass_ba_details']
    primary_skill_name = pb.get('primary_skill', 'N/A'); main_res_name = pb.get('main_resource', 'Ressource')
    if pb.get('pass_count', 0) > 0:
        summary_lines.append(f"* Passen genutzt ({pb['pass_perc']:.1f}% / {pb['pass_count']} mal):");
        summary_lines.append(f"    - Hauptskill ('{primary_skill_name}') verfügbar in: {pb['pass_skill_usable_perc']:.1f}% d. Fälle ({pb['pass_skill_usable_count']} mal).");
        avg_res = pb.get('pass_avg_res_perc', -1)
        if avg_res >= 0: summary_lines.append(f"    - Ø {main_res_name.capitalize()} dabei: {avg_res:.1f}%")
    else: summary_lines.append("* Passen: Wurde nicht genutzt.")
    if pb.get('ba_count', 0) > 0:
        summary_lines.append(f"\n* Basis-Angriff genutzt ({pb['ba_perc']:.1f}% / {pb['ba_count']} mal):");
        summary_lines.append(f"    - Hauptskill ('{primary_skill_name}') verfügbar in: {pb['ba_skill_usable_perc']:.1f}% d. Fälle ({pb['ba_skill_usable_count']} mal).");
        avg_res = pb.get('ba_avg_res_perc', -1)
        if avg_res >= 0: summary_lines.append(f"    - Ø {main_res_name.capitalize()} dabei: {avg_res:.1f}%")
    else: summary_lines.append("\n* Basis-Angriff: Wurde nicht genutzt.")
    summary_lines.append("\n")
    # --- Leistung gegen Gegner ---
    summary_lines.extend([section_sep, f" 6. Leistung des Helden gegen einzelne Gegner ".center(60), section_sep]); os_stats = data['opponent_stats']
    if os_stats:
        for opp_class, stats_opp in sorted(os_stats.items()):
            if stats_opp.get('total_episodes', 0) > 0:
                summary_lines.append(f"\n* Gegen {opp_class} (Gespielt: {stats_opp['total_episodes']}):");
                summary_lines.append(f"    - Ergebnis: {stats_opp['win_rate']:.1f}% Sieg / {stats_opp['loss_rate']:.1f}% Niederl. / {stats_opp['timeout_rate']:.1f}% Timeout");
                summary_lines.append(f"    - Ø Dauer: {stats_opp['avg_overall_turns']:.1f} Züge (Sieg: {stats_opp['avg_win_turns']:.1f}, Niederl.: {stats_opp['avg_loss_turns']:.1f})");
                summary_lines.append(f"    - Ø Rest-HP (Held): Sieg {stats_opp['avg_win_hp_perc']:.1f}% / Niederl. {stats_opp['avg_loss_hp_perc']:.1f}%"); # Added loss HP
                summary_lines.append(f"    - Ø Rest-Mana (Held): Sieg {stats_opp['avg_win_mana_perc']:.1f}% / Niederl. {stats_opp['avg_loss_mana_perc']:.1f}%");
                summary_lines.append(f"    - Ø Schaden (Verurs./Erlitt.): {stats_opp['avg_dmg_dealt']:.1f} / {stats_opp['avg_dmg_taken']:.1f}");
                summary_lines.append(f"    - Ø Heilung (Held): {stats_opp['avg_healing_done']:.1f}");
                summary_lines.append(f"    - Helden-Strategie vs {opp_class}:")
                opp_skill_usage = stats_opp.get('hero_skill_usage', {});
                # Show top 3-4 skills used against this opponent
                top_skills = sorted(opp_skill_usage.items(), key=lambda item: item[1], reverse=True)[:4];
                usage_str = ", ".join([f"{name} ({perc:.0f}%)" for name, perc in top_skills if perc > 1]);
                summary_lines.append(f"      -> Top Aktionen: {usage_str if usage_str else 'N/A'}")
    else: summary_lines.append("  (Keine Daten pro Gegner verfügbar)")
    summary_lines.append("\n")
    # --- Gegnerverhalten ---
    summary_lines.extend([section_sep, f" 7. Verhalten der Gegner gegen {class_name} ".center(60), section_sep]); ea = data['enemy_actions']
    if ea:
        for opp_type, action_counts in sorted(ea.items()):
            summary_lines.append(f"\n* Aktionen von {opp_type}:"); total_opp_actions = sum(action_counts.values())
            if total_opp_actions > 0:
                sorted_opp_actions = sorted(action_counts.items(), key=lambda item: item[1], reverse=True);
                # Show top 3-4 actions of the opponent
                action_str = ", ".join([f"{name} ({((count/total_opp_actions)*100):.0f}%)" for name, count in sorted_opp_actions[:4] if count > 0]);
                summary_lines.append(f"    -> Hauptaktionen: {action_str if action_str else 'N/A'}")
            else: summary_lines.append("    (Keine Aktionen aufgezeichnet)")
    else: summary_lines.append("  (Keine Daten zum Gegnerverhalten verfügbar)")
    summary_lines.append("\n")
    # --- Anhänge ---
    summary_lines.extend([section_sep, " 8. Anhänge / Rohdaten-Verweise ".center(60), section_sep])
    # Try to get monitor log path dynamically if possible, otherwise use config
    monitor_log_path = "Nicht ermittelbar"
    if 'rpg_config' in sys.modules and hasattr(rpg_config, 'LOG_DIR_BASE'):
        monitor_dir = os.path.join(rpg_config.LOG_DIR_BASE, f"{class_name.lower()}_monitor_logs"); # Assuming this structure
        monitor_file = os.path.join(monitor_dir, "monitor.csv")
        monitor_log_path = monitor_file # Show path even if not found
    summary_lines.append(f"- Monitor-Log (Training): {monitor_log_path}");
    summary_lines.append(f"- Detailliertes Schritt-Log (Evaluierung): {data['step_log_path']}"); # Use path from data
    summary_lines.append("\n")
    summary_lines.append(f"{title_sep}")

    # --- File Writing ---
    file_mode = "a" if append else "w"
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, file_mode, encoding="utf-8") as f:
            # Add separator if appending to existing file
            if append and os.path.exists(filepath) and os.path.getsize(filepath) > 0:
                 f.write("\n\n" + "="*80 + f"\n=== Neuer Bericht angehängt am: {data['eval_timestamp'].strftime('%Y-%m-%d %H:%M:%S')} ===\n" + "="*80 + "\n\n")
            f.write("\n".join(summary_lines))
        print(f"  TXT Zusammenfassung {'angehängt an' if append else 'gespeichert in'}: {filepath}")
    except Exception as e: print(f"FEHLER beim Speichern der TXT Zusammenfassung {filepath}: {e}")


def _save_report_csv(data: dict, summary_dir: str):
    """ Erstellt/Aktualisiert eine CSV-Datei für den Vergleich von Läufen. """
    class_name = data['class_name']; run_timestamp = data['eval_timestamp'].strftime("%Y%m%d_%H%M%S");
    # Define filename for the comparison CSV (goes into base summary_dir)
    filepath = os.path.join(summary_dir, f"evaluation_comparison_{class_name.lower()}.csv");
    print(f"Erstelle/Aktualisiere Vergleichs-CSV: {filepath}")

    # --- Define Metrics to Save ---
    metrics_to_save = {}; stats = data['overall_stats']; pb = data['pass_ba_details']
    metrics_to_save["Timestamp"] = run_timestamp # Add timestamp as a column value
    metrics_to_save["Gewinnrate Gesamt (%)"] = f"{stats.get('win_rate', 0):.1f}";
    metrics_to_save["Ø Belohnung"] = f"{stats.get('avg_reward', 0):.2f}";
    metrics_to_save["Ø Kampfdauer"] = f"{stats.get('avg_turns', 0):.1f}";
    metrics_to_save["Ø Rest-Mana (Sieg %)"] = f"{stats.get('avg_win_mana_perc', 0):.1f}";
    metrics_to_save["Ø Fehler-Reward"] = f"{data.get('avg_reward_components', {}).get('Skill Nutzung (Fehler)', 0):.2f}";
    metrics_to_save["Passen (%)"] = f"{pb.get('pass_perc', 0):.1f}";
    metrics_to_save["Basis-Angriff (%)"] = f"{pb.get('ba_perc', 0):.1f}";

    # Add win rate against each opponent
    for opp, opp_stats in data.get('opponent_stats', {}).items():
        metrics_to_save[f"Gewinnrate vs {opp} (%)"] = f"{opp_stats.get('win_rate', 0):.1f}"

    # --- Read existing CSV or create new DataFrame ---
    try:
        if os.path.exists(filepath):
            df = pd.read_csv(filepath)
            # Check if timestamp column exists, if not add it
            if "Timestamp" not in df.columns:
                 df.insert(0, "Timestamp", "") # Insert at the beginning
        else:
            # Create DataFrame with columns based on the metrics we want to save
            df = pd.DataFrame(columns=list(metrics_to_save.keys()))

        # --- Append new row ---
        # Check if a row with this timestamp already exists (unlikely but possible)
        if run_timestamp in df["Timestamp"].values:
            print(f"WARNUNG: Zeitstempel {run_timestamp} existiert bereits in CSV. Überschreibe Zeile.")
            # Find index and update row
            idx = df[df["Timestamp"] == run_timestamp].index
            df.loc[idx, metrics_to_save.keys()] = metrics_to_save.values()
        else:
            # Append as a new row (convert Series to DataFrame row)
            new_row = pd.DataFrame([metrics_to_save])
            df = pd.concat([df, new_row], ignore_index=True)

        # Sort by timestamp descending before saving
        # Convert timestamp column to datetime objects for proper sorting if needed
        try:
            df['Timestamp_dt'] = pd.to_datetime(df['Timestamp'], format='%Y%m%d_%H%M%S')
            df = df.sort_values(by='Timestamp_dt', ascending=False).drop(columns=['Timestamp_dt'])
        except ValueError:
            print("WARNUNG: Konnte Timestamp-Spalte nicht für Sortierung konvertieren.")
            # Keep original order if conversion fails

        # Save updated DataFrame
        df.to_csv(filepath, index=False) # Don't save DataFrame index
        print(f"  Vergleichs-CSV erfolgreich gespeichert: {filepath}")

    except Exception as e:
        print(f"FEHLER beim Speichern/Aktualisieren der Vergleichs-CSV {filepath}: {e}"); traceback.print_exc()


def _save_report_html(data: dict, target_dir: str):
    """ Speichert den Bericht als HTML-Datei. """
    class_name = data['class_name']; now_str = data['eval_timestamp'].strftime("%Y%m%d_%H%M%S");
    filename = f"evaluation_summary_{class_name.lower()}_{now_str}.html";
    filepath = os.path.join(target_dir, filename);
    print(f"Erstelle HTML-Bericht: {filepath}")

    # --- Helper for HTML escaping ---
    def escape(text): return html.escape(str(text))

    # --- Generate HTML snippets ---
    code_versions_rows = ''.join(f"<tr><td>{escape(name)}.py</td><td>{escape(info)}</td></tr>" for name, info in data.get('code_versions', {}).items())

    # Opponent stats table rows
    opponent_rows = ''
    for opp, stats_opp in sorted(data.get('opponent_stats', {}).items()):
         top_skills_list = sorted(stats_opp.get('hero_skill_usage', {}).items(), key=lambda item: item[1], reverse=True)[:3]
         top_skills_str = ", ".join([f"{escape(n)} ({p:.0f}%)" for n, p in top_skills_list if p > 1]) or 'N/A'
         opponent_rows += f"""<tr>
           <td>{escape(opp)}</td>
           <td>{stats_opp.get('win_rate', 0):.1f}</td>
           <td>{stats_opp.get('avg_overall_turns', 0):.1f}</td>
           <td>{stats_opp.get('avg_win_hp_perc', 0):.1f}</td>
           <td>{stats_opp.get('avg_loss_hp_perc', -1):.1f}</td>
           <td>{stats_opp.get('avg_win_mana_perc', 0):.1f}</td>
           <td>{stats_opp.get('avg_loss_mana_perc', -1):.1f}</td>
           <td>{top_skills_str}</td>
         </tr>"""

    action_type_list = ''.join(f"<li>{escape(type_name.replace('_', ' ').capitalize())}: {perc:.1f}%</li>" for type_name, perc in sorted(data.get('type_percentages', {}).items(), key=lambda item: item[1], reverse=True) if perc > 0.1)

    # Specific actions list (Class skills + Others)
    ap = data.get('action_percentages', {}); csn = data.get('class_skill_names', [])
    class_skills_used_html = ""
    other_actions_used_html = ""
    if ap:
        class_skills_used = {k:v for k,v in ap.items() if k in csn}
        other_actions_used = {k:v for k,v in ap.items() if k not in csn}
        sorted_class_skills = sorted(class_skills_used.items(), key=lambda item: item[1], reverse=True)
        sorted_other_actions = sorted(other_actions_used.items(), key=lambda item: item[1], reverse=True)
        if sorted_class_skills: class_skills_used_html = "<h5>Klassenskills</h5><ul>" + ''.join(f"<li>{escape(skill_name)}: {perc:.1f}%</li>" for skill_name, perc in sorted_class_skills if perc > 0.01) + "</ul>"
        if sorted_other_actions: other_actions_used_html = "<h5>Andere Aktionen</h5><ul>" + ''.join(f"<li>{escape(action_name)}: {perc:.1f}%</li>" for action_name, perc in sorted_other_actions if perc > 0.01) + "</ul>"
    specific_action_list = class_skills_used_html + other_actions_used_html

    # Pass/BA Details Table
    pb = data.get('pass_ba_details', {})
    pass_ba_table = f"""
        <h4>Passen / Basis-Angriff Details</h4>
        <table>
          <tr><th>Aktion</th><th>Anteil (%)</th><th>Anzahl</th><th>Hauptskill verfügbar (%)</th><th>Hauptskill verfügbar (Anzahl)</th><th>Ø {escape(pb.get('main_resource', 'Ressource'))} (%)</th></tr>
          <tr>
            <td>Passen</td><td>{pb.get('pass_perc', 0):.1f}</td><td>{pb.get('pass_count', 0)}</td>
            <td>{pb.get('pass_skill_usable_perc', 0):.1f}</td><td>{pb.get('pass_skill_usable_count', 0)}</td>
            <td>{pb.get('pass_avg_res_perc', -1):.1f if pb.get('pass_avg_res_perc', -1) >= 0 else 'N/A'}</td>
          </tr>
          <tr>
            <td>Basis-Angriff</td><td>{pb.get('ba_perc', 0):.1f}</td><td>{pb.get('ba_count', 0)}</td>
            <td>{pb.get('ba_skill_usable_perc', 0):.1f}</td><td>{pb.get('ba_skill_usable_count', 0)}</td>
            <td>{pb.get('ba_avg_res_perc', -1):.1f if pb.get('ba_avg_res_perc', -1) >= 0 else 'N/A'}</td>
          </tr>
        </table>
        <p><small>Hauptskill: {escape(pb.get('primary_skill', 'N/A'))}</small></p>
    """

    # --- HTML Structure ---
    stats = data.get('overall_stats', {})
    html_content = f"""<!DOCTYPE html><html lang="de"><head><meta charset="UTF-8"><title>Evaluierungsbericht: {escape(class_name)}</title>
<style>
  body{{font-family: sans-serif; margin: 20px; line-height: 1.6;}}
  table{{border-collapse: collapse; margin-bottom: 20px; width: auto;}}
  th, td{{border: 1px solid #ccc; padding: 8px; text-align: left; vertical-align: top;}}
  th{{background-color: #f2f2f2; font-weight: bold;}}
  h1, h2, h3 {{border-bottom: 1px solid #ddd; padding-bottom: 5px; margin-top: 30px;}}
  h1 {{font-size: 1.8em;}} h2 {{font-size: 1.5em;}} h3 {{font-size: 1.2em;}}
  .code{{font-family: monospace; background-color: #eee; padding: 2px 4px; border: 1px solid #ddd; border-radius: 3px; word-wrap: break-word;}}
  .metrics-table td:first-child{{font-weight: bold;}}
  ul {{margin-top: 5px; padding-left: 20px;}}
  li {{margin-bottom: 5px;}}
  details > summary {{ cursor: pointer; font-weight: bold; margin-bottom: 10px; }}
</style>
</head><body>
<h1>Evaluierungsbericht: {escape(class_name)}</h1>
<p>Bericht generiert am: {data['eval_timestamp'].strftime('%Y-%m-%d %H:%M:%S')}</p>

<details open><summary><h2>1. Metadaten & Setup</h2></summary>
  <table>
    <tr><th>Parameter</th><th>Wert</th></tr>
    <tr><td>Getestetes Modell</td><td><span class="code">{escape(data.get('model_path', 'N/A'))}</span></td></tr>
    <tr><td>Kämpfe pro Gegner</td><td>{escape(data.get('eval_params', {}).get('fights_per_opponent', 'N/A'))}</td></tr>
    <tr><td>Aktionswahl</td><td>{'Festgelegt (Deterministic)' if data.get('eval_params', {}).get('deterministic', True) else 'Zufällig (Stochastic)'}</td></tr>
    <tr><td>Max. Runden pro Kampf</td><td>{escape(data.get('eval_params', {}).get('max_turns', 'N/A'))}</td></tr>
    <tr><td>Gegner</td><td>{escape(", ".join(data.get('eval_params', {}).get('opponents', [])))}</td></tr>
  </table>
  <h3>Code-Versionen</h3>
  <table><tr><th>Datei</th><th>Info</th></tr>{code_versions_rows}</table>
</details>

<details open><summary><h2>2. Gesamtleistung ({escape(stats.get('episodes_run', 0))} Kämpfe)</h2></summary>
  <table class="metrics-table">
    <tr><th>Metrik</th><th>Wert</th></tr>
    <tr><td>Gewinnrate</td><td>{stats.get('win_rate', 0):.1f}%</td></tr>
    <tr><td>Verlustrate</td><td>{stats.get('loss_rate', 0):.1f}%</td></tr>
    <tr><td>Timeout-Rate</td><td>{stats.get('timeout_rate', 0):.1f}%</td></tr>
    <tr><td>Ø Belohnung</td><td>{stats.get('avg_reward', 0):.2f} (±{stats.get('std_reward', 0):.2f})</td></tr>
    <tr><td>Ø Kampfdauer</td><td>{stats.get('avg_turns', 0):.1f} Runden</td></tr>
    <tr><td>Ø Rest-HP (Sieg)</td><td>{stats.get('avg_win_hp_perc', 0):.1f}%</td></tr>
    <tr><td>Ø Rest-HP (Niederl./Timeout)</td><td>{stats.get('avg_loss_hp_perc', -1):.1f}%</td></tr>
    <tr><td>Ø Rest-Mana (Sieg)</td><td>{stats.get('avg_win_mana_perc', 0):.1f}%</td></tr>
    <tr><td>Ø Rest-Mana (Niederl./Timeout)</td><td>{stats.get('avg_loss_mana_perc', -1):.1f}%</td></tr>
    <tr><td>Ø Schaden Verurs.</td><td>{stats.get('avg_dmg_dealt', 0):.1f}</td></tr>
    <tr><td>Ø Schaden Erlitten</td><td>{stats.get('avg_dmg_taken', 0):.1f}</td></tr>
    <tr><td>Ø Heilung Gewirkt</td><td>{stats.get('avg_healing_done', 0):.1f}</td></tr>
  </table>
</details>

<details><summary><h2>3. Leistung gegen einzelne Gegner</h2></summary>
  <table>
    <tr><th>Gegner</th><th>Win Rate (%)</th><th>Ø Dauer</th><th>Ø Rest-HP Sieg (%)</th><th>Ø Rest-HP Niederl. (%)</th><th>Ø Rest-Mana Sieg (%)</th><th>Ø Rest-Mana Niederl. (%)</th><th>Top Aktionen Held</th></tr>
    {opponent_rows}
  </table>
</details>

<details><summary><h2>4. Strategie-Analyse (Gesamt)</h2></summary>
  <h3>Aktionstypen</h3>
  <ul>{action_type_list if action_type_list else "<li>(Keine Daten)</li>"}</ul>
  <h3>Spezifische Aktionen</h3>
  {specific_action_list if specific_action_list else "<p>(Keine Daten)</p>"}
  {pass_ba_table}
</details>

<details><summary><h2>5. Rohdaten-Verweise</h2></summary>
  <p>Monitor-Log (Training): <span class="code">{escape(data.get('monitor_log_path', 'N/A'))}</span></p>
  <p>Detailliertes Schritt-Log (Evaluierung): <span class="code">{escape(data.get('step_log_path', 'N/A'))}</span></p>
</details>

</body></html>"""

    # --- Write HTML file ---
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f: f.write(html_content)
        print(f"  HTML Zusammenfassung gespeichert: {filepath}")
    except Exception as e: print(f"FEHLER beim Speichern der HTML Zusammenfassung {filepath}: {e}")

# --- Ende Hilfsfunktionen ---

# Final print statement indicating the script version/purpose
print("Trainings- und Evaluierungs-Utilities in rpg_training_utils.py geschrieben/überschrieben (V26 - Widget Support).") # Version angepasst

