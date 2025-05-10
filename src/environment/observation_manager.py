# src/environment/observation_manager.py
"""
Verwaltet die Erstellung und Normalisierung des Observation Space für die RL-Umgebung.
"""
import numpy as np
import logging
from typing import List, Dict, Any, Optional
from gymnasium import spaces # Für die Definition des Spaces

# Importiere relevante Klassen für Typ-Hinweise und Datenzugriff
if True: # Um Zirkularimporte zu vermeiden, falls StateManager ObservationManager importieren würde
    from src.environment.state_manager import EnvStateManager 
    from src.game_logic.entities import CharacterInstance
    from src.definitions.skill import SkillTemplate
    # Globale Definitionen werden hier nicht direkt geladen, sondern dem Manager übergeben oder er greift auf sie zu.

logger = logging.getLogger(__name__)

# Konstanten für die Struktur des Observation Space (müssen mit rpg_env.py synchron sein)
MAX_SKILLS_OBS = 6    # Maximale Anzahl an Heldenskills in der Observation
MAX_OPPONENTS_OBS = 3 # Maximale Anzahl an Gegnern in der Observation

class ObservationManager:
    def __init__(self, 
                 skill_templates: Dict[str, SkillTemplate], # Wird für Skill-Usability benötigt
                 hero_starting_skills_ids_ordered: List[str]): # Feste Reihenfolge der Skills des Helden
        
        self.skill_templates = skill_templates
        # Die Reihenfolge der Skills in der Observation muss konsistent sein.
        # Wir nehmen die ersten MAX_SKILLS_OBS aus den Start-Skills des Helden.
        self.observed_hero_skill_ids = hero_starting_skills_ids_ordered[:MAX_SKILLS_OBS]

        # --- Definition des Observation Space ---
        # Held:
        # 1. HP (normalisiert 0-1)
        # 2. Primäre Ressource (normalisiert 0-1)
        # 3. Schildpunkte (normalisiert zur MaxHP des Helden 0-1)
        # 4. bis (3 + MAX_SKILLS_OBS): Nutzbarkeit jedes der ersten MAX_SKILLS_OBS Skills (0 oder 1)
        # Gegner (für jeden der MAX_OPPONENTS_OBS Slots):
        # 1. HP (normalisiert 0-1)
        # 2. is_alive (0 oder 1)
        # (Optional könnten hier weitere Gegner-Features hinzukommen, z.B. Distanz, stärkster Angriff etc.)

        num_hero_features = 3 + MAX_SKILLS_OBS
        num_features_per_opponent = 2
        self.total_observation_features = num_hero_features + (MAX_OPPONENTS_OBS * num_features_per_opponent)
        
        self.observation_space = spaces.Box(
            low=0, 
            high=1, 
            shape=(self.total_observation_features,), 
            dtype=np.float32
        )
        logger.info(f"ObservationManager initialisiert. Observation Space: {self.observation_space}")

    def get_observation_space(self) -> spaces.Box:
        """Gibt den definierten Observation Space zurück."""
        return self.observation_space

    def get_observation(self, state_manager: EnvStateManager) -> np.ndarray:
        """
        Erstellt das NumPy-Array für die Observation basierend auf dem aktuellen Spielzustand.
        """
        obs_list = []
        hero = state_manager.get_hero()

        # Helden-Features
        if hero and not hero.is_defeated:
            obs_list.append(hero.current_hp / hero.max_hp if hero.max_hp > 0 else 0.0)
            
            primary_res_val, primary_res_max = 0.0, 0.0
            hero_template = hero.base_template
            if hasattr(hero_template, 'resource_type'):
                res_type = hero_template.resource_type
                if res_type == "MANA": primary_res_val, primary_res_max = hero.current_mana, hero.max_mana
                elif res_type == "STAMINA": primary_res_val, primary_res_max = hero.current_stamina, hero.max_stamina
                elif res_type == "ENERGY": primary_res_val, primary_res_max = hero.current_energy, hero.max_energy
            obs_list.append(primary_res_val / primary_res_max if primary_res_max > 0 else 0.0)
            
            obs_list.append(hero.shield_points / hero.max_hp if hero.max_hp > 0 and hero.shield_points > 0 else 0.0)

            # Skill-Nutzbarkeit (basierend auf den im Konstruktor festgelegten Skills)
            for i in range(MAX_SKILLS_OBS):
                if i < len(self.observed_hero_skill_ids):
                    skill_id = self.observed_hero_skill_ids[i]
                    skill_template = self.skill_templates.get(skill_id)
                    is_usable = skill_template and hero.can_afford_skill(skill_template)
                    obs_list.append(1.0 if is_usable else 0.0)
                else:
                    obs_list.append(0.0) # Padding
        else: # Held besiegt oder nicht vorhanden
            obs_list.extend([0.0] * (3 + MAX_SKILLS_OBS))

        # Gegner-Features
        # Wir greifen auf state_manager.opponents zu, da dies eine Liste fester Größe ist.
        # get_live_opponents() würde die Reihenfolge ändern können.
        for i in range(MAX_OPPONENTS_OBS):
            opponent_instance = state_manager.opponents[i] # Kann None sein
            if opponent_instance and not opponent_instance.is_defeated:
                obs_list.append(opponent_instance.current_hp / opponent_instance.max_hp if opponent_instance.max_hp > 0 else 0.0)
                obs_list.append(1.0) # is_alive
            else:
                obs_list.append(0.0) # HP
                obs_list.append(0.0) # not_alive
        
        if len(obs_list) != self.total_observation_features:
            logger.error(f"Fehler bei Observationserstellung: Länge {len(obs_list)} entspricht nicht erwarteter Länge {self.total_observation_features}. Padding/Logik prüfen!")
            # Notfall-Padding, um Shape-Fehler zu vermeiden, aber das ist ein Bug.
            while len(obs_list) < self.total_observation_features: obs_list.append(0.0)
            if len(obs_list) > self.total_observation_features: obs_list = obs_list[:self.total_observation_features]


        return np.array(obs_list, dtype=np.float32)

