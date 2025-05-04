"""
CLI Manager Module

Hauptmodul für die Kommandozeilen-Benutzeroberfläche.
"""

import logging
import os
import sys
import time
from typing import Dict, List, Any, Optional

from src.game_logic.entity.player import Player
from src.game_logic.entity.enemy import Enemy
from src.ui.cli.combat_cli import CombatCLI
from src.ui.cli.cli_utils import clear_screen, colorize, get_input, print_title

# Logger für dieses Modul einrichten
logger = logging.getLogger(__name__)


class CLIManager:
    """
    Manager für die Kommandozeilen-Benutzeroberfläche des Spiels.
    
    Diese Klasse ist verantwortlich für die Darstellung des Hauptmenüs
    und die Navigation zwischen verschiedenen Spielbereichen.
    """
    
    def __init__(self) -> None:
        """
        Initialisiert einen neuen CLIManager.
        """
        self.running: bool = False
        self.current_player: Optional[Player] = None
        self.combat_cli = CombatCLI()
        
        logger.info("CLI Manager initialisiert")
    
    def start(self) -> None:
        """
        Startet die CLI und zeigt das Hauptmenü an.
        """
        self.running = True
        self.show_welcome_screen()
        
        while self.running:
            self.show_main_menu()
    
    def stop(self) -> None:
        """
        Beendet die CLI.
        """
        self.running = False
        print("\nDanke fürs Spielen! Bis zum nächsten Mal.")
        logger.info("Spiel beendet")
    
    def show_welcome_screen(self) -> None:
        """
        Zeigt den Willkommensbildschirm an.
        """
        clear_screen()
        print_title("Python RPG")
        print(colorize("\nWillkommen im Python RPG Testmodus!\n", "cyan"))
        print("Diese CLI-Version dient zum Testen des Kampfsystems.")
        print("Du kannst verschiedene Charaktere erstellen und gegen Gegner kämpfen.")
        print("\nDrücke Enter, um fortzufahren...")
        input()
    
    def show_main_menu(self) -> None:
        """
        Zeigt das Hauptmenü an und verarbeitet die Benutzereingabe.
        """
        clear_screen()
        print_title("Hauptmenü")
        
        options = [
            "Neuen Charakter erstellen",
            "Testkampf starten",
            "Beenden"
        ]
        
        # Falls bereits ein Charakter existiert, zeige dessen Status
        if self.current_player:
            print(f"\nAktueller Charakter: {colorize(self.current_player.name, 'green')} "
                  f"(Level {self.current_player.level} {self.current_player.character_class})\n")
        else:
            print("\nKein Charakter erstellt.\n")
        
        # Menüoptionen anzeigen
        for i, option in enumerate(options, 1):
            print(f"{i}. {option}")
        
        # Benutzereingabe verarbeiten
        choice = get_input("\nWähle eine Option (1-3): ", valid_range=(1, 3))
        
        if choice == 1:
            self.create_character()
        elif choice == 2:
            if self.current_player:
                self.start_test_combat()
            else:
                print("\nDu musst zuerst einen Charakter erstellen!")
                time.sleep(2)
        elif choice == 3:
            self.stop()
    
    def create_character(self) -> None:
        """
        Ermöglicht dem Benutzer, einen neuen Charakter zu erstellen.
        """
        clear_screen()
        print_title("Charaktererstellung")
        
        name = input("\nWie soll dein Charakter heißen? ")
        
        class_options = {
            1: "warrior",
            2: "mage",
            3: "rogue",
            4: "cleric"
        }
        
        print("\nVerfügbare Klassen:")
        print("1. Krieger (Hohe Stärke und Verteidigung)")
        print("2. Magier (Hohe Intelligenz und mächtige Zauber)")
        print("3. Schurke (Hohe Geschicklichkeit und kritische Treffer)")
        print("4. Kleriker (Ausgewogene Attribute und Heilfähigkeiten)")
        
        class_choice = get_input("Wähle eine Klasse (1-4): ", valid_range=(1, 4))
        character_class = class_options[class_choice]
        
        # Erzeuge einen neuen Spieler mit Basisattributen
        self.current_player = Player(
            name=name,
            character_class=character_class,
            level=1
        )
        
        print(f"\n{colorize('Charakter erstellt!', 'green')}")
        print(f"Name: {name}")
        print(f"Klasse: {character_class.capitalize()}")
        print(f"Level: 1")
        print("\nDrücke Enter, um fortzufahren...")
        input()
    
    def start_test_combat(self) -> None:
        """
        Startet einen Testkampf mit dem aktuellen Charakter.
        """
        if not self.current_player:
            logger.error("Versuch, einen Kampf ohne Spieler zu starten.")
            return
        
        clear_screen()
        print_title("Testkampf")
        
        difficulty_options = {
            1: "Leicht (1 schwacher Gegner)",
            2: "Mittel (2 normale Gegner)",
            3: "Schwer (3 Gegner, einer davon stark)"
        }
        
        print("\nWähle eine Schwierigkeitsstufe für den Kampf:")
        for key, value in difficulty_options.items():
            print(f"{key}. {value}")
        
        difficulty = get_input("Wähle eine Option (1-3): ", valid_range=(1, 3))
        
        # Generiere Gegner basierend auf der Schwierigkeit
        enemies = self._generate_enemies(difficulty)
        
        # Starte den Kampf in der CombatCLI
        self.combat_cli.start_combat(self.current_player, enemies)
    
    def _generate_enemies(self, difficulty: int) -> List[Enemy]:
        """
        Generiert Gegner basierend auf der ausgewählten Schwierigkeit.
        
        Args:
            difficulty: Schwierigkeitsstufe (1-3)
            
        Returns:
            Liste von generierten Gegnern
        """
        enemies = []
        
        if difficulty == 1:
            # Leicht: Eine Ratte
            enemies.append(Enemy(
                name="Aggressive Ratte",
                id="ratte_wild_1",
                level=1,
                hp=15,
                attack=3,
                defense=1
            ))
        
        elif difficulty == 2:
            # Mittel: Zwei Goblins
            enemies.append(Enemy(
                name="Goblin Kämpfer",
                id="goblin_kaempfer_1",
                level=2,
                hp=25,
                attack=4,
                defense=2
            ))
            
            enemies.append(Enemy(
                name="Goblin Plünderer",
                id="goblin_pluenderer_1",
                level=2,
                hp=20,
                attack=5,
                defense=1
            ))
        
        elif difficulty == 3:
            # Schwer: Zwei Goblins und ein Skelettkrieger
            enemies.append(Enemy(
                name="Goblin Anführer",
                id="goblin_anfuehrer_1",
                level=3,
                hp=30,
                attack=5,
                defense=3
            ))
            
            enemies.append(Enemy(
                name="Goblin Bogenschütze",
                id="goblin_bogenschuetze_1",
                level=2,
                hp=18,
                attack=6,
                defense=1
            ))
            
            enemies.append(Enemy(
                name="Skelettkrieger",
                id="skelett_krieger_1",
                level=3,
                hp=40,
                attack=6,
                defense=4
            ))
        
        return enemies


if __name__ == "__main__":
    # Konfiguriere das Logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("game.log"),
            logging.StreamHandler()
        ]
    )
    
    # Starte die CLI
    cli = CLIManager()
    try:
        cli.start()
    except KeyboardInterrupt:
        print("\nSpiel durch Benutzer beendet.")
    except Exception as e:
        logger.exception(f"Unerwarteter Fehler: {str(e)}")
        print(f"\nEs ist ein Fehler aufgetreten: {str(e)}")
        print("Bitte überprüfe die Logdatei für mehr Informationen.")
    
    sys.exit(0)
