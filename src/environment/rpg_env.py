import gymnasium as gym
from gymnasium import spaces
import numpy as np
import logging
import typing
import random

# Importiere unsere Spiel-Logik und Definitionen
try:
    from src.definitions import loader
    from src.game_logic.entities import CharacterInstance
    from src.game_logic import combat
    from src.ai import ai_dispatcher
    from src.definitions.skill import Skill
    from src.environment.action_manager import ActionManager, PASS_ACTION_INDEX, MAX_AGENT_SKILLS
except ImportError:
    logger_env_fallback = logging.getLogger(__name__ + "_fallback_env") # Eindeutiger Logger-Name
    logger_env_fallback.error("FEHLER: Konnte src-Module nicht laden in rpg_env.py. Fallback-Dummies werden verwendet.")

    # --- KORRIGIERTE DUMMY-KLASSEN ---
    MAX_AGENT_SKILLS_fallback = 4  # Muss hier definiert sein für Dummy ActionManager
    PASS_ACTION_INDEX_fallback = MAX_AGENT_SKILLS_fallback

    class DummySkill: # Umbenannt, um Konflikt mit 'Skill' Type Hint zu vermeiden
        def __init__(self, skill_id="dummy_skill"):
            self.skill_id = skill_id
            self.name = skill_id
        def get_cost_resource(self): return "NONE"
        def get_cost_amount(self): return 0

    class DummyCharacterDefinition:
        def __init__(self, name="DummyDef", skill_ids=None, primary_resource="NONE"):
            self.name = name
            self.skill_ids = skill_ids if skill_ids is not None else []
            self.primary_resource = primary_resource

    class DummyCharacterInstance:
        def __init__(self, definition=None):
            self.definition = definition if definition else DummyCharacterDefinition()
            self.name = self.definition.name
            self.level = 1
            self.current_hp = 10; self.max_hp = 10
            self.current_mana = 10; self.max_mana = 10
            self.current_stamina = 10; self.max_stamina = 10
            self.current_energy = 10; self.max_energy = 10
            self.active_status_effects = []
        def is_alive(self): return True
        def can_act(self): return True
        def has_status_effect(self, effect_id): return False
        def can_afford_cost(self, res, amount): return True
        # Minimal pay_cost, damit combat.execute_attack_action nicht fehlschlägt
        def pay_cost(self, res, amount): return True
        def get_attribute_bonus(self, attr_name): return 0 # Für combat calls
        def tick_status_effects(self): pass
        def take_damage(self, amount): self.current_hp -=amount # Minimal
        def __repr__(self): return f"<DummyChar {self.name}>"


    loader = type('DummyLoader', (), {
        'get_character_class': lambda x: DummyCharacterDefinition(name=x, skill_ids=["dummy_skill1","dummy_skill2"]) if x else None,
        'get_opponent': lambda x: DummyCharacterDefinition(name=x, skill_ids=["dummy_skill_opp"]) if x else None,
        'get_skill': lambda x: DummySkill(x) if x else None
    })()
    combat = type('DummyCombat', (), {'execute_attack_action': lambda a,b,c: {"hit": False, "damage_dealt": 0, "defender_hp_after": 0, "defender_is_alive": True, "log_messages":[] }})()
    ai_dispatcher = type('DummyAIDispatcher', (), {'get_ai_action': lambda a,b: (None,None)})()

    class ActionManager:
        def __init__(self,pi):
            self.action_space=spaces.Discrete(MAX_AGENT_SKILLS_fallback+1)
            self._player_skills = [DummySkill(f"dummy_s{i}") for i in range(MAX_AGENT_SKILLS_fallback)]
        def get_action_masks(self): return [True]*(MAX_AGENT_SKILLS_fallback+1)
        def get_skill_for_action(self,idx): return self._player_skills[idx] if 0 <= idx < MAX_AGENT_SKILLS_fallback else None

    # Überschreibe die globalen Konstanten nur im Fallback-Fall, wenn sie nicht aus dem try-Block kommen
    if 'MAX_AGENT_SKILLS' not in globals(): MAX_AGENT_SKILLS = MAX_AGENT_SKILLS_fallback
    if 'PASS_ACTION_INDEX' not in globals(): PASS_ACTION_INDEX = PASS_ACTION_INDEX_fallback
    # Skill wird im try-Block importiert. Wenn das fehlschlägt, haben wir DummySkill.

