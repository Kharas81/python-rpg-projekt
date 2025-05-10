# src/game_logic/effects.py
"""
Definiert die Basisklasse für Status-Effekte und konkrete Implementierungen.
Status-Effekte modifizieren Charakterinstanzen über Zeit oder bei bestimmten Ereignissen.
"""
import logging
from typing import TYPE_CHECKING, Optional, Dict, Any, Callable

# Um zirkuläre Importe bei Typ-Hinweisen zu vermeiden:
if TYPE_CHECKING:
    from src.game_logic.entities import CharacterInstance

logger = logging.getLogger(__name__)

class StatusEffect:
    """
    Basisklasse für alle Status-Effekte.
    Ein Status-Effekt hat eine Dauer, eine Stärke (Potency) und beeinflusst
    eine Ziel-Charakterinstanz.
    """
    def __init__(self,
                 effect_id: str,
                 name: str,
                 description: str,
                 target: 'CharacterInstance',
                 source_actor: Optional['CharacterInstance'], # Wer hat den Effekt verursacht?
                 duration_rounds: int, # Dauer in Runden, -1 für permanent bis entfernt
                 potency: float = 1.0, # Stärke des Effekts (z.B. Schadenshöhe, Stat-Modifikator)
                 is_positive: bool = False, # Ist der Effekt positiv (Buff) oder negativ (Debuff)?
                 application_chance: float = 1.0, # Nicht hier, sondern im Skill-Template
                 scales_with_attribute: Optional[str] = None, # Attribut des Anwenders für Skalierung der Potenz
                 attribute_potency_multiplier: float = 1.0):
        
        self.effect_id: str = effect_id # Eindeutige ID des Effekttyps (z.B. "BURNING", "STUNNED")
        self.name: str = name
        self.description: str = description
        self.target: 'CharacterInstance' = target
        self.source_actor: Optional['CharacterInstance'] = source_actor # Kann None sein, wenn z.B. Umgebungseffekt
        
        self.initial_duration: int = duration_rounds
        self.remaining_duration: int = duration_rounds # Runden verbleibend
        
        self.initial_potency: float = potency
        self.current_potency: float = potency # Potenz kann sich evtl. ändern
        
        self.is_positive: bool = is_positive
        self.is_dispellable: bool = True # Kann der Effekt entfernt werden?
        self.is_stackable: bool = False # Kann derselbe Effekt mehrfach auf dem Ziel aktiv sein? (Für Basis-Implementierung erstmal False)

        # Skalierung der Potenz basierend auf dem Anwender (source_actor)
        if scales_with_attribute and source_actor:
            attr_bonus = source_actor.get_attribute_bonus(scales_with_attribute)
            scaled_potency_bonus = attr_bonus * attribute_potency_multiplier
            self.current_potency += scaled_potency_bonus
            self.current_potency = max(0, self.current_potency) # Potenz nicht negativ durch Skalierung
            logger.debug(f"Effekt '{self.name}' Potenz von {potency} skaliert mit {scales_with_attribute} "
                         f"(Bonus {attr_bonus} * Mult {attribute_potency_multiplier} = {scaled_potency_bonus}) "
                         f"auf {self.current_potency} für Ziel '{target.name}'.")


    def on_apply(self) -> None:
        """Wird einmalig ausgeführt, wenn der Effekt auf das Ziel angewendet wird."""
        logger.info(f"Effekt '{self.name}' (Pot: {self.current_potency}, Dauer: {self.remaining_duration}R) "
                    f"wurde auf '{self.target.name}' angewendet.")
        # Spezifische Logik für das Anwenden (z.B. einmalige Stat-Änderung)
        pass

    def on_tick(self) -> None:
        """
        Wird zu Beginn jeder Runde des Ziels ausgeführt, solange der Effekt aktiv ist.
        (Oder am Ende der Runde, je nach Spieldesign-Entscheidung).
        Für unser Design (gemäß ANNEX): Am Anfang der Runde des betroffenen Charakters.
        """
        # logger.debug(f"Tick für Effekt '{self.name}' auf '{self.target.name}'. Verbleibende Dauer: {self.remaining_duration}")
        pass # Spezifische Logik pro Tick (z.B. Schaden über Zeit)

    def on_remove(self) -> None:
        """Wird einmalig ausgeführt, wenn der Effekt vom Ziel entfernt wird (abgelaufen oder dispellt)."""
        logger.info(f"Effekt '{self.name}' wurde von '{self.target.name}' entfernt.")
        # Spezifische Logik für das Entfernen (z.B. Wiederherstellen von Stats)
        pass

    def tick_duration(self) -> bool:
        """
        Reduziert die verbleibende Dauer um eins.
        Gibt True zurück, wenn der Effekt danach abgelaufen ist, sonst False.
        """
        if self.remaining_duration == -1: # Permanent
            return False
            
        if self.remaining_duration > 0:
            self.remaining_duration -= 1
            # logger.debug(f"Effekt '{self.name}' auf '{self.target.name}', Dauer reduziert auf {self.remaining_duration}R.")
        
        return self.remaining_duration == 0

    def refresh(self, new_duration: int, new_potency: float, 
                new_scales_with_attribute: Optional[str] = None, 
                new_attribute_potency_multiplier: float = 1.0) -> None:
        """
        Aktualisiert einen bereits existierenden Effekt (gemäß ANNEX).
        Dauer wird auf MAX(alte_dauer, neue_dauer) gesetzt.
        Stärke wird überschrieben.
        """
        self.remaining_duration = max(self.remaining_duration, new_duration)
        self.initial_duration = self.remaining_duration # Initial auch anpassen
        
        old_potency = self.current_potency
        self.initial_potency = new_potency # Basis-Potenz vor Skalierung neu setzen
        self.current_potency = new_potency

        if new_scales_with_attribute and self.source_actor: # Erneute Skalierung mit potenziell neuen Werten
            attr_bonus = self.source_actor.get_attribute_bonus(new_scales_with_attribute)
            scaled_potency_bonus = attr_bonus * new_attribute_potency_multiplier
            self.current_potency += scaled_potency_bonus
            self.current_potency = max(0, self.current_potency)
        
        logger.info(f"Effekt '{self.name}' auf '{self.target.name}' aufgefrischt. "
                    f"Neue Dauer: {self.remaining_duration}R, neue Potenz: {self.current_potency} (vorher {old_potency}).")


    def __str__(self) -> str:
        return f"{self.name} (Pot: {self.current_potency:.1f}, {self.remaining_duration}R left)"