if __name__ == '__main__':
    # Für Tests des ObservationManagers benötigen wir einen EnvStateManager
    # und geladene Definitionen.
    print("--- Teste ObservationManager ---")
    
    # Minimales Setup für Abhängigkeiten
    try:
        from src.definitions.loader import load_character_templates, load_opponent_templates, load_skill_templates
        from src.game_logic.combat import CombatHandler
        from src.environment.state_manager import EnvStateManager
        import src.utils.logging_setup # Für Logging

        char_temps = load_character_templates()
        opp_temps = load_opponent_templates()
        skill_temps = load_skill_templates()
        combat_hnd = CombatHandler()

        if not char_temps or not opp_temps or not skill_temps:
            raise Exception("Konnte nicht alle Templates für den Test laden.")

        # Held für den Test auswählen
        test_hero_id = "krieger" # oder "schurke", etc.
        hero_template_for_test = char_temps.get(test_hero_id)
        if not hero_template_for_test:
            raise Exception(f"Heldentemplate {test_hero_id} nicht gefunden.")
        
        hero_skills_ordered = hero_template_for_test.starting_skills # oder .skills

        obs_manager = ObservationManager(skill_templates=skill_temps, hero_starting_skills_ids_ordered=hero_skills_ordered)
        state_manager = EnvStateManager(
            character_templates=char_temps,
            opponent_templates=opp_temps,
            combat_handler=combat_hnd,
            max_supported_opponents=MAX_OPPONENTS_OBS # Wichtig: Gleicher Wert
        )

        print(f"Observation Space Definition: {obs_manager.get_observation_space()}")
        print(f"Erwartete Anzahl Features: {obs_manager.total_observation_features}")

        # Reset State Manager
        opponent_ids_for_test = ["goblin_lv1", "goblin_archer_lv2"]
        if not state_manager.reset_state(hero_id=test_hero_id, opponent_ids=opponent_ids_for_test):
            print("Fehler beim Reset des StateManagers für den Test.")
        else:
            observation = obs_manager.get_observation(state_manager)
            print(f"\nGenerierte Observation (Länge: {len(observation)}):")
            print(observation)
            assert len(observation) == obs_manager.total_observation_features, "Länge der Observation stimmt nicht!"

            # Simuliere Schaden am Helden und an einem Gegner
            hero_instance = state_manager.get_hero()
            live_opps = state_manager.get_live_opponents()

            if hero_instance:
                hero_instance.take_damage(20)
                print(f"\nHeld HP nach Schaden: {hero_instance.current_hp}")
            
            if live_opps:
                live_opps[0].take_damage(30)
                print(f"{live_opps[0].name} HP nach Schaden: {live_opps[0].current_hp}")
            
            observation_after_damage = obs_manager.get_observation(state_manager)
            print(f"\nObservation nach Schaden (Länge: {len(observation_after_damage)}):")
            print(observation_after_damage)
            assert len(observation_after_damage) == obs_manager.total_observation_features

            # Simuliere, dass der Held einen Skill nicht mehr nutzen kann (z.B. keine Ressourcen)
            if hero_instance and obs_manager.observed_hero_skill_ids:
                first_skill_id = obs_manager.observed_hero_skill_ids[0]
                first_skill_template = skill_temps.get(first_skill_id)
                if first_skill_template:
                    res_type = first_skill_template.cost.type
                    if res_type == "STAMINA": hero_instance.current_stamina = 0
                    elif res_type == "MANA": hero_instance.current_mana = 0
                    elif res_type == "ENERGY": hero_instance.current_energy = 0
                    print(f"\n{hero_instance.name} Ressourcen für Skill '{first_skill_id}' auf 0 gesetzt.")
            
            observation_no_res = obs_manager.get_observation(state_manager)
            print(f"\nObservation nach Ressourcenverlust (Länge: {len(observation_no_res)}):")
            print(observation_no_res)


    except ImportError as e:
        print(f"FEHLER bei Imports für den Test in observation_manager.py: {e}")
    except Exception as e:
        print(f"Ein Fehler ist während des Testlaufs in observation_manager.py aufgetreten: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n--- ObservationManager-Tests abgeschlossen ---")