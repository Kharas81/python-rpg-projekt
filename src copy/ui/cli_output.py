# src/ui/cli_output.py
"""
Modul für formatierte Kommandozeilen-Ausgaben für die RPG-Simulation.
"""
import logging
from typing import List, Optional, Dict, Any

# Importe für Typ-Annotationen (falls komplexere Objekte formatiert werden)
if True: # Um Zirkularimport zu vermeiden
    from src.game_logic.entities import CharacterInstance
    from src.definitions.skill import SkillTemplate
    from src.game_logic.effects import StatusEffect


logger = logging.getLogger(__name__)

# ANSI-Escape-Codes für Farben (optional, zur besseren Lesbarkeit)
# Diese funktionieren möglicherweise nicht in allen Terminals gleich gut.
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"

    # Standardfarben
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Helle Farben
    LIGHT_RED = "\033[91m"
    LIGHT_GREEN = "\033[92m"
    LIGHT_YELLOW = "\033[93m"
    LIGHT_BLUE = "\033[94m"
    LIGHT_MAGENTA = "\033[95m"
    LIGHT_CYAN = "\033[96m"

    # Hintergrundfarben (seltener verwendet für CLI-Log)
    # BG_RED = "\033[41m"
    # BG_GREEN = "\033[42m"

USE_COLORS = True # Globale Einstellung, um Farben an-/abzuschalten

def _c(text: str, color_code: str) -> str:
    """Hilfsfunktion zum Anwenden von Farben, wenn USE_COLORS True ist."""
    return f"{color_code}{text}{Colors.RESET}" if USE_COLORS else text

def print_message(message: str, color: Optional[str] = None, bold: bool = False, underline: bool = False):
    """Gibt eine formatierte Nachricht auf der Konsole aus."""
    prefix = ""
    if bold: prefix += Colors.BOLD
    if underline: prefix += Colors.UNDERLINE
    
    output_message = message
    if color:
        output_message = f"{prefix}{color}{message}{Colors.RESET}"
    elif prefix: # Nur Bold/Underline ohne Farbe
        output_message = f"{prefix}{message}{Colors.RESET}"
        
    print(output_message)
    # Zusätzlich ins Logging, aber nur die reine Nachricht ohne ANSI-Codes
    # logger.info(message) # Oder je nach Kontext einen anderen Log-Level

def display_character_status(char_instance: 'CharacterInstance', is_player_team: bool = True):
    """Zeigt den Status einer Charakterinstanz an."""
    color = Colors.LIGHT_GREEN if is_player_team else Colors.LIGHT_RED
    name_str = _c(f"{char_instance.name} (Lvl {char_instance.level})", color + Colors.BOLD)
    
    hp_color = Colors.GREEN
    if char_instance.current_hp / char_instance.max_hp < 0.3:
        hp_color = Colors.RED
    elif char_instance.current_hp / char_instance.max_hp < 0.6:
        hp_color = Colors.YELLOW
        
    hp_str = _c(f"HP: {char_instance.current_hp}/{char_instance.max_hp}", hp_color)
    shield_str = _c(f"Schild: {char_instance.shield_points}", Colors.CYAN) if char_instance.shield_points > 0 else ""

    # Ressourcen anzeigen (Mana, Stamina, Energy)
    resources = []
    if char_instance.max_mana > 0:
        resources.append(_c(f"Mana: {char_instance.current_mana}/{char_instance.max_mana}", Colors.BLUE))
    if char_instance.max_stamina > 0:
        resources.append(_c(f"Stamina: {char_instance.current_stamina}/{char_instance.max_stamina}", Colors.YELLOW))
    if char_instance.max_energy > 0:
        resources.append(_c(f"Energy: {char_instance.current_energy}/{char_instance.max_energy}", Colors.MAGENTA))
    
    resource_str = " | ".join(r for r in resources if r)

    status_line = f"{name_str} | {hp_str}"
    if shield_str:
        status_line += f" | {shield_str}"
    if resource_str:
        status_line += f" | {resource_str}"

    print(status_line)

    # Status-Effekte anzeigen
    if char_instance.status_effects:
        effects_str_parts = []
        for effect in char_instance.status_effects:
            eff_color = Colors.LIGHT_GREEN if effect.is_positive else Colors.LIGHT_RED
            effects_str_parts.append(_c(f"{effect.name}({effect.current_potency:.0f}, {effect.remaining_duration}R)", eff_color))
        print(f"  └ Effekte: {', '.join(effects_str_parts)}")
    
    if char_instance.is_defeated:
        print(_c("  └ BESIEGT", Colors.RED + Colors.BOLD))