logger = logging.getLogger(__name__)

OBS_SPACE_DIMS = 3 + 1 + MAX_AGENT_SKILLS + 2

class RPGEnv(gym.Env):
    metadata = {'render_modes': ['human', 'ansi'], 'render_fps': 4}
    def __init__(self, render_mode: typing.Optional[str] = None, player_class_id: str = "krieger", opponent_id: str = "goblin_lv1", max_expected_level: int = 20):
        super().__init__(); self.player_class_id = player_class_id; self.opponent_id = opponent_id; self.render_mode = render_mode
        self.max_expected_level = float(max_expected_level); self.player: typing.Optional[CharacterInstance] = None; self.opponent: typing.Optional[CharacterInstance] = None
        self.current_round: int = 0; self.max_rounds: int = 100; self.action_manager: typing.Optional[ActionManager] = None
        # Erstelle ActionManager mit einer temporären, aber vollständigeren Dummy-Instanz oder echter Instanz
        try:
            temp_player_def = loader.get_character_class(self.player_class_id)
            if not temp_player_def : raise RuntimeError(f"Spielerdefinition '{self.player_class_id}' für Env-Init nicht geladen.")
            # Verwende die echte CharacterInstance-Klasse, wenn sie verfügbar ist
            from src.game_logic.entities import CharacterInstance as RealCharacterInstance
            temp_player_inst = RealCharacterInstance(temp_player_def)
        except (RuntimeError, ImportError): # Fallback auf DummyCharacterInstance falls nötig
            logger_env_fallback.warning("Verwende DummyCharacterInstance für temporäre Spielerinstanz im Env-Konstruktor.")
            temp_player_inst = DummyCharacterInstance(DummyCharacterDefinition(name=player_class_id, skill_ids=["s1","s2","s3","s4"]))

        self.action_manager = ActionManager(temp_player_inst)
        self.action_space = self.action_manager.action_space
        self.observation_space = spaces.Box(low=0, high=1, shape=(OBS_SPACE_DIMS,), dtype=np.float32)
        logger.info(f"RPGEnv initialisiert. Action Space: {self.action_space}, Observation Space: {self.observation_space}")

    def _update_player_skills_in_action_manager(self): # Umbenannt für Klarheit
        """Aktualisiert die Skills im ActionManager basierend auf der aktuellen Spielerinstanz."""
        if self.player and self.action_manager:
            # Der ActionManager braucht die Spielerinstanz, um seine internen Skills zu aktualisieren
            # Dies ist etwas umständlich. Besser wäre, der AM nimmt die Def und erstellt Skills selbst.
            # Oder die RPGEnv übergibt die Skill-Objekte.
            # Für jetzt: ActionManager aktualisiert sich selbst basierend auf der PlayerInstance
            self.action_manager.player_instance = self.player # Stelle sicher, dass AM die aktuelle Instanz hat
            self.action_manager._update_player_skills() # Private Methode des AM aufrufen
        elif self.action_manager: # Player ist None, aber AM existiert
             self.action_manager._player_skills = [None] * MAX_AGENT_SKILLS


    def _get_observation(self) -> np.ndarray:
        if self.player is None or self.opponent is None or self.action_manager is None:
            return np.zeros(self.observation_space.shape, dtype=self.observation_space.dtype)
        obs_list = []
        obs_list.append(self.player.current_hp / self.player.max_hp if self.player.max_hp > 0 else 0.0)
        primary_res_current, primary_res_max = 0.0, 0.0
        # Prüfe, ob self.player.definition existiert und das Attribut hat
        player_def = getattr(self.player, 'definition', None)
        if player_def and hasattr(player_def, 'primary_resource'):
            res_type = player_def.primary_resource
            if res_type == "MANA" and self.player.max_mana > 0: primary_res_current,primary_res_max = self.player.current_mana,self.player.max_mana
            elif res_type == "STAMINA" and self.player.max_stamina > 0: primary_res_current,primary_res_max = self.player.current_stamina,self.player.max_stamina
            elif res_type == "ENERGY" and self.player.max_energy > 0: primary_res_current,primary_res_max = self.player.current_energy,self.player.max_energy
        obs_list.append(primary_res_current / primary_res_max if primary_res_max > 0 else 0.0)
        obs_list.append(float(self.player.level) / self.max_expected_level)
        obs_list.append(self.opponent.current_hp / self.opponent.max_hp if self.opponent.max_hp > 0 else 0.0)
        for i in range(MAX_AGENT_SKILLS):
            skill = self.action_manager._player_skills[i] # Greife auf die Skills im AM zu
            usable = 0.0
            if skill and hasattr(self.player, 'can_afford_cost') and self.player.can_afford_cost(skill.get_cost_resource(), skill.get_cost_amount()):
                usable = 1.0
            obs_list.append(usable)
        obs_list.append(1.0 if hasattr(self.player, 'has_status_effect') and self.player.has_status_effect("STUNNED") else 0.0)
        obs_list.append(1.0 if hasattr(self.opponent, 'has_status_effect') and self.opponent.has_status_effect("STUNNED") else 0.0)
        return np.array(obs_list, dtype=np.float32)

    def action_masks(self) -> typing.List[bool]:
        if self.action_manager: return self.action_manager.get_action_masks()
        return [False] * TOTAL_ACTIONS

    def _get_info(self) -> dict: return {"player_hp": self.player.current_hp if self.player else -1, "opponent_hp": self.opponent.current_hp if self.opponent else -1, "round": self.current_round }

    def reset(self, seed: typing.Optional[int] = None, options: typing.Optional[dict] = None) -> typing.Tuple[np.ndarray, dict]:
        super().reset(seed=seed); logger.info("Umgebung wird zurückgesetzt.")
        # Verwende die echten Klassen, wenn verfügbar
        try: from src.game_logic.entities import CharacterInstance as RealCharacterInstance
        except ImportError: RealCharacterInstance = DummyCharacterInstance

        player_def = loader.get_character_class(self.player_class_id)
        opponent_def = loader.get_opponent(self.opponent_id)
        if not player_def or not opponent_def: raise RuntimeError("Fehler beim Laden der Definitionen.")
        self.player = RealCharacterInstance(player_def)
        self.opponent = RealCharacterInstance(opponent_def)
        self.action_manager = ActionManager(self.player) # AM mit *echter* Spielerinstanz
        self.action_space = self.action_manager.action_space # Action Space vom AM holen
        self.current_round = 0; logger.info(f"Reset: Spieler '{self.player.name}', Gegner '{self.opponent.name}'")
        return self._get_observation(), self._get_info()

    def step(self, action: int) -> typing.Tuple[np.ndarray, float, bool, bool, dict]:
        if self.player is None or self.opponent is None or self.action_manager is None: raise RuntimeError("Umgebung nicht initialisiert.")
        self.current_round += 1; logger.info(f"\n--- Runde {self.current_round} (RL Step) ---")
        logger.info(f"Spieler: {self.player} | Gegner: {self.opponent}"); logger.info(f"Agent wählt Aktion: {action}")
        terminated, truncated, reward, player_action_description = False, False, 0.0, "Nichts getan"
        current_action_masks = self.action_masks()
        if not current_action_masks[action]: reward -= 2.0; logger.warning(f"Agent wählte ungültige Aktion {action}."); player_action_description = f"Ungültige Aktion {action}"
        elif self.player.is_alive() and self.player.can_act():
            skill_to_use = self.action_manager.get_skill_for_action(action)
            if action == PASS_ACTION_INDEX or (skill_to_use is None and action == PASS_ACTION_INDEX) : player_action_description = "Passen"; logger.info(f"Spieler passt."); reward -= 0.1 # Passen ist eine gültige Aktion
            elif skill_to_use:
                player_action_description = f"Skill '{skill_to_use.name}'"
                logger.info(f"Spieler führt {player_action_description} aus.")
                attack_result = combat.execute_attack_action(self.player, self.opponent, skill_to_use)
                if attack_result["hit"]: reward += float(attack_result["damage_dealt"]) * 0.1
                if not self.opponent.is_alive(): reward += 10.0; terminated = True; logger.info("Gegner besiegt!")
            else: player_action_description = f"Fehler Aktion {action}"; logger.error(f"Agent wählte Aktion {action} ohne Skill."); reward -= 1.0
        elif self.player.is_alive(): player_action_description = "Kann nicht handeln"; logger.info(f"Spieler {player_action_description}.")

        if not terminated and self.opponent.is_alive() and self.opponent.can_act():
            logger.info(f"Gegner ({self.opponent.name}) ist am Zug."); opponent_skill_id, target = ai_dispatcher.get_ai_action(self.opponent, [self.player])
            if opponent_skill_id and target: opponent_skill = loader.get_skill(opponent_skill_id)
                if opponent_skill: logger.info(f"Gegner führt Skill '{opponent_skill.name}' aus."); opponent_attack_result = combat.execute_attack_action(self.opponent, self.player, opponent_skill)
                    if opponent_attack_result["hit"]: reward -= float(opponent_attack_result["damage_dealt"]) * 0.15
                    if not self.player.is_alive(): reward -= 10.0; terminated = True; logger.info("Spieler besiegt!")
        elif self.opponent.is_alive(): logger.info(f"Gegner ({self.opponent.name}) kann nicht handeln.")

        if self.player.is_alive(): self.player.tick_status_effects()
        if not terminated and not self.player.is_alive(): reward -= 10.0; terminated = True; logger.info("Spieler durch eigene Effekte besiegt!")
        if self.opponent.is_alive(): self.opponent.tick_status_effects()
        if not terminated and not self.opponent.is_alive(): reward += 10.0; terminated = True; logger.info("Gegner durch eigene Effekte besiegt!")

        if not terminated and self.current_round >= self.max_rounds: logger.info(f"Max Runden erreicht."); truncated = True; reward -= 5.0
        observation = self._get_observation(); info = self._get_info(); info["player_action"] = player_action_description
        logger.info(f"Runde {self.current_round} Ende. Reward: {reward:.2f}, Terminated: {terminated}, Truncated: {truncated}")
        return observation, reward, terminated, truncated, info

    def render(self):
        if self.render_mode=='human' or self.render_mode=='ansi':
            if self.player and self.opponent: output=(f"\n--- Runde {self.current_round} ---\nSpieler: {self.player}\nGegner: {self.opponent}\n{'-'*20}\n");
                if self.render_mode=='human': print(output); return None
                elif self.render_mode=='ansi': return output
        return None
    def close(self): logger.info("RPGEnv wird geschlossen.")

