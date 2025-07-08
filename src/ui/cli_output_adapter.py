# src/ui/cli_output_adapter.py
"""
Adapter class that implements the CombatOutputInterface using the
functions from the src.ui.cli_output module.
"""
from typing import Optional

# Importiere das Interface und unser existierendes cli_output Modul
from src.game_logic.combat.interfaces import CombatOutputInterface
from src.ui import cli_output

class CliOutputAdapter(CombatOutputInterface):
    """
    Concrete implementation of CombatOutputInterface that routes calls
    to the existing cli_output module's functions.
    """
    def display_combat_action(self, actor_name: str, skill_name: str,
                              target_name: Optional[str], details: str = "") -> None:
        cli_output.display_combat_action(actor_name, skill_name, target_name, details)

    def display_damage_taken(self, target_name: str, damage_amount: int, damage_type: str,
                             new_hp: int, max_hp: int, absorbed_by_shield: int = 0) -> None:
        # damage_amount hier ist der Schaden, der nach Rüstung/MR und Minimalschaden
        # für die HP-Reduktion oder Schildabsorption relevant ist.
        cli_output.display_damage_taken(target_name, damage_amount, damage_type.upper(),
                                        new_hp, max_hp, absorbed_by_shield)

    def display_healing_received(self, target_name: str, heal_amount: int,
                                 new_hp: int, max_hp: int) -> None:
        cli_output.display_healing_received(target_name, heal_amount, new_hp, max_hp)

    def display_status_effect_applied(self, target_name: str, effect_name: str,
                                      duration: int) -> None:
        cli_output.display_status_effect_applied(target_name, effect_name, duration)

    def display_status_effect_refreshed(self, target_name: str, effect_name: str,
                                        new_duration: int, new_potency: float) -> None:
        # cli_output hat keine dedizierte "refreshed" Methode.
        # Wir verwenden print_message für eine informative Ausgabe.
        message = (f"Effekt '{effect_name}' auf {target_name} aktualisiert: "
                   f"Dauer {new_duration}R, Potenz {new_potency:.1f}.")
        cli_output.print_message(message, color=cli_output.Colors.YELLOW, log_to_combat=True)

    def display_status_effect_removed(self, target_name: str, effect_name: str) -> None:
        cli_output.display_status_effect_removed(target_name, effect_name)

    def display_miss(self, actor_name: str, target_name: str,
                     skill_name: Optional[str] = None) -> None:
        cli_output.display_miss(actor_name, target_name, skill_name)

    def display_cannot_act(self, actor_name: str, reason: Optional[str] = None) -> None:
        message = f"{actor_name} kann nicht handeln"
        if reason:
            message += f" ({reason})"
        message += "."
        cli_output.print_message(message, color=cli_output.Colors.YELLOW, log_to_combat=True)
        
    def display_no_valid_targets(self, actor_name: str, skill_name: str) -> None:
        message = f"{actor_name} findet keine gültigen Ziele für {skill_name}."
        cli_output.print_message(message, color=cli_output.Colors.YELLOW, log_to_combat=True)
        
    def display_insufficient_resources(self, actor_name: str, skill_name: str,
                                       resource_type: str, required_amount: int) -> None:
        message = (f"{actor_name} hat nicht genug {resource_type.upper()} für {skill_name} "
                   f"(benötigt: {required_amount}).")
        cli_output.print_message(message, color=cli_output.Colors.YELLOW, log_to_combat=True)

    def display_execute_condition_not_met(self, actor_name: str, skill_name: str, target_name: str) -> None:
        message = f"{skill_name} kann nicht auf {target_name} angewendet werden (Bedingung nicht erfüllt)."
        cli_output.print_message(message, color=cli_output.Colors.YELLOW, log_to_combat=True)

    def log_combat_info(self, message: str, to_console: bool = False) -> None:
        # Die `to_console`-Flag steuert, ob die Nachricht auch auf der Konsole erscheint,
        # zusätzlich zum dedizierten Kampf-Log (falls print_message das so handhabt).
        cli_output.print_message(message, log_to_combat=True, force_console=to_console)