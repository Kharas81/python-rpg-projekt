import gymnasium as gym
from gymnasium import spaces
import numpy as np
import logging
import typing
import random # Für die Auswahl des Ziels im Dummy-Step

# Importiere unsere Spiel-Logik und Definitionen
try:
    from src.definitions import loader
    from src.game_logic.entities import CharacterInstance
    from src.game_logic import combat
    from src.ai import ai_dispatcher
    from src.definitions.skill import Skill # Für Type Hinting und Zugriff
except ImportError:
    logger_env_fallback = logging.getLogger(__name__)
    logger_env_fallback.error("FEHLER: Konnte src-Module nicht laden in rpg_env.py.")
    # Minimal-Dummies, damit die Klasse zumindest definiert werden kann
    class CharacterInstance: pass; class Skill: pass
    loader = type('DummyLoader', (), {'get_character_class': lambda x: None, 'get_opponent': lambda x: None, 'get_skill': lambda x: None})()
    combat = type('DummyCombat', (), {'execute_attack_action': lambda a,b,c: {}})()
    ai_dispatcher = type('DummyAIDispatcher', (), {'get_ai_action': lambda a,b: (None,None)})()

logger = logging.getLogger(__name__)

MAX_AGENT_SKILLS = 4 # Agent kann die ersten 4 Skills nutzen
TOTAL_ACTIONS = MAX_AGENT_SKILLS + 1 # Skills + 1 Passen-Aktion
PASS_ACTION_INDEX = MAX_AGENT_SKILLS # Index für die Passen-Aktion

# Dimensionen des Observation Space (Beispiel)
# Player (HP, Res, Lvl), Opponent (HP), Skills (4x Usable), Status (P.Stun, O.Stun)
OBS_SPACE_DIMS = 3 + 1 + MAX_AGENT_SKILLS + 2


