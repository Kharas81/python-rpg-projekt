# src/definitions/base_definitions.py

import dataclasses
from typing import Dict, List

@dataclasses.dataclass(frozen=True) # frozen=True macht Instanzen unveränderlich nach Erstellung
class StatDefinition:
    """Repräsentiert die Definition eines Stats, Attributs, Ressource oder Flags."""
    id: str          # Eindeutige ID (z.B. "STR", "HP", "IS_UNDEAD")
    name: str        # Angezeigter Name (z.B. "Stärke", "Lebenspunkte")
    description: str # Beschreibung der Funktionsweise

    def __str__(self) -> str:
        """Gibt eine benutzerfreundliche String-Repräsentation zurück."""
        return f"{self.name} ({self.id}): {self.description}"

# Typ-Alias für bessere Lesbarkeit, wenn wir mit geladenen Definitionen arbeiten
DefinitionsDatabase = Dict[str, StatDefinition]

@dataclasses.dataclass(frozen=True)
class CharacterClassDefinition:
    """Repräsentiert die Definition einer Charakterklasse."""
    id: str                 # Eindeutige ID (z.B. "WARRIOR")
    name: str               # Angezeigter Name (z.B. "Krieger")
    description: str        # Beschreibung der Klasse
    base_stats: Dict[str, int] # Basiswerte für Stats (ID -> Wert)
    starting_skills: List[str] # Liste der IDs der Start-Skills

    def __str__(self) -> str:
        """Gibt eine benutzerfreundliche String-Repräsentation zurück."""
        stats_str = ", ".join(f"{k}={v}" for k, v in self.base_stats.items())
        skills_str = ", ".join(self.starting_skills)
        return (f"{self.name} ({self.id}): {self.description}\n"
                f"  Base Stats: [{stats_str}]\n"
                f"  Starting Skills: [{skills_str}]")

# Typ-Alias für die Datenbank der Charakterklassen
ClassDatabase = Dict[str, CharacterClassDefinition]