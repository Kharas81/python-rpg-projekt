# src/definitions/base_definitions.py

import dataclasses
from typing import Dict, List, Optional, Union, Any

# --- Stat / Attribute / Resource / Flag Definitions ---

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


# --- Character Class Definitions ---

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


# --- Skill and Effect Definitions ---

@dataclasses.dataclass(frozen=True)
class EffectDefinition:
    """Repräsentiert einen einzelnen Effekt eines Skills."""
    # Kernfelder
    type: str # Typ des Effekts (DAMAGE, HEAL, APPLY_STATUS, MODIFY_STAT, ABSORB_SHIELD)

    # Optional: Felder für verschiedene Effekttypen (mit Defaults)
    damage_type: Optional[str] = None          # Für DAMAGE: PHYSICAL, MAGIC, FIRE, etc.
    base_value: Optional[float] = None         # Für DAMAGE, HEAL, ABSORB, MODIFY_STAT
    use_weapon_damage: bool = False            # Für DAMAGE: True wenn Waffenschaden Basis ist
    scaling_stat: Optional[str] = None         # Für DAMAGE, HEAL, ABSORB: Stat für Bonus-Skalierung
    bonus_multiplier: float = 1.0              # Für DAMAGE, HEAL, ABSORB: Multiplikator für Bonus
    hit_multiplier: float = 1.0                # Für DAMAGE: Multiplikator für Gesamtschaden
    status_id: Optional[str] = None            # Für APPLY_STATUS: ID des StatusEffekts
    chance: float = 1.0                        # Für APPLY_STATUS: Wahrscheinlichkeit (0.0-1.0)
    duration: Optional[int] = None             # Für APPLY_STATUS, MODIFY_STAT, ABSORB: Dauer in Runden
    stat_id: Optional[str] = None              # Für MODIFY_STAT: ID des zu ändernden Stats
    value: Optional[float] = None              # Für MODIFY_STAT: Änderungswert (kann negativ sein)
    applies_to: Optional[str] = None           # Für AREA Effekte: PRIMARY oder SECONDARY
    num_secondary_targets: Optional[int] = None # Für AREA Effekte: Anzahl Nebenziele
    special: Optional[Dict[str, Any]] = None   # Für spezielle Modifikatoren (z.B. armor_penetration)

    def __str__(self) -> str:
        """Gibt eine kompakte String-Repräsentation des Effekts zurück."""
        details = [f"type={self.type}"]
        for field in dataclasses.fields(self):
            # Zeige nur Felder an, die nicht None sind (außer 'type') und nicht dem Default entsprechen
            value = getattr(self, field.name)
            if field.name != 'type' and value is not None:
                 is_default = False
                 # Prüfe auf Defaults (None wird oben schon ausgeschlossen)
                 if field.default != dataclasses.MISSING and field.default is not None:
                      if field.default == value:
                           is_default = True
                 # Spezifische Default-Werte prüfen
                 elif field.name == 'use_weapon_damage' and value is False: is_default = True
                 elif field.name == 'bonus_multiplier' and value == 1.0: is_default = True
                 elif field.name == 'hit_multiplier' and value == 1.0: is_default = True
                 elif field.name == 'chance' and value == 1.0: is_default = True

                 if not is_default:
                     details.append(f"{field.name}={value!r}") # !r nutzt repr() für Strings etc.

        return f"Effect({', '.join(details)})"


@dataclasses.dataclass(frozen=True)
class SkillDefinition:
    """Repräsentiert die Definition eines Skills."""
    id: str
    name: str
    description: str
    cost: Dict[str, int]             # Ressource ID -> Kosten
    target: str                      # Zieltyp (ENEMY, SELF, ALLY, AREA)
    effects: List[EffectDefinition]  # Liste der Effekte dieses Skills

    def __str__(self) -> str:
        """Gibt eine benutzerfreundliche String-Repräsentation zurück."""
        cost_str = ", ".join(f"{res}={val}" for res, val in self.cost.items()) if self.cost else "None"
        effects_str = "\n    ".join(str(eff) for eff in self.effects)
        return (f"{self.name} ({self.id}): {self.description}\n"
                f"  Cost: [{cost_str}], Target: {self.target}\n"
                f"  Effects:\n    {effects_str}")

# Typ-Alias für die Datenbank der Skills
SkillDatabase = Dict[str, SkillDefinition]