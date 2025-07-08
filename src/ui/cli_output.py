# src/ui/cli_output.py
"""
Modul für formatierte Kommandozeilen-Ausgaben für die RPG-Simulation.
Loggt wichtige Kampfmeldungen auch in eine Datei über den "cli_kampf_log" Logger.
Berücksichtigt jetzt einen Ausführungskontext (z.B. RL-Training) für reduzierte Ausgaben.
"""
import logging
import re
from typing import List, Optional, Dict, Any

# KORREKTUR: Der Importpfad für StatusEffect wird hier korrigiert.
from src.game_logic.entities import CharacterInstance
from src.game_logic.combat.effects.base_effect import StatusEffect


# Globaler Logger für dieses Modul (nicht für Kampfdetails)
module_logger = logging.getLogger(__name__)
# Dedizierter Logger für Kampfdetails, der in eine separate Datei schreibt
kampf_logger = logging.getLogger("combat_log")

class Colors:
    RESET = "\033[0m"; BOLD = "\033[1m"; UNDERLINE = "\033[4m"
    BLACK = "\033[30m"; RED = "\033[31m"; GREEN = "\033[32m"; YELLOW = "\033[33m"
    BLUE = "\033[34m"; MAGENTA = "\033[35m"; CYAN = "\033[36m"; WHITE = "\033[37m"
    LIGHT_RED = "\033[91m"; LIGHT_GREEN = "\033[92m"; LIGHT_YELLOW = "\033[93m"
    LIGHT_BLUE = "\033[94m"; LIGHT_MAGENTA = "\033[95m"; LIGHT_CYAN = "\033[96m"

USE_COLORS_GLOBALLY = True
ANSI_ESCAPE_PATTERN = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

_EXECUTION_CONTEXT: Optional[str] = None
_RL_OUTPUT_SETTINGS: Dict[str, Any] = {}

def _load_rl_output_settings_if_needed():
    global _RL_OUTPUT_SETTINGS
    if not _RL_OUTPUT_SETTINGS:
        try:
            from src.config.config import CONFIG
            if CONFIG:
                _RL_OUTPUT_SETTINGS = CONFIG.get("rl_output_settings", {})
                module_logger.debug(f"RL Output Settings geladen: {_RL_OUTPUT_SETTINGS}")
            else:
                module_logger.warning("CONFIG nicht verfügbar für _load_rl_output_settings_if_needed.")
        except ImportError:
            module_logger.error("Fehler beim Import von CONFIG für RL Output Settings.")
        except Exception as e:
            module_logger.error(f"Unerwarteter Fehler beim Laden der RL Output Settings: {e}")

def set_execution_context(context: Optional[str]):
    global _EXECUTION_CONTEXT
    old_context = _EXECUTION_CONTEXT
    _EXECUTION_CONTEXT = context
    if old_context != _EXECUTION_CONTEXT:
        module_logger.info(f"Ausführungskontext geändert von '{old_context}' zu '{_EXECUTION_CONTEXT}'.")
        _load_rl_output_settings_if_needed()

def _should_use_rich_colors() -> bool:
    _load_rl_output_settings_if_needed()
    if _EXECUTION_CONTEXT == "rl_training":
        force_disable = _RL_OUTPUT_SETTINGS.get("force_disable_rich_colors_in_rl_console", True)
        verbosity = _RL_OUTPUT_SETTINGS.get("console_verbosity_during_training", "minimal")
        if force_disable and verbosity != "normal":
            return False
    return USE_COLORS_GLOBALLY

def _get_console_verbosity() -> str:
    _load_rl_output_settings_if_needed()
    if _EXECUTION_CONTEXT == "rl_training":
        return _RL_OUTPUT_SETTINGS.get("console_verbosity_during_training", "minimal")
    return "normal"

def _clean_ansi(text: str) -> str:
    return ANSI_ESCAPE_PATTERN.sub('', text)

def _c(text: str, color_code: str) -> str:
    return f"{color_code}{text}{Colors.RESET}" if _should_use_rich_colors() else text

def _log_to_combat_file(message: str, level: int = logging.INFO):
    clean_message = _clean_ansi(message)
    kampf_logger.log(level, clean_message)

