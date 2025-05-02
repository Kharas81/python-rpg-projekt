# src/config.py

"""
Zentrale Konfigurationsdatei für Spielkonstanten und Einstellungen.
"""

# --- Attribute & Stat Berechnungen ---

# Basiswert, von dem Attribute abgezogen werden, bevor der Bonus berechnet wird
# Beispiel: Bonus = (Attributwert - ATTRIBUTE_BONUS_BASE) // ATTRIBUTE_BONUS_DIVISOR
ATTRIBUTE_BONUS_BASE: int = 10
ATTRIBUTE_BONUS_DIVISOR: int = 2

# HP-Berechnung
# Beispiel: Total HP = BASE_HP + (CON * CON_HP_MODIFIER)
BASE_HP: int = 50
CON_HP_MODIFIER: int = 5

# --- Weitere Einstellungen könnten hier folgen ---
# z.B. Standard-Spielgeschwindigkeit, Pfade, etc.