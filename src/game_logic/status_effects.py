from dataclasses import dataclass, field
from typing import Optional, Any # Any für Combatant wegen zirkulärem Import-Risiko

# Hinweis: Direkter Import von Character/Enemy hier würde zu zirkulären Imports führen.
# Wir verwenden 'Any' oder String-Annotationen, falls nötig.

@dataclass
class StatusEffect:
    """ Repräsentiert einen aktiven Statuseffekt auf einem Combatant. """
    effect_id: str               # Eindeutige ID des Effekts (z.B. "STUNNED", "BURNING")
    display_name: str            # Angezeigter Name (z.B. "Betäubt", "Brennt")
    total_duration: int          # Ursprüngliche Dauer in Runden
    duration_remaining: int      # Verbleibende Dauer in Runden
    magnitude: Optional[Any] = None # Stärke/Wert des Effekts (z.B. -3 für WEAKENED, Schadenswert für BURNING?)
    caster: Optional[Any] = None # Wer hat den Effekt verursacht? (Typ: Combatant)
    source_skill_id: Optional[str] = None # Welcher Skill hat den Effekt verursacht?

    def __post_init__(self):
        # Sicherstellen, dass duration_remaining gesetzt ist, falls nicht übergeben
        if self.duration_remaining is None:
            self.duration_remaining = self.total_duration

    def tick_down(self):
        """ Reduziert die verbleibende Dauer um 1. """
        if self.duration_remaining > 0:
            self.duration_remaining -= 1

    def is_expired(self) -> bool:
        """ Prüft, ob der Effekt abgelaufen ist. """
        return self.duration_remaining <= 0

    def __str__(self):
        return f"{self.display_name} ({self.duration_remaining}/{self.total_duration} Runden)"

