import logging
import random # Für zufällige Startreihenfolge oder Aktionen
import time # Um die Simulation ggf. zu verlangsamen

# Importiere unsere Spiel-Logik und Definitionen
try:
    from src.definitions import loader
    from src.game_logic.entities import CharacterInstance
    from src.game_logic import combat
    from src.ai import ai_dispatcher
except ImportError:
     # Fallback für den Fall, dass die Struktur beim direkten Testen nicht erkannt wird
     # Im Normalbetrieb (via main.py) sollten die Imports oben funktionieren.
    print("WARNUNG: cli_main_loop.py - Module nicht direkt geladen.")
    # Hier sind relative Imports schwierig, da die Struktur relativ zu src/main.py erwartet wird.
    # Stelle sicher, dass du das Modul über main.py oder mit korrektem PYTHONPATH testest.
    # Für einen isolierten Test wären sys.path Anpassungen nötig.
    # Wir gehen davon aus, dass es über main.py aufgerufen wird.
    # raise # Optional Fehler werfen, wenn es nicht über main.py läuft
    # Fallback: Beende, wenn nicht korrekt importiert
    import sys
    print("FEHLER: Führe dieses Modul über 'python src/main.py --mode auto' aus.")
    sys.exit(1)


logger = logging.getLogger(__name__)

# --- Konfiguration für die Simulation ---
PLAYER_CLASS_ID = "krieger" # Welchen Charakter spielt der "Spieler"?
OPPONENT_ID = "goblin_lv1" # Welcher Gegner?
MAX_ROUNDS = 100 # Maximale Runden, um Endlosschleifen zu verhindern