# --- Konkrete Effekt-Implementierungen ---

class BurningEffect(StatusEffect):
    """Verursacht Schaden über Zeit (DoT)."""
    def __init__(self, target: 'CharacterInstance', source_actor: Optional['CharacterInstance'], duration_rounds: int, potency: float, **kwargs):
        # kwargs fängt zusätzliche Parameter wie scales_with_attribute ab
        super().__init__(effect_id="BURNING", name="Brennen", 
                         description=f"Verursacht {potency:.0f} Feuerschaden pro Runde.",
                         target=target, source_actor=source_actor, duration_rounds=duration_rounds, potency=potency, 
                         is_positive=False, **kwargs)

    def on_tick(self) -> None:
        super().on_tick()
        if self.target and not self.target.is_defeated:
            damage = int(self.current_potency) # Potenz ist hier der Schaden pro Tick
            logger.info(f"'{self.target.name}' erleidet {damage} Schaden durch '{self.name}'.")
            # Wichtig: Direkter Schaden, ignoriert Rüstung laut ANNEX
            self.target.current_hp -= damage # Direkte HP-Reduktion
            if self.target.current_hp <= 0:
                self.target.current_hp = 0
                self.target.is_defeated = True
                self.target.can_act = False
                logger.info(f"'{self.target.name}' wurde durch '{self.name}' besiegt!")
            # Hier kein take_damage() verwenden, um Rüstung/Schild-Interaktion zu umgehen, falls so gewollt.
            # ANNEX: "Direkter Schaden (ignoriert Rüstung): potency Punkte pro Runde"