if __name__ == '__main__':
    try:
        import sys; from pathlib import Path; project_dir = Path(__file__).resolve().parent.parent.parent
        if str(project_dir) not in sys.path: sys.path.insert(0, str(project_dir))
        from src.utils.logging_setup import setup_logging; setup_logging()
    except ImportError: print("FEHLER: Logging-Setup für rpg_env.py Test nicht gefunden.")
    print("\n--- Test der RPGEnv mit ActionManager ---"); env = RPGEnv(render_mode='human', player_class_id="krieger", opponent_id="goblin_lv1")
    from gymnasium.utils.env_checker import check_env
    try: print("\nPrüfe Umgebung mit Gymnasium env_checker..."); check_env(env, warn=True, skip_render_check=True); print("Env Check (Basis) bestanden.")
    except Exception as e: print(f"FEHLER beim Env Check: {e}")
    print("\nTeste reset():"); obs, info = env.reset(); print(f"  Observation nach Reset (Shape {obs.shape}): {obs}"); print(f"  Info nach Reset: {info}"); assert obs.shape == env.observation_space.shape
    print("\nTeste einige Steps mit Action Masks:")
    for i in range(10):
        action_mask = env.action_masks(); print(f"\n-- Step {i+1} --"); print(f"  Player: {env.player}"); print(f"  Verfügbare Aktionen (Maske): {action_mask}")
        valid_actions = [idx for idx, v in enumerate(action_mask) if v]
        if not valid_actions: print("  Keine gültigen Aktionen für Spieler!"); break
        action_to_take = random.choice(valid_actions); print(f"  Wähle Aktion {action_to_take} (aus {valid_actions})")
        obs, reward, terminated, truncated, info = env.step(action_to_take); env.render()
        print(f"  Observation (Shape {obs.shape}): {obs}"); print(f"  Reward: {reward}"); print(f"  Terminated: {terminated}, Truncated: {truncated}"); print(f"  Info: {info}")
        if terminated or truncated: print("Episode beendet."); break
    env.close(); print("\nRPGEnv Test abgeschlossen.")
