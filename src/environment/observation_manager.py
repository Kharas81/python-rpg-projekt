"""
Verwaltet die Beobachtungen (Observations) für die RL-Umgebung.
Konvertiert den Spielzustand in ein Format, das von RL-Agenten verwendet werden kann.
"""
from typing import Dict, List, Any, Tuple, Optional
import numpy as np
from src.environment.env_state import EnvState
from src.game_logic.entities import CharacterInstance
from src.config.config import get_config


class ObservationManager:
    """
    Konvertiert den Spielzustand in RL-Beobachtungen und verwaltet die Beobachtungsräume.
    """
    
    def __init__(self):
        """
        Initialisiert den ObservationManager mit Konfigurationsparametern.
        """
        self.config = get_config()
        
        # Konfiguration aus der settings.json5-Datei
        rl_settings = self.config.get('rl_settings', {})
        self.max_players = rl_settings.get('max_players', 4)
        self.max_opponents = rl_settings.get('max_opponents', 6)
        self.max_status_effects = rl_settings.get('max_status_effects', 5)
        
        # Definiere die Form der Beobachtung
        # Diese Struktur ist ein Beispiel und sollte an das spezifische Spiel angepasst werden
        self.observation_shape = self._calculate_observation_shape()
        
    def _calculate_observation_shape(self) -> Tuple[int, ...]:
        """
        Berechnet die Form des Beobachtungsvektors basierend auf der Konfiguration.
        
        Returns:
            Tuple[int, ...]: Die Form des Beobachtungsvektors.
        """
        # Für jeden Spielercharakter: HP, Mana/Stamina/Energy, Rüstung, Magieresistenz, Status-Effekte, etc.
        player_features = 10  # Grundlegende Spielerattribute
        status_effect_features = 2  # pro Status-Effekt (z.B. Typ und verbleibende Dauer)
        
        # Für jeden Gegner: Ähnliche Werte wie für Spieler
        opponent_features = 10  # Grundlegende Gegnerattribute
        
        # Allgemeine Kampfinformationen: Aktuelle Runde, aktueller Akteur, etc.
        general_features = 5
        
        # Gesamtform: Flacher Vektor für einfache Modelle
        # [allgemeine Infos, Spieler1, Spieler2, ..., Gegner1, Gegner2, ...]
        total_features = (
            general_features +
            (player_features + self.max_status_effects * status_effect_features) * self.max_players +
            (opponent_features + self.max_status_effects * status_effect_features) * self.max_opponents
        )
        
        return (total_features,)
    
    def get_observation_space(self) -> Dict[str, Any]:
        """
        Gibt den Beobachtungsraum für die Gym-Umgebung zurück.
        
        Returns:
            Dict[str, Any]: Ein Dictionary, das den Beobachtungsraum beschreibt.
        """
        # Wir verwenden hier ein Dictionary-Format, das von gymnasium unterstützt wird
        # In einer tatsächlichen Implementierung würden wir die gym.spaces.Box oder andere 
        # gymnasium-Klassen verwenden
        return {
            'type': 'Box',
            'shape': self.observation_shape,
            'low': -1.0,  # Untere Grenze der Beobachtungen
            'high': 1.0,  # Obere Grenze der Beobachtungen
            'dtype': 'float32'
        }
    
    def get_observation(self, state: EnvState) -> np.ndarray:
        """
        Konvertiert den aktuellen Spielzustand in eine Beobachtung für den RL-Agenten.
        
        Args:
            state: Der aktuelle Umgebungszustand.
            
        Returns:
            np.ndarray: Die Beobachtung als normalisierter numpy-Array.
        """
        # Hier erstellen wir den Beobachtungsvektor aus dem Spielzustand
        # In einer vollständigen Implementierung würden wir alle relevanten Informationen extrahieren
        
        # Initialisiere den Beobachtungsvektor mit Nullen
        observation = np.zeros(self.observation_shape, dtype=np.float32)
        
        # Fülle den Vektor mit Informationen
        self._add_general_info(observation, state, start_idx=0)
        
        # Index-Offset für den nächsten Abschnitt
        offset = 5  # Nach den allgemeinen Informationen
        
        # Füge Spielerinformationen hinzu
        player_section_size = 10 + self.max_status_effects * 2  # Spielerfeatures + Statuseffekte
        for i, pc in enumerate(state.player_characters):
            if i >= self.max_players:
                break
            self._add_character_info(observation, pc, offset + i * player_section_size)
        
        # Offset für Gegnerinformationen
        offset = 5 + self.max_players * player_section_size
        
        # Füge Gegnerinformationen hinzu
        opponent_section_size = 10 + self.max_status_effects * 2  # Gegnerfeatures + Statuseffekte
        for i, opp in enumerate(state.opponents):
            if i >= self.max_opponents:
                break
            self._add_character_info(observation, opp, offset + i * opponent_section_size)
        
        # Normalisiere die Beobachtung auf den Bereich [-1, 1]
        return self._normalize_observation(observation)
    
    def _add_general_info(self, observation: np.ndarray, state: EnvState, start_idx: int) -> None:
        """
        Fügt allgemeine Kampfinformationen zur Beobachtung hinzu.
        
        Args:
            observation: Der zu füllende Beobachtungsvektor.
            state: Der aktuelle Umgebungszustand.
            start_idx: Der Startindex im Beobachtungsvektor.
        """
        # Beispiel für allgemeine Informationen:
        observation[start_idx] = state.current_round / 20.0  # Normalisierte Rundennummer (angenommen max 20 Runden)
        observation[start_idx + 1] = state.current_actor_idx / len(state.initiative_order) if state.initiative_order else 0
        observation[start_idx + 2] = 1.0 if state.is_current_actor_player() else -1.0
        observation[start_idx + 3] = len(state.player_characters) / self.max_players
        observation[start_idx + 4] = len(state.opponents) / self.max_opponents
    
    def _add_character_info(self, observation: np.ndarray, character: CharacterInstance, start_idx: int) -> None:
        """
        Fügt Charakterinformationen zur Beobachtung hinzu.
        
        Args:
            observation: Der zu füllende Beobachtungsvektor.
            character: Der Charakter, dessen Informationen hinzugefügt werden sollen.
            start_idx: Der Startindex im Beobachtungsvektor.
        """
        if not character:
            return
            
        # Grundlegende Charakterattribute
        # In einer tatsächlichen Implementierung würden wir hier alle relevanten Attribute extrahieren
        observation[start_idx] = 1.0 if character.is_alive() else 0.0
        observation[start_idx + 1] = character.hp / character.max_hp if character.max_hp > 0 else 0.0
        
        # Beispiel für weitere Attribute (muss an die tatsächlichen Charakter-Attribute angepasst werden)
        if hasattr(character, 'mana') and hasattr(character, 'max_mana') and character.max_mana > 0:
            observation[start_idx + 2] = character.mana / character.max_mana
        
        if hasattr(character, 'stamina') and hasattr(character, 'max_stamina') and character.max_stamina > 0:
            observation[start_idx + 3] = character.stamina / character.max_stamina
        
        if hasattr(character, 'energy') and hasattr(character, 'max_energy') and character.max_energy > 0:
            observation[start_idx + 4] = character.energy / character.max_energy
        
        # Rüstung und Magieresistenz
        if hasattr(character, 'armor'):
            observation[start_idx + 5] = character.armor / 20.0  # Angenommen max Rüstung ist 20
        
        if hasattr(character, 'magic_resist'):
            observation[start_idx + 6] = character.magic_resist / 20.0  # Angenommen max Magieresistenz ist 20
        
        # Füge Status-Effekte hinzu
        if hasattr(character, 'status_effects'):
            self._add_status_effects(observation, character.status_effects, start_idx + 10)
    
    def _add_status_effects(self, observation: np.ndarray, status_effects: List[Dict[str, Any]], start_idx: int) -> None:
        """
        Fügt Status-Effekt-Informationen zur Beobachtung hinzu.
        
        Args:
            observation: Der zu füllende Beobachtungsvektor.
            status_effects: Die Status-Effekte des Charakters.
            start_idx: Der Startindex im Beobachtungsvektor.
        """
        # Hier würden wir die Status-Effekte des Charakters in den Beobachtungsvektor einfügen
        # In einer tatsächlichen Implementierung würden wir die Effekte in einer konsistenten Reihenfolge sortieren
        
        # Beispiel für Status-Effekt-Kodierung:
        # - Für jeden Status-Effekt verwenden wir 2 Werte: Typ (One-Hot oder ID) und verbleibende Dauer
        for i, effect in enumerate(status_effects[:self.max_status_effects]):
            if i >= self.max_status_effects:
                break
                
            # Effekt-Typ (könnte eine One-Hot-Kodierung sein, hier verwenden wir eine einfache ID)
            effect_id = self._get_effect_id(effect.get('id', 'unknown'))
            observation[start_idx + i * 2] = effect_id / 10.0  # Normalisiert (angenommen max 10 verschiedene Effekte)
            
            # Verbleibende Dauer
            observation[start_idx + i * 2 + 1] = effect.get('remaining_duration', 0) / 5.0  # Normalisiert (max 5 Runden)
    
    def _get_effect_id(self, effect_id: str) -> int:
        """
        Konvertiert eine Effekt-ID in eine numerische ID für die Beobachtung.
        
        Args:
            effect_id: Die String-ID des Effekts.
            
        Returns:
            int: Die numerische ID des Effekts.
        """
        # In einer tatsächlichen Implementierung würden wir eine konsistente Mapping-Funktion implementieren
        # Hier verwenden wir eine einfache Beispiel-Mapping-Funktion
        effect_map = {
            'BURNING': 1,
            'STUNNED': 2,
            'SLOWED': 3,
            'WEAKENED': 4,
            'ACCURACY_DOWN': 5,
            'INITIATIVE_UP': 6,
            'SHIELDED': 7,
            'DEFENSE_UP': 8,
            # Weitere Effekte...
        }
        return effect_map.get(effect_id, 0)
    
    def _normalize_observation(self, observation: np.ndarray) -> np.ndarray:
        """
        Normalisiert die Beobachtung auf den Bereich [-1, 1].
        
        Args:
            observation: Der zu normalisierende Beobachtungsvektor.
            
        Returns:
            np.ndarray: Der normalisierte Beobachtungsvektor.
        """
        # In einer tatsächlichen Implementierung würden wir hier möglicherweise 
        # Min-Max-Skalierung oder andere Normalisierungstechniken anwenden
        
        # Hier nehmen wir an, dass die Werte bereits im Bereich [0, 1] liegen
        # und transformieren sie auf [-1, 1]
        return 2.0 * observation - 1.0
