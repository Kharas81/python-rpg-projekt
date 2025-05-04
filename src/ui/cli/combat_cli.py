"""
Combat CLI Module

Spezialisierte Benutzeroberfläche für das Kampfsystem.
"""

import logging
import time
import random
from typing import Dict, List, Any, Optional

from src.game_logic.entity.player import Player
from src.game_logic.entity.enemy import Enemy
from src.game_logic.combat.combat_manager import CombatManager
from src.ui.cli.cli_utils import clear_screen, colorize, print_title, print_boxed

# Logger für dieses Modul einrichten
logger = logging.getLogger(__name__)


class CombatCLI:
    """
    Spezialisierte CLI für das Kampfsystem.
    
    Diese Klasse stellt die Benutzeroberfläche für Kampfsituationen dar
    und interagiert mit dem CombatManager.
    """
    
    def __init__(self) -> None:
        """
        Initialisiert eine neue CombatCLI.
        """
        self.combat_manager = CombatManager()
        self.player = None
        self.enemies = []
        self.ai_mode = False
        
        logger.info("Combat CLI initialisiert")
    
    def start_combat(self, player: Player, enemies: List[Enemy], ai_mode: bool = False) -> None:
        """
        Startet einen Kampf mit dem angegebenen Spieler und Gegnern.
        
        Args:
            player: Der Spielercharakter
            enemies: Liste der Gegner
            ai_mode: Ob der Kampf KI-gesteuert sein soll
        """
        self.player = player
        self.enemies = enemies
        self.ai_mode = ai_mode
        
        # Starte den Kampf im CombatManager
        result = self.combat_manager.start_combat([player], enemies)
        
        if result["success"]:
            print(colorize("\nKampf gestartet!", "green"))
            time.sleep(1)
            self._combat_loop()
        else:
            print(f"Fehler beim Starten des Kampfes: {result.get('message', 'Unbekannter Fehler')}")
            time.sleep(2)
    
    def _combat_loop(self) -> None:
        """
        Hauptschleife für den Kampfablauf.
        """
        # Kampf läuft, solange er aktiv ist
        while self.combat_manager.combat_active:
            # Hole Kampfzusammenfassung
            summary = self.combat_manager.get_combat_summary()
            
            # Hole die aktuelle Entität
            current_entity = self.combat_manager.get_current_entity()
            
            # Zeige Kampfstatus an
            self._display_combat_status(summary)
            
            # Im KI-Modus kurze Pause für die Lesbarkeit
            if self.ai_mode:
                time.sleep(1)
            
            # Verarbeite Zug basierend auf dem Typ der aktuellen Entität
            if current_entity == self.player:
                # Spieler ist am Zug - im KI-Modus automatisch handeln
                if self.ai_mode:
                    self._handle_ai_player_turn()
                else:
                    self._handle_player_turn()
            else:
                # Gegner ist am Zug (KI)
                self._handle_enemy_turn(current_entity)
        
        # Kampf ist beendet, zeige Ergebnis
        self._display_combat_results()
    
    def _display_combat_status(self, summary: Dict[str, Any]) -> None:
        """
        Zeigt den aktuellen Status des Kampfes an.
        
        Args:
            summary: Kampfzusammenfassung vom CombatManager
        """
        clear_screen()
        print_title(f"Kampf - Runde {summary['round']}")
        
        # Spielerinformationen anzeigen
        print_boxed("Spieler", "cyan")
        for player_info in summary["players"]:
            hp_percent = player_info["current_hp"] / player_info["max_hp"] * 100
            hp_color = "green" if hp_percent > 50 else "yellow" if hp_percent > 25 else "red"
            
            print(f"{colorize(player_info['name'], 'cyan')} - "
                  f"HP: {colorize(f'{player_info['current_hp']}/{player_info['max_hp']}', hp_color)}")
            
            # Status-Effekte anzeigen
            if player_info["status_effects"]:
                effects = ", ".join(player_info["status_effects"])
                print(f"Status: {colorize(effects, 'magenta')}")
        
        print("\n")
        
        # Gegnerinformationen anzeigen
        print_boxed("Gegner", "red")
        for i, enemy_info in enumerate(summary["enemies"], 1):
            hp_percent = enemy_info["current_hp"] / enemy_info["max_hp"] * 100
            hp_color = "green" if hp_percent > 50 else "yellow" if hp_percent > 25 else "red"
            
            print(f"{i}. {colorize(enemy_info['name'], 'red')} - "
                  f"HP: {colorize(f'{enemy_info['current_hp']}/{enemy_info['max_hp']}', hp_color)}")
            
            # Status-Effekte anzeigen
            if enemy_info["status_effects"]:
                effects = ", ".join(enemy_info["status_effects"])
                print(f"   Status: {colorize(effects, 'magenta')}")
        
        print("\n")
        
        # Aktuelle Entität hervorheben
        current = summary.get("current_entity", "")
        if current:
            print(f"Am Zug: {colorize(current, 'yellow')}")
        
        print("\n")
        
        # Kampflog anzeigen (letzte Einträge)
        print_boxed("Kampflog", "blue")
        for log_entry in summary.get("log", [])[-3:]:  # Zeige die letzten 3 Logeinträge
            print(f"• {log_entry}")
        
        print("\n")
        
        # Im KI-Modus, zeige an dass dies ein automatisierter Durchlauf ist
        if self.ai_mode:
            print(colorize("KI-Trainingsmodus aktiv: Aktionen werden automatisch ausgeführt", "magenta"))
            print("\n")
    
    def _handle_ai_player_turn(self) -> None:
        """
        Automatische Aktionsauswahl für den KI-Spieler.
        """
        print(colorize("\nKI entscheidet für den Spieler...", "cyan"))
        time.sleep(1)
        
        # Zuerst prüfen, ob Skills verfügbar sind und mit 40% Wahrscheinlichkeit einen Skill verwenden
        skills = self.player.get_available_skills()
        use_skill = random.random() < 0.4 and skills
        
        if use_skill:
            # Wähle einen zufälligen Skill
            selected_skill = random.choice(skills)
            print(colorize(f"KI wählt Skill: {selected_skill.replace('_', ' ').title()}", "cyan"))
            
            # Hole gültige Ziele für den Skill
            valid_targets = self.combat_manager.get_valid_targets("skill", self.player)
            if valid_targets:
                # Wähle ein zufälliges Ziel
                target = random.choice(valid_targets)
                print(colorize(f"KI wählt Ziel: {target['name']}", "cyan"))
                
                # Erstelle Aktionsdaten
                action_data = {
                    "type": "skill",
                    "skill_id": selected_skill,
                    "targets": [target["id"]]
                }
                
                # Führe Aktion aus
                result = self.combat_manager.execute_action(action_data)
                if "message" in result:
                    print(f"\n{result['message']}")
                
                time.sleep(1)
                return
        
        # Wenn kein Skill verwendet wird oder keine verfügbar sind, führe einen normalen Angriff aus
        # Hole gültige Ziele für einen Angriff
        valid_targets = self.combat_manager.get_valid_targets("attack", self.player)
        
        if valid_targets:
            # Wähle ein zufälliges Ziel
            target = random.choice(valid_targets)
            print(colorize(f"KI wählt Angriff auf: {target['name']}", "cyan"))
            
            # Erstelle Aktionsdaten
            action_data = {
                "type": "attack",
                "target": target["id"]
            }
            
            # Führe Aktion aus
            result = self.combat_manager.execute_action(action_data)
            if "message" in result:
                print(f"\n{result['message']}")
            
            time.sleep(1)
        else:
            # Keine gültigen Ziele - unwahrscheinlich, aber zur Sicherheit
            print(colorize("\nKeine gültigen Ziele verfügbar!", "red"))
            time.sleep(1)
    
    def _handle_player_turn(self) -> None:
        """
        Verarbeitet den Zug des Spielers (manueller Modus - nicht verwendet im KI-Training).
        """
        # Diese Methode wird im KI-Modus nicht verwendet, ist aber hier für Vollständigkeit
        pass
    
    def _handle_enemy_turn(self, enemy: Enemy) -> None:
        """
        Verarbeitet den Zug eines Gegners (KI).
        
        Args:
            enemy: Der Gegner, der am Zug ist
        """
        print(f"\n{colorize(enemy.name, 'red')} ist am Zug...")
        time.sleep(0.5)
        
        # Einfache KI-Entscheidung: Greife den Spieler an
        action_data = {
            "type": "attack",
            "target": self.player.unique_id
        }
        
        # Führe Aktion aus
        result = self.combat_manager.execute_action(action_data)
        
        # Zeige Ergebnis an
        if "message" in result:
            print(f"\n{result['message']}")
        
        time.sleep(1)
    
    def _display_combat_results(self) -> None:
        """
        Zeigt das Ergebnis des Kampfes an.
        """
        clear_screen()
        summary = self.combat_manager.get_combat_summary()
        
        # Prüfe den Kampfausgang
        players_alive = any(p["current_hp"] > 0 for p in summary["players"])
        enemies_alive = any(e["current_hp"] > 0 for e in summary["enemies"])
        
        if players_alive and not enemies_alive:
            # Spieler hat gewonnen
            print_title("Kampf gewonnen!", "green")
            print("\nAlle Gegner wurden besiegt!")
            
            # Zeige Statistiken
            stats = summary.get("statistics", {})
            damage_dealt = stats.get("damage_dealt", {}).get(self.player.unique_id, 0)
            healing_done = stats.get("healing_done", {}).get(self.player.unique_id, 0)
            
            print(f"\nStatistiken:")
            print(f"Verursachter Schaden: {damage_dealt}")
            print(f"Geheilte HP: {healing_done}")
            
            # In einer vollständigen Implementation würden hier Belohnungen verteilt
            print("\nKampfbelohnungen würden hier verteilt werden.")
            
        elif not players_alive:
            # Spieler hat verloren
            print_title("Kampf verloren!", "red")
            print("\nDer Spieler wurde besiegt!")
            
        else:
            # Unentschieden oder andere Ergebnisse
            print_title("Kampf beendet", "yellow")
            print("\nDer Kampf ist ohne klaren Sieger zu Ende gegangen.")
        
        # Zeige noch mehr Kampfstatistiken für das RL-Training
        print("\nKampfstatistiken für RL-Training:")
        print(f"Kampfrunden: {summary['round']}")
        
        # Bei automatischem Modus kurz warten und dann fortfahren
        if self.ai_mode:
            print("\nAutomatischer Modus: Fortfahren in 3 Sekunden...")
            time.sleep(3)
        else:
            print("\nDrücke Enter, um fortzufahren...")
            input()
