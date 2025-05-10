"""
CLI-Hauptschleife

Implementiert die Hauptschleife für die automatische Simulation.
"""
import time
import random
import logging
from typing import List, Dict, Any, Optional, Tuple

from src.definitions import loader
from src.game_logic.entities import CharacterInstance
from src.game_logic.combat import CombatEncounter
from src.game_logic.leveling import get_leveling_service
from src.ai.ai_dispatcher import get_ai_dispatcher
from src.ui.cli_output import get_cli_output
# get_logger wird nun direkt hier importiert, falls nicht schon in logging_setup
# from src.utils.logging_setup import get_logger # Annahme: get_logger kommt aus logging_setup

# Logger für dieses Modul (nutzt das Standard-Logging, falls get_logger nicht verfügbar ist)
try:
    from src.utils.logging_setup import get_logger
    logger = get_logger(__name__)
except ImportError:
    # Fallback, falls get_logger nicht gefunden wird
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.warning("Konnte src.utils.logging_setup.get_logger nicht importieren. Verwende Standard-Logging.")


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
        try:
            self.character_templates = loader.load_characters(characters_path)
            self.skill_definitions = loader.load_skills(skills_path)
            self.opponent_templates = loader.load_opponents(opponents_path)
            logger.info("Spieldaten erfolgreich geladen.")
        except FileNotFoundError as e:
            logger.error(f"Fehler beim Laden der Spieldaten: Datei nicht gefunden - {e}")
            # Hier könnte man das Programm beenden oder einen Fehler werfen
            raise # Die Exception weiterwerfen, damit main.py sie fangen kann
        except Exception as e:
            logger.error(f"Ein unerwarteter Fehler ist beim Laden der Spieldaten aufgetreten: {e}")
            raise # Die Exception weiterwerfen


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
        logger.info(f"Simulation gestartet mit {num_players} Spielern und {num_encounters} Begegnungen.")

        # Spielercharaktere erstellen
        self._create_player_characters(num_players)

        # Mehrere Begegnungen simulieren
        for i in range(num_encounters):
            # Prüfen, ob noch Spieler am Leben sind, bevor eine neue Begegnung gestartet wird
            if not any(player.is_alive() for player in self.players):
                self.cli_output.print_message("\nAlle Spieler sind ausgeschaltet. Simulation endet vorzeitig.")
                logger.info("Simulation vorzeitig beendet: Alle Spieler besiegt.")
                break # Schleife beenden, wenn alle Spieler tot sind

            self.cli_output.print_header(f"Begegnung {i+1}/{num_encounters}")
            logger.info(f"Starte Begegnung {i+1}/{num_encounters}")

            # NEU: Anzahl der Gegner für diese Begegnung abfragen
            while True:
                try:
                    opp_input = input(f"Anzahl Gegner für Begegnung {i+1} (Standard: Zufall 1-3): ")
                    if not opp_input: # Wenn Eingabe leer ist, zufällige Anzahl generieren lassen
                        num_opponents_this_encounter = None # Signalisiert zufällige Generierung
                        break
                    num_opponents_this_encounter = int(opp_input)
                    if num_opponents_this_encounter < 0:
                        print("Bitte geben Sie eine nicht-negative Zahl ein.")
                        continue
                    break
                except ValueError:
                    print("Ungültige Eingabe. Bitte geben Sie eine Zahl ein.")

            # Zufällige Gegner generieren (oder spezifische Anzahl, falls angegeben)
            opponents = self._generate_random_opponents(specific_num_opponents=num_opponents_this_encounter)

            # Prüfen, ob Gegner generiert wurden
            if not opponents:
                self.cli_output.print_message("Keine Gegner für diese Begegnung. Überspringe Kampf.")
                logger.info("Keine Gegner generiert, überspringe Kampf.")
                continue # Nächste Begegnung starten

            # Kampf starten
            self._run_combat_encounter(opponents)

            # Kurze Pause zwischen Begegnungen, wenn es nicht die letzte ist
            if i < num_encounters - 1:
                 # Prüfen, ob Spieler den Kampf überlebt haben, bevor gewartet wird
                 if any(player.is_alive() for player in self.players):
                    self.cli_output.print_message("\nNächste Begegnung wird vorbereitet...\n")
                    self.cli_output.wait(2.0)
                 else:
                     # Wenn alle Spieler tot sind, nicht warten und die Schleife wird oben beendet
                     pass


        self.cli_output.print_header("Simulation beendet")
        self._show_final_stats()
        logger.info("Simulation erfolgreich beendet.")


    def _create_player_characters(self, num_players: int) -> None:
        """
        Erstellt die Spielercharaktere.

        Args:
            num_players (int): Anzahl der zu erstellenden Charaktere
        """
        self.cli_output.print_subheader("Charaktererstellung")
        logger.info(f"Erstelle {num_players} Spielercharaktere.")

        self.players = []
        available_templates = list(self.character_templates.values())

        if not available_templates:
            logger.error("Keine Charakter-Templates gefunden. Kann keine Spieler erstellen.")
            self.cli_output.print_message("Fehler: Keine Charakter-Templates gefunden!")
            return # Keine Spieler erstellt

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
            logger.debug(f"Erstellter Spieler: {player.name} (ID: {player.id})")


        # Detaillierte Statistiken anzeigen (optional, kann bei vielen Spielern unübersichtlich werden)
        # for player in self.players:
        #     self.cli_output.print_character_stats(player, detailed=True)


    def _generate_random_opponents(self, min_opponents: int = 1, max_opponents: int = 3, specific_num_opponents: Optional[int] = None) -> List[CharacterInstance]:
        """
        Generiert Gegner für eine Begegnung.

        Args:
            min_opponents (int): Minimale Anzahl an Gegnern (wird ignoriert, wenn specific_num_opponents gesetzt ist)
            max_opponents (int): Maximale Anzahl an Gegnern (wird ignoriert, wenn specific_num_opponents gesetzt ist)
            specific_num_opponents (Optional[int]): Eine spezifische Anzahl von Gegnern, die erstellt werden soll.
                                                    Wenn None, wird eine zufällige Anzahl zwischen min_opponents und max_opponents gewählt.

        Returns:
            List[CharacterInstance]: Die generierten Gegner
        """
        self.cli_output.print_subheader("Gegner erscheinen!")

        if not self.opponent_templates:
             logger.error("Keine Gegner-Templates gefunden. Kann keine Gegner generieren.")
             self.cli_output.print_message("Fehler: Keine Gegner-Templates gefunden!")
             return [] # Leere Liste zurückgeben

        # Bestimme die Anzahl der zu generierenden Gegner
        if specific_num_opponents is not None:
            num_opponents = specific_num_opponents
            logger.info(f"Generiere spezifische Anzahl Gegner: {num_opponents}.")
            if num_opponents < 0:
                 logger.warning(f"Ungültige spezifische Anzahl Gegner ({num_opponents}) erhalten. Generiere 0 Gegner.")
                 num_opponents = 0 # Stelle sicher, dass es nicht negativ ist
        else:
            # Anzahl der Gegner bestimmen (basierend auf Zufall im Standardbereich)
            num_opponents = random.randint(min_opponents, max_opponents)
            logger.info(f"Generiere zufällige Anzahl Gegner: {num_opponents} (Bereich {min_opponents}-{max_opponents}).")

        if num_opponents == 0:
             self.cli_output.print_message("Keine Gegner erscheinen.")
             return [] # Keine Gegner zu generieren

        # Durchschnittslevel der lebenden Spieler berechnen
        alive_players = [p for p in self.players if p.is_alive()]
        if not alive_players:
            logger.warning("Keine lebenden Spieler, generiere Gegner auf Level 1.")
            avg_player_level = 1
        else:
            avg_player_level = sum(p.level for p in alive_players) // len(alive_players)

        # Gegner generieren
        opponents = []
        available_templates = list(self.opponent_templates.values())

        # Sicherstellen, dass wir nicht versuchen, mehr Gegner zu erstellen als Templates vorhanden sind,
        # es sei denn, wir erlauben die Wiederverwendung von Templates.
        # Aktuell wird random.choice verwendet, was Wiederverwendung erlaubt.
        # Wenn spezifische Anzahl > Anzahl Templates, werden Templates wiederverwendet.

        for i in range(num_opponents):
            # Zufälliges Template auswählen
            template = random.choice(available_templates)

            # Gegner-Level bestimmen (nahe am Durchschnittslevel der Spieler)
            level_variance = random.randint(-1, 1)  # -1, 0 oder 1
            opponent_level = max(1, avg_player_level + level_variance)

            # Gegner erstellen
            opponent = CharacterInstance.from_template(template, level=opponent_level)
            opponents.append(opponent)

            self.cli_output.print_message(f"Gegner erscheint: {opponent.name} (Level {opponent_level})")
            logger.debug(f"Erstellter Gegner: {opponent.name} (ID: {opponent.id}, Level: {opponent_level})")


        # Kurze Pause nach der Gegnergenerierung
        self.cli_output.wait(1.0)

        return opponents

    def _run_combat_encounter(self, opponents: List[CharacterInstance]) -> None:
        """
        Führt einen Kampf zwischen Spielern und Gegnern durch.

        Args:
            opponents (List[CharacterInstance]): Die Gegner
        """
        if not self.players or not any(p.is_alive() for p in self.players):
             logger.warning("Keine lebenden Spieler zu Beginn des Kampfes.")
             self.cli_output.print_message("Keine lebenden Spieler für diesen Kampf.")
             return

        if not opponents:
             logger.info("Keine Gegner für diesen Kampf generiert.")
             self.cli_output.print_message("Keine Gegner erscheinen.")
             # Spieler erhalten trotzdem XP, wenn keine Gegner da sind? Oder nur bei Sieg?
             # Aktuell: Kein Kampf, keine XP.
             return

        logger.info(f"Starte Kampf: Spieler vs. {len(opponents)} Gegner.")
        # Kampf initialisieren
        # Stellen Sie sicher, dass CombatEncounter nur lebende Charaktere erhält
        self.current_encounter = CombatEncounter([p for p in self.players if p.is_alive()], opponents)
        self.current_encounter.start_combat()

        # Status vor dem Kampf anzeigen
        self.cli_output.print_combat_summary([p for p in self.players if p.is_alive()], [o for o in opponents if o.is_alive()])
        self.cli_output.wait(1.0)

        # Kampfschleife
        while self.current_encounter.is_active:
            # Nächste Runde vorbereiten, wenn die Zugreihenfolge leer ist
            if not self.current_encounter.turn_order:
                self.current_encounter.next_round()
                self.cli_output.print_message(f"\nRunde {self.current_encounter.round} beginnt!")
                self.cli_output.print_combat_summary([p for p in self.players if p.is_alive()], [o for o in opponents if o.is_alive()]) # Aktualisierte Anzeige
                self.cli_output.wait(1.0) # Kurze Pause am Rundenanfang

            # Nächsten Charakter in der Zugreihenfolge holen
            if not self.current_encounter.turn_order:
                logger.error("Fehler: Keine Charaktere in der Zugreihenfolge am Anfang einer Runde!")
                break

            current_character = self.current_encounter.turn_order.pop(0)

            # Prüfen, ob der Charakter noch lebt und handeln kann
            if not current_character.is_alive() or not current_character.can_act():
                logger.debug(f"{current_character.name} ist nicht kampffähig oder kann nicht handeln.")
                continue # Überspringe diesen Charakter

            # Charakter am Zug anzeigen
            is_player = current_character in self.players
            self.cli_output.print_message(f"\n{current_character.name} ist am Zug!")
            logger.debug(f"{current_character.name} (Spieler: {is_player}) ist am Zug.")


            # Aktion auswählen und ausführen
            # Stellen Sie sicher, dass nur lebende Charaktere als Ziele übergeben werden
            alive_allies = [c for c in (self.players if is_player else opponents) if c.is_alive()]
            alive_enemies = [c for c in (opponents if is_player else self.players) if c.is_alive()]

            if not alive_enemies and any(c.is_alive() for c in alive_allies): # Prüfen, ob noch lebende Verbündete da sind, wenn keine Gegner da sind
                 logger.debug(f"Keine lebenden Gegner für {current_character.name}. Kampfende erwartet.")
                 # Der Charakter sollte in diesem Fall nichts tun müssen, aber die Schleife wird bald enden.
                 continue # Keine Gegner mehr, Kampf wird bald enden


            self._perform_character_action(current_character, is_player, alive_allies, alive_enemies)

            # Kurze Pause nach jeder Aktion
            self.cli_output.wait(0.5)

            # Prüfen, ob der Kampf beendet ist nach jeder Aktion
            if self.current_encounter.check_combat_end():
                 logger.info("Kampfende nach Aktion erkannt.")
                 break

        # Kampfergebnis anzeigen
        self._show_combat_results()
        logger.info("Kampf beendet.")


    def _perform_character_action(self, character: CharacterInstance, is_player: bool, allies: List[CharacterInstance], enemies: List[CharacterInstance]) -> None:
        """
        Führt die Aktion eines Charakters aus.

        Args:
            character (CharacterInstance): Der handelnde Charakter
            is_player (bool): True, wenn es ein Spielercharakter ist, False für Gegner
            allies (List[CharacterInstance]): Liste der lebenden Verbündeten
            enemies (List[CharacterInstance]): Liste der lebenden Feinde
        """
        # Verfügbare Skills für den Charakter laden
        available_skills = {skill_id: self.skill_definitions.get(skill_id)
                            for skill_id in character.skill_ids
                            if skill_id in self.skill_definitions}

        if not available_skills:
             logger.warning(f"{character.name} hat keine verfügbaren Skills.")
             self.cli_output.print_message(f"{character.name} hat keine verfügbaren Skills!")
             return # Charakter kann nichts tun

        # KI-Entscheidung für den nächsten Zug
        # Übergeben Sie die Listen der lebenden Verbündeten und Feinde an die KI
        skill, primary_target, secondary_targets = self.ai_dispatcher.choose_action(
            character, allies, enemies, available_skills
        )

        if not skill:
            logger.warning(f"KI konnte keine Aktion für {character.name} auswählen.")
            self.cli_output.print_message(f"{character.name} kann keine Aktion ausführen (KI-Entscheidung fehlgeschlagen)!")
            return

        # Prüfen, ob 'requires_target' Attribut existiert, bevor darauf zugegriffen wird
        # Wenn der Skill ein Ziel benötigt UND kein primäres Ziel ausgewählt wurde
        if hasattr(skill, 'requires_target') and skill.requires_target and not primary_target:
             logger.warning(f"KI wählte Skill '{skill.name}', der ein Ziel erfordert, aber kein gültiges Ziel für {character.name} gefunden.")
             self.cli_output.print_message(f"{character.name} wählt {skill.name}, findet aber kein gültiges Ziel!")
             return

        # Kampfaktion erstellen und ausführen
        # Importiere CombatAction und get_combat_system hier, falls sie nur hier benötigt werden
        from src.game_logic.combat import CombatAction, get_combat_system
        combat_system = get_combat_system()

        action = CombatAction(character, skill, primary_target, secondary_targets)
        logger.debug(f"Führe Aktion aus: {character.name} verwendet {skill.name} auf {primary_target.name if primary_target else 'kein Ziel'}")
        result = combat_system.execute_action(action)

        # Ergebnis anzeigen
        # is_self_effect = skill.is_self_effect() # Annahme: SkillDefinition hat diese Methode
        # is_healing = 'base_healing' in skill.effects # Annahme: SkillDefinition hat 'effects' Attribut

        # Aktionsausgabe
        action_desc = f"{character.name} verwendet {skill.name}"
        target_desc = f"auf {primary_target.name}" if primary_target else ""

        # Logik für "auf sich selbst" kann beibehalten werden, wenn skill.is_self_effect existiert
        # if hasattr(skill, 'is_self_effect') and skill.is_self_effect() and character == primary_target:
        #     target_desc = "auf sich selbst"

        self.cli_output.print_message(f"{action_desc} {target_desc}")

        # Trefferausgabe
        for target in result.hits:
            if target in result.damage_dealt:
                damage = result.damage_dealt[target]
                self.cli_output.print_message(f"  • Trifft {target.name} für {damage} Schaden")
                if not target.is_alive():
                    self.cli_output.print_message(f"  • {target.name} wurde besiegt!")
                    logger.info(f"{target.name} wurde besiegt.")

            if target in result.healing_done:
                healing = result.healing_done[target]
                self.cli_output.print_message(f"  • Heilt {target.name} um {healing} HP")

            if target in result.effects_applied:
                effects = result.effects_applied[target]
                self.cli_output.print_message(f"  • Wendet Effekt(e) an: {', '.join(effects)}")

        for target in result.misses:
            self.cli_output.print_message(f"  • Verfehlt {target.name}")

        # Status nach der Aktion anzeigen (optional, kann bei vielen Aktionen zu viel Output erzeugen)
        # self.cli_output.wait(0.5) # Pause nach jeder Aktion kann die Simulation verlangsamen

    def _show_combat_results(self) -> None:
        """Zeigt die Ergebnisse des aktuellen Kampfes an."""
        if not self.current_encounter:
            logger.warning("show_combat_results aufgerufen, aber kein aktiver Kampf.")
            return

        self.cli_output.print_subheader("Kampfergebnis")

        if self.current_encounter.winner == 'players':
            self.cli_output.print_message("Die Spieler haben gesiegt!")
            logger.info("Spieler haben den Kampf gewonnen.")

            # XP vergeben
            # Stellen Sie sicher, dass XP nur an lebende Spieler vergeben wird
            self.current_encounter.award_xp_for_victory(self.leveling_service, [p for p in self.players if p.is_alive()])

            # Status der überlebenden Spieler anzeigen
            alive_players = [p for p in self.players if p.is_alive()]
            if alive_players:
                self.cli_output.print_message("\nÜberlebende Spieler:")
                for player in alive_players:
                    self.cli_output.print_character_stats(player, detailed=True)

                    # XP-Fortschritt anzeigen
                    next_level_xp = self.leveling_service.get_xp_for_next_level(player)
                    progress = self.leveling_service.get_xp_progress_percentage(player)
                    self.cli_output.print_message(
                        f"XP: {player.xp}/{next_level_xp} ({progress:.1f}% zum nächsten Level)"
                    )
                    logger.debug(f"{player.name} XP Fortschritt: {player.xp}/{next_level_xp} ({progress:.1f}%)")
            else:
                 self.cli_output.print_message("Keine Spieler haben überlebt.")


        elif self.current_encounter.winner == 'opponents':
            self.cli_output.print_message("Die Gegner haben gesiegt! GAME OVER")
            logger.info("Gegner haben den Kampf gewonnen. GAME OVER.")
            # In einer echten Implementierung würde hier das Spiel beendet oder neu gestartet

        else:
            self.cli_output.print_message("Der Kampf endete unentschieden.")
            logger.info("Der Kampf endete unentschieden.")

        self.cli_output.wait(2.0) # Kurze Pause nach Kampfergebnis

    def _show_final_stats(self) -> None:
        """Zeigt die Endstatistiken der Spieler an."""
        self.cli_output.print_subheader("Endstatistiken")
        logger.info("Zeige Endstatistiken der Spieler.")

        if not self.players:
             self.cli_output.print_message("Keine Spieler vorhanden.")
             logger.warning("Keine Spieler für Endstatistiken gefunden.")
             return

        for i, player in enumerate(self.players):
            status = "Lebt" if player.is_alive() else "Gefallen im Kampf"
            self.cli_output.print_message(f"Spieler {i+1}: {player.name} (Level {player.level}) - Status: {status}")
            self.cli_output.print_character_stats(player, detailed=True)

            if player.is_alive():
                next_level_xp = self.leveling_service.get_xp_for_next_level(player)
                progress = self.leveling_service.get_xp_progress_percentage(player)
                self.cli_output.print_message(
                    f"XP: {player.xp}/{next_level_xp} ({progress:.1f}% zum nächsten Level)"
                )
            else:
                 # Status wurde oben schon ausgegeben, kann hier weggelassen werden oder detaillierter sein
                 pass # oder self.cli_output.print_message("Status: Gefallen im Kampf")

        self.cli_output.wait(3.0) # Längere Pause am Ende


# Die run_simulation Funktion akzeptiert nun die Anzahl der Spieler und Begegnungen
def run_simulation(characters_path: str, skills_path: str, opponents_path: str, num_players: int, num_encounters: int) -> None:
    """
    Führt die CLI-Simulation durch.

    Args:
        characters_path (str): Pfad zur characters.json5-Datei
        skills_path (str): Pfad zur skills.json5-Datei
        opponents_path (str): Pfad zur opponents.json5-Datei
        num_players (int): Anzahl der Spielercharaktere
        num_encounters (int): Anzahl der zu simulierenden Begegnungen
    """
    try:
        simulation = CLISimulation(characters_path, skills_path, opponents_path)

        # Startet die Simulation mit den übergebenen Werten
        simulation.start_simulation(num_players, num_encounters)

    except FileNotFoundError as e:
         logger.error(f"Simulation konnte nicht gestartet werden: {e}")
         print(f"FEHLER: Benötigte Datei nicht gefunden: {e}")
    except Exception as e:
         logger.exception(f"Ein unerwarteter Fehler ist während der Simulation aufgetreten: {e}")
         print(f"FEHLER: Ein unerwarteter Fehler ist aufgetreten: {e}")