def print_message(message: str, color: Optional[str] = None, bold: bool = False,
                  underline: bool = False, log_to_combat: bool = False, log_level: int = logging.INFO,
                  force_console: bool = False):
    console_verbosity = _get_console_verbosity()
    if log_to_combat:
        _log_to_combat_file(message, log_level)
    if not force_console:
        if console_verbosity == "none": return
        if console_verbosity == "minimal" and log_level < logging.WARNING: return

    prefix = ""
    if bold: prefix += Colors.BOLD
    if underline: prefix += Colors.UNDERLINE

    console_message = message
    if _should_use_rich_colors():
        if color: console_message = f"{prefix}{color}{message}{Colors.RESET}"
        elif prefix: console_message = f"{prefix}{message}{Colors.RESET}"
    
    print(console_message)

def format_character_status_line(char_instance: 'CharacterInstance', is_player_team: bool, no_prefix: bool = False) -> str:
    """Gibt eine einzelne, formatierte Zeile für den Charakterstatus zurück."""
    color = Colors.LIGHT_GREEN if is_player_team else Colors.LIGHT_RED
    name_str = _c(f"{char_instance.name} (Lvl {char_instance.level})", color + Colors.BOLD)
    
    hp_color = Colors.GREEN
    hp_perc = char_instance.current_hp / char_instance.max_hp if char_instance.max_hp > 0 else 0
    if hp_perc < 0.3: hp_color = Colors.RED
    elif hp_perc < 0.6: hp_color = Colors.YELLOW
    
    hp_str = _c(f"HP: {char_instance.current_hp}/{char_instance.max_hp}", hp_color)
    shield_str = _c(f"Schild: {char_instance.shield_points}", Colors.CYAN) if char_instance.shield_points > 0 else ""

    resources = []
    res_type_map = {"MANA": (char_instance.current_mana, char_instance.max_mana, Colors.BLUE),
                    "STAMINA": (char_instance.current_stamina, char_instance.max_stamina, Colors.YELLOW),
                    "ENERGY": (char_instance.current_energy, char_instance.max_energy, Colors.MAGENTA)}
    
    if hasattr(char_instance.base_template, 'resource_type'):
        res_type = char_instance.base_template.resource_type
        if res_type and res_type != "NONE" and res_type in res_type_map:
            current, max_val, res_color = res_type_map[res_type]
            if max_val > 0: resources.append(_c(f"{res_type[0]}: {current}/{max_val}", res_color))

    resource_str = " | ".join(r for r in resources if r)
    
    prefix_str = "  " if not no_prefix else ""
    status_line = f"{prefix_str}{name_str} | {hp_str}{f' | {shield_str}' if shield_str else ''}{f' | {resource_str}' if resource_str else ''}"
    
    return status_line

def display_character_status(char_instance: 'CharacterInstance', is_player_team: bool = True):
    if _get_console_verbosity() == "none": return
    print(format_character_status_line(char_instance, is_player_team))

    if _get_console_verbosity() == "normal" and char_instance.status_effects:
        effects_str_parts = [_c(f"{eff.name}({eff.current_potency:.0f}, {eff.remaining_duration}R)", Colors.LIGHT_GREEN if eff.is_positive else Colors.LIGHT_RED) for eff in char_instance.status_effects]
        print(f"  └ Effekte: {', '.join(effects_str_parts)}")

    if char_instance.is_defeated:
        print_message(f"  └ {char_instance.name} BESIEGT", Colors.RED + Colors.BOLD, force_console=True)

def display_combat_action(actor_name: str, skill_name: str, target_name: Optional[str], details: str = ""):
    log_message = f"{actor_name} setzt '{skill_name}'"
    if target_name: log_message += f" auf {target_name}"
    log_message += " ein."
    if details: log_message += f" ({details})"
    _log_to_combat_file(log_message)

    if _get_console_verbosity() != "normal": return

    actor_c = _c(actor_name, Colors.LIGHT_YELLOW)
    skill_c = _c(skill_name, Colors.CYAN + Colors.BOLD)
    target_c_str = _c(target_name, Colors.LIGHT_MAGENTA) if target_name else ""
    console_msg = f"{actor_c} setzt '{skill_c}'"
    if target_name: console_msg += f" auf {target_c_str}"
    console_msg += " ein."
    if details: console_msg += f" ({_c(details, Colors.WHITE)})"
    print(console_msg)

