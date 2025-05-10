# src/environment/action_manager.py
"""
Verwaltet den Action Space, die Erstellung von Action Masks und das Mapping
von numerischen Aktionen zu konkreten Spielaktionen für die RL-Umgebung.
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from gymnasium import spaces 

if True: 
    from src.environment.state_manager import EnvStateManager
    from src.game_logic.entities import CharacterInstance
    from src.definitions.skill import SkillTemplate

logger = logging.getLogger(__name__)

MAX_SKILLS_ACTION = 6    
MAX_OPPONENTS_ACTION = 3 

class ActionManager:
    def __init__(self, 
                 skill_templates: Dict[str, SkillTemplate], 
                 hero_initial_skill_ids: List[str]): # Die Start-Skills des Helden in fester Reihenfolge
        
        self.skill_templates = skill_templates
        self.hero_action_skill_ids = hero_initial_skill_ids[:MAX_SKILLS_ACTION]
        self.num_skills_in_space = len(self.hero_action_skill_ids)

        self.num_target_options_in_space = 1 + MAX_OPPONENTS_ACTION 

        self.action_space_size = self.num_skills_in_space * self.num_target_options_in_space
        if self.action_space_size == 0: 
            self.action_space_size = 1 
            logger.warning("ActionManager: Action Space Größe ist 0, auf 1 gesetzt. Dies deutet auf ein Problem mit Heldenskills hin.")
        
        self.action_space = spaces.Discrete(self.action_space_size)
        logger.info(f"ActionManager initialisiert. Action Space: {self.action_space} "
                    f"({self.num_skills_in_space} Skills x {self.num_target_options_in_space} Zieloptionen)")

    def get_action_space(self) -> spaces.Discrete:
        return self.action_space

    def get_action_mask(self, state_manager: EnvStateManager) -> List[bool]:
        mask = [False] * self.action_space_size
        hero = state_manager.get_hero()

        if not hero or hero.is_defeated or not hero.can_act:
            # Wenn keine Aktion möglich ist und die Maske leer bleibt, muss step() das handhaben.
            # Oder eine No-Op Aktion (falls definiert an Index 0) könnte hier erlaubt werden.
            # if self.action_space_size > 0: mask[0] = True # Beispiel für No-Op an Index 0
            return mask 

        current_action_id = 0
        for skill_idx in range(self.num_skills_in_space): # Iteriere über die Skills im Action Space
            if skill_idx >= len(self.hero_action_skill_ids): # Sollte nicht passieren, wenn num_skills_in_space korrekt ist
                logger.warning(f"ActionManager: Skill-Index {skill_idx} außerhalb der Grenzen von hero_action_skill_ids.")
                # Fülle restliche Masken für diesen ungültigen Skill-Block mit False
                for _ in range(self.num_target_options_in_space):
                    if current_action_id < self.action_space_size: mask[current_action_id] = False
                    current_action_id += 1
                continue

            skill_id = self.hero_action_skill_ids[skill_idx]
            skill_template = self.skill_templates.get(skill_id)

            if not skill_template or not hero.can_afford_skill(skill_template):
                for _ in range(self.num_target_options_in_space):
                    if current_action_id < self.action_space_size: mask[current_action_id] = False
                    current_action_id += 1
                continue 

            # Skill ist leistbar, jetzt Ziele prüfen
            for target_option_idx in range(self.num_target_options_in_space):
                if current_action_id >= self.action_space_size: # Sicherheitscheck
                    logger.error("ActionManager: current_action_id hat die Action Space Größe überschritten.")
                    break 
                
                actual_target_entity: Optional[CharacterInstance] = None
                is_valid_target_for_this_skill_type = False

                if target_option_idx == 0: # Ziel ist der Held selbst
                    actual_target_entity = hero
                    if skill_template.target_type == "SELF" or skill_template.target_type.startswith("ALLY_"):
                        is_valid_target_for_this_skill_type = True
                else: # Ziel ist ein Gegner-Slot 
                    opponent_slot_idx = target_option_idx - 1 # Konvertiere zu 0-basiertem Index für self.opponents
                    # Zugriff auf state_manager.opponents (Liste fester Größe mit potenziellen None-Werten)
                    if opponent_slot_idx < len(state_manager.opponents) and \
                       state_manager.opponents[opponent_slot_idx] and \
                       not state_manager.opponents[opponent_slot_idx].is_defeated: # Ist der Gegner in diesem Slot lebendig?
                        actual_target_entity = state_manager.opponents[opponent_slot_idx]
                        if skill_template.target_type.startswith("ENEMY_"):
                            is_valid_target_for_this_skill_type = True
                
                if actual_target_entity and is_valid_target_for_this_skill_type:
                    mask[current_action_id] = True
                else:
                    mask[current_action_id] = False
                current_action_id += 1
        
        if not any(mask) and self.action_space_size > 0:
            logger.debug("ActionManager: Nach Maskierung ist keine Aktion gültig. "
                        "Die Umgebung muss einen Zustand ohne gültige Aktionen handhaben können (z.B. Episode beenden).")
            # Erwäge, hier eine Warnung zu loggen, wenn das häufig passiert,
            # da es ein Zeichen für ein Problem im Spieldesign oder in der Maskenlogik sein könnte.
            # Es ist besser, wenn die Umgebung/Agent einen "Passen"-Zug hat.
        return mask

    def get_game_action(self, action_id: int, state_manager: EnvStateManager) -> Optional[Tuple[str, CharacterInstance]]:
        hero = state_manager.get_hero()
        if not hero or action_id < 0 or action_id >= self.action_space_size:
            logger.warning(f"ActionManager: Ungültige action_id ({action_id}) oder kein Held.")
            return None

        skill_idx_in_action_list = action_id // self.num_target_options_in_space
        target_option_idx = action_id % self.num_target_options_in_space

        if skill_idx_in_action_list >= len(self.hero_action_skill_ids):
            logger.warning(f"ActionManager: Berechneter Skill-Index ({skill_idx_in_action_list}) außerhalb der Grenzen für Held '{hero.name}'. "
                           f"Action ID: {action_id}, Verfügbare Skills im Space: {self.hero_action_skill_ids}")
            return None
        
        skill_id_to_use = self.hero_action_skill_ids[skill_idx_in_action_list]
        
        target_instance: Optional[CharacterInstance] = None
        if target_option_idx == 0: 
            target_instance = hero
        else: 
            opponent_slot_idx = target_option_idx - 1
            if opponent_slot_idx < len(state_manager.opponents) and \
               state_manager.opponents[opponent_slot_idx] and \
               not state_manager.opponents[opponent_slot_idx].is_defeated:
                target_instance = state_manager.opponents[opponent_slot_idx]
        
        if not target_instance:
            # Dies sollte idealerweise von der Action Mask verhindert werden.
            # Wenn es hier passiert, war die Maske nicht präzise genug oder der Agent hat eine ungültige Aktion gewählt.
            logger.debug(f"ActionManager: Für Aktion {action_id} (Skill '{skill_id_to_use}', Ziel-Opt {target_option_idx}) kein gültiges lebendes Ziel gefunden im aktuellen Zustand.")
            return None
            
        return skill_id_to_use, target_instance

# ... (if __name__ == '__main__' Block bleibt gleich) ...
if __name__ == '__main__':
    print("--- Teste ActionManager ---")
    try:
        from src.definitions.loader import load_character_templates, load_opponent_templates, load_skill_templates
        from src.game_logic.combat import CombatHandler
        from src.environment.state_manager import EnvStateManager
        import src.utils.logging_setup

        char_temps = load_character_templates()
        opp_temps = load_opponent_templates()
        skill_temps = load_skill_templates()
        combat_hnd = CombatHandler()

        if not char_temps or not opp_temps or not skill_temps:
            raise Exception("Konnte nicht alle Templates für den Test laden.")

        test_hero_id = "krieger" 
        hero_template_for_test = char_temps.get(test_hero_id)
        if not hero_template_for_test: raise Exception(f"Heldentemplate {test_hero_id} nicht gefunden.")
        
        hero_skills_ordered = hero_template_for_test.starting_skills 
        
        action_manager = ActionManager(skill_templates=skill_temps, hero_initial_skill_ids=hero_skills_ordered)
        state_manager = EnvStateManager(
            character_templates=char_temps,
            opponent_templates=opp_temps,
            combat_handler=combat_hnd,
            max_supported_opponents=MAX_OPPONENTS_ACTION 
        )

        print(f"Action Space Definition: {action_manager.get_action_space()}")
        print(f"Erwartete Action Space Größe: {action_manager.action_space_size}")
        print(f"Skills im Action Space: {action_manager.hero_action_skill_ids}")

        opponent_ids_for_test = ["goblin_lv1", "goblin_archer_lv2"] 
        if not state_manager.reset_state(hero_id=test_hero_id, opponent_ids=opponent_ids_for_test):
            print("Fehler beim Reset des StateManagers für den Test.")
        else:
            hero_instance = state_manager.get_hero()
            if not hero_instance: raise Exception("Held nicht erstellt im Test.")

            action_mask = action_manager.get_action_mask(state_manager)
            print(f"\nGenerierte Action Mask (Länge: {len(action_mask)}):")
            valid_action_indices = [i for i, valid in enumerate(action_mask) if valid]
            print(f"Indizes gültiger Aktionen: {valid_action_indices}")

            if valid_action_indices:
                test_action_id = random.choice(valid_action_indices)
                print(f"\nTeste Konvertierung für zufällige gültige Aktion ID: {test_action_id}")
                game_action = action_manager.get_game_action(test_action_id, state_manager)
                if game_action:
                    skill_id, target = game_action
                    print(f"  -> Skill ID: '{skill_id}', Ziel: '{target.name}'")
                else:
                    print(f"  -> Konnte keine Spielaktion für ID {test_action_id} ableiten (unerwartet).")
            else:
                print("\nKeine gültigen Aktionen laut Maske gefunden für den Test.")

            power_strike_id = "power_strike"
            if hero_instance and power_strike_id in action_manager.hero_action_skill_ids:
                hero_instance.current_stamina = 0 
                print(f"\n{hero_instance.name} hat 0 Stamina.")
                action_mask_no_res = action_manager.get_action_mask(state_manager)
                print(f"Action Mask, wenn keine Stamina für Power Strike:")
                
                power_strike_skill_idx = -1
                try: power_strike_skill_idx = action_manager.hero_action_skill_ids.index(power_strike_id)
                except ValueError: pass

                if power_strike_skill_idx != -1:
                    all_power_strike_actions_masked = True
                    for target_opt_idx in range(action_manager.num_target_options_in_space):
                        action_id_ps = power_strike_skill_idx * action_manager.num_target_options_in_space + target_opt_idx
                        if action_id_ps < len(action_mask_no_res) and action_mask_no_res[action_id_ps]:
                             all_power_strike_actions_masked = False
                             print(f"FEHLER: Power Strike Aktion {action_id_ps} sollte ungültig sein ohne Stamina, ist aber {action_mask_no_res[action_id_ps]}.")
                    if all_power_strike_actions_masked:
                        print("  Prüfung für Power Strike ohne Stamina erfolgreich (Aktionen sind korrekt maskiert).")
                    else:
                        print("  FEHLER bei Prüfung für Power Strike ohne Stamina.")


    except ImportError as e:
        print(f"FEHLER bei Imports für den Test in action_manager.py: {e}")
    except Exception as e:
        print(f"Ein Fehler ist während des Testlaufs in action_manager.py aufgetreten: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n--- ActionManager-Tests abgeschlossen ---")