class StunnedEffect(StatusEffect):
    """Verhindert Aktionen des Ziels."""
    def __init__(self, target: 'CharacterInstance', source_actor: Optional['CharacterInstance'], duration_rounds: int, **kwargs):
        # Potenz ist hier nicht direkt relevant für den Effekt selbst, aber Standardwert ist 1
        super().__init__(effect_id="STUNNED", name="Betäubt", 
                         description="Kann keine Aktionen ausführen.",
                         target=target, source_actor=source_actor, duration_rounds=duration_rounds, potency=1.0, 
                         is_positive=False, **kwargs)

    def on_apply(self) -> None:
        super().on_apply()
        if self.target:
            self.target.can_act = False
            logger.debug(f"'{self.target.name}' kann aufgrund von '{self.name}' nicht handeln.")

    def on_remove(self) -> None:
        super().on_remove()
        if self.target:
            # Prüfe, ob andere Stun-Effekte noch aktiv sind, bevor can_act wiederhergestellt wird.
            # Für diese einfache Implementierung gehen wir davon aus, dass es nur einen gibt oder der letzte entfernt wird.
            # Eine robustere Lösung würde alle Effekte prüfen.
            is_still_stunned = any(isinstance(eff, StunnedEffect) for eff in self.target.status_effects if eff is not self)
            if not is_still_stunned:
                self.target.can_act = True
                logger.debug(f"'{self.target.name}' kann wieder handeln, da '{self.name}' entfernt wurde.")
            else:
                logger.debug(f"'{self.target.name}' ist immer noch betäubt durch andere Effekte.")


class SlowedEffect(StatusEffect):
    """Reduziert Initiative und Ausweichen."""
    def __init__(self, target: 'CharacterInstance', source_actor: Optional['CharacterInstance'], duration_rounds: int, potency: float, **kwargs):
        # potency: z.B. 1 -> -5 Initiative, -1 Ausweichen
        super().__init__(effect_id="SLOWED", name="Verlangsamt",
                         description=f"Reduziert Initiative um {potency*5} und Ausweichen um {potency}.",
                         target=target, source_actor=source_actor, duration_rounds=duration_rounds, potency=potency,
                         is_positive=False, **kwargs)
        self.initiative_reduction = 0
        self.evasion_reduction = 0

    def on_apply(self) -> None:
        super().on_apply()
        if self.target:
            self.initiative_reduction = int(self.current_potency * 5) # Gemäß ANNEX: Initiative -5*potency
            self.evasion_reduction = int(self.current_potency)      # Gemäß ANNEX: Ausweichen -potency
            
            self.target.current_initiative -= self.initiative_reduction
            self.target.evasion -= self.evasion_reduction # Annahme: CharacterInstance hat 'evasion' Attribut
            logger.debug(f"'{self.target.name}' Initiative -{self.initiative_reduction}, Evasion -{self.evasion_reduction} durch '{self.name}'.")

    def on_remove(self) -> None:
        super().on_remove()
        if self.target:
            self.target.current_initiative += self.initiative_reduction
            self.target.evasion += self.evasion_reduction
            logger.debug(f"'{self.target.name}' Initiative +{self.initiative_reduction}, Evasion +{self.evasion_reduction} wiederhergestellt nach '{self.name}'.")


class ShieldedEffect(StatusEffect):
    """Absorbiert Schaden durch temporäre Schildpunkte."""
    def __init__(self, target: 'CharacterInstance', source_actor: Optional['CharacterInstance'], duration_rounds: int, potency: float, **kwargs):
        # potency: Höhe der Schildpunkte
        super().__init__(effect_id="SHIELDED", name="Geschützt",
                         description=f"Absorbiert bis zu {potency:.0f} Schaden.",
                         target=target, source_actor=source_actor, duration_rounds=duration_rounds, potency=potency,
                         is_positive=True, **kwargs)

    def on_apply(self) -> None:
        super().on_apply()
        if self.target:
            # ANNEX: "Der SHIELDED-Status-Effekt setzt die Schildpunkte auf den Stärkewert des Effekts"
            # Dies bedeutet, es ist kein Stapeln von Schild-Effekten, sondern ein Überschreiben/Auffrischen.
            # Die CharacterInstance.shield_points sollten hier direkt gesetzt/aktualisiert werden.
            # Wir nehmen an, dass mehrere SHIELDED Effekte nicht gleichzeitig aktiv sind oder
            # der stärkste gilt. Die Logik in CharacterInstance.take_damage() behandelt shield_points.
            # Dieser Effekt sorgt dafür, dass die shield_points gesetzt werden.
            # Wenn ein neuer SHIELDED Effekt angewendet wird, während ein alter noch läuft,
            # wird der alte typischerweise entfernt und der neue angewendet.
            self.target.shield_points = max(self.target.shield_points, int(self.current_potency)) # Nimm den höheren Schildwert
            logger.debug(f"'{self.target.name}' erhält Schildpunkte: {self.target.shield_points} durch '{self.name}'.")

    def on_remove(self) -> None:
        super().on_remove()
        if self.target:
            # Beim Entfernen des Effekts wird der Schild nicht automatisch auf 0 gesetzt,
            # sondern nur, wenn dieser spezifische Effekt der Grund für die aktuellen Schildpunkte war.
            # Da wir Schildpunkte als einen Pool sehen, der von verschiedenen Quellen kommen kann,
            # ist es komplexer. Fürs Erste: Wenn der Effekt abläuft, werden die von ihm gewährten Punkte entfernt,
            # aber nur, wenn sie noch da sind.
            # Einfacher Ansatz: Der Schild bleibt, bis er durch Schaden aufgebraucht ist oder ein anderer Effekt ihn ändert.
            # Der Effekt selbst "verfällt", aber die Schildpunkte bleiben.
            # ANNEX sagt nur "setzt die Schildpunkte". Es sagt nicht, was beim Ablauf passiert.
            # Logische Annahme: Der Schild bleibt, bis er weg ist oder der Effekt neu gesetzt wird.
            # Daher hier keine Aktion beim on_remove für shield_points.
            logger.debug(f"Effekt '{self.name}' auf '{self.target.name}' entfernt. Schildpunkte bleiben bis aufgebraucht.")
            pass