def display_combat_action(actor_name: str, skill_name: str, target_name: Optional[str], details: str = ""):
    """Zeigt eine durchgeführte Kampfaktion an."""
    actor_c = _c(actor_name, Colors.LIGHT_YELLOW)
    skill_c = _c(skill_name, Colors.CYAN + Colors.BOLD)
    
    if target_name:
        target_c = _c(target_name, Colors.LIGHT_MAGENTA)
        action_str = f"{actor_c} setzt '{skill_c}' auf {target_c} ein."
    else: # Skill auf sich selbst oder ohne Ziel
        action_str = f"{actor_c} setzt '{skill_c}' ein."
        
    if details:
        action_str += f" ({details})"
        
    print(action_str)

def display_damage_taken(target_name: str, damage_amount: int, damage_type: str, new_hp: int, max_hp: int, absorbed_by_shield: int = 0):
    """Zeigt erlittenen Schaden an."""
    target_c = _c(target_name, Colors.LIGHT_MAGENTA)
    damage_c = _c(str(damage_amount), Colors.RED + Colors.BOLD)
    type_c = _c(damage_type.upper(), Colors.RED)
    
    absorbed_str = ""
    if absorbed_by_shield > 0:
        absorbed_str = _c(f" ({absorbed_by_shield} vom Schild absorbiert)", Colors.CYAN)
        
    print(f"{target_c} erleidet {damage_c} {type_c} Schaden!{absorbed_str} (HP: {new_hp}/{max_hp})")

def display_healing_received(target_name: str, heal_amount: int, new_hp: int, max_hp: int):
    """Zeigt erhaltene Heilung an."""
    target_c = _c(target_name, Colors.LIGHT_MAGENTA)
    heal_c = _c(str(heal_amount), Colors.GREEN + Colors.BOLD)
    print(f"{target_c} wird um {heal_c} HP geheilt! (HP: {new_hp}/{max_hp})")

def display_status_effect_applied(target_name: str, effect_name: str, duration: int):
    """Zeigt an, dass ein Status-Effekt angewendet wurde."""
    target_c = _c(target_name, Colors.LIGHT_MAGENTA)
    effect_c = _c(effect_name, Colors.YELLOW)
    print(f"{target_c} ist jetzt von '{effect_c}' betroffen (Dauer: {duration} Runden).")

def display_status_effect_removed(target_name: str, effect_name: str):
    """Zeigt an, dass ein Status-Effekt entfernt wurde."""
    target_c = _c(target_name, Colors.LIGHT_MAGENTA)
    effect_c = _c(effect_name, Colors.YELLOW)
    print(f"'{effect_c}' wurde von {target_c} entfernt.")

def display_miss(actor_name: str, target_name: str, skill_name: Optional[str] = None):
    """Zeigt einen verfehlten Angriff an."""
    actor_c = _c(actor_name, Colors.LIGHT_YELLOW)
    target_c = _c(target_name, Colors.LIGHT_MAGENTA)
    if skill_name:
        skill_c = _c(skill_name, Colors.CYAN)
        print(f"{actor_c} verfehlt {target_c} mit '{skill_c}'.")
    else:
        print(f"{actor_c} verfehlt {target_c}.")
        
def display_combat_round_start(round_number: int):
    """Zeigt den Beginn einer neuen Kampfrunde an."""
    print_message(f"\n--- Runde {round_number} beginnt ---", Colors.BOLD + Colors.YELLOW)

