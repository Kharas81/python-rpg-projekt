"""
RPG Gymnasium Environment

Diese Datei definiert die Gymnasium-kompatible Umgebung für das textbasierte RPG,
die für das Training von Reinforcement Learning Agenten verwendet wird.
"""
import os
import sys
import random
from typing import Dict, Any, Optional, Tuple, List

import gymnasium as gym
from gymnasium import spaces
import numpy as np

# Stellen sicher, dass src im Python-Pfad ist
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.config.config import get_config
from src.utils.logging_setup import get_logger
from src.definitions import loader
from src.definitions.skill import SkillDefinition
from src.definitions.character import CharacterTemplate, OpponentTemplate
from src.game_logic.entities import CharacterInstance
from src.game_logic.combat import CombatEncounter, CombatSystem, CombatAction, get_combat_system
from src.ai.ai_dispatcher import get_ai_dispatcher
from src.environment.observation_manager import ObservationManager, AGENT_MAX_SKILLS_OBS_ACTION
from src.environment.action_manager import ActionManager
from src.environment.reward_calculator import RewardCalculator

# Logger für dieses Modul
logger = get_logger(__name__)


class RPGEnv(gym.Env):
    """
    Eine Gymnasium-Umgebung für das textbasierte RPG.
    Orchestriert die Interaktion zwischen dem Agenten und der Spielwelt
    mithilfe von ObservationManager, ActionManager und RewardCalculator.
    """
    metadata = {'render_modes': ['human', 'ansi'], 'render_fps': 4}

    def __init__(self, config_override: Optional[Dict[str, Any]] = None):
        super().__init__()

        self.config = get_config()
        rl_env_specific_settings = self.config.rl.get('env', {})
        self.rl_settings = {**self.config.rl, **rl_env_specific_settings}

        if config_override:
            for key, value in config_override.items():
                if isinstance(value, dict) and key in self.rl_settings:
                    self.rl_settings[key].update(value)
                else:
                    self.rl_settings[key] = value
        
        logger.info(f"RPGEnv initialisiert mit RL-Einstellungen: {self.rl_settings}")

        base_path = os.path.dirname(os.path.dirname(__file__))
        self.character_templates: Dict[str, CharacterTemplate] = loader.load_characters(
            os.path.join(base_path, "definitions", "json_data", "characters.json5"))
        self.skill_definitions: Dict[str, SkillDefinition] = loader.load_skills(
            os.path.join(base_path, "definitions", "json_data", "skills.json5"))
        self.opponent_templates: Dict[str, OpponentTemplate] = loader.load_opponents(
            os.path.join(base_path, "definitions", "json_data", "opponents.json5"))

        self.max_steps_per_episode: int = self.rl_settings.get('max_steps', 100)
        self.reward_settings: Dict[str, float] = self.rl_settings.get('reward_settings', {})

        self.max_allies_for_action = self.rl_settings.get('max_allies', 1)
        self.max_enemies_for_action = self.rl_settings.get('max_enemies', 3)
        self.num_target_slots = 1 + self.max_allies_for_action + self.max_enemies_for_action

        self.observation_manager = ObservationManager(
            max_allies=self.max_allies_for_action,
            max_enemies=self.max_enemies_for_action
        )
        self.action_manager = ActionManager(
            agent_max_skills=AGENT_MAX_SKILLS_OBS_ACTION,
            num_target_slots=self.num_target_slots
        )
        self.reward_calculator = RewardCalculator(self.reward_settings)

        self.action_space = spaces.Discrete(self.action_manager.action_space_size)
        logger.info(f"Action Space definiert: Discrete({self.action_space.n}) "
                    f"(Size from ActionManager: {self.action_manager.action_space_size})")
        
        self.observation_space = spaces.Box(
            low=0.0, 
            high=1.0,
            shape=(self.observation_manager.total_observation_size,),
            dtype=np.float32
        )
        logger.info(f"Observation Space definiert: Box(shape=({self.observation_manager.total_observation_size},))")

        self.combat_system: CombatSystem = get_combat_system()
        self.ai_dispatcher = get_ai_dispatcher()

        self.agent_character: Optional[CharacterInstance] = None
        self.current_encounter: Optional[CombatEncounter] = None
        self.current_step: int = 0
        
        self.agent_skill_map: List[Optional[SkillDefinition]] = [None] * AGENT_MAX_SKILLS_OBS_ACTION
        self.target_map: List[Optional[CharacterInstance]] = []

    def _get_observation(self) -> np.ndarray:
        return self.observation_manager.get_observation(
            agent_character=self.agent_character,
            current_encounter=self.current_encounter,
            agent_skill_map=self.agent_skill_map
        )

    def _get_info(self) -> Dict:
        info = {
            'current_step': self.current_step,
            'agent_hp': self.agent_character.hp if self.agent_character else 0,
            'agent_mana': self.agent_character.mana if self.agent_character else 0,
            'round': self.current_encounter.round if self.current_encounter else 0,
            'active_opponents': len([o for o in self.current_encounter.opponents if o.is_alive()]) if self.current_encounter else 0,
        }
        if self.agent_character:
            info['agent_skills'] = [s.id if s else "N/A" for s in self.agent_skill_map]
            info['current_targets'] = [t.name if t else "N/A" for t in self.target_map]
        return info
        
    def _update_target_map(self):
        self.target_map = []
        if not self.current_encounter or not self.agent_character:
            for _ in range(self.num_target_slots):
                self.target_map.append(None)
            return

        self.target_map.append(self.agent_character)

        allies_in_encounter = [p for p in self.current_encounter.players if p != self.agent_character and p.is_alive()]
        for i in range(self.max_allies_for_action):
            self.target_map.append(allies_in_encounter[i] if i < len(allies_in_encounter) else None)

        enemies_in_encounter = [o for o in self.current_encounter.opponents if o.is_alive()]
        for i in range(self.max_enemies_for_action):
            self.target_map.append(enemies_in_encounter[i] if i < len(enemies_in_encounter) else None)
            
    def _update_agent_skill_map(self):
        self.agent_skill_map = [None] * AGENT_MAX_SKILLS_OBS_ACTION
        if self.agent_character:
            for i, skill_id in enumerate(self.agent_character.skill_ids):
                if i >= AGENT_MAX_SKILLS_OBS_ACTION:
                    break
                skill_def = self.skill_definitions.get(skill_id)
                if skill_def:
                    self.agent_skill_map[i] = skill_def

    def reset(self, seed: Optional[int] = None, options: Optional[Dict[str, Any]] = None) -> Tuple[np.ndarray, Dict[str, Any]]:
        super().reset(seed=seed)
        self.current_step = 0
        logger.info("Umgebung wird zurückgesetzt (reset).")

        if not self.character_templates:
            logger.error("Keine Charakter-Templates geladen. Reset nicht möglich.")
            return np.zeros(self.observation_space.shape[0], dtype=np.float32), {} # type: ignore

        agent_template_id = self.rl_settings.get('agent_template_id', None) or random.choice(list(self.character_templates.keys()))
        agent_template = self.character_templates[agent_template_id]
        agent_level = self.rl_settings.get('agent_start_level', 1)
        self.agent_character = CharacterInstance.from_template(agent_template, level=agent_level)
        logger.info(f"Agent-Charakter '{self.agent_character.name}' (Level {agent_level}, Vorlage: {agent_template_id}) erstellt.")
        self._update_agent_skill_map()

        num_opponents = self.rl_settings.get('num_initial_opponents', random.randint(1, self.max_enemies_for_action))
        opponents: List[CharacterInstance] = []
        available_opponent_templates = list(self.opponent_templates.values())
        
        if not available_opponent_templates:
            logger.warning("Keine Gegner-Templates geladen. Erstelle keine Gegner.")
        else:
            for _ in range(num_opponents):
                opponent_template = random.choice(available_opponent_templates)
                opp_level = max(1, self.agent_character.level + random.randint(self.rl_settings.get('opponent_level_variance_min', -1),
                                                                            self.rl_settings.get('opponent_level_variance_max', 0)))
                opponent = CharacterInstance.from_template(opponent_template, level=opp_level)
                opponents.append(opponent)
                logger.info(f"Gegner '{opponent.name}' (Level {opp_level}) erstellt.")
        
        num_allies = self.rl_settings.get('num_initial_allies', 0)
        allies: List[CharacterInstance] = []
        available_player_templates = [ct for ct_id, ct in self.character_templates.items() if ct_id != agent_template_id]
        if not available_player_templates: 
            available_player_templates = list(self.character_templates.values())

        if num_allies > 0 and available_player_templates:
            for _ in range(num_allies):
                if not available_player_templates: break
                ally_template = random.choice(available_player_templates)
                ally = CharacterInstance.from_template(ally_template, level=agent_level)
                allies.append(ally)
                logger.info(f"Verbündeter '{ally.name}' (Level {agent_level}) erstellt.")

        self.current_encounter = CombatEncounter(players=[self.agent_character] + allies, opponents=opponents)
        self.current_encounter.start_combat()
        self._update_target_map() 
        logger.info("Kampfbegegnung gestartet.")

        observation = self._get_observation()
        info = self._get_info()
        info['action_mask'] = self._get_action_mask()

        return observation, info

    def _decode_action(self, action_int: int) -> Tuple[Optional[SkillDefinition], Optional[CharacterInstance], List[CharacterInstance]]:
        return self.action_manager.decode_action(
            action_int=action_int,
            agent_skill_map=self.agent_skill_map,
            target_map=self.target_map,
            agent_character=self.agent_character,
            current_encounter=self.current_encounter
        )

    def _get_action_mask(self) -> List[bool]:
        return self.action_manager.get_action_mask(
            agent_character=self.agent_character,
            current_encounter=self.current_encounter,
            agent_skill_map=self.agent_skill_map,
            target_map=self.target_map
        )

    def _calculate_reward(self,
                          combat_result_agent: Optional[Any],
                          action_taken_by_agent: bool,
                          prev_agent_hp: int,
                          max_steps_penalty_applies: bool
                          ) -> float:
        return self.reward_calculator.calculate_reward(
            combat_result_agent=combat_result_agent,
            action_taken_by_agent=action_taken_by_agent,
            prev_agent_hp=prev_agent_hp,
            agent_character=self.agent_character,
            current_encounter=self.current_encounter,
            is_terminated=(self.current_encounter is not None and not self.current_encounter.is_active),
            is_truncated=(self.current_step >= self.max_steps_per_episode),
            max_steps_penalty_applies=max_steps_penalty_applies
        )

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        self.current_step += 1
        terminated = False
        truncated = False
        
        action_taken_by_agent = False
        combat_result_agent = None 
        prev_agent_hp = self.agent_character.hp if self.agent_character else 0

        if self.agent_character and self.agent_character.can_act() and self.current_encounter and self.current_encounter.is_active:
            decoded_skill, decoded_target, decoded_secondaries = self._decode_action(action)

            if decoded_skill and decoded_target:
                is_valid_for_step = True
                if decoded_skill.is_self_effect() and decoded_target != self.agent_character: is_valid_for_step = False
                elif 'base_healing' in decoded_skill.effects and decoded_target in self.current_encounter.opponents: is_valid_for_step = False
                elif ('base_damage' in decoded_skill.effects or decoded_skill.get_base_damage() is not None) and \
                     decoded_target in self.current_encounter.players and decoded_target != self.agent_character: is_valid_for_step = False

                if is_valid_for_step and self.agent_character.has_enough_resource(decoded_skill):
                    combat_action_obj = CombatAction(self.agent_character, decoded_skill, decoded_target, decoded_secondaries)
                    if combat_action_obj.is_valid():
                        combat_result_agent = self.combat_system.execute_action(combat_action_obj)
                        action_taken_by_agent = True
                        logger.debug(f"Agent '{self.agent_character.name}' Aktion: {decoded_skill.name} auf {decoded_target.name if decoded_target else 'N/A'}")
                    else:
                        logger.debug(f"Agent-Aktion {decoded_skill.name} als ungültig eingestuft (combat_action.is_valid()).")
                else:
                    logger.debug(f"Agent-Aktion {decoded_skill.name} nicht ausgeführt (Ressourcen/Zieltyp/Sicherheitscheck ungültig).")
            else:
                logger.debug(f"Agent konnte Aktion {action} nicht sinnvoll dekodieren oder für Ausführung vorbereiten.")
        
        if self.current_encounter and self.current_encounter.is_active:
            if self.current_encounter.check_combat_end():
                terminated = True
        
        if not terminated and self.current_encounter and self.current_encounter.is_active:
            for opponent in list(self.current_encounter.opponents): 
                if terminated: break 
                if opponent.is_alive() and opponent.can_act():
                    opponent_skills = {sid: self.skill_definitions.get(sid) for sid in opponent.skill_ids if sid in self.skill_definitions}
                    player_side_targets = [p for p in self.current_encounter.players if p.is_alive()]
                    
                    if not player_side_targets:
                        terminated = self.current_encounter.check_combat_end()
                        break

                    chosen_skill_opp, primary_target_opp, secondary_targets_opp = self.ai_dispatcher.choose_action(
                        opponent, 
                        [o for o in self.current_encounter.opponents if o != opponent and o.is_alive()],
                        player_side_targets, 
                        opponent_skills
                    )
                    if chosen_skill_opp and primary_target_opp:
                        opp_action_obj = CombatAction(opponent, chosen_skill_opp, primary_target_opp, secondary_targets_opp)
                        if opp_action_obj.is_valid():
                            self.combat_system.execute_action(opp_action_obj)
                            logger.debug(f"Gegner '{opponent.name}' Aktion: {chosen_skill_opp.name} auf {primary_target_opp.name}")
                            if self.current_encounter.check_combat_end():
                                terminated = True
                                break 
        
        apply_max_steps_penalty = False
        if self.current_step >= self.max_steps_per_episode:
            if not terminated: 
                logger.info(f"Maximale Episodenschritte ({self.max_steps_per_episode}) erreicht.")
                truncated = True # Setze truncated hier
                apply_max_steps_penalty = True
        
        reward = self._calculate_reward(
            combat_result_agent=combat_result_agent,
            action_taken_by_agent=action_taken_by_agent,
            prev_agent_hp=prev_agent_hp,
            max_steps_penalty_applies=apply_max_steps_penalty
        )

        if self.current_encounter and self.current_encounter.is_active and not (terminated or truncated):
             self.current_encounter.next_round() 
        
        self._update_target_map() 
        
        observation = self._get_observation()
        info = self._get_info()
        info['action_mask'] = self._get_action_mask()

        if terminated or truncated:
             logger.info(f"Episode beendet. Terminated: {terminated}, Truncated: {truncated}, Reward: {reward:.2f}, Steps: {self.current_step}")
        
        return observation, reward, terminated, truncated, info

    def render(self, mode: str = 'human') -> Optional[List[str]]:
        output_lines = []
        header = f"--- Schritt: {self.current_step}, Runde: {self.current_encounter.round if self.current_encounter else 0} ---"
        output_lines.append(header)

        if self.agent_character:
            agent_str = f"Agent: {self.agent_character.name} | HP: {self.agent_character.hp}/{self.agent_character.get_max_hp()} | Mana: {self.agent_character.mana}"
            effects_str = ", ".join([f"{eid}({eff.duration})" for eid, eff in self.agent_character.active_effects.items()])
            if effects_str: agent_str += f" | Effekte: {effects_str}"
            output_lines.append(agent_str)

        if self.current_encounter:
            output_lines.append("Verbündete:")
            allies_in_encounter = [p for p in self.current_encounter.players if p != self.agent_character]
            if allies_in_encounter:
                for i, ally_char in enumerate(allies_in_encounter):
                    ally_str = f"  {i+1}. {ally_char.name} | HP: {ally_char.hp}/{ally_char.get_max_hp()}"
                    effects_str = ", ".join([f"{eid}({eff.duration})" for eid, eff in ally_char.active_effects.items()])
                    if effects_str: ally_str += f" | Effekte: {effects_str}"
                    output_lines.append(ally_str)
            else:
                output_lines.append("  Keine")

            output_lines.append("Gegner:")
            if self.current_encounter.opponents:
                for i, opp in enumerate(self.current_encounter.opponents):
                    opp_str = f"  {i+1}. {opp.name} | HP: {opp.hp}/{opp.get_max_hp()}"
                    effects_str = ", ".join([f"{eid}({eff.duration})" for eid, eff in opp.active_effects.items()])
                    if effects_str: opp_str += f" | Effekte: {effects_str}"
                    output_lines.append(opp_str)
            else:
                output_lines.append("  Keine")
        
        if mode == 'human':
            print("\n".join(output_lines))
            return None
        elif mode == 'ansi':
            return output_lines
        else: # pragma: no cover
            return super().render(mode=mode)


    def close(self):
        logger.info("RPGEnv wird geschlossen.")
        pass

