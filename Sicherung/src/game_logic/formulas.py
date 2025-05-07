import typing
import math

# --- Attribut-Bonus ---
def calculate_attribute_bonus(attribute_value: int) -> int:
    """
    Berechnet den Bonus (oder Malus) basierend auf einem Attributwert.
    Formel: (Attributwert - 10) / 2, abgerundet.
    """
    bonus = math.floor((attribute_value - 10) / 2)
    return int(bonus)

# --- HP-Berechnung ---
def calculate_max_hp(base_hp: int, constitution: int) -> int:
    """
    Berechnet die maximalen Lebenspunkte basierend auf Basis-HP und Konstitution.

    Args:
        base_hp: Der Basis-HP-Wert aus der Charakterdefinition (combat_values).
        constitution: Der Konstitutionswert des Charakters.

    Returns:
        Die maximalen Lebenspunkte (mindestens 1).
    """
    # Formel angepasst an ANNEX: base_hp + CON * 5
    # Die Konstante 5 für CON-Multiplikator könnte auch aus Config kommen
    hp = base_hp + constitution * 5
    return max(1, hp) # Sicherstellen, dass HP mindestens 1 ist

# --- Zukünftige Formeln können hier hinzugefügt werden ---
# z.B. calculate_hit_chance, calculate_damage etc.


# --- Testblock ---
if __name__ == '__main__':
    print("--- Formel Test: Attribut-Bonus ---")
    test_values = [8, 9, 10, 11, 12, 13, 14, 15, 16]
    print(f"Teste Attributwerte: {test_values}")
    for value in test_values:
        bonus = calculate_attribute_bonus(value)
        print(f"  Attribut {value:2d} -> Bonus {bonus:2d}")

    print("\n--- Formel Test: Max HP ---")
    # Beispiel Krieger: base_hp=50, CON=12 -> 50 + 12*5 = 110
    # Beispiel Goblin: base_hp=50, CON=9 -> 50 + 9*5 = 95
    test_hp_data = [(50, 12), (50, 9), (40, 8), (60, 15)]
    print(f"Teste (Base HP, CON): {test_hp_data}")
    for base, con in test_hp_data:
         max_hp = calculate_max_hp(base, con)
         print(f"  Base HP {base:2d}, CON {con:2d} -> Max HP {max_hp:3d}")