# --- Weitere Effekte gemäß ANNEX ---
class WeakenedEffect(StatusEffect):
    """Reduziert Stärke."""
    def __init__(self, target: 'CharacterInstance', source_actor: Optional['CharacterInstance'], duration_rounds: int, potency: float, **kwargs):
        super().__init__(effect_id="WEAKENED", name="Geschwächt (STR)",
                         description=f"Reduziert Stärke um {potency:.0f}.",
                         target=target, source_actor=source_actor, duration_rounds=duration_rounds, potency=potency,
                         is_positive=False, **kwargs)
        self.str_reduction = 0

    def on_apply(self) -> None:
        super().on_apply()
        if self.target:
            self.str_reduction = int(self.current_potency)
            self.target.attributes["STR"] = self.target.attributes.get("STR", 10) - self.str_reduction
            logger.debug(f"'{self.target.name}' STR -{self.str_reduction} durch '{self.name}'. Neu: {self.target.attributes['STR']}")

    def on_remove(self) -> None:
        super().on_remove()
        if self.target:
            self.target.attributes["STR"] = self.target.attributes.get("STR", 10) + self.str_reduction
            logger.debug(f"'{self.target.name}' STR +{self.str_reduction} wiederhergestellt nach '{self.name}'. Neu: {self.target.attributes['STR']}")

class AccuracyDownEffect(StatusEffect):
    """Reduziert Treffergenauigkeit."""
    def __init__(self, target: 'CharacterInstance', source_actor: Optional['CharacterInstance'], duration_rounds: int, potency: float, **kwargs):
        super().__init__(effect_id="ACCURACY_DOWN", name="Genauigkeit verringert",
                         description=f"Reduziert Genauigkeit um {potency:.0f}.",
                         target=target, source_actor=source_actor, duration_rounds=duration_rounds, potency=potency,
                         is_positive=False, **kwargs)
        self.accuracy_reduction = 0

    def on_apply(self) -> None:
        super().on_apply()
        if self.target:
            self.accuracy_reduction = int(self.current_potency)
            self.target.accuracy -= self.accuracy_reduction # Annahme: CharacterInstance.accuracy
            logger.debug(f"'{self.target.name}' Genauigkeit -{self.accuracy_reduction} durch '{self.name}'.")

    def on_remove(self) -> None:
        super().on_remove()
        if self.target:
            self.target.accuracy += self.accuracy_reduction
            logger.debug(f"'{self.target.name}' Genauigkeit +{self.accuracy_reduction} wiederhergestellt nach '{self.name}'.")


class InitiativeUpEffect(StatusEffect):
    """Erhöht Initiative."""
    def __init__(self, target: 'CharacterInstance', source_actor: Optional['CharacterInstance'], duration_rounds: int, potency: float, **kwargs):
        super().__init__(effect_id="INITIATIVE_UP", name="Initiative erhöht",
                         description=f"Erhöht Initiative um {potency:.0f}.",
                         target=target, source_actor=source_actor, duration_rounds=duration_rounds, potency=potency,
                         is_positive=True, **kwargs)
        self.initiative_increase = 0

    def on_apply(self) -> None:
        super().on_apply()
        if self.target:
            self.initiative_increase = int(self.current_potency)
            self.target.current_initiative += self.initiative_increase
            logger.debug(f"'{self.target.name}' Initiative +{self.initiative_increase} durch '{self.name}'.")

    def on_remove(self) -> None:
        super().on_remove()
        if self.target:
            self.target.current_initiative -= self.initiative_increase
            logger.debug(f"'{self.target.name}' Initiative -{self.initiative_increase} (normalisiert) nach '{self.name}'.")