if __name__ == '__main__':
    logger.info("Teste RPGEnv...")
    
    test_env_config = {
        "max_steps": 30,
        "num_initial_opponents": 1,
        "num_initial_allies": 0, 
        "agent_start_level": 1,
        "reward_settings": {
            "time_penalty_per_step": -0.05,
            "victory_reward": 100.0,
            "defeat_penalty": -100.0,
            "enemy_defeated_reward": 20.0,
            "damage_dealt_factor": 0.2,
            "damage_taken_factor": -0.2, 
            "invalid_action_penalty": -2.0,
            "max_steps_penalty": -20.0,
            "healing_factor": 0.15
        }
    }
    
    env = RPGEnv(config_override=test_env_config)

    try:
        from gymnasium.utils.env_checker import check_env
        logger.info("Gymnasium Env Check (check_env) wird für diese Testrunde übersprungen.")
    except ImportError:
        logger.warning("gymnasium.utils.env_checker nicht gefunden.")
    except Exception as e:
        logger.error(f"Fehler beim Env Check: {e}")

    for episode in range(2): 
        logger.info(f"\n--- START EPISODE {episode + 1} ---")
        obs, info = env.reset()
        terminated = False
        truncated = False
        total_reward_episode = 0.0
        
        env.render(mode='human')
        logger.info(f"Initiale Observation (Teilausschnitt): {obs[:env.observation_manager.character_feature_size if hasattr(env.observation_manager, 'character_feature_size') else 10]}...") 
        logger.info(f"Initiale Action Mask (Summe True): {sum(info.get('action_mask', []))}, Maske: {info.get('action_mask')}")


        for step_num in range(env.max_steps_per_episode + 5): 
            action_mask = info.get('action_mask', [True] * env.action_space.n) 
            valid_actions = [i for i, valid in enumerate(action_mask) if valid]
            
            if not valid_actions:
                logger.error(f"EPISODE {episode+1} SCHRITT {step_num + 1}: Keine gültigen Aktionen! Maske: {action_mask}")
                break 

            action = random.choice(valid_actions)
            
            decoded_skill_obj, decoded_target_obj, _ = env._decode_action(action)
            skill_name = decoded_skill_obj.name if decoded_skill_obj else "N/A"
            target_name = decoded_target_obj.name if decoded_target_obj else "N/A"

            logger.info(f"\nEPISODE {episode+1} SCHRITT {step_num + 1} (Env Step: {env.current_step})")
            logger.info(f"Gewählte Aktion: {action} -> Skill '{skill_name}' auf Ziel '{target_name}' (aus {len(valid_actions)} validen Aktionen)")
            
            obs, reward, terminated, truncated, info = env.step(action)
            total_reward_episode += reward
            
            env.render(mode='human')
            logger.info(f"Belohnung: {reward:.2f} | Gesamtbelohnung Episode: {total_reward_episode:.2f}")
            logger.info(f"Terminated: {terminated}, Truncated: {truncated}")
            logger.info(f"Nächste Action Mask (Summe True): {sum(info.get('action_mask', []))}, Maske: {info.get('action_mask')}")
            
            if terminated or truncated:
                logger.info(f"EPISODE {episode+1} BEENDET nach {step_num + 1} Schritten.")
                break
        logger.info(f"--- ENDE EPISODE {episode + 1} --- Gesamtbelohnung: {total_reward_episode:.2f}")

    env.close()
    logger.info("RPGEnv Test beendet.")