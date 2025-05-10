"""
Status-Effekte

Enthält die Status-Effekt-Klassen und deren Logik.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List

from src.utils.logging_setup import get_logger


# Logger für dieses Modul
logger = get_logger(__name__)


class StatusEffect(ABC):
    """
    Abstrakte Basisklasse für Status-Effekte.
    
    Alle konkreten Status-Effekte müssen von dieser Klasse erben und
    die abstrakten Methoden implementieren.
    """
    
    def __init__(self, duration: int, potency: int):
        """
        Initialisiert einen Status-Effekt.
        
        Args:
            duration (int): Die Dauer des Effekts in Runden
            potency (int): Die Stärke des Effekts
        """
        self.duration = duration
        self.potency = potency
        self.name = self.__class__.__name__
    
    @abstractmethod
    def on_apply(self, target: Any) -> None:
        """
        Wird aufgerufen, wenn der Effekt auf ein Ziel angewendet wird.
        
        Args:
            target (Any): Das Ziel, auf das der Effekt angewendet wird
        """
        pass
    
    @abstractmethod
    def on_tick(self, target: Any) -> None:
        """
        Wird in jeder Runde aufgerufen, solange der Effekt aktiv ist.
        
        Args:
            target (Any): Das Ziel mit dem aktiven Effekt
        """
        pass
    
    @abstractmethod
    def on_remove(self, target: Any) -> None:
        """
        Wird aufgerufen, wenn der Effekt endet oder entfernt wird.
        
        Args:
            target (Any): Das Ziel, von dem der Effekt entfernt wird
        """
        pass
    
    def tick(self, target: Any) -> bool:
        """
        Verarbeitet einen Tick (eine Runde) des Effekts und reduziert die Dauer.
        
        Args:
            target (Any): Das Ziel mit dem aktiven Effekt
            
        Returns:
            bool: True, wenn der Effekt noch aktiv ist, False wenn er endet
        """
        # Effekt anwenden
        self.on_tick(target)
        
        # Dauer reduzieren
        self.duration -= 1
        
        # Prüfen, ob der Effekt endet
        if self.duration <= 0:
            self.on_remove(target)
            return False
        
        return True
    
    def __str__(self) -> str:
        """String-Repräsentation des Effekts"""
        return f"{self.name} (Dauer: {self.duration}, Stärke: {self.potency})"


# Konkrete Status-Effekt-Implementierungen

class Burning(StatusEffect):
    """Brennend: Verursacht Schaden über Zeit"""
    
    def on_apply(self, target: Any) -> None:
        logger.debug(f"{target.name} brennt! (Stärke: {self.potency})")
    
    def on_tick(self, target: Any) -> None:
        # Direkter Schaden, der Rüstung ignoriert
        damage = self.potency
        target.take_raw_damage(damage)
        logger.debug(f"{target.name} erleidet {damage} Feuerschaden durch Brennen")
    
    def on_remove(self, target: Any) -> None:
        logger.debug(f"{target.name} brennt nicht mehr")


class Stunned(StatusEffect):
    """Betäubt: Verhindert Aktionen"""
    
    def on_apply(self, target: Any) -> None:
        target.status_flags['can_act'] = False
        logger.debug(f"{target.name} ist betäubt und kann nicht handeln")
    
    def on_tick(self, target: Any) -> None:
        # Nichts zu tun bei jedem Tick - der Effekt ist beim Anwenden eingetreten
        pass
    
    def on_remove(self, target: Any) -> None:
        target.status_flags['can_act'] = True
        logger.debug(f"{target.name} ist nicht mehr betäubt")


class Slowed(StatusEffect):
    """Verlangsamt: Reduziert Initiative und Ausweichen"""
    
    def on_apply(self, target: Any) -> None:
        target.status_mods['initiative'] -= 5 * self.potency
        target.status_mods['evasion'] -= self.potency
        logger.debug(f"{target.name} ist verlangsamt (Initiative -5, Ausweichen -{self.potency})")
    
    def on_tick(self, target: Any) -> None:
        # Nichts zu tun bei jedem Tick - der Effekt ist beim Anwenden eingetreten
        pass
    
    def on_remove(self, target: Any) -> None:
        target.status_mods['initiative'] += 5 * self.potency
        target.status_mods['evasion'] += self.potency
        logger.debug(f"{target.name} ist nicht mehr verlangsamt")


class Weakened(StatusEffect):
    """Geschwächt: Reduziert Stärke"""
    
    def on_apply(self, target: Any) -> None:
        target.status_mods['STR'] -= self.potency
        logger.debug(f"{target.name} ist geschwächt (STR -{self.potency})")
    
    def on_tick(self, target: Any) -> None:
        # Nichts zu tun bei jedem Tick - der Effekt ist beim Anwenden eingetreten
        pass
    
    def on_remove(self, target: Any) -> None:
        target.status_mods['STR'] += self.potency
        logger.debug(f"{target.name} ist nicht mehr geschwächt")


class AccuracyDown(StatusEffect):
    """Genauigkeit reduziert: Reduziert Treffergenauigkeit"""
    
    def on_apply(self, target: Any) -> None:
        target.status_mods['accuracy'] -= self.potency
        logger.debug(f"{target.name} hat reduzierte Genauigkeit (-{self.potency})")
    
    def on_tick(self, target: Any) -> None:
        # Nichts zu tun bei jedem Tick - der Effekt ist beim Anwenden eingetreten
        pass
    
    def on_remove(self, target: Any) -> None:
        target.status_mods['accuracy'] += self.potency
        logger.debug(f"{target.name} hat keine reduzierte Genauigkeit mehr")


class InitiativeUp(StatusEffect):
    """Initiative erhöht: Erhöht die Initiative"""
    
    def on_apply(self, target: Any) -> None:
        target.status_mods['initiative'] += self.potency
        logger.debug(f"{target.name} hat erhöhte Initiative (+{self.potency})")
    
    def on_tick(self, target: Any) -> None:
        # Nichts zu tun bei jedem Tick - der Effekt ist beim Anwenden eingetreten
        pass
    
    def on_remove(self, target: Any) -> None:
        target.status_mods['initiative'] -= self.potency
        logger.debug(f"{target.name} hat keine erhöhte Initiative mehr")


class Shielded(StatusEffect):
    """Geschützt: Absorbiert Schaden"""
    
    def on_apply(self, target: Any) -> None:
        target.shield_points = self.potency
        logger.debug(f"{target.name} hat einen Schutzschild ({self.potency} Punkte)")
    
    def on_tick(self, target: Any) -> None:
        # Nichts zu tun bei jedem Tick - der Effekt ist beim Anwenden eingetreten
        pass
    
    def on_remove(self, target: Any) -> None:
        target.shield_points = 0
        logger.debug(f"{target.name} hat keinen Schutzschild mehr")


class DefenseUp(StatusEffect):
    """Verteidigung erhöht: Erhöht Rüstung und Magieresistenz"""
    
    def on_apply(self, target: Any) -> None:
        target.status_mods['armor'] += self.potency
        target.status_mods['magic_resist'] += self.potency
        logger.debug(f"{target.name} hat erhöhte Verteidigung (Rüstung/Magieresistenz +{self.potency})")
    
    def on_tick(self, target: Any) -> None:
        # Nichts zu tun bei jedem Tick - der Effekt ist beim Anwenden eingetreten
        pass
    
    def on_remove(self, target: Any) -> None:
        target.status_mods['armor'] -= self.potency
        target.status_mods['magic_resist'] -= self.potency
        logger.debug(f"{target.name} hat keine erhöhte Verteidigung mehr")


# Factory für Status-Effekte
def create_status_effect(effect_id: str, duration: int, potency: int) -> Optional[StatusEffect]:
    """
    Erstellt einen Status-Effekt basierend auf der ID.
    
    Args:
        effect_id (str): Die ID des Status-Effekts
        duration (int): Die Dauer in Runden
        potency (int): Die Stärke des Effekts
        
    Returns:
        Optional[StatusEffect]: Der erstellte Status-Effekt oder None, wenn die ID ungültig ist
    """
    effect_classes = {
        'BURNING': Burning,
        'STUNNED': Stunned,
        'SLOWED': Slowed,
        'WEAKENED': Weakened,
        'ACCURACY_DOWN': AccuracyDown,
        'INITIATIVE_UP': InitiativeUp,
        'SHIELDED': Shielded,
        'DEFENSE_UP': DefenseUp,
    }
    
    effect_class = effect_classes.get(effect_id)
    if not effect_class:
        logger.error(f"Unbekannter Status-Effekt: {effect_id}")
        return None
    
    return effect_class(duration, potency)
