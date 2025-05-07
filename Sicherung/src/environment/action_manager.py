# KORRIGIERTER IMPORT für gymnasium.spaces
from gymnasium import spaces # KORREKT
import logging
import typing

try:
    from src.game_logic.entities import CharacterInstance
    from src.definitions import loader
    from src.definitions.skill import Skill
except ImportError:
    logger_am_fallback = logging.getLogger(__name__ + "_fallback")
    logger_am_fallback.warning("ActionManager: Konnte Module nicht direkt laden.")
    class CharacterInstance:
        def __init__(self, definition=None): self.definition = type('DummyDef', (), {'skill_ids': []})(); self.name="Dummy"
        def can_afford_cost(self, res, amount): return True
    class Skill:
        def __init__(self, skill_id="dummy"): self.skill_id=skill_id; self.name=skill_id
        def get_cost_resource(self): return "NONE"
        def get_cost_amount(self): return 0
    loader = type('DummyLoader', (), {'get_skill': lambda x: Skill(x) if x else None})()

logger = logging.getLogger(__name__)

MAX_AGENT_SKILLS = 4
PASS_ACTION_INDEX = MAX_AGENT_SKILLS
TOTAL_ACTIONS = MAX_AGENT_SKILLS + 1

class ActionManager:
    def __init__(self, player_instance: CharacterInstance):
        self.player_instance = player_instance
        # KORREKTE VERWENDUNG von spaces.Discrete
        self.action_space = spaces.Discrete(TOTAL_ACTIONS)
        self.num_actions = TOTAL_ACTIONS
        self._player_skills: typing.List[typing.Optional[Skill]] = [None] * MAX_AGENT_SKILLS
        self._update_player_skills()
        logger.info(f"ActionManager initialisiert. Action Space: {self.action_space}")
        logger.debug(f"  Player Skills für ActionManager: {[s.name if s else 'None' for s in self._player_skills]}")

    def _update_player_skills(self):
        if self.player_instance and hasattr(self.player_instance, 'definition'):
            skill_ids = self.player_instance.definition.skill_ids
            for i in range(MAX_AGENT_SKILLS):
                self._player_skills[i] = loader.get_skill(skill_ids[i]) if i < len(skill_ids) else None
        else: self._player_skills = [None] * MAX_AGENT_SKILLS
        logger.debug(f"ActionManager: _player_skills aktualisiert: {[s.name if s else 'None' for s in self._player_skills]}")

    def get_action_masks(self) -> typing.List[bool]:
        if not self.player_instance or not self.player_instance.is_alive() or not self.player_instance.can_act():
            return [False] * self.num_actions
        masks = [False] * self.num_actions
        for i in range(MAX_AGENT_SKILLS):
            skill = self._player_skills[i]
            if skill and self.player_instance.can_afford_cost(skill.get_cost_resource(), skill.get_cost_amount()):
                masks[i] = True
        masks[PASS_ACTION_INDEX] = True
        logger.debug(f"ActionManager: Erstellte Action Mask für '{self.player_instance.name}': {masks}")
        return masks

    def get_skill_for_action(self, action_index: int) -> typing.Optional[Skill]:
        if 0 <= action_index < MAX_AGENT_SKILLS: return self._player_skills[action_index]
        elif action_index == PASS_ACTION_INDEX: logger.debug("Aktion ist 'Passen'."); return None
        logger.warning(f"Ungültiger Aktionsindex {action_index} für get_skill_for_action erhalten.")
        return None

# Testblock bleibt gleich
if __name__ == '__main__':
    try:
        import sys; from pathlib import Path
        project_dir = Path(__file__).resolve().parent.parent.parent
        if str(project_dir) not in sys.path: sys.path.insert(0, str(project_dir))
        from src.utils.logging_setup import setup_logging; setup_logging()
        from src.definitions import loader
        from src.game_logic.entities import CharacterInstance
    except ImportError as e: print(f"FEHLER bei Test-Setup in action_manager.py: {e}"); exit(1)
    print("\n--- ActionManager Test ---")
    krieger_def = loader.get_character_class("krieger"); magier_def = loader.get_character_class("magier")
    if not krieger_def or not magier_def: print("FEHLER: Definitionen nicht geladen."); exit(1)
    krieger_inst = CharacterInstance(krieger_def); magier_inst = CharacterInstance(magier_def)
    print(f"\nTest mit Krieger: {krieger_inst.name}"); am_krieger = ActionManager(krieger_inst)
    print(f"  Geladene Skills im AM: {[s.name if s else 'None' for s in am_krieger._player_skills]}")
    mask_krieger1 = am_krieger.get_action_masks(); print(f"  Action Mask (genug Stamina): {mask_krieger1}"); assert mask_krieger1 == [True, True, False, False, True]
    krieger_inst.current_stamina = 10
    mask_krieger2 = am_krieger.get_action_masks(); print(f"  Action Mask (wenig Stamina): {mask_krieger2}"); assert mask_krieger2 == [True, False, False, False, True]
    skill_action0 = am_krieger.get_skill_for_action(0); skill_action1 = am_krieger.get_skill_for_action(1); skill_action_pass = am_krieger.get_skill_for_action(PASS_ACTION_INDEX)
    print(f"  Skill für Aktion 0: {skill_action0.name if skill_action0 else 'None'}"); print(f"  Skill für Aktion 1: {skill_action1.name if skill_action1 else 'None'}"); print(f"  Skill für Aktion Passen ({PASS_ACTION_INDEX}): {skill_action_pass.name if skill_action_pass else 'Passen'}")
    assert skill_action0 is not None and skill_action0.skill_id == "basic_strike_phys"; assert skill_action1 is not None and skill_action1.skill_id == "power_strike"; assert skill_action_pass is None
    print(f"\nTest mit Magier: {magier_inst.name}"); am_magier = ActionManager(magier_inst)
    mask_magier1 = am_magier.get_action_masks(); print(f"  Action Mask (genug Mana): {mask_magier1}"); assert mask_magier1 == [True, True, False, False, True]
    magier_inst.current_mana = 10
    mask_magier2 = am_magier.get_action_masks(); print(f"  Action Mask (wenig Mana): {mask_magier2}"); assert mask_magier2 == [True, False, False, False, True]
    print("\nAlle ActionManager Tests erfolgreich.")
