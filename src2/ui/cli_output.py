"""
CLI-Ausgabehelfer

Enthält Funktionen für formatierte Ausgaben in der Konsole.
"""
import time
import os
from typing import List, Dict, Any, Optional

from src.game_logic.entities import CharacterInstance
from src.utils.logging_setup import get_logger


# Logger für dieses Modul
logger = get_logger(__name__)


class CLIOutput:
    """
    Klasse für formatierte Konsolenausgaben.
    """
    
    def __init__(self, verbose: bool = True, delay: float = 0.5):
        """
        Initialisiert den CLI-Output-Handler.
        
        Args:
            verbose (bool): Wenn True, werden detaillierte Ausgaben angezeigt
            delay (float): Verzögerung in Sekunden zwischen Ausgaben
        """
        self.verbose = verbose
        self.delay = delay
    
    def clear_screen(self) -> None:
        """Löscht den Bildschirm."""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def wait(self, seconds: Optional[float] = None) -> None:
        """
        Wartet für die angegebene Zeit.
        
        Args:
            seconds (Optional[float]): Die Wartezeit in Sekunden (Standard: self.delay)
        """
        if seconds is None:
            seconds = self.delay
        
        if seconds > 0:
            time.sleep(seconds)
    
    def print_header(self, text: str) -> None:
        """
        Gibt einen hervorgehobenen Überschriftentext aus.
        
        Args:
            text (str): Der anzuzeigende Text
        """
        print("\n" + "=" * 60)
        print(f" {text.upper()} ")
        print("=" * 60 + "\n")
        self.wait(self.delay / 2)
    
    def print_subheader(self, text: str) -> None:
        """
        Gibt einen hervorgehobenen Unterüberschriftentext aus.
        
        Args:
            text (str): Der anzuzeigende Text
        """
        print("\n" + "-" * 50)
        print(f" {text} ")
        print("-" * 50 + "\n")
        self.wait(self.delay / 3)
    
    def print_message(self, message: str) -> None:
        """
        Gibt eine einfache Nachricht aus.
        
        Args:
            message (str): Die anzuzeigende Nachricht
        """
        print(message)
        self.wait(self.delay / 2)
    
    def print_combat_action(self, actor_name: str, action_name: str, target_name: str, result: str) -> None:
        """
        Gibt eine formatierte Kampfaktion aus.
        
        Args:
            actor_name (str): Name des Akteurs
            action_name (str): Name der Aktion
            target_name (str): Name des Ziels
            result (str): Ergebnis der Aktion
        """
        print(f"[AKTION] {actor_name} verwendet {action_name} gegen {target_name}: {result}")
        self.wait()
    
    def print_character_stats(self, character: CharacterInstance, detailed: bool = False) -> None:
        """
        Gibt die Statistiken eines Charakters aus.
        
        Args:
            character (CharacterInstance): Der Charakter
            detailed (bool): Wenn True, werden detaillierte Statistiken angezeigt
        """
        health_percent = round((character.hp / character.get_max_hp()) * 100)
        health_bar = self._generate_bar(health_percent, 20)
        
        print(f"{character.name} (Level {character.level}):")
        print(f"HP: {character.hp}/{character.get_max_hp()} {health_bar} ({health_percent}%)")
        
        # Ressourcen anzeigen, falls vorhanden
        if character.mana > 0:
            print(f"Mana: {character.mana}/{character.base_combat_values.get('base_mana', 0)}")
        if character.stamina > 0:
            print(f"Ausdauer: {character.stamina}/{character.base_combat_values.get('base_stamina', 0)}")
        if character.energy > 0:
            print(f"Energie: {character.energy}/{character.base_combat_values.get('base_energy', 0)}")
        
        # Status-Effekte anzeigen
        if character.active_effects:
            effect_names = [f"{effect_id} ({effect.duration}R)" for effect_id, effect in character.active_effects.items()]
            print(f"Effekte: {', '.join(effect_names)}")
        
        # Detaillierte Statistiken
        if detailed and self.verbose:
            print(f"ATT: STR {character.get_attribute('STR')}, "
                  f"DEX {character.get_attribute('DEX')}, "
                  f"INT {character.get_attribute('INT')}, "
                  f"CON {character.get_attribute('CON')}, "
                  f"WIS {character.get_attribute('WIS')}")
            print(f"DEF: Rüstung {character.get_combat_value('armor')}, "
                  f"Magieresistenz {character.get_combat_value('magic_resist')}")
            print(f"Genauigkeit: {character.get_accuracy()}, Ausweichen: {character.get_evasion()}")
        
        if self.verbose:
            self.wait(self.delay / 4)
    
    def print_combat_summary(self, players: List[CharacterInstance], opponents: List[CharacterInstance]) -> None:
        """
        Gibt eine Zusammenfassung des aktuellen Kampfzustands aus.
        
        Args:
            players (List[CharacterInstance]): Die Spielercharaktere
            opponents (List[CharacterInstance]): Die Gegner
        """
        self.print_subheader("KAMPFÜBERSICHT")
        
        print("SPIELER:")
        for player in players:
            self.print_character_stats(player)
        
        print("\nGEGNER:")
        for opponent in opponents:
            self.print_character_stats(opponent)
        
        print("")  # Leerzeile zur besseren Lesbarkeit
    
    def _generate_bar(self, percent: int, length: int = 20) -> str:
        """
        Generiert einen grafischen Fortschrittsbalken.
        
        Args:
            percent (int): Der Prozentsatz (0-100)
            length (int): Die Länge des Balkens
            
        Returns:
            str: Der grafische Balken
        """
        fill_count = int(percent / 100 * length)
        empty_count = length - fill_count
        
        if percent >= 60:
            color = '\033[92m'  # Grün
        elif percent >= 25:
            color = '\033[93m'  # Gelb
        else:
            color = '\033[91m'  # Rot
        
        reset = '\033[0m'
        
        return f"{color}[{'=' * fill_count}{' ' * empty_count}]{reset}"


# Globaler CLIOutput-Handler
cli_output = CLIOutput()


def get_cli_output() -> CLIOutput:
    """
    Gibt den globalen CLIOutput-Handler zurück.
    
    Returns:
        CLIOutput: Der globale Handler
    """
    return cli_output