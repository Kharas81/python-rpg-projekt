# src/game_logic/formulas.py
"""
Modul für grundlegende Berechnungsformeln im Spiel.
Bezieht Konstanten und Einstellungen aus der globalen Konfiguration.
"""
import math
import logging

# Erhalte einen Logger für dieses Modul
logger = logging.getLogger(__name__)

# Importiere die globale Konfiguration
# Es wird davon ausgegangen, dass config.py bereits geladen und CONFIG verfügbar ist.
try:
    from src.config.config import CONFIG
except ImportError:
    logger.critical("FATAL: Konfigurationsmodul src.config.config konnte nicht importiert werden. Formeln verwenden möglicherweise falsche Standardwerte.")
    # Fallback für den Fall, dass CONFIG nicht geladen werden kann (z.B. bei unit tests ohne vollen App-Kontext)
    # Dies ist nur ein Notbehelf und sollte in der normalen Ausführung nicht passieren.
    class FallbackConfig:
        def get(self, key_path: str, default: any = None) -> any:
            # Minimale Fallback-Werte, die für Tests benötigt werden könnten
            if key_path == "game_settings.min_damage": return 1
            if key_path == "game_settings.hit_chance_base": return 90
            if key_path == "game_settings.hit_chance_accuracy_factor": return 3
            if key_path == "game_settings.hit_chance_evasion_factor": return 2
            if key_path == "game_settings.hit_chance_min": return 5
            if key_path == "game_settings.hit_chance_max": return 95
            if key_path == "game_settings.xp_level_base": return 100
            if key_path == "game_settings.xp_level_factor": return 1.5
            logger.warning(f"CONFIG nicht verfügbar. Fallback für '{key_path}' mit Wert '{default}' verwendet.")
            return default
    CONFIG = FallbackConfig()


def calculate_attribute_bonus(attribute_value: int) -> int:
    """
    Berechnet den Bonus (oder Malus) basierend auf einem Attributwert.
    Formel: (Attributwert - 10) // 2 (Ganzzahlige Division)
    Beispiel: STR 10 -> 0 Bonus, STR 12 -> +1 Bonus, STR 8 -> -1 Bonus
    """
    bonus = (attribute_value - 10) // 2
    # logger.debug(f"Attributbonus für Wert {attribute_value}: {bonus}")
    return bonus

def calculate_max_hp(base_hp: int, constitution_value: int, con_hp_factor: int = 5) -> int:
    """
    Berechnet die maximalen Lebenspunkte eines Charakters.
    Formel: base_hp (aus Template) + (CON * con_hp_factor)
    Der con_hp_factor ist standardmäßig 5, könnte aber konfigurierbar sein.
    """
    # con_hp_factor könnte auch aus CONFIG bezogen werden, falls es dort definiert ist.
    # z.B. con_hp_factor = CONFIG.get("game_settings.constitution_hp_factor", 5)
    max_hp = base_hp + (constitution_value * con_hp_factor)
    # logger.debug(f"Max HP berechnet: Basis={base_hp}, CON={constitution_value}, Faktor={con_hp_factor} -> MaxHP={max_hp}")
    return max(1, max_hp) # Stellt sicher, dass HP mindestens 1 ist

def calculate_damage(base_damage_skill: int,
                     attribute_bonus: int,
                     multiplier_skill: float,
                     critical_hit: bool = False,
                     critical_multiplier: float = 1.5) -> int:
    """
    Berechnet den Basisschaden eines Angriffs oder Skills vor Schadensreduktion.
    Formel: floor((Basis-Schaden_Skill + Attribut-Bonus) * Multiplikator_Skill)
    Wenn kritischer Treffer: Schaden * Krit-Multiplikator
    """
    raw_damage = math.floor((base_damage_skill + attribute_bonus) * multiplier_skill)
    
    if critical_hit:
        raw_damage = math.floor(raw_damage * critical_multiplier)
        # logger.debug(f"Kritischer Treffer! Schaden multipliziert mit {critical_multiplier}")

    # logger.debug(f"Schaden berechnet: BasisSkillDmg={base_damage_skill}, AttrBonus={attribute_bonus}, SkillMult={multiplier_skill}, Krit={critical_hit} -> RawDmg={raw_damage}")
    return max(CONFIG.get("game_settings.min_damage", 1), raw_damage) # Stellt min_damage sicher