def run_simulation():
    """Führt eine einzelne Kampfsimulation im Auto-Modus durch."""
    logger.info("Starte CLI Kampfsimulation...")
    print("\n" + "="*30)
    print("=== KAMPFSIMULATION START ===")
    print("="*30 + "\n")

    # --- 1. Setup: Charaktere laden und instanziieren ---
    player_def = loader.get_character_class(PLAYER_CLASS_ID)
    opponent_def = loader.get_opponent(OPPONENT_ID)

    if not player_def or not opponent_def:
        logger.critical("FEHLER: Spieler- oder Gegnerdefinition konnte nicht geladen werden. Simulation abgebrochen.")
        return

    player = CharacterInstance(player_def)
    opponent = CharacterInstance(opponent_def)

    logger.info(f"Spieler erstellt: {player}")
    logger.info(f"Gegner erstellt: {opponent}")
    print(f"Spieler: {player.name} (Lvl {player.level}, HP {player.current_hp})")
    print(f"Gegner: {opponent.name} (Lvl {opponent.level}, HP {opponent.current_hp})")
    print("-" * 30)

    # --- 2. Kampfschleife ---
    round_counter = 0
    while player.is_alive() and opponent.is_alive() and round_counter < MAX_ROUNDS:
        round_counter += 1
        logger.info(f"--- Runde {round_counter} START ---")
        print(f"\n--- Runde {round_counter} ---")
        print(f"{player.name}: {player.current_hp}/{player.max_hp} HP | {opponent.name}: {opponent.current_hp}/{opponent.max_hp} HP")
        if player.active_status_effects: print(f"  {player.name} Effekte: {[e.effect_id for e in player.active_status_effects]}")
        if opponent.active_status_effects: print(f"  {opponent.name} Effekte: {[e.effect_id for e in opponent.active_status_effects]}")


        # --- Rundenlogik ---
        # TODO: Initiative / Wer beginnt? Fürs Erste: Spieler zuerst.

        # 2a. Spieler-Zug (Simuliert - wählt immer ersten Skill)
        if player.is_alive() and player.can_act(): # Prüfen ob handlungsfähig
            player_skill_id_to_use = player.definition.skill_ids[0] if player.definition.skill_ids else None
            player_skill = loader.get_skill(player_skill_id_to_use) if player_skill_id_to_use else None

            if player_skill:
                print(f"\nSpieler ({player.name}) Zug:")
                combat.execute_attack_action(player, opponent, player_skill)
            else:
                logger.warning(f"Spieler '{player.name}' hat keine Skills zum Angreifen.")
                print(f"Spieler ({player.name}) passt.")
        elif player.is_alive():
             logger.info(f"Spieler '{player.name}' kann diese Runde nicht handeln.")
             print(f"Spieler ({player.name}) kann nicht handeln.")


        # 2b. Gegner-Zug (wenn Spieler noch lebt und Gegner dran ist)
        if opponent.is_alive() and player.is_alive() and opponent.can_act():
             print(f"\nGegner ({opponent.name}) Zug:")
             # AI Dispatcher fragen, was zu tun ist
             opponent_skill_id, target = ai_dispatcher.get_ai_action(opponent, [player]) # Ziel ist immer der Spieler

             if opponent_skill_id and target:
                  opponent_skill = loader.get_skill(opponent_skill_id)
                  if opponent_skill:
                       combat.execute_attack_action(opponent, target, opponent_skill)
                  else:
                       logger.error(f"Gegner '{opponent.name}' AI wählte ungültigen Skill '{opponent_skill_id}'.")
                       print(f"Gegner ({opponent.name}) ist verwirrt.")
             else:
                  logger.info(f"Gegner '{opponent.name}' AI findet keine Aktion.")
                  print(f"Gegner ({opponent.name}) passt.")
        elif opponent.is_alive():
             logger.info(f"Gegner '{opponent.name}' kann diese Runde nicht handeln.")
             print(f"Gegner ({opponent.name}) kann nicht handeln.")


        # 2c. Effekte ticken lassen (am Ende der Runde)
        if player.is_alive(): player.tick_status_effects()
        if opponent.is_alive(): opponent.tick_status_effects()

        logger.info(f"--- Runde {round_counter} ENDE ---")
        # Optional: Kurze Pause zur besseren Lesbarkeit
        # time.sleep(0.5)


    # --- 3. Kampfende ---
    logger.info("Kampfschleife beendet.")
    print("\n" + "="*30)
    print("=== KAMPF BEENDET ===")
    if player.is_alive() and not opponent.is_alive():
        winner = player
        loser = opponent
        print(f"Sieger: {winner.name}!")
        logger.info(f"Sieger: {winner.name}")
    elif not player.is_alive() and opponent.is_alive():
        winner = opponent
        loser = player
        print(f"Sieger: {winner.name}!")
        logger.info(f"Sieger: {winner.name}")
    elif not player.is_alive() and not opponent.is_alive():
        print("Unentschieden! Beide wurden besiegt.")
        logger.info("Unentschieden! Beide wurden besiegt.")
    elif round_counter >= MAX_ROUNDS:
         print(f"Kampf nach {MAX_ROUNDS} Runden abgebrochen (Zeitlimit).")
         logger.warning(f"Kampf nach {MAX_ROUNDS} Runden abgebrochen (Zeitlimit).")
    else: # Sollte nicht passieren
         print("Unbekannter Endzustand.")
         logger.error("Unbekannter Kampf-Endzustand.")

    print(f"Endstatus Spieler: {player}")
    print(f"Endstatus Gegner: {opponent}")
    print("="*30 + "\n")
    logger.info(f"Endstatus Spieler: {player}")
    logger.info(f"Endstatus Gegner: {opponent}")
    logger.info("CLI Kampfsimulation beendet.")


# Optionaler Testblock für dieses Modul (kann leer sein oder spezifische UI-Tests enthalten)
if __name__ == '__main__':
     print("Dieses Modul ist dafür gedacht, über 'src/main.py --mode auto' aufgerufen zu werden.")
     print("Führe 'python src/main.py --mode auto' aus, um die Simulation zu starten.")
     # Optional: Rufe run_simulation() direkt auf für schnelle Tests, benötigt aber korrekten Pfad/Imports
     # try:
     #     from src.utils.logging_setup import setup_logging; setup_logging()
     #     run_simulation()
     # except Exception as e:
     #     print(f"Fehler beim direkten Testlauf: {e}")

