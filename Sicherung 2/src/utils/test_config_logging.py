"""
Einfache Test-Datei, um das Konfiguration- und Logging-Setup zu überprüfen.
"""
import sys
import os

# Stellen sicher, dass src im Python-Pfad ist
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from src.utils.logging_setup import get_logger
from src.config.config import get_config
from src.definitions import loader


def main():
    # Logger holen
    logger = get_logger("test_script")
    logger.info("Test des Konfiguration- und Logging-Setups")
    
    # Konfiguration testen
    config = get_config()
    logger.info(f"Geladene Spieleinstellungen: {config.game_settings}")
    
    # Pfade zu den JSON5-Dateien
    base_path = os.path.dirname(os.path.dirname(__file__))
    characters_path = os.path.join(base_path, "definitions", "json_data", "characters.json5")
    skills_path = os.path.join(base_path, "definitions", "json_data", "skills.json5")
    opponents_path = os.path.join(base_path, "definitions", "json_data", "opponents.json5")
    
    # Laden der JSON5-Dateien testen
    try:
        logger.info("Versuche characters.json5 zu laden...")
        characters = loader.load_characters(characters_path)
        logger.info(f"Erfolgreich {len(characters)} Charaktere geladen!")
        
        logger.info("Versuche skills.json5 zu laden...")
        skills = loader.load_skills(skills_path)
        logger.info(f"Erfolgreich {len(skills)} Skills geladen!")
        
        logger.info("Versuche opponents.json5 zu laden...")
        opponents = loader.load_opponents(opponents_path)
        logger.info(f"Erfolgreich {len(opponents)} Gegner geladen!")
        
        # Ein paar Details ausgeben
        logger.info("\n--- Charakter-Details ---")
        for char_id, char in characters.items():
            logger.info(f"Charakter: {char.name} (ID: {char_id})")
            logger.info(f"  STR: {char.get_attribute('STR')}, DEX: {char.get_attribute('DEX')}")
            logger.info(f"  Skills: {char.skills}")
        
        logger.info("\n--- Skill-Details ---")
        for skill_id, skill in skills.items():
            logger.info(f"Skill: {skill.name} (ID: {skill_id})")
            logger.info(f"  Kosten: {skill.get_cost_value()} {skill.get_cost_type()}")
            
        logger.info("\n--- Gegner-Details ---")
        for opp_id, opp in opponents.items():
            logger.info(f"Gegner: {opp.name} (ID: {opp_id})")
            logger.info(f"  Level: {opp.level}, XP: {opp.xp_reward}")
            logger.info(f"  KI-Strategie: {opp.ai_strategy}")
        
        logger.info("\nAlle Tests erfolgreich!")
        
    except Exception as e:
        logger.exception(f"Test fehlgeschlagen: {str(e)}")


if __name__ == "__main__":
    main()