class DefenseUpEffect(StatusEffect):
    """Erhöht Rüstung und Magieresistenz."""
    def __init__(self, target: 'CharacterInstance', source_actor: Optional['CharacterInstance'], duration_rounds: int, potency: float, **kwargs):
        super().__init__(effect_id="DEFENSE_UP", name="Verteidigung erhöht",
                         description=f"Erhöht Rüstung & MagRes um {potency:.0f}.",
                         target=target, source_actor=source_actor, duration_rounds=duration_rounds, potency=potency,
                         is_positive=True, **kwargs)
        self.defense_increase = 0
    
    def on_apply(self) -> None:
        super().on_apply()
        if self.target:
            self.defense_increase = int(self.current_potency)
            self.target.armor += self.defense_increase
            self.target.magic_resist += self.defense_increase
            logger.debug(f"'{self.target.name}' Rüstung & MagRes +{self.defense_increase} durch '{self.name}'.")

    def on_remove(self) -> None:
        super().on_remove()
        if self.target:
            self.target.armor -= self.defense_increase
            self.target.magic_resist -= self.defense_increase
            logger.debug(f"'{self.target.name}' Rüstung & MagRes -{self.defense_increase} (normalisiert) nach '{self.name}'.")


# --- Registrierung der Effektklassen ---
# Ermöglicht das Erstellen von Effektinstanzen anhand ihrer ID.
EFFECT_CLASS_MAP: Dict[str, Callable[..., StatusEffect]] = {
    "BURNING": BurningEffect,
    "STUNNED": StunnedEffect,
    "SLOWED": SlowedEffect,
    "SHIELDED": ShieldedEffect,
    "WEAKENED": WeakenedEffect, // Effekt für STR -potency
    "ACCURACY_DOWN": AccuracyDownEffect, // Effekt für Genauigkeit -potency
    "INITIATIVE_UP": InitiativeUpEffect, // Effekt für Initiative +potency
    "DEFENSE_UP": DefenseUpEffect, // Effekt für Rüstung +potency, Magieresistenz +potency
    # Weitere Effekte hier registrieren
}

def create_status_effect(effect_id: str, 
                         target: 'CharacterInstance', 
                         source_actor: Optional['CharacterInstance'], 
                         duration_rounds: int, 
                         potency: float,
                         scales_with_attribute: Optional[str] = None,
                         attribute_potency_multiplier: float = 1.0
                         ) -> Optional[StatusEffect]:
    """
    Factory-Funktion zum Erstellen von StatusEffekt-Instanzen.
    """
    effect_class = EFFECT_CLASS_MAP.get(effect_id.upper())
    if effect_class:
        try:
            return effect_class(target=target, 
                                source_actor=source_actor, 
                                duration_rounds=duration_rounds, 
                                potency=potency,
                                scales_with_attribute=scales_with_attribute,
                                attribute_potency_multiplier=attribute_potency_multiplier)
        except Exception as e:
            logger.error(f"Fehler beim Erstellen der Effektinstanz für ID '{effect_id}': {e}")
            return None
    else:
        logger.warning(f"Keine Effektklasse für ID '{effect_id}' in EFFECT_CLASS_MAP gefunden.")
        return None


