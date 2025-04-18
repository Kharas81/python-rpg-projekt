# -*- coding: utf-8 -*-
# Generated/Overwritten on: 2025-04-15 18:06:00 # Zeitpunkt aktualisiert
# rpg_env.py
# V22: Added 'is_success' key to info dict in step() method for Monitor compatibility.

print("--- Loading rpg_env.py (V22 - Added is_success) ---")

import gymnasium as gym
from gymnasium import spaces
import numpy as np
import random, math, os, traceback
from collections import defaultdict
from typing import Optional, Dict, List, Tuple, Any, Union, Set

# Importiere Logik und Definitionen
try:
    from rpg_game_logic import Skill, Character
    _RPG_LOGIC_IMPORTED_SUCCESSFULLY = True
    # Stelle sicher, dass die aktuellsten Definitionen geladen werden
    # (z.B. V15 oder neuer, je nachdem, was im Projekt aktiv ist)
    from rpg_definitions import SKILL_PARAMS as ALL_SKILL_DEFINITIONS
    from rpg_definitions import ALL_BUFFS_DEBUFFS_NAMES, CHAR_PARAMS
    from rpg_definitions import MAX_BUFF_DURATION, MAX_STACKS
    from rpg_definitions import SCHURKEN_AUSWEICHEN_BUFF_NAME
except ImportError as e:
    _RPG_LOGIC_IMPORTED_SUCCESSFULLY = False
    print(f"\n--- !!! IMPORT ERROR IN rpg_env.py !!! ---"); traceback.print_exc()
    class Skill: pass
    class Character: pass
    ALL_SKILL_DEFINITIONS = {}; ALL_BUFFS_DEBUFFS_NAMES = []; CHAR_PARAMS = {}
    MAX_BUFF_DURATION = 10; MAX_STACKS = 1; SCHURKEN_AUSWEICHEN_BUFF_NAME = "Ausweichen verbessern"
except Exception as e:
     _RPG_LOGIC_IMPORTED_SUCCESSFULLY = False
     print(f"\n--- !!! OTHER IMPORT ERROR IN rpg_env.py !!! ---"); traceback.print_exc()
     class Skill: pass
     class Character: pass
     ALL_SKILL_DEFINITIONS = {}; ALL_BUFFS_DEBUFFS_NAMES = []; CHAR_PARAMS = {}
     MAX_BUFF_DURATION = 10; MAX_STACKS = 1; SCHURKEN_AUSWEICHEN_BUFF_NAME = "Ausweichen verbessern"


# Import game configuration constants
try: from rpg_config import MAX_TURNS
except ImportError: MAX_TURNS = 100

