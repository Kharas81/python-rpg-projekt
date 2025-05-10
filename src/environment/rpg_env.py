# src/environment/rpg_env.py
"""
Definiert die Gymnasium-kompatible Umgebung für das RPG-Spiel.
"""
import gymnasium as gym
from gymnasium import spaces # Nur für Typ-Hinweis hier, Space kommt von Managern
import numpy as np
import logging
import random 
import time # Für Rendering-Pause
from typing import Optional, List, Dict, Any, Tuple, SupportsFloat 

# Importiere Manager-Klassen
from src.environment.state_manager import EnvStateManager
from src.environment.observation_manager import ObservationManager, MAX_SKILLS_OBS, MAX_OPPONENTS_OBS # Konstanten importieren
from src.environment.action_manager import ActionManager # MAX_SKILLS_ACTION, MAX_OPPONENTS_ACTION sind dort definiert
from src.environment.reward_manager import RewardManager

# Globale Definitionen und CombatHandler laden
from src.definitions.loader import load_character_templates, load_opponent_templates, load_skill_templates
from src.game_logic.combat import CombatHandler as GlobalCombatHandler 
from src.definitions.character import CharacterTemplate
from src.definitions.opponent import OpponentTemplate
from src.definitions.skill import SkillTemplate


logger = logging.getLogger(__name__)

_CHARACTER_TEMPLATES_ENV: Optional[Dict[str, CharacterTemplate]] = None
_OPPONENT_TEMPLATES_ENV: Optional[Dict[str, OpponentTemplate]] = None
_SKILL_TEMPLATES_ENV: Optional[Dict[str, SkillTemplate]] = None
_COMBAT_HANDLER_ENV: Optional[GlobalCombatHandler] = None

def _ensure_env_definitions_loaded():
    """Lädt globale Spieldefinitionen, die von der Env und ihren Managern benötigt werden."""
    global _CHARACTER_TEMPLATES_ENV, _OPPONENT_TEMPLATES_ENV, _SKILL_TEMPLATES_ENV, _COMBAT_HANDLER_ENV
    # Diese Funktion wird nur einmal beim ersten Env-Init aufgerufen (oder wenn _ensure_env_definitions_loaded in einem Manager fehlt)
    if _CHARACTER_TEMPLATES_ENV is None:
        try: _CHARACTER_TEMPLATES_ENV = load_character_templates(); logger.info("Char-Tmpl für RL-Env(global) geladen.")
        except Exception as e: logger.critical(f"Fehler Laden Char-Tmpl RL-Env(global): {e}"); _CHARACTER_TEMPLATES_ENV = {}
    if _OPPONENT_TEMPLATES_ENV is None:
        try: _OPPONENT_TEMPLATES_ENV = load_opponent_templates(); logger.info("Opp-Tmpl für RL-Env(global) geladen.")
        except Exception as e: logger.critical(f"Fehler Laden Opp-Tmpl RL-Env(global): {e}"); _OPPONENT_TEMPLATES_ENV = {}
    if _SKILL_TEMPLATES_ENV is None: 
        try: _SKILL_TEMPLATES_ENV = load_skill_templates(); logger.info("Skill-Tmpl für RL-Env(global) geladen.")
        except Exception as e: logger.critical(f"Fehler Laden Skill-Tmpl RL-Env(global): {e}"); _SKILL_TEMPLATES_ENV = {}
    if _COMBAT_HANDLER_ENV is None:
        _COMBAT_HANDLER_ENV = GlobalCombatHandler()


