# src/environment/rpg_env.py
"""
Definiert die Gymnasium-kompatible Umgebung für das RPG-Spiel.
Nutzt Manager-Klassen für Zustand, Observation, Aktion und Reward.
"""
import gymnasium as gym
from gymnasium import spaces 
import numpy as np
import logging
import random 
import time 
from typing import Optional, List, Dict, Any, Tuple, SupportsFloat 

from src.environment.state_manager import EnvStateManager
from src.environment.observation_manager import ObservationManager, MAX_SKILLS_OBS, MAX_OPPONENTS_OBS
from src.environment.action_manager import ActionManager 
from src.environment.reward_manager import RewardManager

from src.definitions.loader import load_character_templates, load_opponent_templates, load_skill_templates
from src.game_logic.combat import CombatHandler as GlobalCombatHandler 
from src.definitions.character import CharacterTemplate
from src.definitions.opponent import OpponentTemplate
from src.definitions.skill import SkillTemplate

logger = logging.getLogger(__name__)

# Globale Caches für Definitionen, die einmal geladen und an Manager übergeben werden
_CHARACTER_TEMPLATES_ENV: Optional[Dict[str, CharacterTemplate]] = None
_OPPONENT_TEMPLATES_ENV: Optional[Dict[str, OpponentTemplate]] = None
_SKILL_TEMPLATES_ENV: Optional[Dict[str, SkillTemplate]] = None
_COMBAT_HANDLER_ENV: Optional[GlobalCombatHandler] = None

def _ensure_env_definitions_loaded():
    """Lädt globale Spieldefinitionen, die von der Env und ihren Managern benötigt werden."""
    global _CHARACTER_TEMPLATES_ENV, _OPPONENT_TEMPLATES_ENV, _SKILL_TEMPLATES_ENV, _COMBAT_HANDLER_ENV
    if _CHARACTER_TEMPLATES_ENV is None:
        try: _CHARACTER_TEMPLATES_ENV = load_character_templates(); logger.info("Char-Tmpl für RL-Env(global) geladen.")
        except Exception as e: logger.critical(f"Fehler Laden Char-Tmpl RL-Env(global): {e}", exc_info=True); _CHARACTER_TEMPLATES_ENV = {}
    if _OPPONENT_TEMPLATES_ENV is None:
        try: _OPPONENT_TEMPLATES_ENV = load_opponent_templates(); logger.info("Opp-Tmpl für RL-Env(global) geladen.")
        except Exception as e: logger.critical(f"Fehler Laden Opp-Tmpl RL-Env(global): {e}", exc_info=True); _OPPONENT_TEMPLATES_ENV = {}
    if _SKILL_TEMPLATES_ENV is None: 
        try: _SKILL_TEMPLATES_ENV = load_skill_templates(); logger.info("Skill-Tmpl für RL-Env(global) geladen.")
        except Exception as e: logger.critical(f"Fehler Laden Skill-Tmpl RL-Env(global): {e}", exc_info=True); _SKILL_TEMPLATES_ENV = {}
    if _COMBAT_HANDLER_ENV is None:
        _COMBAT_HANDLER_ENV = GlobalCombatHandler() # Eine globale Instanz reicht