# Define the main RL environment class
class RPGEnv(gym.Env):
    """ Custom Reinforcement Learning Environment for the RPG. """
    metadata = {'render_modes': ['human', 'ansi'], 'render_fps': 4}
    PASS_ACTION_INDEX_OFFSET, BASIC_ATTACK_ACTION_INDEX_OFFSET = 0, 1
    ENEMY_BASIC_ATTACK_INDICATOR = "ENEMY_BASIC_ATTACK" # Special string indicator

    # --- Reward/Penalty Constants (Unchanged from V21) ---
    DAMAGE_REWARD_FACTOR=2.0; LEVEL_UP_REWARD=3.0; BASE_XP_PER_ENEMY_LEVEL=25
    XP_LEVEL_DIFFERENCE_MULTIPLIER=0.25; MAX_EXPECTED_LEVEL=50; BASIC_ATTACK_PENALTY=-0.5 # Hero BA Penalty
    ACTIVE_BUFF_REWARD=0.1; DEBUFF_APPLIED_REWARD=0.2; INVALID_SKILL_PENALTY=-1.0
    PASS_PENALTY=-0.5; TIME_PENALTY=-0.01; TIMEOUT_PENALTY=-10.0; WIN_REWARD=15.0
    LOSS_PENALTY=-10.0; WIN_HP_REWARD_FACTOR=5.0; SKILL_SUCCESS_REWARD=0.1
    BASE_ATTACK_USAGE_REWARD=0.01; INVALID_ACTION_PENALTY=-0.1
    UTILITY_BUFFS_TO_REWARD: Set[str] = {"Segnen", "Regeneration", SCHURKEN_AUSWEICHEN_BUFF_NAME}
    DEBUFFS_TO_REWARD: Set[str] = {"Schwächen", "Vergiften"}
    # -------------------------------------------

    def __init__(self,
                 char_param_definitions: dict = CHAR_PARAMS,
                 all_buffs_debuffs_names: List[str] = ALL_BUFFS_DEBUFFS_NAMES,
                 max_buff_duration: int = MAX_BUFF_DURATION,
                 max_stacks: int = MAX_STACKS,
                 render_mode: Optional[str] = None):
        super().__init__()
        # --- (Initialization largely unchanged from V21) ---
        if not isinstance(char_param_definitions, dict) or not char_param_definitions: raise ValueError("char_param_definitions fehlt oder ist leer.")
        self.char_param_definitions = char_param_definitions
        try:
            if not isinstance(Skill, type): raise TypeError(f"Imported 'Skill' is not a class (Type: {type(Skill)}). Import failed?")
            self.initialized_skills = {name: Skill(**params) for name, params in ALL_SKILL_DEFINITIONS.items()}
        except Exception as ex: print(f"FEHLER RPGEnv __init__: {ex}"); traceback.print_exc(); raise ex
        self.all_skill_objects_list: List[Skill] = list(self.initialized_skills.values()); self.all_skill_names: List[str] = list(self.initialized_skills.keys())
        self._num_skills: int = len(self.all_skill_objects_list)
        self.buff_list_for_obs: List[str] = all_buffs_debuffs_names; self.max_buff_duration: int = max(1, max_buff_duration); self.max_stacks: int = max(1, max_stacks)
        self._pass_action_idx: int = self._num_skills + self.PASS_ACTION_INDEX_OFFSET; self._basic_attack_idx: int = self._num_skills + self.BASIC_ATTACK_ACTION_INDEX_OFFSET
        n_actions: int = self._num_skills + 2; self.action_space = spaces.Discrete(n_actions)
        try: self.action_to_name_map: Dict[int, str] = {i: s.name for i, s in enumerate(self.all_skill_objects_list)}
        except Exception as e: print(f"FEHLER action_map: {e}"); self.action_to_name_map = {i: f"Skill_{i}" for i in range(self._num_skills)}
        self.action_to_name_map[self._pass_action_idx] = "Passen"; self.action_to_name_map[self._basic_attack_idx] = "Basis-Angriff" # Hero Basic Attack
        num_res_perc: int = 8; num_cd_perc: int = self._num_skills; num_buff_features: int = len(self.buff_list_for_obs) * 4; num_level_xp_features: int = 2
        obs_size: int = num_res_perc + num_cd_perc + num_buff_features + num_level_xp_features; obs_size = max(1, obs_size)
        self.observation_space = spaces.Box(low=0.0, high=1.0, shape=(obs_size,), dtype=np.float32)
        self.hero: Optional[Character] = None; self.enemy: Optional[Character] = None; self.turn_count: int = 0; self.hero_level_at_reset: int = 1
        self._fixed_class_for_reset: Optional[str] = None; self._fixed_opponent_for_reset: Optional[str] = None
        self._last_reward_components: Dict[str, float] = {}; self.render_mode = render_mode

        print(f"RPGEnv Instanz erstellt (V22 - Added is_success): ActionSpace={n_actions}, ObsSpace={obs_size}")

    # --- set_fixed_class, set_fixed_opponent, _create_character unchanged ---
    def set_fixed_class(self, class_name: Optional[str]):
        if class_name is None or class_name in self.char_param_definitions: self._fixed_class_for_reset = class_name
        else: print(f"WARNUNG (set_fixed_class): Klasse/Typ '{class_name}' nicht gefunden."); self._fixed_class_for_reset = None

    def set_fixed_opponent(self, opponent_type: Optional[str]):
        if opponent_type is None or opponent_type in self.char_param_definitions: self._fixed_opponent_for_reset = opponent_type
        else: print(f"WARNUNG (set_fixed_opponent): Gegnertyp '{opponent_type}' nicht gefunden."); self._fixed_opponent_for_reset = None

    def _create_character(self, char_type: str, level: int, is_hero: bool) -> Character:
        if char_type not in self.char_param_definitions: raise ValueError(f"Definition für Typ '{char_type}' nicht gefunden.")
        if not _RPG_LOGIC_IMPORTED_SUCCESSFULLY or not hasattr(Character, 'get_stat'): raise TypeError("Originalklasse Character nicht importiert.")
        return Character(name=f"{char_type}_{'Hero' if is_hero else f'L{level}_{random.randint(100,999)}'}", class_name=char_type, level=level, char_definitions=self.char_param_definitions, skill_definitions=self.initialized_skills)

    # --- reset unchanged from V21 ---
    def reset(self, seed: Optional[int] = None, options: Optional[dict] = None) -> Tuple[np.ndarray, dict]:
        super().reset(seed=seed)
        self.turn_count = 0; self._last_reward_components = {}
        hero_classes = ["Krieger", "Magier", "Schurke", "Kleriker"]
        # Stelle sicher, dass diese Liste aktuell ist (z.B. V15 Definitionen)
        ENEMY_TYPES = list(set(k for k in self.char_param_definitions if k not in hero_classes))
        if not ENEMY_TYPES:
             print("WARNUNG reset: Keine Gegnertypen in char_param_definitions gefunden! Verwende Fallback-Liste.")
             ENEMY_TYPES = ["Goblin", "Skelett", "Ork", "Goblin Krieger", "Goblin Schamane", "Ork Berserker", "Skelett Magier"]

        hero_class_name = self._fixed_class_for_reset or random.choice(hero_classes)
        if hero_class_name not in hero_classes: hero_class_name = random.choice(hero_classes)

        if self._fixed_opponent_for_reset:
            enemy_type_name = self._fixed_opponent_for_reset
            if enemy_type_name not in ENEMY_TYPES or enemy_type_name not in self.char_param_definitions:
                 print(f"WARNUNG reset: Fixed opponent '{enemy_type_name}' not in ENEMY_TYPES list or definitions! Choosing random enemy.")
                 enemy_type_name = random.choice([e for e in ENEMY_TYPES if e in self.char_param_definitions]) # Wähle nur existierenden Gegner
                 if not enemy_type_name: raise ValueError("Keine gültigen Gegnertypen zum Auswählen im Reset gefunden!")
        else:
            valid_enemies = [e for e in ENEMY_TYPES if e in self.char_param_definitions]
            if not valid_enemies: raise ValueError("ENEMY_TYPES list contains no valid opponents defined in CHAR_PARAMS!")
            enemy_type_name = random.choice(valid_enemies)

        hero_level = 1; self.hero_level_at_reset = hero_level
        level_difference = random.choice([-1, 0, 1]); enemy_level = max(1, hero_level + level_difference)
        try:
            self.hero = self._create_character(hero_class_name, hero_level, True)
            self.enemy = self._create_character(enemy_type_name, enemy_level, False)
            if hasattr(self.enemy, '_xp_granted'): delattr(self.enemy, '_xp_granted')
        except Exception as e:
            print(f"FATALER FEHLER reset(): {e}"); traceback.print_exc(); self.hero, self.enemy = None, None
            observation = np.zeros(self.observation_space.shape, dtype=self.observation_space.dtype); info = {"error": f"Charaktererstellung fehlgeschlagen: {e}", "reward_components": {}}; return observation, info
        observation = self._get_observation(); info = self._get_info(); info['reward_components'] = {}; return observation, info

    # --- UPDATED STEP METHOD (V22 - Added is_success) ---
    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, dict]:
        """ Executes one time step. Includes enemy action name and handles enemy basic attack. """
        self.turn_count += 1
        terminated: bool = False; truncated: bool = False
        rewards: Dict[str, float] = defaultdict(float)
        fallback_obs = np.zeros(self.observation_space.shape, dtype=self.observation_space.dtype)
        # Standardwert für info, falls früh zurückgekehrt wird
        info = {"error": "Env not init.", "is_success": False, "reward_components": {}, "enemy_action_name": "N/A"}

        if not self.hero or not self.enemy: return fallback_obs, 0.0, True, False, info # Frühzeitiger Return mit Standard-Info

        if self.hero.is_dead() or self.enemy.is_dead():
             terminated = True
             # Hole Basis-Info und aktualisiere sie für den Endzustand
             info = self._get_info() # Holt Basis-Infos wie turn, hp etc.
             info['reward_components'] = {} # Keine neuen Rewards in diesem Schritt
             info["enemy_action_name"] = "N/A" # Keine Gegneraktion möglich
             # Füge is_success hinzu, basierend auf dem Endzustand
             hero_won_episode = terminated and self.hero and not self.hero.is_dead() and self.enemy and self.enemy.is_dead()
             info['is_success'] = hero_won_episode
             return self._get_observation(), 0.0, terminated, truncated, info

        # --- Regulärer Schritt beginnt ---
        enemy_hp_before = self.enemy.current_hp; level_before = self.hero.level
        if not self.action_space.contains(action): action=self._pass_action_idx; rewards['Ungültige Aktion'] += self.INVALID_ACTION_PENALTY
        action_name=self.action_to_name_map.get(action,"Unbekannt"); skill_used_successfully = False; applied_debuff = False; skill_object_used = None

        # --- Hero's Action (Unchanged from V21) ---
        if action==self._pass_action_idx: rewards['Passen'] += self.PASS_PENALTY
        elif action==self._basic_attack_idx:
            rewards['Basis-Angriff Nutzung'] += self.BASE_ATTACK_USAGE_REWARD; rewards['Basis-Angriff Malus'] += self.BASIC_ATTACK_PENALTY # Hero BA Penalty
            target=self.enemy; attacker_stat=self.hero.get_stat('angriff'); defender_stat=target.get_stat('verteidigung'); damage=max(1, math.ceil(attacker_stat*0.6-defender_stat)); target.take_damage(damage);
        elif action<self._num_skills:
             if not self.all_skill_objects_list: rewards['Skill Nutzung (Fehler)'] += self.INVALID_SKILL_PENALTY
             else:
                 if action < len(self.all_skill_objects_list):
                     skill=self.all_skill_objects_list[action]; skill_object_used = skill
                     if self.hero.can_use_skill(skill):
                         is_debuff_to_reward = skill.effect_type == 'debuff' and skill.target_type == 'enemy' and skill.name in self.DEBUFFS_TO_REWARD
                         target=self.enemy if skill.target_type=="enemy" else self.hero; self.hero.use_skill(skill,target);
                         rewards['Skill Nutzung (Erfolg)'] += self.SKILL_SUCCESS_REWARD; skill_used_successfully = True
                         if is_debuff_to_reward: applied_debuff = True
                     else: rewards['Skill Nutzung (Fehler)'] += self.INVALID_SKILL_PENALTY
                 else: rewards['Skill Nutzung (Fehler)'] += self.INVALID_SKILL_PENALTY

        # --- Calculate Rewards based on Hero's Action (Unchanged from V21) ---
        if applied_debuff: rewards['Debuff Angewendet Bonus'] += self.DEBUFF_APPLIED_REWARD
        damage_dealt=max(0,enemy_hp_before-self.enemy.current_hp);
        if damage_dealt>0 and self.enemy.max_hp>0: rewards['Schaden verursacht Bonus']+=(damage_dealt/self.enemy.max_hp)*self.DAMAGE_REWARD_FACTOR

        # --- Hero's Post-Action Phase (Unchanged from V21) ---
        if not self.hero.is_dead():
            self.hero.apply_and_tick_effects();
            for effect_name in self.hero.active_effects:
                if effect_name in self.UTILITY_BUFFS_TO_REWARD: rewards['Aktiver Buff Bonus'] += self.ACTIVE_BUFF_REWARD
            terminated = terminated or self.hero.is_dead() # Prüfe, ob Held durch Effekte stirbt
        else: terminated = True # Held war schon tot oder starb durch Aktion

        # --- Check for Enemy Defeat & Grant XP (Unchanged from V21) ---
        enemy_defeated = self.enemy.is_dead(); terminated = terminated or enemy_defeated
        if enemy_defeated and not getattr(self.enemy,'_xp_granted',False):
             level_delta=self.enemy.level-self.hero_level_at_reset; xp_multiplier=max(0.1,1.0+level_delta*self.XP_LEVEL_DIFFERENCE_MULTIPLIER)
             base_xp=self.BASE_XP_PER_ENEMY_LEVEL*self.enemy.level; xp_gain=math.ceil(base_xp*xp_multiplier)
             if self.hero: self.hero.gain_xp(xp_gain); setattr(self.enemy,'_xp_granted',True);
             if self.hero.level>level_before: rewards['Level Up Bonus']+=self.LEVEL_UP_REWARD*(self.hero.level-level_before)

        # --- Enemy's Action (Unchanged from V21) ---
        enemy_action_name = "N/A" # Default
        if not terminated and not self.enemy.is_dead(): # Nur wenn Kampf noch läuft
             enemy_action_result = self._scripted_enemy_ai()
             if isinstance(enemy_action_result, Skill):
                 enemy_action_name = enemy_action_result.name
                 self.enemy.use_skill(enemy_action_result, self.hero)
                 terminated = terminated or self.hero.is_dead() # Prüfe erneut, ob Held stirbt
             elif enemy_action_result == self.ENEMY_BASIC_ATTACK_INDICATOR:
                 enemy_action_name = "Basis-Angriff (Gegner)"
                 attacker = self.enemy; target = self.hero
                 attacker_stat = attacker.get_stat('angriff')
                 defender_stat = target.get_stat('verteidigung')
                 damage = max(1, math.ceil(attacker_stat * 0.5 - defender_stat * 0.5))
                 target.take_damage(damage)
                 terminated = terminated or self.hero.is_dead() # Prüfe erneut, ob Held stirbt
             else: # Sollte nicht passieren, aber defensiv
                 enemy_action_name = "Passen"

             # --- Enemy Post-Action Phase ---
             if not self.enemy.is_dead(): # Nur wenn Gegner noch lebt
                 self.enemy.apply_and_tick_effects()
                 terminated = terminated or self.enemy.is_dead() # Prüfe, ob Gegner durch Effekte stirbt

        # Final check, Terminal Rewards, Time Penalty, Truncation Check...
        terminated = terminated or self.hero.is_dead() or self.enemy.is_dead() # Finaler Status
        terminal_rewards=self._calculate_terminal_reward(terminated); rewards.update(terminal_rewards)
        rewards['Zeit Malus'] += self.TIME_PENALTY
        if not terminated and self.turn_count>=MAX_TURNS:
            truncated=True;
            rewards['Timeout Malus'] += self.TIMEOUT_PENALTY
            terminated = True # Timeout beendet die Episode auch (terminated=True)

        # Finalize Step...
        total_reward=sum(rewards.values()); self._last_reward_components=dict(rewards)
        observation=self._get_observation()

        # Hole Basis-Info und füge aktuelle Schritt-Infos hinzu
        info=self._get_info()
        info["enemy_action_name"] = enemy_action_name
        info["reward_components"]=self._last_reward_components

        # --- NEU (V22): is_success hinzufügen ---
        # Setze 'is_success' auf True, wenn die Episode terminiert ist UND der Held gewonnen hat.
        hero_won_episode = terminated and self.hero and not self.hero.is_dead() and self.enemy and self.enemy.is_dead()
        info['is_success'] = hero_won_episode
        # --- Ende NEU (V22) ---

        return observation, total_reward, terminated, truncated, info
    # --- END OF UPDATED STEP METHOD ---

    # --- _calculate_terminal_reward unchanged ---
    def _calculate_terminal_reward(self, terminated: bool) -> dict:
        terminal_rewards=defaultdict(float); hero_alive, enemy_alive = False, False
        if self.hero: hero_alive = not self.hero.is_dead()
        if self.enemy: enemy_alive = not self.enemy.is_dead()
        if terminated:
            if not hero_alive: terminal_rewards['Niederlage'] += self.LOSS_PENALTY
            elif not enemy_alive:
                terminal_rewards['Sieg'] += self.WIN_REWARD
                if self.hero and self.hero.max_hp>0: terminal_rewards['Rest-HP Bonus (Sieg)'] += (self.hero.current_hp/self.hero.max_hp) * self.WIN_HP_REWARD_FACTOR
        return dict(terminal_rewards)

    # --- _get_best_damage_skill, _get_heal_skill unchanged ---
    def _get_best_damage_skill(self, character: Character, usable_skills: List[Skill]) -> Optional[Skill]:
        best_skill: Optional[Skill] = None; max_power = -1
        for skill in usable_skills:
            if getattr(skill, 'effect_type', '') == 'damage':
                 power = getattr(skill, 'power', 0); cost = getattr(skill, 'cost', 0)
                 current_power_score = power + (0.1 if cost > 0 else 0)
                 if current_power_score > max_power: max_power = current_power_score; best_skill = skill
        return best_skill

    def _get_heal_skill(self, character: Character, usable_skills: List[Skill]) -> Optional[Skill]:
         for skill in usable_skills:
             if getattr(skill, 'effect_type', '') == 'heal': return skill
         return None

    # --- _scripted_enemy_ai unchanged from V21 ---
    def _scripted_enemy_ai(self) -> Optional[Union[Skill, str]]:
        enemy = self.enemy; hero = self.hero
        if not enemy or enemy.is_dead() or not hero: return None
        if not _RPG_LOGIC_IMPORTED_SUCCESSFULLY or not hasattr(Character, 'can_use_skill'): return self.ENEMY_BASIC_ATTACK_INDICATOR

        usable_skills = [s for s in enemy.skills if enemy.can_use_skill(s)]

        if hasattr(enemy, 'current_hp') and hasattr(enemy, 'max_hp') and enemy.current_hp < enemy.max_hp * 0.3:
            heal_skill = self._get_heal_skill(enemy, usable_skills);
            if heal_skill: return heal_skill

        debuff_skill_to_use: Optional[Skill] = None
        for skill in usable_skills:
            if getattr(skill, 'effect_type', '') == 'debuff' and getattr(skill, 'target_type', '') == 'enemy':
                 if hero and skill.name not in hero.active_effects: debuff_skill_to_use = skill; break
        if debuff_skill_to_use: return debuff_skill_to_use

        buff_skill_to_use: Optional[Skill] = None
        for skill in usable_skills:
           if getattr(skill, 'effect_type', '') == 'buff' and getattr(skill, 'target_type', '') == 'self':
               if skill.name not in enemy.active_effects: buff_skill_to_use = skill; break
        if buff_skill_to_use: return buff_skill_to_use

        damage_skill = self._get_best_damage_skill(enemy, usable_skills);
        if damage_skill: return damage_skill

        other_usable_skills = [s for s in usable_skills if getattr(s, 'effect_type', '') not in ['heal', 'buff', 'debuff']]
        if other_usable_skills: return random.choice(other_usable_skills)

        return self.ENEMY_BASIC_ATTACK_INDICATOR


    # --- _get_observation, _get_info, render, close unchanged from V21 ---
    def _get_observation(self) -> np.ndarray:
        fallback_obs=np.zeros(self.observation_space.shape,dtype=self.observation_space.dtype);
        if not self.hero or not self.enemy: return fallback_obs
        obs_list = []; ratio = lambda c, m: np.clip(c / m, 0.0, 1.0) if m > 0 else 0.0; h, e = self.hero, self.enemy
        obs_list.extend([ratio(h.current_hp,h.max_hp),ratio(h.current_mana,h.max_mana),ratio(h.current_stamina,h.max_stamina),ratio(h.current_energy,h.max_energy),
                         ratio(e.current_hp,e.max_hp),ratio(e.current_mana,e.max_mana),ratio(e.current_stamina,e.max_stamina),ratio(e.current_energy,e.max_energy)])
        if self.all_skill_objects_list:
             for skill in self.all_skill_objects_list: cd_val = h.cooldowns.get(skill.name,0); max_cd = skill.cooldown if skill.cooldown > 0 else 1; obs_list.append(ratio(cd_val, max_cd))
        else: obs_list.extend([0.0] * self._num_skills)
        if self.buff_list_for_obs:
             for buff_name in self.buff_list_for_obs:
                h_eff=h.active_effects.get(buff_name,{}); obs_list.extend([ratio(h_eff.get('duration',0),self.max_buff_duration),ratio(h_eff.get('stacks',0),self.max_stacks)])
                e_eff=e.active_effects.get(buff_name,{}); obs_list.extend([ratio(e_eff.get('duration',0),self.max_buff_duration),ratio(e_eff.get('stacks',0),self.max_stacks)])
        else: obs_list.extend([0.0] * (len(ALL_BUFFS_DEBUFFS_NAMES)*4)) # Verwende importierte Liste für Größe
        xp_next_val = getattr(h, 'xp_to_next_level', 1) # Sicherer Zugriff
        if isinstance(xp_next_val, (int, float)) and xp_next_val <= 0: xp_next_val = 1 # Vermeide Division durch Null
        obs_list.extend([ratio(h.level,self.MAX_EXPECTED_LEVEL),ratio(h.current_xp, xp_next_val)])
        try:
            final_obs=np.array(obs_list,dtype=self.observation_space.dtype);
            # Zusätzlicher Check für korrekte Länge
            if len(final_obs) != self.observation_space.shape[0]:
                 print(f"FEHLER Obs Shape: Erwartet {self.observation_space.shape[0]}, bekommen {len(final_obs)}. Passe an.")
                 # Versuche zu padden/truncaten (einfache Methode)
                 padded_obs=np.zeros(self.observation_space.shape,dtype=self.observation_space.dtype);
                 size_to_copy=min(len(final_obs), self.observation_space.shape[0]);
                 padded_obs[:size_to_copy]=final_obs[:size_to_copy];
                 return padded_obs

        except ValueError as ve:
            print(f"FEHLER np.array Erstellung in _get_observation: {ve}");
            return fallback_obs # Fallback, wenn Array-Erstellung fehlschlägt

        # Shape Check nach erfolgreicher Array-Erstellung
        if final_obs.shape!=self.observation_space.shape:
            print(f"FEHLER Shape nach Array-Erstellung: {final_obs.shape} vs {self.observation_space.shape}");
            # Fallback oder erneutes Padding (sollte durch Längen-Check oben abgedeckt sein)
            return fallback_obs
        return final_obs


    def _get_info(self) -> dict:
        # Diese Funktion holt nur Basis-Infos.
        # Spezifische Schritt-Infos (enemy_action, reward_components, is_success)
        # werden in der step-Methode hinzugefügt.
        h=self.hero; e=self.enemy;
        xp_next = getattr(h, 'xp_to_next_level', 1) if h else 1
        if isinstance(xp_next, (int, float)) and xp_next <= 0: xp_next = "(MAX)"
        current_xp = int(getattr(h, 'current_xp', -1)) if h else -1

        reward_str_parts = [];
        # Verwende _last_reward_components, das in step aktualisiert wird
        for k, v in self._last_reward_components.items():
             if abs(v) > 0.001: reward_str_parts.append(f"{k}:{v:+.2f}")
        reward_str = ", ".join(reward_str_parts) if reward_str_parts else "N/A" # Zeige N/A wenn leer

        info={
            "turn": self.turn_count,
            "hero_class": getattr(h,'class_name','N/A'),
            "hero_level": getattr(h,'level',-1),
            "hero_hp": int(getattr(h,'current_hp',-1)),
            "hero_xp": f"{current_xp}/{xp_next}",
            "hero_res": f"M:{int(getattr(h,'current_mana',0))} S:{int(getattr(h,'current_stamina',0))} E:{int(getattr(h,'current_energy',0))}" if h else "-",
            "enemy_class": getattr(e,'class_name','N/A'),
            "enemy_level": getattr(e,'level',-1),
            "enemy_hp": int(getattr(e,'current_hp',-1)),
            "last_rewards": reward_str # Zeigt Rewards des *letzten* abgeschlossenen Schritts
            }
        return info

    def render(self) -> Optional[str]:
        if self.render_mode=='ansi':
            if self.hero and self.enemy: return f"--- Runde {self.turn_count} ---\nHeld:  {str(self.hero)}\nGegner:{str(self.enemy)}\n"
            else: return "Env not fully initialized."
        return None
    def close(self): pass

print("RL Environment Klasse (RPGEnv) in rpg_env.py geschrieben/überschrieben (V22 - Added is_success).")