class RPGEnv(gym.Env[np.ndarray, int]): # Typ-Hinweise für Observation und Action
    metadata = {'render_modes': ['human', 'ansi'], 'render_fps': 10}

    def __init__(self, 
                 hero_id: str = "krieger", 
                 opponent_ids: Optional[List[str]] = None,
                 max_episode_steps: int = 50,
                 reward_config: Optional[Dict[str, float]] = None, # Für RewardManager
                 render_mode: Optional[str] = None):
        super().__init__()
        _ensure_env_definitions_loaded()

        if not _CHARACTER_TEMPLATES_ENV or not _OPPONENT_TEMPLATES_ENV or \
           not _SKILL_TEMPLATES_ENV or not _COMBAT_HANDLER_ENV:
            msg = "RL-Umgebung konnte aufgrund fehlender globaler Definitionen/CombatHandler nicht initialisiert werden."
            logger.error(msg)
            raise RuntimeError(msg)

        self.hero_id_config = hero_id
        self.opponent_ids_config = opponent_ids if opponent_ids is not None else ["goblin_lv1"]
        # Begrenze Gegner auf MAX_OPPONENTS_OBS (definiert im ObservationManager)
        if len(self.opponent_ids_config) > MAX_OPPONENTS_OBS:
            logger.warning(f"Zu viele Gegner-IDs ({len(self.opponent_ids_config)}) konfiguriert. Begrenze auf {MAX_OPPONENTS_OBS}.")
            self.opponent_ids_config = self.opponent_ids_config[:MAX_OPPONENTS_OBS]
        
        self.max_episode_steps = max_episode_steps
        self.render_mode = render_mode

        # Manager Instanziieren
        self.state_manager = EnvStateManager(
            character_templates=_CHARACTER_TEMPLATES_ENV,
            opponent_templates=_OPPONENT_TEMPLATES_ENV,
            combat_handler=_COMBAT_HANDLER_ENV, 
            max_supported_opponents=MAX_OPPONENTS_OBS # Wichtig: Konsistente Max-Anzahl
        )
        
        hero_template_for_managers = _CHARACTER_TEMPLATES_ENV.get(self.hero_id_config)
        if not hero_template_for_managers:
            raise ValueError(f"Helden-Template '{self.hero_id_config}' nicht in globalen Definitionen gefunden für Manager-Initialisierung.")
        
        # Die Reihenfolge der Skills ist wichtig für Observation und Action Mapping
        # Nimm die Start-Skills des Helden-Templates
        hero_initial_skills_ordered = hero_template_for_managers.starting_skills
        
        self.obs_manager = ObservationManager(
            skill_templates=_SKILL_TEMPLATES_ENV,
            hero_starting_skills_ids_ordered=hero_initial_skills_ordered
        )
        self.action_manager = ActionManager(
            skill_templates=_SKILL_TEMPLATES_ENV,
            hero_initial_skill_ids=hero_initial_skills_ordered
        )
        self.reward_manager = RewardManager(reward_config=reward_config)

        self.observation_space = self.obs_manager.get_observation_space()
        self.action_space = self.action_manager.get_action_space() # Typ ist spaces.Discrete

        logger.info("RPGEnv initialisiert mit allen Managern.")


    def _get_observation(self) -> np.ndarray:
        return self.obs_manager.get_observation(self.state_manager)

    def _get_info(self) -> Dict[str, Any]:
        hero = self.state_manager.get_hero()
        return {
            "current_step": self.state_manager.current_episode_step,
            "hero_hp": hero.current_hp if hero else -1,
            "hero_max_hp": hero.max_hp if hero else -1,
            "opponents_status": [{"name": o.name if o else "N/A", 
                                  "hp": o.current_hp if o else -1, 
                                  "is_defeated": o.is_defeated if o else True} 
                                 for o in self.state_manager.opponents],
            "action_mask": self.action_masks(),
            "last_action_successful" : self.state_manager.last_action_successful
        }

    def action_masks(self) -> List[bool]: # Gymnasium erwartet List[bool] für Discrete Space Masking
        return self.action_manager.get_action_mask(self.state_manager)

    def reset(self, seed: Optional[int] = None, options: Optional[Dict[str, Any]] = None) -> Tuple[np.ndarray, Dict[str, Any]]:
        super().reset(seed=seed) # Wichtig für Reproduzierbarkeit
        
        if not self.state_manager.reset_state(self.hero_id_config, self.opponent_ids_config):
            logger.error("Fehler beim Reset des EnvStateManagers in RPGEnv.reset().")
            # Rückgabe eines Dummy-Zustands, um Absturz zu vermeiden, aber das ist ein Fehler.
            dummy_obs = np.zeros(self.observation_space.shape, dtype=self.observation_space.dtype)
            return dummy_obs, {"error": "StateManager reset failed"}
        
        # Wichtig: ActionManager und ObservationManager könnten Infos aus dem Hero-Template brauchen,
        # das jetzt im StateManager initialisiert wurde.
        # Wenn ihre Konfiguration vom spezifischen Helden abhängt (z.B. Anzahl Skills),
        # könnte hier eine Re-Initialisierung oder ein Update nötig sein.
        # Aktuell ist hero_initial_skill_ids im Action/ObsManager fix bei Env-Init.
        # Das ist ok, solange sich der Held (und seine Skill-Liste) nicht pro Episode ändert.
        # Wenn der Held pro Episode wechseln könnte, müssten die Manager das dynamisch handhaben.
        
        # Initialisiere HP für Reward Manager zu Beginn der Episode
        self.reward_manager.record_hp_at_turn_start(self.state_manager.get_all_live_participants())

        observation = self._get_observation()
        info = self._get_info()
        
        if self.render_mode == "human": self.render()
        return observation, info

    def step(self, action: int) -> Tuple[np.ndarray, SupportsFloat, bool, bool, Dict[str, Any]]:
        terminated = False
        truncated = False
        current_reward: SupportsFloat = 0.0 
        hero = self.state_manager.get_hero()

        if not hero:
            logger.error("Held nicht initialisiert in step(). Episode wird als terminiert behandelt.")
            return self._get_observation(), self.reward_manager.config.get("hero_defeated_penalty", -50.0), True, True, self._get_info()

        # 0. HP zu Beginn des "Frames" (vor Helden- und Gegneraktionen) für Reward speichern
        self.reward_manager.record_hp_at_turn_start(self.state_manager.get_all_live_participants())

        # 1. Aktion des Agenten (Held)
        action_mask = self.action_masks() # Hole aktuelle Maske
        is_action_valid_by_mask = 0 <= action < len(action_mask) and action_mask[action]
        
        game_action_tuple: Optional[Tuple[str, CharacterInstance]] = None
        action_executable = False

        if hero.is_defeated or not hero.can_act:
            logger.debug(f"Held '{hero.name}' kann in step() nicht handeln.")
            self.state_manager.last_action_successful = False # Zählt als nicht erfolgreich
        elif not is_action_valid_by_mask:
            logger.warning(f"RL Agent (Held '{hero.name}') wählte ungültige/maskierte Aktion: {action}. Maske: {action_mask}")
            self.state_manager.last_action_successful = False
        else:
            game_action_tuple = self.action_manager.get_game_action(action, self.state_manager)
            if game_action_tuple:
                skill_id, target_instance = game_action_tuple
                logger.info(f"RL Agent (Held '{hero.name}') AKTION: Skill '{skill_id}' auf Ziel '{target_instance.name}'.")
                # execute_hero_action gibt jetzt (bool, str) zurück.
                action_executable, _ = self.state_manager.execute_hero_action(skill_id, target_instance)
            else: # Sollte nicht passieren, wenn Maske korrekt ist und get_game_action robust
                logger.warning(f"RL Agent (Held '{hero.name}') wählte Aktion {action}, aber get_game_action gab None zurück.")
                self.state_manager.last_action_successful = False
        
        current_reward += self.reward_manager.calculate_reward_for_hero_action(
            self.state_manager, 
            is_action_valid_by_mask, 
            action_executable, # Erfolg der Ausführung
            game_action_tuple[0] if game_action_tuple else None # Skill-ID
        )

        # 2. Prüfen, ob Kampf nach Heldenaktion beendet ist
        term_after_hero, hero_won_after_hero, _ = self.state_manager.check_combat_end_conditions()
        if term_after_hero:
            terminated = True
            # Finaler Reward wird am Ende hinzugefügt

        # 3. Gegneraktionen (wenn Kampf nicht schon vorbei)
        if not terminated:
            # HP des Helden *vor* den Gegnerzügen für Reward-Berechnung merken
            # Diese Logik ist etwas knifflig, da record_hp_at_turn_start am Anfang des Frames ist.
            # Wir bräuchten hier eigentlich den Zustand *nach* der Heldenaktion, *bevor* die NPCs ziehen.
            # Der RewardManager muss das intern besser handhaben oder die Env mehr Zustände übergeben.
            # Einfachheitshalber: RewardManager.calculate_reward_after_opponent_turns wird jetzt intern
            # versuchen, den Schaden am Helden zu schätzen oder zu ignorieren, bis der finale Reward kommt.
            # Wir können aber den HP-Stand des Helden *jetzt* speichern, bevor NPCs ziehen.
            hero_hp_before_npc_turn = hero.current_hp if hero else 0

            self.state_manager.run_opponent_turns()
            
            # Schaden am Helden durch NPCs für Reward berücksichtigen
            if hero:
                damage_taken_from_npcs = hero_hp_before_npc_turn - hero.current_hp
                if damage_taken_from_npcs > 0:
                    npc_damage_penalty = damage_taken_from_npcs * self.reward_manager.config.get("damage_to_hero_penalty_mult", -0.3)
                    current_reward += npc_damage_penalty
                    logger.debug(f"RewardManager: Strafe {npc_damage_penalty:.2f} für {damage_taken_from_npcs} Schaden am Helden durch NPCs.")


            # Erneute Prüfung nach Gegnerzügen
            term_after_npc, _, _ = self.state_manager.check_combat_end_conditions()
            if term_after_npc:
                terminated = True
        
        # 4. Schrittende und finaler Reward
        self.state_manager.increment_step()
        if self.state_manager.current_episode_step >= self.max_episode_steps and not terminated:
            truncated = True
        
        current_reward += self.reward_manager.get_final_episode_rewards(self.state_manager, truncated)
        
        observation = self._get_observation()
        info = self._get_info() # Info enthält jetzt auch action_mask
        
        if self.render_mode == "human":
            self.render()
            if not terminated and not truncated: time.sleep(0.05)

        return observation, current_reward, terminated, truncated, info

    def render(self):
        if self.render_mode == "human":
            hero = self.state_manager.get_hero()
            opponents = self.state_manager.opponents

            print(f"\n--- Env Step: {self.state_manager.current_episode_step}, Max: {self.max_episode_steps} ---")
            if hero:
                res_val, res_max, res_type_str = 0,0,"NONE"
                if hasattr(hero.base_template, 'resource_type'):
                    res_type = hero.base_template.resource_type
                    if res_type == "MANA": res_val, res_max, res_type_str = hero.current_mana, hero.max_mana, "Mana"
                    elif res_type == "STAMINA": res_val, res_max, res_type_str = hero.current_stamina, hero.max_stamina, "Stam"
                    elif res_type == "ENERGY": res_val, res_max, res_type_str = hero.current_energy, hero.max_energy, "Ener"
                print(f"  Hero: {hero.name} HP: {hero.current_hp}/{hero.max_hp} "
                      f"{res_type_str}: {res_val}/{res_max} "
                      f"S: {hero.shield_points} Eff: {[str(e) for e in hero.status_effects]}")
            for i, opponent in enumerate(opponents):
                if opponent: 
                    print(f"  Opp{i+1}: {opponent.name} HP: {opponent.current_hp}/{opponent.max_hp} "
                          f"Eff: {[str(e) for e in opponent.status_effects]}")
            
            term, won, msg = self.state_manager.check_combat_end_conditions()
            if term: print(f"  KAMPFENDE: {msg} (Held gewonnen: {won})")


    def close(self):
        logger.info("RL-Umgebung wird geschlossen.")

