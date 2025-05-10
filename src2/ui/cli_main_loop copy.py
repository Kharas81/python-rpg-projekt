"""
CLI-Hauptschleife

Implementiert die Hauptschleife für die automatische Simulation.
"""
import time
import random
from typing import List, Dict, Any, Optional, Tuple

from src.definitions import loader
from src.game_logic.entities import CharacterInstance
from src.game_logic.combat import CombatEncounter
from src.game_logic.leveling import get_leveling_service
from src.ai.ai_dispatcher import get_ai_dispatcher
from src.ui.cli_output import get_cli_output
from src.utils.logging_setup import get_logger


# Logger für dieses Modul
logger = get_logger(__name__)


class CLISimulation:
    """
    Verwaltet die automatische Simulation im CLI-Modus.
    """
    
    def __init__(self, characters_path: str, skills_path: str, opponents_path: str):
        """
        Initialisiert die Simulation.
        
        Args:
            characters_path (str): Pfad zur characters.json5-Datei
            skills_path (str): Pfad zur skills.json5-Datei
            opponents_path (str): Pfad zur opponents.json5-Datei
        """
        self.characters_path = characters_path
        self.skills_path = skills_path
        self.opponents_path = opponents_path
        
        self.cli_output = get_cli_output()
        self.leveling_service = get_leveling_service()
        self.ai_dispatcher = get_ai_dispatcher()
        
        # Daten laden
        self.character_templates = loader.load_characters(characters_path)
        self.skill_definitions = loader.load_skills(skills_path)
        self.opponent_templates = loader.load_opponents(opponents_path)
        
        # Aktive Spieler und Gegner
        self.players: List[CharacterInstance] = []
        self.current_encounter: Optional[CombatEncounter] = None
    
    def start_simulation(self, num_players: int = 1, num_encounters: int = 3) -> None:
        """
        Startet die Simulation.
        
        Args:
            num_players (int): Anzahl der Spielercharaktere
            num_encounters (int): Anzahl der zu simulierenden Begegnungen
        """
        self.cli_output.clear_screen()
        self.cli_output.print_header("RPG Simulation gestartet")
        
        # Spielercharaktere erstellen
        self._create_player_characters(num_players)
        
        # Mehrere Begegnungen simulieren
        for i in range(num_encounters):
            self.cli_output.print_header(f"Begegnung {i+1}/{num_encounters}")
            
            # Zufällige Gegner generieren
            opponents = self._generate_random_opponents()
            
            # Kampf starten
            self._run_combat_encounter(opponents)
            
            # Kurze Pause zwischen Begegnungen
            if i < num_encounters - 1:
                self.cli_output.print_message("\nNächste Begegnung wird vorbereitet...\n")
                self.cli_output.wait(2.0)
        
        self.cli_output.print_header("Simulation beendet")
        self._show_final_stats()
    
    def _create_player_characters(self, num_players: int) -> None:
        """
        Erstellt die Spielercharaktere.
        
        Args:
            num_players (int): Anzahl der zu erstellenden Charaktere
        """
        self.cli_output.print_subheader("Charaktererstellung")
        
        self.players = []
        available_templates = list(self.character_templates.values())
        
        for i in range(num_players):
            # Template zufällig auswählen (oder alle verwenden, wenn genug vorhanden sind)
            if i < len(available_templates):
                template = available_templates[i]
            else:
                template = random.choice(available_templates)
            
            # Charakter erstellen
            player = CharacterInstance.from_template(template)
            self.players.append(player)
            
            self.cli_output.print_message(f"Spieler {i+1}: {player.name} erstellt (Klasse: {template.id})")
        
        # Detaillierte Statistiken anzeigen
        for player in self.players:
            self.cli_output.print_character_stats(player, detailed=True)
    
    def _generate_random_opponents(self, min_opponents: int = 1, max_opponents: int = 3) -> List[CharacterInstance]:
        """
        Generiert zufällige Gegner für eine Begegnung.
        
        Args:
            min_opponents (int): Minimale Anzahl an Gegnern
            max_opponents (int): Maximale Anzahl an Gegnern
            
        Returns:
            List[CharacterInstance]: Die generierten Gegner
        """
        self.cli_output.print_subheader("Gegner erscheinen!")
        
        # Anzahl der Gegner bestimmen (basierend auf Spieleranzahl)
        player_count = len(self.players)
        num_opponents = random.randint(min_opponents, min(max_opponents, player_count + 1))
        
        # Durchschnittslevel der Spieler berechnen
        avg_player_level = sum(p.level for p in self.players) // player_count
        
        # Gegner generieren
        opponents = []
        available_templates = list(self.opponent_templates.values())
        
        for i in range(num_opponents):
            # Zufälliges Template auswählen
            template = random.choice(available_templates)
            
            # Gegner-Level bestimmen (nahe am Spieler-Level)
            level_variance = random.randint(-1, 1)  # -1, 0 oder 1
            opponent_level = max(1, avg_player_level + level_variance)
            
            # Gegner erstellen
            opponent = CharacterInstance.from_template(template, level=opponent_level)
            opponents.append(opponent)
            
            self.cli_output.print_message(f"Gegner erscheint: {opponent.name} (Level {opponent_level})")
        
        # Kurze Pause nach der Gegnergenerierung
        self.cli_output.wait(1.0)
        
        return opponents
    
    def _run_combat_encounter(self, opponents: List[CharacterInstance]) -> None:
        """
        Führt einen Kampf zwischen Spielern und Gegnern durch.
        
        Args:
            opponents (List[CharacterInstance]): Die Gegner
        """
        # Kampf initialisieren
        self.current_encounter = CombatEncounter(self.players, opponents)
        self.current_encounter.start_combat()
        
        # Status vor dem Kampf anzeigen
        self.cli_output.print_combat_summary(self.players, opponents)
        self.cli_output.wait(1.0)
        
        # Kampfschleife
        while self.current_encounter.is_active:
            # Nächste Runde vorbereiten, wenn die Zugreihenfolge leer ist
            if not self.current_encounter.turn_order:
                self.current_encounter.next_round()
                self.cli_output.print_message(f"\nRunde {self.current_encounter.round} beginnt!")
                self.cli_output.print_combat_summary(self.players, opponents)
            
            # Nächsten Charakter in der Zugreihenfolge holen
            if not self.current_encounter.turn_order:
                logger.error("Fehler: Keine Charaktere in der Zugreihenfolge!")
                break
                
            current_character = self.current_encounter.turn_order.pop(0)
            
            # Prüfen, ob der Charakter noch lebt und handeln kann
            if not current_character.is_alive() or not current_character.can_act():
                continue
            
            # Charakter am Zug anzeigen
            is_player = current_character in self.players
            self.cli_output.print_message(f"\n{current_character.name} ist am Zug!")
            
            # Aktion auswählen und ausführen
            self._perform_character_action(current_character, is_player)
            
            # Prüfen, ob der Kampf beendet ist
            if self.current_encounter.check_combat_end():
                break
        
        # Kampfergebnis anzeigen
        self._show_combat_results()
    
    def _perform_character_action(self, character: CharacterInstance, is_player: bool) -> None:
        """
        Führt die Aktion eines Charakters aus.
        
        Args:
            character (CharacterInstance): Der handelnde Charakter
            is_player (bool): True, wenn es ein Spielercharakter ist, False für Gegner
        """
        # Verfügbare Skills für den Charakter laden
        available_skills = {skill_id: self.skill_definitions.get(skill_id) 
                           for skill_id in character.skill_ids 
                           if skill_id in self.skill_definitions}
        
        # Verbündete und Feinde bestimmen
        allies = self.players if is_player else self.current_encounter.opponents
        enemies = self.current_encounter.opponents if is_player else self.players
        
        # KI-Entscheidung für den nächsten Zug
        skill, primary_target, secondary_targets = self.ai_dispatcher.choose_action(
            character, allies, enemies, available_skills
        )
        
        if not skill or not primary_target:
            self.cli_output.print_message(f"{character.name} kann keine Aktion ausführen!")
            return
        
        # Kampfaktion erstellen und ausführen
        from src.game_logic.combat import CombatAction, get_combat_system
        combat_system = get_combat_system()
        
        action = CombatAction(character, skill, primary_target, secondary_targets)
        result = combat_system.execute_action(action)
        
        # Ergebnis anzeigen
        is_self_effect = skill.is_self_effect()
        is_healing = 'base_healing' in skill.effects
        
        # Aktionsausgabe
        action_desc = f"{character.name} verwendet {skill.name}"
        target_desc = f"auf {primary_target.name}"
        
        if is_self_effect and character == primary_target:
            target_desc = "auf sich selbst"
        
        self.cli_output.print_message(f"{action_desc} {target_desc}")
        
        # Trefferausgabe
        for target in result.hits:
            if target in result.damage_dealt:
                damage = result.damage_dealt[target]
                self.cli_output.print_message(f"  • Trifft {target.name} für {damage} Schaden")
                if not target.is_alive():
                    self.cli_output.print_message(f"  • {target.name} wurde besiegt!")
            
            if target in result.healing_done:
                healing = result.healing_done[target]
                self.cli_output.print_message(f"  • Heilt {target.name} um {healing} HP")
            
            if target in result.effects_applied:
                effects = result.effects_applied[target]
                self.cli_output.print_message(f"  • Wendet Effekt(e) an: {', '.join(effects)}")
        
        for target in result.misses:
            self.cli_output.print_message(f"  • Verfehlt {target.name}")
        
        # Status nach der Aktion anzeigen
        self.cli_output.wait(0.5)
    
    def _show_combat_results(self) -> None:
        """Zeigt die Ergebnisse des aktuellen Kampfes an."""
        if not self.current_encounter:
            return
        
        self.cli_output.print_subheader("Kampfergebnis")
        
        if self.current_encounter.winner == 'players':
            self.cli_output.print_message("Die Spieler haben gesiegt!")
            
            # XP vergeben
            self.current_encounter.award_xp_for_victory(self.leveling_service)
            
            # Status der überlebenden Spieler anzeigen
            for player in self.players:
                if player.is_alive():
                    self.cli_output.print_character_stats(player, detailed=True)
                    
                    # XP-Fortschritt anzeigen
                    next_level_xp = self.leveling_service.get_xp_for_next_level(player)
                    progress = self.leveling_service.get_xp_progress_percentage(player)
                    self.cli_output.print_message(
                        f"XP: {player.xp}/{next_level_xp} ({progress:.1f}% zum nächsten Level)"
                    )
        
        elif self.current_encounter.winner == 'opponents':
            self.cli_output.print_message("Die Gegner haben gesiegt! GAME OVER")
            # In einer echten Implementierung würde hier das Spiel beendet oder neu gestartet
        
        else:
            self.cli_output.print_message("Der Kampf endete unentschieden.")
    
    def _show_final_stats(self) -> None:
        """Zeigt die Endstatistiken der Spieler an."""
        self.cli_output.print_subheader("Endstatistiken")
        
        for i, player in enumerate(self.players):
            self.cli_output.print_message(f"Spieler {i+1}: {player.name} (Level {player.level})")
            self.cli_output.print_character_stats(player, detailed=True)
            
            if player.is_alive():
                next_level_xp = self.leveling_service.get_xp_for_next_level(player)
                progress = self.leveling_service.get_xp_progress_percentage(player)
                self.cli_output.print_message(
                    f"XP: {player.xp}/{next_level_xp} ({progress:.1f}% zum nächsten Level)"
                )
            else:
                self.cli_output.print_message("Status: Gefallen im Kampf")


def run_simulation(characters_path: str, skills_path: str, opponents_path: str) -> None:
    """
    Führt die CLI-Simulation durch.
    
    Args:
        characters_path (str): Pfad zur characters.json5-Datei
        skills_path (str): Pfad zur skills.json5-Datei
        opponents_path (str): Pfad zur opponents.json5-Datei
    """
    simulation = CLISimulation(characters_path, skills_path, opponents_path)
    
    # Standardwerte für die Simulation
    num_players = 2
    num_encounters = 3
    
    simulation.start_simulation(num_players, num_encounters)