class RPGEnv(gym.Env):
    metadata = {'render_modes': ['human', 'ansi'], 'render_fps': 4}

    def __init__(self, render_mode: typing.Optional[str] = None,
                 player_class_id: str = "krieger",
                 opponent_id: str = "goblin_lv1",
                 max_expected_level: int = 20): # Für Level-Normalisierung
        super().__init__()

        self.player_class_id = player_class_id
        self.opponent_id = opponent_id
        self.render_mode = render_mode
        self.max_expected_level = float(max_expected_level)

        self.player: typing.Optional[CharacterInstance] = None
        self.opponent: typing.Optional[CharacterInstance] = None
        self.current_round: int = 0
        self.max_rounds: int = 100

        # --- Action Space Definition ---
        # MAX_AGENT_SKILLS für die Skills + 1 für "Passen"
        self.action_space = spaces.Discrete(TOTAL_ACTIONS)

        # --- Observation Space Definition ---
        # Player HP (norm), Player Resource (norm), Player Level (norm)
        # Opponent HP (norm)
        # Skill 0..MAX_AGENT_SKILLS-1 Usable (0 oder 1)
        # Player Stunned (0 oder 1), Opponent Stunned (0 oder 1)
        self.observation_space = spaces.Box(low=0, high=1, shape=(OBS_SPACE_DIMS,), dtype=np.float32)

        # Speichere die Skill-Objekte des Spielers für einfachen Zugriff
        self._player_skills: typing.List[typing.Optional[Skill]] = [None] * MAX_AGENT_SKILLS

        logger.info(f"RPGEnv initialisiert für Spieler '{player_class_id}' vs Gegner '{opponent_id}'.")
        logger.info(f"Action Space: {self.action_space} (0-{MAX_AGENT_SKILLS-1}: Skills, {PASS_ACTION_INDEX}: Passen)")
        logger.info(f"Observation Space: {self.observation_space} (Shape: {OBS_SPACE_DIMS})")

    def _update_player_skills(self):
        """Lädt die ersten MAX_AGENT_SKILLS des Spielers und speichert sie."""
        if self.player:
            skill_ids = self.player.definition.skill_ids
            for i in range(MAX_AGENT_SKILLS):
                if i < len(skill_ids):
                    self._player_skills[i] = loader.get_skill(skill_ids[i])
                else:
                    self._player_skills[i] = None
        else:
            self._player_skills = [None] * MAX_AGENT_SKILLS


    def _get_observation(self) -> np.ndarray:
        if self.player is None or self.opponent is None:
            logger.error("Player oder Opponent nicht initialisiert in _get_observation.")
            return np.zeros(self.observation_space.shape, dtype=self.observation_space.dtype)

        obs_list = []
        # Spieler-Werte
        obs_list.append(self.player.current_hp / self.player.max_hp if self.player.max_hp > 0 else 0.0)
        # Primärressource des Spielers (Beispiel: Mana, falls vorhanden, sonst Stamina etc.)
        # Dies muss robuster werden, wenn Spieler verschiedene Ressourcentypen haben
        # Für den Krieger (Standard) nehmen wir Stamina.
        primary_res_current = 0.0
        primary_res_max = 0.0
        if self.player.definition.primary_resource == "MANA" and self.player.max_mana > 0:
            primary_res_current = self.player.current_mana
            primary_res_max = self.player.max_mana
        elif self.player.definition.primary_resource == "STAMINA" and self.player.max_stamina > 0:
            primary_res_current = self.player.current_stamina
            primary_res_max = self.player.max_stamina
        elif self.player.definition.primary_resource == "ENERGY" and self.player.max_energy > 0:
            primary_res_current = self.player.current_energy
            primary_res_max = self.player.max_energy
        obs_list.append(primary_res_current / primary_res_max if primary_res_max > 0 else 0.0)
        obs_list.append(float(self.player.level) / self.max_expected_level)

        # Gegner-Werte
        obs_list.append(self.opponent.current_hp / self.opponent.max_hp if self.opponent.max_hp > 0 else 0.0)

        # Skill-Nutzbarkeit
        for i in range(MAX_AGENT_SKILLS):
            skill = self._player_skills[i]
            usable = 0.0
            if skill and self.player.can_afford_cost(skill.get_cost_resource(), skill.get_cost_amount()):
                usable = 1.0
            obs_list.append(usable)

        # Status-Effekte (Beispiel: STUNNED)
        obs_list.append(1.0 if self.player.has_status_effect("STUNNED") else 0.0)
        obs_list.append(1.0 if self.opponent.has_status_effect("STUNNED") else 0.0)

        return np.array(obs_list, dtype=np.float32)

    def action_masks(self) -> typing.List[bool]:
        """
        Gibt eine Maske gültiger Aktionen zurück. True für gültig, False für ungültig.
        Die Reihenfolge entspricht dem Action Space: Skill 0..MAX_AGENT_SKILLS-1, dann Passen.
        """
        if self.player is None or not self.player.is_alive() or not self.player.can_act():
            # Wenn Spieler nicht handeln kann, ist nur "Passen" (implizit) eine Option,
            # aber der Agent sollte das nicht aktiv wählen müssen, die Umgebung simuliert es.
            # Für MaskablePPO: Alle Aktionen maskieren, wenn der Spieler nicht handeln kann.
            return [False] * TOTAL_ACTIONS

        masks = [False] * TOTAL_ACTIONS
        for i in range(MAX_AGENT_SKILLS):
            skill = self._player_skills[i]
            if skill and self.player.can_afford_cost(skill.get_cost_resource(), skill.get_cost_amount()):
                masks[i] = True
        masks[PASS_ACTION_INDEX] = True # Passen ist immer eine Option (wenn der Spieler handeln kann)
        return masks

    def _get_info(self) -> dict: # Unverändert
        return {"player_hp": self.player.current_hp if self.player else -1, "opponent_hp": self.opponent.current_hp if self.opponent else -1, "round": self.current_round }

    def reset(self, seed: typing.Optional[int] = None, options: typing.Optional[dict] = None) -> typing.Tuple[np.ndarray, dict]:
        super().reset(seed=seed)
        logger.info("Umgebung wird zurückgesetzt (neue Episode/Kampf).")
        player_def = loader.get_character_class(self.player_class_id)
        opponent_def = loader.get_opponent(self.opponent_id)
        if not player_def or not opponent_def: raise RuntimeError("Fehler beim Laden der Definitionen.")
        self.player = CharacterInstance(player_def)
        self.opponent = CharacterInstance(opponent_def)
        self._update_player_skills() # Lade Spieler-Skills nach Instanziierung
        self.current_round = 0
        logger.info(f"Reset: Spieler '{self.player.name}' (HP {self.player.current_hp}), Gegner '{self.opponent.name}' (HP {self.opponent.current_hp})")
        return self._get_observation(), self._get_info()

    def step(self, action: int) -> typing.Tuple[np.ndarray, float, bool, bool, dict]:
        if self.player is None or self.opponent is None: raise RuntimeError("Umgebung nicht initialisiert.")
        self.current_round += 1
        logger.info(f"\n--- Runde {self.current_round} (RL Step) ---")
        logger.info(f"Spieler: {self.player} | Gegner: {self.opponent}") # Zeigt auch Effekte
        logger.info(f"Agent wählt Aktion: {action}")

        terminated = False; truncated = False; reward = 0.0; player_action_description = "Nichts getan"

        current_action_masks = self.action_masks()
        if not current_action_masks[action]: # Überprüfe, ob die gewählte Aktion gültig war
            logger.warning(f"Agent wählte ungültige Aktion {action} (Maske: {current_action_masks}). Strafe.")
            reward -= 2.0 # Hohe Strafe für Auswahl einer maskierten Aktion
            # Episode nicht unbedingt beenden, aber Agent sollte das lernen
        elif self.player.is_alive() and self.player.can_act():
            if action < MAX_AGENT_SKILLS: # Es ist eine Skill-Aktion
                skill_to_use = self._player_skills[action]
                if skill_to_use: # Sollte durch Maske sichergestellt sein, aber doppelt prüfen
                    player_action_description = f"Skill '{skill_to_use.name}' auf '{self.opponent.name}'"
                    logger.info(f"Spieler ({self.player.name}) führt {player_action_description} aus.")
                    attack_result = combat.execute_attack_action(self.player, self.opponent, skill_to_use)
                    if attack_result["hit"]: reward += float(attack_result["damage_dealt"]) * 0.1
                    if not self.opponent.is_alive(): reward += 10.0; terminated = True; logger.info("Gegner besiegt!")
                else: # Sollte nicht passieren, wenn Maske korrekt ist
                    player_action_description = "Versuchter ungültiger Skill-Slot"
                    logger.error(f"Agent wählte Skill-Slot {action}, der keinen gültigen Skill enthält, trotz Maske."); reward -= 1.0
            elif action == PASS_ACTION_INDEX:
                player_action_description = "Passen"
                logger.info(f"Spieler ({self.player.name}) passt.")
                reward -= 0.1 # Kleine Strafe fürs Passen, um Aktivität zu fördern
        elif self.player.is_alive() and not self.player.can_act():
            player_action_description = "Kann nicht handeln (z.B. STUNNED)"
            logger.info(f"Spieler ({self.player.name}) {player_action_description}.")
        # (Wenn Spieler nicht lebt, passiert hier nichts von Spielerseite)

        # Gegner-Zug (falls noch relevant)
        if not terminated and self.opponent.is_alive() and self.opponent.can_act():
            logger.info(f"Gegner ({self.opponent.name}) ist am Zug.")
            opponent_skill_id, target = ai_dispatcher.get_ai_action(self.opponent, [self.player])
            if opponent_skill_id and target:
                opponent_skill = loader.get_skill(opponent_skill_id)
                if opponent_skill:
                    logger.info(f"Gegner ({self.opponent.name}) führt Skill '{opponent_skill.name}' auf '{self.player.name}' aus.")
                    opponent_attack_result = combat.execute_attack_action(self.opponent, self.player, opponent_skill)
                    if opponent_attack_result["hit"]: reward -= float(opponent_attack_result["damage_dealt"]) * 0.15 # Etwas höhere Strafe für erl. Schaden
                    if not self.player.is_alive(): reward -= 10.0; terminated = True; logger.info("Spieler besiegt!")
            # ... (Rest der Gegnerlogik) ...
        elif self.opponent.is_alive() and not self.opponent.can_act(): logger.info(f"Gegner ({self.opponent.name}) kann nicht handeln.")

        # Effekte ticken lassen & auf Tod durch Effekte prüfen
        if self.player.is_alive(): self.player.tick_status_effects()
        if not terminated and not self.player.is_alive(): reward -= 10.0; terminated = True; logger.info("Spieler durch eigene Effekte besiegt!")
        if self.opponent.is_alive(): self.opponent.tick_status_effects()
        if not terminated and not self.opponent.is_alive(): reward += 10.0; terminated = True; logger.info("Gegner durch eigene Effekte besiegt!")

        if not terminated and self.current_round >= self.max_rounds:
            logger.info(f"Maximalzahl von {self.max_rounds} Runden erreicht."); truncated = True; reward -= 5.0 # Höhere Strafe fürs Zeitlimit

        observation = self._get_observation()
        info = self._get_info()
        info["player_action"] = player_action_description # Zusätzliche Info für Debugging
        logger.info(f"Runde {self.current_round} Ende. Reward: {reward:.2f}, Terminated: {terminated}, Truncated: {truncated}")
        return observation, reward, terminated, truncated, info

    def render(self): # Unverändert
        if self.render_mode == 'human' or self.render_mode == 'ansi':
            if self.player and self.opponent:
                output = (f"\n--- Runde {self.current_round} ---\n"
                          f"Spieler: {self.player}\n" # Nutzt __repr__ von CharacterInstance
                          f"Gegner: {self.opponent}\n{'-'*20}\n")
                if self.render_mode == 'human': print(output); return None
                elif self.render_mode == 'ansi': return output
            else: return "Umgebung nicht initialisiert." if self.render_mode == 'ansi' else None
        return None
    def close(self): logger.info("RPGEnv wird geschlossen.") # Unverändert