def calculate_damage_reduction(incoming_damage: int, armor_or_magic_resist: int) -> int:
    """
    Berechnet den reduzierten Schaden nach Anwendung von Rüstung oder Magieresistenz.
    Formel: max(min_damage, Eingehender_Schaden - (Rüstung oder Magieresistenz))
    """
    reduced_damage = max(CONFIG.get("game_settings.min_damage", 1), incoming_damage - armor_or_magic_resist)
    # logger.debug(f"Schadensreduktion: Eingehend={incoming_damage}, Resist={armor_or_magic_resist} -> Reduziert={reduced_damage}")
    return reduced_damage

def calculate_hit_chance(accuracy: int, # Genauigkeit des Angreifers
                         evasion: int,   # Ausweichen des Verteidigers
                         base_chance_override: Optional[int] = None # Für Skills mit fester Trefferchance
                         ) -> int:
    """
    Berechnet die Trefferchance in Prozent.
    Formel: base_chance + (accuracy * accuracy_factor) - (evasion * evasion_factor)
    Das Ergebnis wird auf min_chance und max_chance begrenzt.
    Werte aus game_settings.json5 werden verwendet.
    """
    if base_chance_override is not None:
        # logger.debug(f"Trefferchance-Override verwendet: {base_chance_override}%")
        return max(CONFIG.get("game_settings.hit_chance_min", 5), 
                   min(CONFIG.get("game_settings.hit_chance_max", 95), base_chance_override))

    base_chance = CONFIG.get("game_settings.hit_chance_base", 90)
    accuracy_factor = CONFIG.get("game_settings.hit_chance_accuracy_factor", 3)
    evasion_factor = CONFIG.get("game_settings.hit_chance_evasion_factor", 2)
    min_chance = CONFIG.get("game_settings.hit_chance_min", 5)
    max_chance = CONFIG.get("game_settings.hit_chance_max", 95)
    
    hit_chance = base_chance + (accuracy * accuracy_factor) - (evasion * evasion_factor)
    final_hit_chance = max(min_chance, min(max_chance, hit_chance))
    
    # logger.debug(f"Trefferchance berechnet: Basis={base_chance}, Acc={accuracy}(*{accuracy_factor}), Eva={evasion}(*{evasion_factor}) -> Roh={hit_chance} -> Final={final_hit_chance}%")
    return final_hit_chance

def calculate_xp_for_next_level(current_level: int) -> int:
    """
    Berechnet die benötigten Erfahrungspunkte für das nächste Level.
    Formel: ceil(xp_level_base * (xp_level_factor ^ (Aktuelles_Level - 1)))
    (Hinweis: Für Level 1 auf 2 ist es xp_level_base * xp_level_factor^0 = xp_level_base)
    Wenn current_level = 1, dann ist der Exponent 0.
    """
    if current_level < 1:
        # logger.warning(f"Ungültiges current_level für XP-Berechnung: {current_level}. Gebe hohen Wert zurück.")
        return 999999999 # Sollte nicht passieren

    base_xp = CONFIG.get("game_settings.xp_level_base", 100)
    factor = CONFIG.get("game_settings.xp_level_factor", 1.5)
    
    # Für Level 1 (um auf Level 2 zu kommen) ist der Exponent (1-1)=0
    # Für Level 2 (um auf Level 3 zu kommen) ist der Exponent (2-1)=1
    # etc.
    # Die Formel in ANNEX (Aktuelles_Level - 1) ist korrekt, um die XP für den Aufstieg *vom aktuellen Level* zu berechnen.
    if current_level == 0: # Spezialfall für initiales Level, oder falls Level 0 nicht existiert
        required_xp = base_xp
    else:
        required_xp = math.ceil(base_xp * (factor ** (current_level -1))) # ANNEX: (Aktuelles_Level -1)
        
    # logger.debug(f"XP für nächstes Level (von {current_level}): BasisXP={base_xp}, Faktor={factor} -> Benötigt={required_xp}")
    return required_xp

def calculate_initiative(dexterity_value: int, initiative_bonus: int = 0) -> int:
    """
    Berechnet den Basis-Initiativewert eines Charakters.
    Formel: DEX * 2 + initiative_bonus
    """
    base_initiative = (dexterity_value * 2) + initiative_bonus
    # logger.debug(f"Initiative berechnet: DEX={dexterity_value}*2, Bonus={initiative_bonus} -> Initiative={base_initiative}")
    return base_initiative


