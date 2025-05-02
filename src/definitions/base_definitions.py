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