class RPGEnv(gym.Env[np.ndarray, int]): 
    metadata = {'render_modes': ['human', 'ansi'], 'render_fps': 10}

    def __init__(self, 
                 hero_id: str = "krieger", 
                 opponent_setup_config: Optional[Dict[str, Any]] = None, # Akzeptiert jetzt opponent_setup_config
                 max_episode_steps: int = 50,
                 reward_config: Optional[Dict[str, float]] = None,
                 render_mode: Optional[str] = None):
        super().__init__()
        _ensure_env_definitions_loaded()

        if not _CHARACTER_TEMPLATES_ENV or not _OPPONENT_TEMPLATES_ENV or \
           not _SKILL_TEMPLATES_ENV or not _COMBAT_HANDLER_ENV:
            msg = "RPGEnv: Globale Spieldefinitionen oder CombatHandler nicht korrekt initialisiert."
            logger.error(msg)
            raise RuntimeError(msg)

        self.hero_id_config = hero_id
        # Speichere die opponent_setup_config für das reset
        self.opponent_setup_config_for_reset = opponent_setup_config if opponent_setup_config is not None \
                                               else {"ids": ["goblin_lv1"], "num_opponents": 1, "level_pool": "1-2"} 
        
        # Sicherstellen, dass die Anzahl der Gegner in der Config MAX_OPPONENTS_OBS nicht überschreitet
        num_opp_in_config = self.opponent_setup_config_for_reset.get("num_opponents", 1)
        if "ids" in self.opponent_setup_config_for_reset and self.opponent_setup_config_for_reset["ids"]:
            num_opp_in_config = len(self.opponent_setup_config_for_reset["ids"])

        if num_opp_in_config > MAX_OPPONENTS_OBS:
            logger.warning(f"RPGEnv __init__: Gegneranzahl in opponent_setup_config ({num_opp_in_config}) "
                           f"überschreitet MAX_OPPONENTS_OBS ({MAX_OPPONENTS_OBS}). Wird begrenzt.")
            if "ids" in self.opponent_setup_config_for_reset and self.opponent_setup_config_for_reset["ids"]:
                 self.opponent_setup_config_for_reset["ids"] = self.opponent_setup_config_for_reset["ids"][:MAX_OPPONENTS_OBS]
            # num_opponents wird vom StateManager._create_dynamic_opponent_team gehandhabt/begrenzt
            self.opponent_setup_config_for_reset["num_opponents"] = min(num_opp_in_config, MAX_OPPONENTS_OBS)


        self.max_episode_steps = max_episode_steps
        self.render_mode = render_mode

        self.state_manager = EnvStateManager(
            character_templates=_CHARACTER_TEMPLATES_ENV,
            opponent_templates=_OPPONENT_TEMPLATES_ENV,
            combat_handler=_COMBAT_HANDLER_ENV, 
            max_supported_opponents=MAX_OPPONENTS_OBS 
        )
        
        hero_template_for_managers = _CHARACTER_TEMPLATES_ENV.get(self.hero_id_config)
        if not hero_template_for_managers:
            raise ValueError(f"Helden-Template '{self.hero_id_config}' nicht gefunden für Manager-Init.")
        
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
        self.action_space = self.action_manager.get_action_space() 
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
                                 for o in self.state_manager.opponents], # Iteriere über die Slot-Liste
            "action_mask": self.action_masks(),
            "last_action_successful" : self.state_manager.last_action_successful
        }

    def action_masks(self) -> List[bool]: 
        return self.action_manager.get_action_mask(self.state_manager)

    def reset(self, seed: Optional[int] = None, options: Optional[Dict[str, Any]] = None) -> Tuple[np.ndarray, Dict[str, Any]]:
        super().reset(seed=seed) 
        
        # `opponent_setup_config_for_reset` wurde in __init__ vorbereitet
        if not self.state_manager.reset_state(self.hero_id_config, self.opponent_setup_config_for_reset):
            logger.error("Fehler beim Reset des EnvStateManagers in RPGEnv.reset().")
            dummy_obs = np.zeros(self.observation_space.shape, dtype=self.observation_space.dtype)
            return dummy_obs, {"error": "StateManager reset failed"}
        
        # Aktualisiere die Skill-Liste im ActionManager, falls der Held sich ändern könnte (nicht im aktuellen Plan)
        # oder wenn die Skills des Helden sich dynamisch ändern könnten.
        # Für den Moment ist das nicht nötig, da der Held und seine Start-Skills bei Env-Init festgelegt werden.
        # hero = self.state_manager.get_hero()
        # if hero:
        #     self.action_manager.update_hero_skills(hero.skills) # Beispiel für eine Update-Methode

        self.reward_manager.record_hp_at_turn_start(self.state_manager.get_all_live_participants())
        observation = self._get_observation()
        info = self._get_info()
        if self.render_mode == "human": self.render()
        return observation, info

    def step(self, action: int) -> Tuple[np.ndarray, SupportsFloat, bool, bool, Dict[str, Any]]:
        terminated = False
        truncated = False
        current_reward: SupportsFloat = self.reward_manager.config.get("step_penalty", -0.01)
        hero = self.state_manager.get_hero()

        if not hero:
            logger.error("Held nicht initialisiert in step(). Episode wird als terminiert behandelt.")
            return self._get_observation(), self.reward_manager.config.get("hero_defeated_penalty", -50.0), True, True, self._get_info()

        self.reward_manager.record_hp_at_turn_start(self.state_manager.get_all_live_participants())

        action_mask = self.action_masks() 
        is_action_valid_by_mask = 0 <= action < len(action_mask) and action_mask[action]
        
        game_action_tuple: Optional[Tuple[str, CharacterInstance]] = None
        action_executed_successfully = False # Ob die Aktion vom StateManager ausgeführt wurde

        if hero.is_defeated or not hero.can_act:
            logger.debug(f"Held '{hero.name}' kann in step() nicht handeln.")
            self.state_manager.last_action_successful = False
        elif not is_action_valid_by_mask:
            logger.warning(f"RL Agent (Held '{hero.name}') wählte ungültige/maskierte Aktion: {action}. Maske: {action_mask}")
            self.state_manager.last_action_successful = False
        else:
            game_action_tuple = self.action_manager.get_game_action(action, self.state_manager)
            if game_action_tuple:
                skill_id, target_instance = game_action_tuple
                logger.info(f"RL Agent (Held '{hero.name}') AKTION: Skill '{skill_id}' auf Ziel '{target_instance.name}'.")
                action_executed_successfully, _ = self.state_manager.execute_hero_action(skill_id, target_instance)
            else: 
                logger.warning(f"RL Agent (Held '{hero.name}') wählte Aktion {action}, aber get_game_action gab None zurück.")
                self.state_manager.last_action_successful = False
        
        current_reward += self.reward_manager.calculate_reward_for_hero_action(
            self.state_manager, 
            is_action_valid_by_mask, 
            action_executed_successfully, 
            game_action_tuple[0] if game_action_tuple else None 
        )

        term_after_hero, hero_won_after_hero, msg_after_hero = self.state_manager.check_combat_end_conditions()
        if term_after_hero:
            terminated = True
        
        if not terminated:
            hero_hp_before_npc_turn = hero.current_hp if hero else 0
            self.state_manager.run_opponent_turns()
            
            if hero: # Nur wenn Held noch existiert
                damage_taken_from_npcs = hero_hp_before_npc_turn - hero.current_hp
                if damage_taken_from_npcs > 0:
                    npc_damage_penalty = damage_taken_from_npcs * self.reward_manager.config.get("damage_to_hero_penalty_mult", -0.3)
                    current_reward += npc_damage_penalty
                    logger.debug(f"RewardManager: Strafe {npc_damage_penalty:.2f} für {damage_taken_from_npcs} Schaden am Helden durch NPCs.")

            term_after_npc, _, _ = self.state_manager.check_combat_end_conditions()
            if term_after_npc:
                terminated = True
        
        self.state_manager.increment_step()
        if self.state_manager.current_episode_step >= self.max_episode_steps and not terminated:
            truncated = True
        
        current_reward += self.reward_manager.get_final_episode_rewards(self.state_manager, truncated) # truncated hier übergeben
        
        observation = self._get_observation()
        info = self._get_info() 
        
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
            for i, opponent in enumerate(opponents): # Iteriere über die Slot-Liste
                if opponent: 
                    print(f"  Opp{i+1}: {opponent.name} HP: {opponent.current_hp}/{opponent.max_hp} "
                          f"Eff: {[str(e) for e in opponent.status_effects]}")
            
            term, won, msg = self.state_manager.check_combat_end_conditions()
            if term: print(f"  KAMPFENDE: {msg} (Held gewonnen: {won})")


    def close(self):
        logger.info("RL-Umgebung wird geschlossen.")

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
    
    # Beispiel-Konfiguration für Gegner, die RPGEnv.__init__ jetzt erwartet
    test_opponent_setup = {
        "num_opponents": 2, 
        "level_pool": "1-2", 
        # "ids": ["goblin_lv1", "goblin_archer_lv2"] # Optional: spezifische IDs
    }
    if "ids" not in test_opponent_setup: # Sicherstellen, dass 'ids' nicht zum Fehler führt, wenn es nicht da ist
        test_opponent_setup["ids"] = [] # Leere Liste, StateManager wird Pool nutzen


    env_config_for_test = { 
        "hero_id": "krieger", 
        "opponent_setup_config": test_opponent_setup, 
        "max_episode_steps": 20, # Weniger Schritte für Test
        "render_mode": "human" 
    }
    env = RPGEnv(**env_config_for_test)

    try:
        from gymnasium.utils.env_checker import check_env
        # print("Gymnasium check_env: Prüfung gestartet...")
        # check_env(env) 
        # print("Gymnasium check_env: Prüfung abgeschlossen.")
    except ImportError: print("gymnasium.utils.env_checker nicht gefunden.")
    except Exception as e: print(f"Fehler bei check_env: {e}")

    num_episodes_for_test = 1 # Nur eine Episode für einen schnellen Test
    all_episode_rewards = []

    for ep in range(num_episodes_for_test):
        print(f"\n{'='*10} Starte Test-Episode {ep + 1} {'='*10}")
        obs, info = env.reset()
        terminated = False
        truncated = False
        episode_reward = 0
        episode_steps = 0

        while not terminated and not truncated:
            action_mask = info.get("action_mask", [False]*env.action_space.n) # Hole Maske aus Info
            valid_actions = [i for i, valid in enumerate(action_mask) if valid]
            
            action_to_take = -1
            if not valid_actions:
                print(f"Step {episode_steps + 1}: Keine gültigen Aktionen für den Helden verfügbar! (Maske: {action_mask}). Versuche Aktion 0 als Fallback.")
                if env.action_space.n > 0 : action_to_take = 0 
                else: 
                    print("FEHLER: Action Space ist leer. Breche ab."); break 
            else:
                action_to_take = random.choice(valid_actions)
            
            # Logge die gewählte Aktion und die Maske
            # skill_idx_calc = action_to_take // env.action_manager.num_target_options_in_space if env.action_manager.num_target_options_in_space > 0 else -1
            # target_idx_calc = action_to_take % env.action_manager.num_target_options_in_space if env.action_manager.num_target_options_in_space > 0 else -1
            # print(f"\nStep {episode_steps + 1}: Gewählte Aktion {action_to_take} (S:{skill_idx_calc}, T:{target_idx_calc}) | Gültig lt. Maske: {action_mask[action_to_take] if 0 <= action_to_take < len(action_mask) else 'ID out of bound'}")
            
            obs, reward, terminated, truncated, info = env.step(action_to_take)
            episode_reward += reward
            episode_steps += 1
            
            print(f"  Step {episode_steps}: Act={action_to_take}, Rew={reward:.2f}, Term={terminated}, Trunc={truncated}, HeroHP={info.get('hero_hp', 'N/A')}")

        print(f"Episode {ep + 1} beendet nach {episode_steps} Schritten. Episoden-Reward: {episode_reward:.2f}")
        all_episode_rewards.append(episode_reward)
    
    if all_episode_rewards:
        print(f"\nDurchschnittlicher Reward über {num_episodes_for_test} Episoden: {sum(all_episode_rewards)/len(all_episode_rewards):.2f}")
    env.close()
    print("\n--- RPGEnv Test (Refactored) abgeschlossen ---")