"""
Verwaltet die Aktionen für die RL-Umgebung.
Definiert den Aktionsraum und die Logik zur Aktionsausführung.
"""
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
from src.environment.env_state import EnvState
# Entferne den Import der nicht existierenden Funktion
# from src.game_logic.combat import apply_skill
from src.config.config import get_config


class ActionManager:
    """
    Verwaltet Aktionen für RL-Agenten, einschließlich Aktionsvalidierung und Action Masking.
    """
    
    def __init__(self):
        """
        Initialisiert den ActionManager mit Konfigurationsparametern.
        """
        self.config = get_config()
        
        # Konfiguration aus settings.json5
        rl_settings = self.config.get('rl_settings', {})
        self.max_skills = rl_settings.get('max_skills_per_character', 10)
        self.max_targets = rl_settings.get('max_targets', 10)
        
        # Aktionsraum definieren
        self.action_space_size = self.max_skills * self.max_targets
        
    def get_action_space(self) -> Dict[str, Any]:
        """
        Gibt den Aktionsraum für die Gym-Umgebung zurück.
        
        Returns:
            Dict[str, Any]: Ein Dictionary, das den Aktionsraum beschreibt.
        """
        # In einer tatsächlichen Implementierung würden wir die gym.spaces.Discrete
        # oder andere gymnasium-Klassen verwenden
        return {
            'type': 'Discrete',
            'n': self.action_space_size
        }
    
    def get_action_mask(self, state: EnvState) -> np.ndarray:
        """
        Erstellt eine Maske für die Aktionen, die im aktuellen Zustand möglich sind.
        Dies ist ein Kernmechanismus für MaskablePPO.
        
        Args:
            state: Der aktuelle Umgebungszustand.
            
        Returns:
            np.ndarray: Eine binäre Maske, die angibt, welche Aktionen gültig sind (1=gültig, 0=ungültig).
        """
        # Initialisiere alle Aktionen als ungültig
        mask = np.zeros(self.action_space_size, dtype=np.int8)
        
        # Wenn der Kampf beendet ist oder kein Akteur am Zug ist, alles ungültig lassen
        if state.is_done or not state.initiative_order:
            return mask
        
        # Prüfe, ob der aktuelle Akteur ein Spieler ist
        if not state.is_current_actor_player():
            # Wenn der aktuelle Akteur kein Spieler ist, sind alle Aktionen ungültig
            return mask
        
        # Hole den aktuellen Spielercharakter
        current_actor = state.get_current_actor()
        if not current_actor or not current_actor.is_alive():
            return mask
        
        # Durchlaufe alle Skills des Charakters
        for skill_idx, skill_id in enumerate(self._get_available_skills(current_actor)):
            if skill_idx >= self.max_skills:
                break
                
            # Prüfe, ob der Spieler genügend Ressourcen für den Skill hat
            if not self._has_resources_for_skill(current_actor, skill_id):
                continue
                
            # Für jeden Skill, bestimme gültige Ziele
            for target_idx, target in enumerate(self._get_valid_targets(state, current_actor, skill_id)):
                if target_idx >= self.max_targets:
                    break
                    
                # Berechne den Aktionsindex und setze die Maske auf gültig
                action_idx = skill_idx * self.max_targets + target_idx
                if action_idx < self.action_space_size:
                    mask[action_idx] = 1
        
        return mask
    
    def decode_action(self, action_idx: int) -> Tuple[str, int]:
        """
        Dekodiert eine Aktions-ID in Skill-ID und Ziel-Index.
        
        Args:
            action_idx: Der Index der ausgewählten Aktion.
            
        Returns:
            Tuple[str, int]: Ein Tupel aus Skill-ID und Ziel-Index.
        """
        skill_idx = action_idx // self.max_targets
        target_idx = action_idx % self.max_targets
        
        # In einer tatsächlichen Implementierung würden wir die tatsächliche Skill-ID zurückgeben
        # Hier geben wir nur den Index zurück
        return (f"skill_{skill_idx}", target_idx)
    
    def execute_action(self, state: EnvState, action_idx: int) -> float:
        """
        Führt eine Aktion im Umgebungszustand aus und gibt die resultierende Belohnung zurück.
        
        Args:
            state: Der aktuelle Umgebungszustand.
            action_idx: Der Index der auszuführenden Aktion.
            
        Returns:
            float: Die Belohnung für diese Aktion.
        """
        # Dekodiere die Aktion
        skill_id, target_idx = self.decode_action(action_idx)
        
        # Hole den aktuellen Akteur und das Ziel
        current_actor = state.get_current_actor()
        if not current_actor:
            return 0.0
            
        # Bestimme die gültigen Ziele für den Skill
        valid_targets = self._get_valid_targets(state, current_actor, skill_id)
        if not valid_targets or target_idx >= len(valid_targets):
            return 0.0
            
        target = valid_targets[target_idx]
        
        # Führe den Skill aus
        result = self._use_skill(state, current_actor, target, skill_id)
        
        # Berechne die Belohnung basierend auf dem Ergebnis
        reward = self._calculate_reward(state, current_actor, target, skill_id, result)
        
        # Aktualisiere die akkumulierte Belohnung und letzte Aktionsbelohnung
        state.last_action_reward = reward
        state.accumulated_reward += reward
        
        # Gehe zum nächsten Akteur
        state.advance_to_next_actor()
        
        return reward
        
    def _get_available_skills(self, character) -> List[str]:
        """
        Gibt die verfügbaren Skills eines Charakters zurück.
        
        Args:
            character: Der Charakter, dessen Skills geprüft werden sollen.
            
        Returns:
            List[str]: Eine Liste der verfügbaren Skill-IDs.
        """
        # In einer tatsächlichen Implementierung würden wir die tatsächlichen Skills des Charakters zurückgeben
        # Hier geben wir eine einfache Liste zurück
        if hasattr(character, 'skills'):
            return character.skills
        return []
    
    def _has_resources_for_skill(self, character, skill_id: str) -> bool:
        """
        Prüft, ob ein Charakter genügend Ressourcen für einen Skill hat.
        
        Args:
            character: Der Charakter, der den Skill ausführen möchte.
            skill_id: Die ID des Skills.
            
        Returns:
            bool: True, wenn der Charakter genügend Ressourcen hat, sonst False.
        """
        # In einer tatsächlichen Implementierung würden wir die tatsächlichen Ressourcenanforderungen prüfen
        # Hier nehmen wir an, dass der Charakter genügend Ressourcen hat
        
        # Beispiel für eine Ressourcenprüfung:
        if hasattr(character, 'get_skill_cost'):
            cost_value, cost_type = character.get_skill_cost(skill_id)
            
            # Prüfe den Ressourcentyp und -wert
            if cost_type == 'MANA' and hasattr(character, 'mana'):
                return character.mana >= cost_value
            elif cost_type == 'STAMINA' and hasattr(character, 'stamina'):
                return character.stamina >= cost_value
            elif cost_type == 'ENERGY' and hasattr(character, 'energy'):
                return character.energy >= cost_value
            
        # Standardmäßig nehmen wir an, dass der Skill keine Ressourcen benötigt
        return True
    
    def _get_valid_targets(self, state: EnvState, actor, skill_id: str) -> List[Any]:
        """
        Bestimmt die gültigen Ziele für einen Skill.
        
        Args:
            state: Der aktuelle Umgebungszustand.
            actor: Der Charakter, der den Skill ausführt.
            skill_id: Die ID des Skills.
            
        Returns:
            List[Any]: Eine Liste der gültigen Ziele.
        """
        # In einer tatsächlichen Implementierung würden wir die Zieltypen des Skills prüfen
        # und entsprechend gültige Ziele zurückgeben
        
        # Beispiel für eine einfache Zielbestimmung:
        # - Angenommen, offensive Skills richten sich gegen Gegner
        # - Unterstützende Skills richten sich gegen Verbündete
        
        # Bestimme, ob es sich um einen offensiven oder unterstützenden Skill handelt
        # In einer tatsächlichen Implementierung würden wir dies aus den Skill-Definitionen lesen
        is_offensive = True  # Standardannahme
        
        if hasattr(actor, 'get_skill_type'):
            skill_type = actor.get_skill_type(skill_id)
            is_offensive = skill_type == 'OFFENSIVE'
        
        if is_offensive:
            # Offensive Skills richten sich gegen Gegner
            if isinstance(actor, state.player_characters.__class__):
                return [opp for opp in state.opponents if opp.is_alive()]
            else:
                return [pc for pc in state.player_characters if pc.is_alive()]
        else:
            # Unterstützende Skills richten sich gegen Verbündete
            if isinstance(actor, state.player_characters.__class__):
                return [pc for pc in state.player_characters if pc.is_alive()]
            else:
                return [opp for opp in state.opponents if opp.is_alive()]
    
    def _use_skill(self, state: EnvState, actor, target, skill_id: str) -> Dict[str, Any]:
        """
        Führt einen Skill aus und gibt das Ergebnis zurück.
        
        Args:
            state: Der aktuelle Umgebungszustand.
            actor: Der Charakter, der den Skill ausführt.
            target: Das Ziel des Skills.
            skill_id: Die ID des Skills.
            
        Returns:
            Dict[str, Any]: Das Ergebnis der Skill-Ausführung.
        """
        # In einer tatsächlichen Implementierung würden wir hier die tatsächliche Skill-Logik aufrufen
        # Hier implementieren wir eine einfache Logik direkt

        # Beispiel für ein Skill-Ergebnis
        result = {
            'success': True,  # Skill wurde erfolgreich ausgeführt
            'damage_dealt': 0,  # Schaden, der verursacht wurde
            'healing_done': 0,  # Heilung, die durchgeführt wurde
            'status_effects_applied': [],  # Statuseffekte, die angewendet wurden
            'message': f"{actor.name if hasattr(actor, 'name') else 'Actor'} used {skill_id} on {target.name if hasattr(target, 'name') else 'Target'}"
        }
        
        # Simuliere verschiedene Arten von Skills
        if 'attack' in skill_id or 'strike' in skill_id:
            # Offensiver Skill
            damage = np.random.randint(5, 15)  # Zufälliger Schaden zwischen 5 und 14
            result['damage_dealt'] = damage
            
            # Wenn das Target HP hat, reduziere sie
            if hasattr(target, 'hp'):
                target.hp = max(0, target.hp - damage)
                
                # Prüfe, ob das Ziel besiegt wurde
                if target.hp <= 0 and hasattr(target, 'set_dead'):
                    target.set_dead()
        
        elif 'heal' in skill_id:
            # Heilungs-Skill
            healing = np.random.randint(8, 20)  # Zufällige Heilung zwischen 8 und 19
            result['healing_done'] = healing
            
            # Wenn das Target HP und max_hp hat, erhöhe HP
            if hasattr(target, 'hp') and hasattr(target, 'max_hp'):
                target.hp = min(target.max_hp, target.hp + healing)
        
        elif 'stun' in skill_id or 'slow' in skill_id:
            # Status-Effekt-Skill
            effect_name = 'STUNNED' if 'stun' in skill_id else 'SLOWED'
            result['status_effects_applied'].append(effect_name)
            
            # Wenn das Target status_effects hat, füge den Effekt hinzu
            if hasattr(target, 'add_status_effect'):
                duration = 2  # 2 Runden
                potency = 1 if effect_name == 'STUNNED' else 3
                target.add_status_effect(effect_name, duration, potency)
        
        # Aktualisiere die Kampfgeschichte
        if hasattr(state, 'combat_history'):
            state.combat_history.append({
                'round': state.current_round,
                'actor': actor.name if hasattr(actor, 'name') else 'Unknown',
                'skill': skill_id,
                'target': target.name if hasattr(target, 'name') else 'Unknown',
                'result': result
            })
        
        return result
    
    def _calculate_reward(self, state: EnvState, actor, target, skill_id: str, result: Dict[str, Any]) -> float:
        """
        Berechnet die Belohnung für eine Aktion.
        
        Args:
            state: Der aktuelle Umgebungszustand.
            actor: Der Charakter, der die Aktion ausgeführt hat.
            target: Das Ziel der Aktion.
            skill_id: Die ID des verwendeten Skills.
            result: Das Ergebnis der Aktion.
            
        Returns:
            float: Die Belohnung für die Aktion.
        """
        # In einer tatsächlichen Implementierung würden wir hier eine komplexere Belohnungsfunktion implementieren
        # Hier verwenden wir eine einfache Belohnungsfunktion
        
        # Lade die Belohnungsparameter aus der Konfiguration
        rl_settings = self.config.get('rl_settings', {})
        rewards = rl_settings.get('rewards', {})
        damage_reward_factor = rewards.get('damage_factor', 0.1)
        healing_reward_factor = rewards.get('healing_factor', 0.2)
        kill_reward = rewards.get('kill', 1.0)
        effect_application_reward = rewards.get('effect_application', 0.5)
        
        # Initialisiere die Belohnung
        reward = 0.0
        
        # Belohnung für verursachten Schaden
        reward += result.get('damage_dealt', 0) * damage_reward_factor
        
        # Belohnung für Heilung
        reward += result.get('healing_done', 0) * healing_reward_factor
        
        # Belohnung für Kill
        if target and hasattr(target, 'is_alive') and not target.is_alive():
            reward += kill_reward
        
        # Belohnung für angewandte Statuseffekte
        reward += len(result.get('status_effects_applied', [])) * effect_application_reward
        
        return reward
