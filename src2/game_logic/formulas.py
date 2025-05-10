"""
Formeln und Berechnungen

Enthält grundlegende Berechnungsformeln für Spiel-Mechaniken wie
Attributboni, HP-Berechnung, Trefferchance usw.
"""
import math
from typing import Optional

from src.config.config import get_config
from src.utils.logging_setup import get_logger


# Logger für dieses Modul
logger = get_logger(__name__)


def calculate_attribute_bonus(attribute_value: int) -> int:
    """
    Berechnet den Bonus/Malus für einen Attributwert.
    Formel: (Attributwert - 10) // 2 (ganzzahlige Division)
    
    Args:
        attribute_value (int): Der Attributwert (z.B. STR, DEX)
        
    Returns:
        int: Der Bonus/Malus für diesen Attributwert
    """
    return (attribute_value - 10) // 2


def calculate_max_hp(base_hp: int, constitution: int) -> int:
    """
    Berechnet die maximalen Lebenspunkte.
    Formel: Basis-HP + (Konstitution * 5)
    
    Args:
        base_hp (int): Die Basis-Lebenspunkte
        constitution (int): Der Konstitutionswert (CON)
        
    Returns:
        int: Die maximalen Lebenspunkte
    """
    return base_hp + (constitution * 5)


def calculate_damage(
    base_damage: Optional[int], 
    attribute_value: int, 
    multiplier: float = 1.0
) -> int:
    """
    Berechnet den Schaden einer Aktion.
    Formel: floor((Basis-Schaden + Attribut-Bonus) * Multiplikator)
    
    Args:
        base_damage (Optional[int]): Der Basis-Schaden (None nutzt Standardwert)
        attribute_value (int): Der relevante Attributwert (z.B. STR, INT)
        multiplier (float): Ein Multiplikator für den Schaden (Standard: 1.0)
        
    Returns:
        int: Der berechnete Schaden (abgerundet)
    """
    config = get_config()
    if base_damage is None:
        base_damage = config.game_settings.get('base_weapon_damage', 5)
        
    attribute_bonus = calculate_attribute_bonus(attribute_value)
    return math.floor((base_damage + attribute_bonus) * multiplier)


def calculate_healing(
    base_healing: int,
    attribute_value: int,
    multiplier: float = 1.0
) -> int:
    """
    Berechnet die Heilung einer Aktion.
    Formel: floor((Basis-Heilung + Attribut-Bonus) * Multiplikator)
    
    Args:
        base_healing (int): Die Basis-Heilung
        attribute_value (int): Der relevante Attributwert (z.B. WIS)
        multiplier (float): Ein Multiplikator für die Heilung (Standard: 1.0)
        
    Returns:
        int: Die berechnete Heilung (abgerundet)
    """
    attribute_bonus = calculate_attribute_bonus(attribute_value)
    return math.floor((base_healing + attribute_bonus) * multiplier)


def calculate_damage_reduction(damage: int, defense: int) -> int:
    """
    Berechnet den reduzierten Schaden nach Anwendung der Verteidigung.
    Formel: max(min_damage, Schaden - Verteidigung)
    
    Args:
        damage (int): Der ursprüngliche Schaden
        defense (int): Der Verteidigungswert (Rüstung oder Magieresistenz)
        
    Returns:
        int: Der reduzierte Schaden
    """
    config = get_config()
    min_damage = config.game_settings.get('min_damage', 1)
    
    reduced_damage = max(min_damage, damage - defense)
    return reduced_damage


def calculate_hit_chance(accuracy: int, evasion: int) -> int:
    """
    Berechnet die Trefferchance basierend auf Genauigkeit und Ausweichen.
    Formel: max(min_chance, min(max_chance, base_chance + (Genauigkeit*Faktor) - (Ausweichen*Faktor)))
    
    Args:
        accuracy (int): Der Genauigkeitswert des Angreifers
        evasion (int): Der Ausweichenwert des Ziels
        
    Returns:
        int: Die Trefferchance in Prozent (5-95)
    """
    config = get_config()
    base_chance = config.game_settings.get('hit_chance_base', 90)
    accuracy_factor = config.game_settings.get('hit_chance_accuracy_factor', 3)
    evasion_factor = config.game_settings.get('hit_chance_evasion_factor', 2)
    min_chance = config.game_settings.get('hit_chance_min', 5)
    max_chance = config.game_settings.get('hit_chance_max', 95)
    
    # Berechnung mit Abrundung auf ganze Prozente
    hit_chance = base_chance + (accuracy * accuracy_factor) - (evasion * evasion_factor)
    
    # Auf den erlaubten Bereich beschränken
    hit_chance = max(min_chance, min(max_chance, hit_chance))
    
    return hit_chance


def calculate_xp_for_level(level: int) -> int:
    """
    Berechnet die benötigte XP für ein bestimmtes Level.
    Formel: ceiling(xp_level_base * (xp_level_factor ^ (level - 1)))
    
    Args:
        level (int): Das zu berechnende Level
        
    Returns:
        int: Die benötigte XP für dieses Level
    """
    config = get_config()
    xp_base = config.game_settings.get('xp_level_base', 100)
    xp_factor = config.game_settings.get('xp_level_factor', 1.5)
    
    # Level 1 benötigt 0 XP, da es das Startlevel ist
    if level <= 1:
        return 0
    
    # XP für Level berechnen und aufrunden
    required_xp = math.ceil(xp_base * (xp_factor ** (level - 1)))
    return required_xp


def calculate_accuracy_modifier(dexterity: int, effects_mod: int = 0) -> int:
    """
    Berechnet den Genauigkeitsmodifikator basierend auf Geschicklichkeit und Effekten.
    
    Args:
        dexterity (int): Der Geschicklichkeitswert
        effects_mod (int): Modifikator durch Status-Effekte
        
    Returns:
        int: Der Gesamtmodifikator für Genauigkeit
    """
    base_mod = calculate_attribute_bonus(dexterity)
    return base_mod + effects_mod


def calculate_evasion_modifier(dexterity: int, effects_mod: int = 0) -> int:
    """
    Berechnet den Ausweichmodifikator basierend auf Geschicklichkeit und Effekten.
    
    Args:
        dexterity (int): Der Geschicklichkeitswert
        effects_mod (int): Modifikator durch Status-Effekte
        
    Returns:
        int: Der Gesamtmodifikator für Ausweichen
    """
    base_mod = calculate_attribute_bonus(dexterity)
    return base_mod + effects_mod