# --- Testblock für die Umgebung ---
if __name__ == '__main__':
    try:
        import sys; from pathlib import Path
        project_dir = Path(__file__).resolve().parent.parent.parent
        if str(project_dir) not in sys.path: sys.path.insert(0, str(project_dir))
        from src.utils.logging_setup import setup_logging; setup_logging()
    except ImportError: print("FEHLER: Logging-Setup für rpg_env.py Test nicht gefunden.")

    print("\n--- Test der RPGEnv mit konkreten Spaces ---")
    env = RPGEnv(render_mode='human', player_class_id="krieger", opponent_id="goblin_lv1")

    from gymnasium.utils.env_checker import check_env
    try:
        print("\nPrüfe Umgebung mit Gymnasium env_checker...")
        check_env(env, warn=True, skip_render_check=True)
        print("Env Check (Basis) bestanden (Render Check übersprungen).")
    except Exception as e: print(f"FEHLER beim Env Check: {e}")

    print("\nTeste reset():")
    obs, info = env.reset()
    print(f"  Observation nach Reset (Shape {obs.shape}): {obs}")
    print(f"  Info nach Reset: {info}")
    assert obs.shape == env.observation_space.shape

    print("\nTeste einige Steps mit Action Masks:")
    for i in range(10): # Teste mehr Runden
        action_mask = env.action_masks()
        print(f"\n-- Step {i+1} --")
        print(f"  Verfügbare Aktionen (Maske): {action_mask}")
        # Wähle eine gültige Aktion, falls möglich
        valid_actions = [idx for idx, is_valid in enumerate(action_mask) if is_valid]
        if not valid_actions:
            print("  Keine gültigen Aktionen verfügbar laut Maske (Spieler kann nicht handeln?).")
            # Wenn keine Aktion gültig ist, ist das ein Zustand, den der Agent nicht erreichen sollte,
            # oder die Episode sollte enden. Step wird trotzdem mit einer "Dummy"-Aktion aufgerufen.
            # In einem echten Szenario würde PPO hier nicht hinkommen, wenn Maske korrekt ist.
            # Für den Test nehmen wir einfach die Passen-Aktion, wenn alles andere maskiert ist.
            action_to_take = PASS_ACTION_INDEX if action_mask[PASS_ACTION_INDEX] else 0
        else:
            action_to_take = random.choice(valid_actions)

        print(f"  Wähle Aktion {action_to_take} (aus {valid_actions})")
        obs, reward, terminated, truncated, info = env.step(action_to_take)
        env.render() # Ausgabe des Zustands
        print(f"  Observation (Shape {obs.shape}): {obs}")
        print(f"  Reward: {reward}")
        print(f"  Terminated: {terminated}, Truncated: {truncated}")
        print(f"  Info: {info}")
        if terminated or truncated: print("Episode beendet."); break
    env.close()
    print("\nRPGEnv Test abgeschlossen.")