def display_damage_taken(target_name: str, damage_amount: int, damage_type: str, new_hp: int, max_hp: int, absorbed_by_shield: int = 0):
    absorbed_str_log = f" ({absorbed_by_shield} Schild absorbiert)" if absorbed_by_shield > 0 else ""
    log_message = f"{target_name} erleidet {damage_amount} {damage_type.upper()} Schaden!{absorbed_str_log} (HP: {new_hp}/{max_hp})"
    _log_to_combat_file(log_message)

    if _get_console_verbosity() != "normal": return

    target_c=_c(target_name, Colors.LIGHT_MAGENTA); damage_c=_c(str(damage_amount), Colors.RED+Colors.BOLD); type_c=_c(damage_type.upper(), Colors.RED)
    absorbed_c_str = _c(f" ({absorbed_by_shield} Schild absorbiert)", Colors.CYAN) if absorbed_by_shield > 0 else ""
    print(f"{target_c} erleidet {damage_c} {type_c} Schaden!{absorbed_c_str} (HP: {new_hp}/{max_hp})")

def display_healing_received(target_name: str, heal_amount: int, new_hp: int, max_hp: int):
    log_message = f"{target_name} wird um {heal_amount} HP geheilt! (HP: {new_hp}/{max_hp})"
    _log_to_combat_file(log_message)

    if _get_console_verbosity() != "normal": return

    target_c=_c(target_name, Colors.LIGHT_MAGENTA); heal_c=_c(str(heal_amount), Colors.GREEN+Colors.BOLD)
    print(f"{target_c} wird um {heal_c} HP geheilt! (HP: {new_hp}/{max_hp})")

def display_status_effect_applied(target_name: str, effect_name: str, duration: int):
    log_message = f"{target_name} ist jetzt von '{effect_name}' betroffen (Dauer: {duration} Runden)."
    _log_to_combat_file(log_message)

    if _get_console_verbosity() != "normal": return

    target_c=_c(target_name, Colors.LIGHT_MAGENTA); effect_c=_c(effect_name, Colors.YELLOW)
    print(f"{target_c} ist jetzt von '{effect_c}' betroffen (Dauer: {duration} Runden).")

def display_status_effect_removed(target_name: str, effect_name: str):
    log_message = f"'{effect_name}' wurde von {target_name} entfernt."
    _log_to_combat_file(log_message)

    if _get_console_verbosity() != "normal": return

    target_c=_c(target_name, Colors.LIGHT_MAGENTA); effect_c=_c(effect_name, Colors.YELLOW)
    print(f"'{effect_c}' wurde von {target_c} entfernt.")

def display_miss(actor_name: str, target_name: str, skill_name: Optional[str] = None):
    log_message = f"{actor_name} verfehlt {target_name}" + (f" mit '{skill_name}'." if skill_name else ".")
    _log_to_combat_file(log_message)

    if _get_console_verbosity() != "normal": return

    actor_c=_c(actor_name, Colors.LIGHT_YELLOW); target_c=_c(target_name, Colors.LIGHT_MAGENTA)
    console_message = f"{actor_c} verfehlt {target_c}";
    if skill_name: console_message += f" mit '{_c(skill_name, Colors.CYAN)}'."
    else: console_message += "."
    print(console_message)

def display_combat_round_start(round_number: int):
    log_message = f"--- Runde {round_number} beginnt ---"
    print_message(log_message, Colors.BOLD + Colors.YELLOW, log_to_combat=True, force_console=(_get_console_verbosity() == "minimal"))

def display_combat_end(victory_team_name: Optional[str] = None):
    log_message = f"=== KAMPF BEENDET - Team '{victory_team_name}' hat gewonnen! ===" if victory_team_name \
                  else "=== KAMPF BEENDET (Unentschieden oder unbekannter Ausgang) ==="
    color = Colors.BOLD + Colors.LIGHT_GREEN if victory_team_name else Colors.BOLD + Colors.YELLOW
    print_message(log_message, color, log_to_combat=True, force_console=True)

def display_xp_gain(character_name: str, xp_amount: int):
    log_message = f"{character_name} erhält {xp_amount} Erfahrungspunkte."
    _log_to_combat_file(log_message)

    if _get_console_verbosity() != "normal": return

    char_c=_c(character_name, Colors.LIGHT_GREEN); xp_c=_c(str(xp_amount), Colors.CYAN)
    print(f"{char_c} erhält {xp_c} Erfahrungspunkte.")

def display_level_up(character_name: str, new_level: int):
    log_message = f"LEVEL UP! {character_name} hat Level {new_level} erreicht!"
    color = Colors.BOLD + Colors.YELLOW
    print_message(log_message, color, log_to_combat=True, force_console=True)

_load_rl_output_settings_if_needed()