if __name__ == "__main__":
    # Testen der Formeln
    print("--- Teste Formeln ---")

    # Konfiguration laden (normalerweise durch Import von config erledigt, aber hier explizit für den Test)
    # Dies stellt sicher, dass CONFIG für die Tests verfügbar ist, falls dieses Skript direkt ausgeführt wird.
    try:
        from src.config.config import load_config
        cfg = load_config() # Stellt sicher, dass CONFIG initialisiert ist
        print(f"CONFIG.game_settings.min_damage: {CONFIG.get('game_settings.min_damage')}")
    except ImportError:
        print("Konnte Konfiguration nicht laden, Fallbacks werden verwendet.")

    # Attributbonus
    print(f"\nAttributbonus für 10 DEX: {calculate_attribute_bonus(10)}") # Erwartet: 0
    print(f"Attributbonus für 13 STR: {calculate_attribute_bonus(13)}") # Erwartet: 1
    print(f"Attributbonus für 7 INT: {calculate_attribute_bonus(7)}")   # Erwartet: -2

    # Max HP
    print(f"\nMax HP (Basis 50, CON 12): {calculate_max_hp(base_hp=50, constitution_value=12)}") # Erw: 50 + 12*5 = 110
    print(f"Max HP (Basis 30, CON 8, Faktor 4): {calculate_max_hp(base_hp=30, constitution_value=8, con_hp_factor=4)}") # Erw: 30 + 8*4 = 62
    
    # Schaden
    # Annahme: game_settings.min_damage = 1 (aus settings.json5 oder Fallback)
    print(f"\nSchaden (Basis 10, Bonus +2, Multi 1.0): {calculate_damage(10, 2, 1.0)}") # Erw: 12
    print(f"Schaden (Basis 5, Bonus +0, Multi 1.5): {calculate_damage(5, 0, 1.5)}")   # Erw: floor(7.5) = 7
    print(f"Schaden (Basis 5, Bonus +0, Multi 1.5, Kritisch): {calculate_damage(5, 0, 1.5, critical_hit=True, critical_multiplier=2.0)}") # Erw: floor(7.5)*2 = 7*2 = 14
    print(f"Schaden (Basis 1, Bonus -1, Multi 1.0): {calculate_damage(1, -1, 1.0)}") # Erw: max(1, 0) = 1 (wegen min_damage)

    # Schadensreduktion
    # Annahme: game_settings.min_damage = 1
    print(f"\nSchadensreduktion (Dmg 15, Resist 5): {calculate_damage_reduction(15, 5)}") # Erw: 10
    print(f"Schadensreduktion (Dmg 10, Resist 12): {calculate_damage_reduction(10, 12)}") # Erw: max(1, -2) = 1

    # Trefferchance
    # Annahmen aus settings.json5: base 90, acc_factor 3, eva_factor 2, min 5, max 95
    print(f"\nTrefferchance (Acc 0, Eva 0): {calculate_hit_chance(0, 0)}%") # Erw: 90
    print(f"Trefferchance (Acc 5, Eva 2): {calculate_hit_chance(5, 2)}%") # Erw: 90 + 5*3 - 2*2 = 90 + 15 - 4 = 101 -> 95 (max)
    print(f"Trefferchance (Acc -2, Eva 10): {calculate_hit_chance(-2, 10)}%") # Erw: 90 - 6 - 20 = 64
    print(f"Trefferchance (Acc 0, Eva 0, Override 75%): {calculate_hit_chance(0, 0, base_chance_override=75)}%") # Erw: 75
    print(f"Trefferchance (Acc 0, Eva 0, Override 100%): {calculate_hit_chance(0, 0, base_chance_override=100)}%") # Erw: 95 (max)
    print(f"Trefferchance (Acc 0, Eva 0, Override 0%): {calculate_hit_chance(0, 0, base_chance_override=0)}%") # Erw: 5 (min)

    # XP für nächstes Level
    # Annahmen aus settings.json5: base 100, factor 1.5
    print(f"\nXP für Level 2 (von Level 1): {calculate_xp_for_next_level(1)}") # Erw: ceil(100 * 1.5^0) = 100
    print(f"XP für Level 3 (von Level 2): {calculate_xp_for_next_level(2)}") # Erw: ceil(100 * 1.5^1) = 150
    print(f"XP für Level 4 (von Level 3): {calculate_xp_for_next_level(3)}") # Erw: ceil(100 * 1.5^2) = ceil(100 * 2.25) = 225

    # Initiative
    print(f"\nInitiative (DEX 10, Bonus 0): {calculate_initiative(10, 0)}") # Erw: 20
    print(f"Initiative (DEX 14, Bonus 5): {calculate_initiative(14, 5)}") # Erw: 28 + 5 = 33

    print("\n--- Formel-Tests abgeschlossen ---")