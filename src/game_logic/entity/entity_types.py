"""
Entity Types Module

Definiert die verschiedenen Typen von Entitäten im Spiel.
"""

from enum import Enum, auto


class EntityType(Enum):
    """
    Enum für die Typen von Entitäten.
    
    Wird verwendet, um die Natur einer Entität zu identifizieren, was
    wichtig für die Spiellogik, KI-Entscheidungen und UI-Darstellung ist.
    """
    PLAYER = auto()  # Spielercharaktere
    ENEMY = auto()   # Feindliche Kreaturen und NPCs
    NPC = auto()     # Neutrale oder freundliche NPCs