def display_combat_end(victory_team_name: Optional[str] = None):
    """Zeigt das Ende des Kampfes an."""
    if victory_team_name:
        print_message(f"\n=== KAMPF BEENDET - Team '{victory_team_name}' hat gewonnen! ===", Colors.BOLD + Colors.LIGHT_GREEN)
    else:
        print_message("\n=== KAMPF BEENDET (Unentschieden oder unbekannter Ausgang) ===", Colors.BOLD + Colors.YELLOW)

def display_xp_gain(character_name: str, xp_amount: int):
    """Zeigt erhaltene Erfahrungspunkte an."""
    char_c = _c(character_name, Colors.LIGHT_GREEN)
    xp_c = _c(str(xp_amount), Colors.CYAN)
    print(f"{char_c} erhält {xp_c} Erfahrungspunkte.")

def display_level_up(character_name: str, new_level: int):
    """Zeigt einen Levelaufstieg an."""
    char_c = _c(character_name, Colors.LIGHT_GREEN + Colors.BOLD)
    level_c = _c(str(new_level), Colors.YELLOW + Colors.BOLD)
    print_message(f"LEVEL UP! {char_c} hat Level {level_c} erreicht!", Colors.BOLD + Colors.YELLOW)

if __name__ == '__main__':
    # Testen der cli_output Funktionen
    # Erstelle Dummy-Objekte für den Test
    class DummyEffect:
        def __init__(self, name, potency, duration, is_positive):
            self.name = name
            self.current_potency = potency
            self.remaining_duration = duration
            self.is_positive = is_positive
        def __str__(self): return f"{self.name}({self.current_potency}, {self.remaining_duration}R)"

    class DummyChar:
        def __init__(self, name, level, hp, max_hp, mana=0, max_mana=0, stamina=0, max_stamina=0, energy=0, max_energy=0, shield=0, defeated=False):
            self.name = name
            self.level = level
            self.current_hp = hp
            self.max_hp = max_hp
            self.current_mana = mana
            self.max_mana = max_mana
            self.current_stamina = stamina
            self.max_stamina = max_stamina
            self.current_energy = energy
            self.max_energy = max_energy
            self.shield_points = shield
            self.is_defeated = defeated
            self.status_effects: List[DummyEffect] = []
        def add_effect(self, name, potency, duration, is_positive):
            self.status_effects.append(DummyEffect(name, potency, duration, is_positive))

    print_message("Starte CLI Output Tests...", Colors.BOLD)
    
    player = DummyChar("Held Karras", 5, 80, 100, mana=50, max_mana=70, shield=10)
    player.add_effect("Regeneration", 5, 3, True)
    player.add_effect("Brennen", 3, 2, False)
    
    enemy = DummyChar("Goblin Boss", 3, 40, 60, stamina=30, max_stamina=30)
    enemy_defeated = DummyChar("Besiegter Goblin", 1, 0, 30, defeated=True)

    display_combat_round_start(1)
    
    print("\n-- Charakterstatus --")
    display_character_status(player, is_player_team=True)
    display_character_status(enemy, is_player_team=False)
    display_character_status(enemy_defeated, is_player_team=False)
    
    print("\n-- Kampfaktionen --")
    display_combat_action("Held Karras", "Feuerball", "Goblin Boss", "15 Schaden")
    display_damage_taken("Goblin Boss", 15, "FIRE", 25, 60)
    display_healing_received("Held Karras", 20, 100, 100)
    display_status_effect_applied("Goblin Boss", "Brennen", 2)
    display_miss("Goblin Boss", "Held Karras", "Wilder Schlag")
    display_status_effect_removed("Goblin Boss", "Brennen")
    
    print("\n-- XP und Level Up --")
    display_xp_gain("Held Karras", 150)
    display_level_up("Held Karras", 6)
    
    display_combat_end("Spieler-Team")

    print_message("\nCLI Output Tests abgeschlossen.", Colors.BOLD)
    print_message("Test mit deaktivierten Farben:")
    USE_COLORS = False
    display_character_status(player, is_player_team=True)
    display_combat_action("Held Karras", "Mächtiger Hieb", "Goblin Boss")