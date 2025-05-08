# src/definitions/character.py

from dataclasses import dataclass, field # field entfernt, da nicht direkt genutzt ohne default_factory
from typing import List, Dict

# Ty Алиасы для лучшей читаемости (Type Aliases for better readability)
PrimaryAttributeSet = Dict[str, int]  # z.B. {"STR": 10, "DEX": 12, ...}
BaseCombatValueSet = Dict[str, int]    # z.B. {"base_hp": 50, "armor": 5, ...}
SkillIdList = List[str]                # z.B. ["basic_strike_phys", "power_strike"]

@dataclass(frozen=True) # frozen=True macht Instanzen unveränderlich (immutable)
class CharacterDefinition:
    """
    Repräsentiert die statische Definition einer Charakterklasse,
    geladen aus den JSON-Dateien.
    Diese Objekte sind als unveränderlich gedacht, da sie Templates darstellen.
    """
    id: str                     # Eindeutige ID der Charakterklasse, z.B. "krieger"
    name: str                   # Anzeigename, z.B. "Krieger"
    description: str            # Kurze Beschreibung der Klasse

    primary_attributes: PrimaryAttributeSet   # Startwerte der Primärattribute
                                              # Beispiel: {"STR": 14, "DEX": 10, ...}

    base_combat_values: BaseCombatValueSet    # Basis-Kampfwerte (HP, Ressourcen, Rüstung etc.)
                                              # Beispiel: {"base_hp": 50, "base_stamina": 100, ...}

    starting_skills: SkillIdList              # Liste der IDs der Start-Skills
                                              # Beispiel: ["basic_strike_phys", "power_strike"]

    def __post_init__(self):
        # Hier könnten Validierungen stattfinden.
        # Fürs Erste halten wir es einfach.
        pass