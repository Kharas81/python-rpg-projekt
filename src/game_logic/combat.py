import random
import sys
from typing import List, Optional, Union, Tuple

# Zugriff auf Charakter/Enemy-Klassen und Definitionen
try:
    from .character import Character
    from .enemy import Enemy
    from definitions import loader
    from definitions.models import SkillDefinition, SkillEffectDefinition
except ImportError:
    try:
        from src.game_logic.character import Character
        from src.game_logic.enemy import Enemy
        from src.definitions import loader
        from src.definitions.models import SkillDefinition, SkillEffectDefinition
    except ImportError:
        print("FEHLER: Konnte game_logic/definitions-Module in combat.py nicht importieren.", file=sys.stderr)
        sys.exit(1)

# Typ-Alias für Kämpfer
Combatant = Union[Character, Enemy]

# Konstanten für Trefferchance-Berechnung (später evtl. in config auslagern)
BASE_HIT_CHANCE = 90
HIT_CHANCE_ACCURACY_FACTOR = 3
HIT_CHANCE_EVASION_FACTOR = 2
MIN_HIT_CHANCE = 5
MAX_HIT_CHANCE = 95

class CombatEncounter:
    """
    Verwaltet einen einzelnen Kampf zwischen dem Spieler und einem oder mehreren Gegnern.
    """
    def __init__(self, player: Character, enemies: List[Enemy]):
        self.player: Character = player
        self.enemies: List[Enemy] = [e for e in enemies if e.is_alive()] # Nur lebende Gegner hinzufügen
        if not self.enemies:
            raise ValueError("Kampf kann nicht ohne Gegner gestartet werden.")

        self.combatants: List[Combatant] = [self.player] + self.enemies
        self.turn_order: List[Combatant] = []
        self.current_turn_index: int = 0
        self.round_number: int = 0
        self.status: str = "PENDING" # PENDING, ONGOING, PLAYER_VICTORY, PLAYER_DEFEAT

        self._calculate_turn_order()

    def _calculate_turn_order(self):
        """Bestimmt die Zugreihenfolge basierend auf Initiative."""
        # Sortiere Kämpfer nach Initiative absteigend. Bei Gleichstand ist die Reihenfolge stabil (wie in self.combatants).
        self.turn_order = sorted(
            self.combatants,
            key=lambda c: c.get_combat_stat("INITIATIVE") or 0,
            reverse=True
        )
        self.current_turn_index = 0
        print("\nZugreihenfolge:")
        for i, combatant in enumerate(self.turn_order):
            print(f"  {i+1}. {combatant.name} (Initiative: {combatant.get_combat_stat('INITIATIVE') or 0})")

    def start_combat(self):
        """Startet den Kampf."""
        if self.status == "PENDING":
            print(f"\n--- Kampf beginnt! {self.player.name} vs {', '.join([e.name for e in self.enemies])} ---")
            self.status = "ONGOING"
            self.round_number = 1
            # Optional: Erste Runde direkt starten? Oder nur vorbereiten?
            # self.next_turn() # Um den ersten Kämpfer zu bestimmen

    def get_current_combatant(self) -> Optional[Combatant]:
        """Gibt den Kämpfer zurück, der aktuell am Zug ist."""
        if not self.turn_order or self.current_turn_index >= len(self.turn_order):
            return None
        return self.turn_order[self.current_turn_index]

    def next_turn(self) -> Optional[Combatant]:
        """Wechselt zum nächsten Kämpfer in der Zugreihenfolge."""
        if self.status != "ONGOING":
            return None

        # Finde den nächsten lebenden Kämpfer in der Reihenfolge
        next_index = (self.current_turn_index + 1) % len(self.turn_order)

        # Prüfe, ob eine neue Runde beginnt
        if next_index < self.current_turn_index: # Überlauf -> neue Runde
             self.round_number += 1
             print(f"\n--- Runde {self.round_number} ---")
             # TODO: Hier könnten Rundeneffekte angewendet werden (z.B. DoTs aktualisieren)
             # for combatant in self.combatants: combatant.update_effects()

        self.current_turn_index = next_index

        current_combatant = self.get_current_combatant()

        # Überspringe besiegte Kämpfer
        while current_combatant and not current_combatant.is_alive():
            # print(f"{current_combatant.name} ist besiegt und wird übersprungen.")
            next_index = (self.current_turn_index + 1) % len(self.turn_order)
            if next_index < self.current_turn_index: # Überlauf beim Überspringen
                self.round_number += 1
                print(f"\n--- Runde {self.round_number} ---")
            self.current_turn_index = next_index
            current_combatant = self.get_current_combatant()
            # Sicherheitscheck, um Endlosschleife zu vermeiden, wenn alle tot sind
            if all(not c.is_alive() for c in self.turn_order):
                 print("WARNUNG: Alle Kämpfer sind besiegt, nächster Zug nicht möglich.")
                 return None


        if current_combatant:
             print(f"\n{current_combatant.name} ist am Zug.")
        return current_combatant


    def is_combat_over(self) -> bool:
        """Prüft, ob der Kampf beendet ist und aktualisiert den Status."""
        if self.status != "ONGOING":
            return True # Kampf war schon vorbei oder noch nicht gestartet

        if not self.player.is_alive():
            self.status = "PLAYER_DEFEAT"
            print(f"\n--- {self.player.name} wurde besiegt! Kampf verloren! ---")
            return True

        living_enemies = [e for e in self.enemies if e.is_alive()]
        if not living_enemies:
            self.status = "PLAYER_VICTORY"
            print(f"\n--- Alle Gegner besiegt! Kampf gewonnen! ---")
            # TODO: Belohnungen geben (XP, Loot etc.)
            # xp_reward = sum(e.get_xp_reward() for e in self.enemies)
            # self.player.add_xp(xp_reward)
            return True

        return False

    def get_living_enemies(self) -> List[Enemy]:
        """Gibt eine Liste der noch lebenden Gegner zurück."""
        return [e for e in self.enemies if e.is_alive()]

    def display_combat_status(self):
        """Zeigt den Status aller lebenden Kämpfer an."""
        print("\n--- Kampfstatus ---")
        self.player.display_status() # Ausführlicher Status für Spieler
        print("-" * 20)
        for enemy in self.get_living_enemies():
            enemy.display_short_status() # Kurzer Status für Gegner
        print("-" * 20)


    def _calculate_hit_chance(self, attacker: Combatant, target: Combatant) -> int:
        """Berechnet die Trefferchance in Prozent."""
        attacker_acc_mod = attacker.get_combat_stat("ACCURACY_MODIFIER") or 0
        target_eva_mod = target.get_combat_stat("EVASION_MODIFIER") or 0

        chance = (BASE_HIT_CHANCE +
                  (attacker_acc_mod * HIT_CHANCE_ACCURACY_FACTOR) -
                  (target_eva_mod * HIT_CHANCE_EVASION_FACTOR))

        # Clamp chance between min and max
        chance = max(MIN_HIT_CHANCE, min(MAX_HIT_CHANCE, chance))
        return int(chance)

    def apply_skill(self, attacker: Combatant, target: Combatant, skill: SkillDefinition) -> bool:
        """
        Versucht, einen Skill anzuwenden. Prüft Kosten, Trefferchance und wendet Effekte an.
        Gibt True zurück, wenn der Skill erfolgreich angewendet wurde (oder keine Aktion erforderte),
        False, wenn Kosten nicht gedeckt oder Angriff verfehlt hat.
        """
        if not attacker.is_alive() or not target.is_alive():
            print("Fehler: Angreifer oder Ziel ist nicht am Leben.")
            return False

        print(f"{attacker.name} setzt '{skill.name}' gegen {target.name} ein.")

        # 1. Kosten prüfen und abziehen
        if not attacker.consume_resource(skill.cost.resource, skill.cost.amount):
            # Fehlermeldung kommt von consume_resource
            return False # Skill konnte wegen Kosten nicht eingesetzt werden

        # 2. Trefferchance prüfen (nur für Fähigkeiten, die ein Ziel haben und Schaden/Debuffs verursachen?)
        # Annahme: Skills wie Heilung oder Buffs treffen automatisch?
        # Fürs Erste: Prüfen wir die Trefferchance für alle Skills, die nicht auf SELF zielen.
        needs_hit_check = skill.target_type != "SELF" # Einfache Annahme
        hit_chance = 100 # Standard für Selbst-Buffs/Heilungen
        if needs_hit_check:
            hit_chance = self._calculate_hit_chance(attacker, target)
            roll = random.randint(1, 100)
            print(f"  (Trefferchance: {hit_chance}%, Wurf: {roll})")
            if roll > hit_chance:
                print(f"  >> {skill.name} verfehlt!")
                return False # Angriff verfehlt

        # 3. Effekte anwenden
        print(f"  >> {skill.name} trifft!")
        for effect in skill.effects:
            self._apply_effect(attacker, target, effect, skill)

        return True # Skill wurde erfolgreich angewendet


    def _apply_effect(self, attacker: Combatant, target: Combatant, effect: SkillEffectDefinition, skill: SkillDefinition):
        """Wendet einen einzelnen Effekt eines Skills an."""
        # TODO: Diese Logik verfeinern und ggf. in die Charakter/Enemy Klassen verschieben?

        if effect.type == "DAMAGE":
            # Schaden berechnen
            # TODO: Basis-Waffenschaden des Angreifers holen, falls base_value == "WEAPON"
            base_dmg = 0
            if isinstance(effect.base_value, int):
                base_dmg = effect.base_value
            elif effect.base_value == "WEAPON":
                 # Hier bräuchten wir den Waffenschaden des Angreifers
                 # Nehmen wir vorerst einen Standardwert an
                 base_dmg = 5 # PLATZHALTER!
                 print("  (WARNUNG: Waffenschaden ist noch nicht implementiert, nehme 5 an)")

            scaling_bonus = 0
            if effect.scaling_attribute:
                attr_value = attacker.get_attribute(effect.scaling_attribute)
                scaling_bonus = (attr_value - 10) // 2

            total_damage = (base_dmg + scaling_bonus) * (effect.multiplier or 1.0)

            # TODO: Bonus vs Type berücksichtigen (effect.bonus_vs_type)
            # TODO: Ignorierte Rüstung berücksichtigen (effect.ignores_armor_percentage) - komplexer!

            # Schaden auf Ziel anwenden
            damage_type = effect.damage_type or "UNKNOWN"
            target.apply_damage(int(round(total_damage)), damage_type)

        elif effect.type == "HEAL":
             base_heal = effect.base_value or 0
             scaling_heal = 0
             if effect.scaling_attribute and effect.scaling_factor:
                  attr_value = attacker.get_attribute(effect.scaling_attribute)
                  scaling_heal = attr_value * effect.scaling_factor

             total_heal = base_heal + scaling_heal
             target.apply_heal(int(round(total_heal)))

        elif effect.type == "APPLY_STATUS":
             # TODO: Statuseffekt-Logik implementieren
             print(f"  > Effekt '{effect.status_effect}' auf {target.name} angewendet (Dauer: {effect.duration}, Stärke: {effect.magnitude}). (Logik fehlt noch!)")
             # target.add_effect(StatusEffect(effect.status_effect, effect.duration, effect.magnitude))

        elif effect.type == "ABSORB_SHIELD":
              # TODO: Schild-Logik implementieren
              print(f"  > Effekt 'ABSORB_SHIELD' auf {target.name} angewendet. (Logik fehlt noch!)")

        # TODO: AREA_DAMAGE Effekt behandeln (in apply_skill direkt?)

        else:
            print(f"  WARNUNG: Unbekannter Effekt-Typ '{effect.type}'")