if __name__ == '__main__':
    # Testen der Status-Effekte
    # Benötigt eine dummy CharacterInstance und ggf. Templates für Tests
    
    # Minimales Setup für CharacterInstance, um Fehler zu vermeiden
    class DummyTemplate:
        id = "dummy"
        name = "Dummy Template"
        primary_attributes = {"STR": 10, "DEX": 10, "CON": 10, "INT": 10, "WIS": 10}
        base_hp = 100
        combat_values = {"base_mana": 50, "base_stamina": 50, "base_energy": 50, "armor": 5, "magic_resist": 5, "initiative_bonus":0}
        skills = []
        level = 1

    # Importiere CharacterInstance erst hier, um zirkuläre Abhängigkeiten auf Modulebene zu vermeiden,
    # falls CharacterInstance direkt StatusEffect importieren würde.
    from src.game_logic.entities import CharacterInstance

    print("\n--- Teste Status-Effekte ---")
    
    # Erstelle eine Test-Charakterinstanz
    source = CharacterInstance(base_template=DummyTemplate(), name_override="SourceChar")
    source.attributes["INT"] = 16 # Für Skalierungstests (Bonus +3)

    player = CharacterInstance(base_template=DummyTemplate(), name_override="TestPlayer")
    print(f"Initial: {player.name} HP: {player.current_hp}, Initiative: {player.current_initiative}, STR: {player.attributes['STR']}")

    # Test BurningEffect
    print("\n-- Teste Burning --")
    burning_effect = create_status_effect("BURNING", player, source, duration_rounds=3, potency=5, scales_with_attribute="INT", attribute_potency_multiplier=0.5)
    if burning_effect:
        player.status_effects.append(burning_effect)
        burning_effect.on_apply() # Manuell für Test aufrufen
        print(burning_effect) # Erwartete Potenz: 5 + (3 * 0.5) = 6.5
        
        for i in range(4):
            print(f"Runde {i+1} Tick:")
            if burning_effect.tick_duration(): # Reduziert Dauer und prüft ob abgelaufen
                burning_effect.on_remove()
                player.status_effects.remove(burning_effect)
                print(f"Burning-Effekt entfernt.")
                break # Effekt ist vorbei
            burning_effect.on_tick()
            print(f"{player.name} HP: {player.current_hp}")
    
    # Test StunnedEffect
    print("\n-- Teste Stunned --")
    player.can_act = True # Reset
    stun_effect = create_status_effect("STUNNED", player, source, duration_rounds=1, potency=1)
    if stun_effect:
        player.status_effects.append(stun_effect)
        stun_effect.on_apply()
        print(f"{player.name} kann handeln: {player.can_act}") # Erwartet: False
        stun_effect.tick_duration()
        stun_effect.on_remove()
        player.status_effects.remove(stun_effect)
        print(f"{player.name} kann handeln nach Stun: {player.can_act}") # Erwartet: True

    # Test SlowedEffect
    print("\n-- Teste Slowed --")
    initial_initiative = player.current_initiative
    initial_evasion = player.evasion
    slow_effect = create_status_effect("SLOWED", player, source, duration_rounds=2, potency=2) # potency 2 -> Ini -10, Eva -2
    if slow_effect:
        player.status_effects.append(slow_effect)
        slow_effect.on_apply()
        print(f"{player.name} Initiative: {player.current_initiative} (vorher {initial_initiative}), Evasion: {player.evasion} (vorher {initial_evasion})")
        slow_effect.tick_duration()
        slow_effect.tick_duration()
        slow_effect.on_remove()
        player.status_effects.remove(slow_effect)
        print(f"{player.name} Initiative nach Slow: {player.current_initiative}, Evasion: {player.evasion}")

    # Test ShieldedEffect
    print("\n-- Teste Shielded --")
    player.shield_points = 0 # Reset
    shield_effect = create_status_effect("SHIELDED", player, source, duration_rounds=3, potency=20, scales_with_attribute="INT", attribute_potency_multiplier=2)
    if shield_effect: # Erwartete Potenz: 20 + (3 * 2) = 26
        player.status_effects.append(shield_effect)
        shield_effect.on_apply()
        print(f"{player.name} Schildpunkte: {player.shield_points}")
        # Schaden nehmen
        player.take_damage(15, "PHYSICAL")
        print(f"{player.name} Schildpunkte nach 15 Schaden: {player.shield_points}, HP: {player.current_hp}")
        player.take_damage(15, "PHYSICAL")
        print(f"{player.name} Schildpunkte nach weiteren 15 Schaden: {player.shield_points}, HP: {player.current_hp}")
        shield_effect.tick_duration(); shield_effect.tick_duration(); shield_effect.tick_duration()
        shield_effect.on_remove() # Schild sollte noch da sein, bis er auf 0 ist
        player.status_effects.remove(shield_effect)
        print(f"{player.name} Schildpunkte nach Effektende: {player.shield_points}")

    # Test Refresh
    print("\n-- Teste Refresh von Effekt --")
    # player.current_hp = player.max_hp # Reset HP
    burn_refresh = create_status_effect("BURNING", player, source, duration_rounds=1, potency=2)
    if burn_refresh:
        burn_refresh.on_apply()
        print(f"Initialer Burn: {burn_refresh}")
        burn_refresh.refresh(new_duration=3, new_potency=4)
        print(f"Refreshed Burn: {burn_refresh}")
        # Ticken lassen...
        burn_refresh.on_remove()

    print("\n--- Effekt-Tests abgeschlossen ---")