# ... (if __name__ == '__main__' Block bleibt gleich, aber random muss importiert sein)
if __name__ == '__main__':
    try:
        import src.utils.logging_setup 
        from src.config.config import CONFIG 
        if not CONFIG: raise Exception("Konfiguration nicht geladen.")
        _ensure_env_definitions_loaded() 
        if not _CHARACTER_TEMPLATES_ENV or not _OPPONENT_TEMPLATES_ENV or not _SKILL_TEMPLATES_ENV:
            raise Exception("Spieldefinitionen konnten nicht für den Env-Test geladen werden.")
    except Exception as e:
        print(f"Fehler beim Setup für Env-Test: {e}")
        exit(1)

    print("\n--- Teste RPGEnv (Refactored) ---")
    env_config = {
        "hero_id": "krieger", 
        "opponent_ids": ["goblin_lv1", "goblin_archer_lv2"], 
        "max_episode_steps": 25, # Weniger Schritte für schnellere Tests
        "render_mode": "human",
        "reward_config": {"step_penalty": -0.02} # Beispiel für Custom Reward Config
    }
    env = RPGEnv(**env_config)

    try:
        from gymnasium.utils.env_checker import check_env
        # print("Gymnasium check_env: Prüfung gestartet...")
        # check_env(env) 
        # print("Gymnasium check_env: Prüfung abgeschlossen (wenn keine Fehler).")
    except ImportError: print("gymnasium.utils.env_checker nicht gefunden.")
    except Exception as e: print(f"Fehler bei check_env: {e}")


    num_episodes_for_test = 2
    all_episode_rewards = []

    for ep in range(num_episodes_for_test):
        print(f"\n{'='*10} Starte Test-Episode {ep + 1} {'='*10}")
        obs, info = env.reset()
        terminated = False
        truncated = False
        episode_reward = 0
        episode_steps = 0

        # print(f"Episode {ep+1} - Initial Observation (Shape: {obs.shape}): {obs}")
        # print(f"Episode {ep+1} - Initial Info: {info}")


        while not terminated and not truncated:
            action_mask = env.action_masks() # In Info enthalten, aber hier nochmal holen für Klarheit
            valid_actions = [i for i, valid in enumerate(action_mask) if valid]
            
            if not valid_actions:
                print(f"Step {episode_steps + 1}: Keine gültigen Aktionen für den Helden verfügbar! (Maske: {action_mask}). Episode wird wahrscheinlich fehlschlagen.")
                # Hier könnte man eine no-op Aktion erzwingen oder die Episode beenden
                # Für den Test nehmen wir die erste Aktion, auch wenn sie ungültig ist, um den Flow zu sehen
                if env.action_space.n > 0 : action = 0 
                else: break # Kein Action Space -> Fehler
            else:
                action = random.choice(valid_actions)
            
            # Logge die gewählte Aktion und die Maske
            # skill_idx = action // env.action_manager.num_target_options_in_space if env.action_manager.num_target_options_in_space > 0 else -1
            # target_idx = action % env.action_manager.num_target_options_in_space if env.action_manager.num_target_options_in_space > 0 else -1
            # print(f"\nStep {episode_steps + 1}: Gewählte Aktion {action} (S:{skill_idx}, T:{target_idx}) | Gültig lt. Maske: {action_mask[action] if 0 <= action < len(action_mask) else 'ID out of bound'}")
            # print(f"  Action Mask: {action_mask}") # Kann sehr lang sein

            obs, reward, terminated, truncated, info = env.step(action)
            episode_reward += reward
            episode_steps += 1
            
            # print(f"  Obs (Shape: {obs.shape}): {obs}") 
            # print(f"  Step {episode_steps}: Act={action}, Rew={reward:.2f}, Term={terminated}, Trunc={truncated}, HeroHP={info.get('hero_hp', 'N/A')}")
            # print(f"  Info: {info}") 

        print(f"Episode {ep + 1} beendet nach {episode_steps} Schritten. Episoden-Reward: {episode_reward:.2f}")
        all_episode_rewards.append(episode_reward)
    
    if all_episode_rewards:
        print(f"\nDurchschnittlicher Reward über {num_episodes_for_test} Episoden: {sum(all_episode_rewards)/len(all_episode_rewards):.2f}")
    env.close()
    print("\n--- RPGEnv Test (Refactored) abgeschlossen ---")