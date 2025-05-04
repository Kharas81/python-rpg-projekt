"""
CLI Manager Module

Hauptmodul für die Kommandozeilen-Benutzeroberfläche.
"""

import logging
import os
import sys
import time
import json
import random
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
        self.mode = "auto"  # Standardmäßig auto-Modus
        
        # Lade die Charakterdaten aus der JSON-Datei
        self.character_data = self._load_character_data()
        self.enemy_data = self._load_enemy_data()
        
        logger.info("CLI Manager initialisiert")
    
    def _load_character_data(self) -> Dict[str, Any]:
        """
        Lädt die Charakterdaten aus der JSON-Datei.
        
        Returns:
            Dictionary mit den Charakterdaten
        """
        try:
            with open('src/definitions/json_data/characters.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info("Charakterdaten erfolgreich geladen")
                return data
        except FileNotFoundError:
            # Falls die Datei nicht im regulären Pfad ist, versuche einen alternativen Pfad
            try:
                with open('characters.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.info("Charakterdaten aus alternativem Pfad geladen")
                    return data
            except FileNotFoundError:
                logger.warning("Charakterdaten konnten nicht geladen werden")
                return {"character_classes": {
                    "warrior": {
                        "name": "Krieger",
                        "level": 1,
                        "attributes": {"strength": 15, "dexterity": 10, "intelligence": 5, "constitution": 14, "wisdom": 6},
                        "defenses": {"armor": 5, "magic_resistance": 1},
                        "resources": {"max_stamina": 100, "max_energy": None, "max_mana": None},
                        "known_skills": ["basic_strike_phys"]
                    }
                }}
    
    def _load_enemy_data(self) -> Dict[str, Any]:
        """
        Lädt die Gegnerdaten aus der JSON-Datei.
        
        Returns:
            Dictionary mit den Gegnerdaten
        """
        try:
            with open('src/definitions/json_data/enemies.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info("Gegnerdaten erfolgreich geladen")
                return data
        except FileNotFoundError:
            # Falls die Datei nicht im regulären Pfad ist, versuche einen alternativen Pfad
            try:
                with open('enemies.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.info("Gegnerdaten aus alternativem Pfad geladen")
                    return data
            except FileNotFoundError:
                logger.warning("Gegnerdaten konnten nicht geladen werden")
                return {"enemies": {
                    "goblin": {
                        "id": "goblin",
                        "name": "Goblin",
                        "level": 1,
                        "attributes": {"strength": 8, "dexterity": 12, "intelligence": 5, "constitution": 9, "wisdom": 5},
                        "defenses": {"armor": 2, "magic_resistance": 0},
                        "resources": {"max_stamina": 50, "max_energy": None, "max_mana": None},
                        "known_skills": ["basic_strike_phys"]
                    }
                }}
    
    def start(self, mode: str = "auto") -> None:
        """
        Startet die CLI und zeigt das Hauptmenü an.
        
        Args:
            mode: Betriebsmodus ('auto' für KI-Training, 'manual' für interaktiven Modus)
        """
        self.running = True
        self.mode = mode
        self.show_welcome_screen()
        
        if mode == "auto":
            # Auto-Start eines Testszenarios für KI-gesteuertes Gameplay
            self.create_character_auto()
            self.start_auto_test_combat()
        else:
            # Manueller Modus - zeige Hauptmenü
            while self.running:
                self.show_main_menu()
    
    def stop(self) -> None:
        """
        Beendet die CLI.
        """
        self.running = False
        print("\nProgramm wird beendet.")
        logger.info("Spiel beendet")
    
    def show_welcome_screen(self) -> None:
        """
        Zeigt den Willkommensbildschirm an.
        """
        clear_screen()
        
        if self.mode == "auto":
            print_title("Python RPG - KI-Trainingsmodus")
            print(colorize("\nWillkommen im Python RPG KI-Trainingsmodus!\n", "cyan"))
            print("Diese Sitzung wird automatisch einen Testkampf starten und durchführen.")
            print("Das Kampfsystem ist für das Reinforcement Learning vorbereitet.")
            print("\nInitialisierung läuft...")
            time.sleep(2)  # Kurze Pause für Lesbarkeit
        else:
            print_title("Python RPG - Interaktiver Modus")
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
        
        # Erstelle den Player mit den Daten aus der JSON-Datei
        try:
            # Erstelle Player-ID
            player_id = f"{character_class}_{name.lower().replace(' ', '_')}"
            
            # Bereite Daten aus character_classes und setze den Namen
            if character_class in self.character_data["character_classes"]:
                data_dict = self.character_data["character_classes"][character_class].copy()
                data_dict["name"] = name
                data_dict["character_class"] = character_class
            else:
                # Fallback, falls die Klasse nicht gefunden wird
                logger.warning(f"Klasse {character_class} nicht gefunden, verwende Standard-Werte")
                data_dict = {
                    "name": name,
                    "character_class": character_class,
                    "level": 1,
                    "attributes": {"strength": 10, "dexterity": 10, "intelligence": 10, "constitution": 10, "wisdom": 10},
                    "defenses": {"armor": 2, "magic_resistance": 2},
                    "resources": {"max_stamina": 50, "max_energy": None, "max_mana": 50},
                    "known_skills": ["basic_strike_phys"]
                }
            
            # Erstelle den Spieler
            self.current_player = Player(player_id, data_dict)
            
            logger.info(f"Charakter '{name}' der Klasse {character_class} erfolgreich erstellt")
            print(f"\n{colorize('Charakter erstellt!', 'green')}")
            print(f"Name: {name}")
            print(f"Klasse: {character_class.capitalize()}")
            print(f"Level: 1")
            print("\nDrücke Enter, um fortzufahren...")
            input()
        
        except Exception as e:
            logger.exception(f"Fehler bei der Charaktererstellung: {str(e)}")
            print(f"\n{colorize('Fehler bei der Charaktererstellung:', 'red')} {str(e)}")
            print("Bitte überprüfe die Player-Klassen-Implementation.")
            time.sleep(3)
    
    def create_character_auto(self) -> None:
        """
        Erstellt automatisch einen Testcharakter für KI-Training.
        """
        # Wähle automatisch einen Krieger für einfache Tests
        character_class = "warrior"
        name = "KI-Trainingscharakter"
        
        # Erstelle den Player mit den Daten aus der JSON-Datei
        try:
            # Erstelle Player-ID
            player_id = "test_player_1"
            
            # Bereite Daten aus character_classes und setze den Namen
            if character_class in self.character_data["character_classes"]:
                data_dict = self.character_data["character_classes"][character_class].copy()
                data_dict["name"] = name
                data_dict["character_class"] = character_class
            else:
                # Fallback, falls die Klasse nicht gefunden wird
                logger.warning(f"Klasse {character_class} nicht gefunden, verwende Standard-Werte")
                data_dict = {
                    "name": name,
                    "character_class": character_class,
                    "level": 1,
                    "attributes": {"strength": 10, "dexterity": 10, "intelligence": 10, "constitution": 10, "wisdom": 10},
                    "defenses": {"armor": 2, "magic_resistance": 2},
                    "resources": {"max_stamina": 50, "max_energy": None, "max_mana": 50},
                    "known_skills": ["basic_strike_phys"]
                }
            
            # Erstelle den Spieler
            self.current_player = Player(player_id, data_dict)
            
            logger.info(f"Auto-Charakter '{name}' der Klasse {character_class} erfolgreich erstellt")
            print(f"\n{colorize('Charakter erstellt:', 'green')} {name} (Level 1 {character_class.capitalize()})")
            time.sleep(1)
        
        except Exception as e:
            logger.exception(f"Fehler bei der Auto-Charaktererstellung: {str(e)}")
            print(f"\n{colorize('Fehler bei der Auto-Charaktererstellung:', 'red')} {str(e)}")
            print("Bitte überprüfe die Player-Klassen-Implementation.")
            time.sleep(3)
    
    def start_test_combat(self) -> None:
        """
        Startet einen Testkampf mit dem aktuellen Charakter (manueller Modus).
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
        
        # Starte den Kampf in der CombatCLI mit manuellem Modus
        self.combat_cli.start_combat(self.current_player, enemies, ai_mode=False)
    
    def start_auto_test_combat(self) -> None:
        """
        Startet automatisch einen Testkampf für KI-Training.
        """
        if not self.current_player:
            logger.error("Versuch, einen Kampf ohne Spieler zu starten.")
            return
        
        clear_screen()
        print_title("KI-Trainings-Kampf")
        print("\nEin Trainingskampf wird für die KI automatisch generiert...")
        
        # Wähle automatisch mittlere Schwierigkeit
        difficulty = 2
        
        # Generiere Gegner basierend auf der Schwierigkeit
        enemies = self._generate_enemies(difficulty)
        
        # Ausgabe der generierten Gegner
        print(f"\nGenerierte Gegner für Schwierigkeitsstufe {difficulty}:")
        for enemy in enemies:
            print(f"- {enemy.name} (Level {enemy.level})")
        
        time.sleep(2)
        
        # Starte den Kampf in der CombatCLI mit KI-Modus
        self.combat_cli.start_combat(self.current_player, enemies, ai_mode=True)
        
        # Nach dem Kampf beenden
        self.stop()
    
    def _generate_enemies(self, difficulty: int) -> List[Enemy]:
        """
        Generiert Gegner basierend auf der ausgewählten Schwierigkeit.
        
        Args:
            difficulty: Schwierigkeitsstufe (1-3)
            
        Returns:
            Liste von generierten Gegnern
        """
        enemies = []
        
        try:
            enemy_types = {
                1: ["giant_rat"],
                2: ["goblin", "goblin_warrior"],
                3: ["goblin_warrior", "skeleton_archer", "goblin_shaman"]
            }
            
            selected_enemy_types = enemy_types.get(difficulty, ["goblin"])
            
            for enemy_type in selected_enemy_types:
                if enemy_type in self.enemy_data["enemies"]:
                    # Erstelle Enemy-ID
                    enemy_id = f"{enemy_type}_{random.randint(1000, 9999)}"
                    
                    # Kopiere die Gegnerdaten
                    data_dict = self.enemy_data["enemies"][enemy_type].copy()
                    
                    # Erstelle den Gegner
                    enemy = Enemy(enemy_id, data_dict)
                    enemies.append(enemy)
                else:
                    logger.warning(f"Gegnertyp {enemy_type} nicht gefunden")
            
            if not enemies:
                # Fallback: Erstelle einen generischen Goblin
                enemy_id = "goblin_fallback"
                data_dict = {
                    "name": "Goblin (Fallback)",
                    "level": difficulty,
                    "attributes": {"strength": 8, "dexterity": 10, "intelligence": 5, "constitution": 8, "wisdom": 5},
                    "defenses": {"armor": 2, "magic_resistance": 1},
                    "resources": {"max_stamina": 40, "max_energy": None, "max_mana": None},
                    "known_skills": ["basic_strike_phys"]
                }
                enemy = Enemy(enemy_id, data_dict)
                enemies.append(enemy)
            
        except Exception as e:
            logger.exception(f"Fehler beim Generieren von Gegnern: {str(e)}")
            print(f"\n{colorize('Fehler beim Generieren von Gegnern:', 'red')} {str(e)}")
            print("Bitte überprüfe die Enemy-Klassen-Implementation.")
            time.sleep(3)
        
        return enemies
