"""
Kampfsystem

Enthält Klassen und Funktionen für die Abwicklung von Kampfaktionen.
"""
import random
from typing import Dict, List, Any, Optional, Tuple, Union, Set

from src.definitions.skill import SkillDefinition
from src.game_logic.entities import CharacterInstance
from src.game_logic.formulas import calculate_damage, calculate_hit_chance, calculate_damage_reduction
from src.utils.logging_setup import get_logger


# Logger für dieses Modul
logger = get_logger(__name__)


class CombatAction:
    """
    Repräsentiert eine Kampfaktion (z.B. einen Angriff oder eine Fertigkeit).
    """
    def __init__(self, 
                 actor: CharacterInstance, 
                 skill: SkillDefinition,
                 primary_target: Optional[CharacterInstance] = None,
                 secondary_targets: Optional[List[CharacterInstance]] = None):
        """
        Initialisiert eine Kampfaktion.
        
        Args:
            actor (CharacterInstance): Der Ausführende der Aktion
            skill (SkillDefinition): Der verwendete Skill
            primary_target (Optional[CharacterInstance]): Das Hauptziel
            secondary_targets (Optional[List[CharacterInstance]]): Sekundäre Ziele (für Flächeneffekte)
        """
        self.actor = actor
        self.skill = skill
        self.primary_target = primary_target
        self.secondary_targets = secondary_targets or []
    
    def is_valid(self) -> bool:
        """
        Prüft, ob die Aktion gültig ist.
        
        Returns:
            bool: True, wenn die Aktion gültig ist, sonst False
        """
        # Prüfen, ob der Akteur handeln kann
        if not self.actor.can_act():
            logger.debug(f"{self.actor.name} kann nicht handeln")
            return False
        
        # Prüfen, ob der Akteur genug Ressourcen hat
        if not self.actor.has_enough_resource(self.skill):
            logger.debug(f"{self.actor.name} hat nicht genug Ressourcen für {self.skill.name}")
            return False
        
        # Prüfen, ob das Hauptziel gültig ist (falls erforderlich)
        if not self.skill.is_self_effect() and self.primary_target is None:
            logger.debug(f"Kein Ziel für Nicht-Selbsteffekt {self.skill.name}")
            return False
        
        # Prüfen, ob das Hauptziel als Ziel ausgewählt werden kann
        if self.primary_target and not self.primary_target.can_be_targeted():
            logger.debug(f"{self.primary_target.name} kann nicht als Ziel ausgewählt werden")
            return False
        
        return True


class CombatResult:
    """
    Enthält die Ergebnisse einer Kampfaktion.
    """
    def __init__(self):
        """Initialisiert ein leeres Ergebnis."""
        self.hits: List[CharacterInstance] = []
        self.misses: List[CharacterInstance] = []
        self.damage_dealt: Dict[CharacterInstance, int] = {}
        self.healing_done: Dict[CharacterInstance, int] = {}
        self.effects_applied: Dict[CharacterInstance, List[str]] = {}
        self.deaths: List[CharacterInstance] = []
        self.resources_spent: Dict[str, int] = {}


class CombatSystem:
    """
    Verwaltet die Kampflogik und -aktionen.
    """
    def __init__(self):
        """Initialisiert das Kampfsystem."""
        pass
    
    def execute_action(self, action: CombatAction) -> CombatResult:
        """
        Führt eine Kampfaktion aus.
        
        Args:
            action (CombatAction): Die auszuführende Aktion
            
        Returns:
            CombatResult: Das Ergebnis der Aktion
        """
        result = CombatResult()
        
        # Prüfen, ob die Aktion gültig ist
        if not action.is_valid():
            logger.warning(f"Ungültige Kampfaktion: {action.skill.name} von {action.actor.name}")
            return result
        
        # Ressourcen verbrauchen
        cost_value = action.skill.get_cost_value()
        cost_type = action.skill.get_cost_type()
        
        success = action.actor.spend_resource(action.skill)
        if not success:
            logger.warning(f"{action.actor.name} konnte die Ressourcen für {action.skill.name} nicht aufbringen")
            return result
        
        result.resources_spent[cost_type] = cost_value
        
        # Selbst-Effekt prüfen
        if action.skill.is_self_effect():
            self._apply_self_effect(action, result)
        else:
            # Für Angriffe oder Zauber auf andere
            self._apply_combat_effect(action, result)
        
        return result
    
    def _apply_self_effect(self, action: CombatAction, result: CombatResult) -> None:
        """
        Wendet einen Selbst-Effekt an.
        
        Args:
            action (CombatAction): Die Kampfaktion
            result (CombatResult): Das zu aktualisierende Ergebnis
        """
        # Status-Effekte auf den Akteur anwenden
        applied_effects = []
        for effect in action.skill.applies_effects:
            action.actor.apply_status_effect(effect.id, effect.duration, effect.potency)
            applied_effects.append(effect.id)
        
        if applied_effects:
            result.effects_applied[action.actor] = applied_effects
            logger.debug(f"{action.actor.name} wendet Selbsteffekt(e) an: {', '.join(applied_effects)}")
        
        # Heilung prüfen
        if 'base_healing' in action.skill.effects:
            base_healing = action.skill.effects['base_healing']
            scaling_attr = action.skill.effects.get('scaling_attribute', 'WIS')
            multiplier = action.skill.effects.get('healing_multiplier', 1.0)
            
            attr_value = action.actor.get_attribute(scaling_attr)
            healing = calculate_damage(base_healing, attr_value, multiplier)  # Wir verwenden die Schadensformel für Heilung
            
            actual_healing = action.actor.heal(healing)
            result.healing_done[action.actor] = actual_healing
            logger.info(f"{action.actor.name} heilt sich selbst um {actual_healing} HP")
    
    def _apply_combat_effect(self, action: CombatAction, result: CombatResult) -> None:
        """
        Wendet einen Kampfeffekt (Schaden, Status) auf ein Ziel an.
        
        Args:
            action (CombatAction): Die Kampfaktion
            result (CombatResult): Das zu aktualisierende Ergebnis
        """
        # Ziele festlegen
        targets = [action.primary_target]
        
        # Bei Flächeneffekten die sekundären Ziele hinzufügen
        if action.skill.is_area_effect() and action.secondary_targets:
            targets.extend(action.secondary_targets)
        
        # Für jedes Ziel die Effekte anwenden
        for target in targets:
            if not target.can_be_targeted():
                continue
            
            # Heilung prüfen
            if 'base_healing' in action.skill.effects:
                self._apply_healing(action, target, result)
                continue
            
            # Trefferchance berechnen
            hit_chance = calculate_hit_chance(action.actor.get_accuracy(), target.get_evasion())
            roll = random.randint(1, 100)
            
            if roll <= hit_chance:
                # Treffer!
                result.hits.append(target)
                
                # Schaden berechnen und anwenden
                if 'base_damage' in action.skill.effects or action.skill.get_base_damage() is not None:
                    self._apply_damage(action, target, result)
                
                # Status-Effekte anwenden
                if action.skill.applies_effects:
                    applied_effects = []
                    for effect in action.skill.applies_effects:
                        target.apply_status_effect(effect.id, effect.duration, effect.potency)
                        applied_effects.append(effect.id)
                    
                    if applied_effects:
                        if target not in result.effects_applied:
                            result.effects_applied[target] = []
                        result.effects_applied[target].extend(applied_effects)
            else:
                # Verfehlt!
                result.misses.append(target)
                logger.debug(f"{action.actor.name} verfehlt {target.name} mit {action.skill.name} (Wurf: {roll}, benötigt: {hit_chance})")
    
    def _apply_damage(self, action: CombatAction, target: CharacterInstance, result: CombatResult) -> None:
        """
        Wendet Schaden auf ein Ziel an.
        
        Args:
            action (CombatAction): Die Kampfaktion
            target (CharacterInstance): Das Ziel
            result (CombatResult): Das zu aktualisierende Ergebnis
        """
        # Schadensberechnung
        base_damage = action.skill.get_base_damage()
        scaling_attr = action.skill.get_scaling_attribute()
        multiplier = action.skill.get_multiplier()
        damage_type = action.skill.get_damage_type()
        
        # Bonus gegen bestimmte Gegnertypen
        bonus_type = action.skill.effects.get('bonus_vs_type', None)
        if bonus_type and target.has_tag(bonus_type):
            bonus_multiplier = action.skill.effects.get('bonus_multiplier', 1.0)
            multiplier *= bonus_multiplier
            logger.debug(f"{action.skill.name} erhält Bonus-Multiplikator {bonus_multiplier} gegen {target.name} (Tag: {bonus_type})")
        
        # Attributwert des Akteurs für Skalierung
        attr_value = action.actor.get_attribute(scaling_attr)
        
        # Rohschaden berechnen
        raw_damage = calculate_damage(base_damage, attr_value, multiplier)
        
        # Schaden anwenden (mit Verteidigungsreduzierung)
        actual_damage, is_dead = target.take_damage(raw_damage, damage_type)
        
        # Ergebnis aktualisieren
        result.damage_dealt[target] = actual_damage
        
        if is_dead:
            result.deaths.append(target)
            logger.info(f"{action.actor.name} besiegt {target.name} mit {action.skill.name} ({actual_damage} Schaden)")
        else:
            logger.debug(f"{action.actor.name} fügt {target.name} {actual_damage} Schaden zu mit {action.skill.name}")
    
    def _apply_healing(self, action: CombatAction, target: CharacterInstance, result: CombatResult) -> None:
        """
        Wendet Heilung auf ein Ziel an.
        
        Args:
            action (CombatAction): Die Kampfaktion
            target (CharacterInstance): Das Ziel
            result (CombatResult): Das zu aktualisierende Ergebnis
        """
        # Heilungsberechnung
        base_healing = action.skill.effects['base_healing']
        scaling_attr = action.skill.effects.get('scaling_attribute', 'WIS')
        multiplier = action.skill.effects.get('healing_multiplier', 1.0)
        
        # Attributwert des Akteurs für Skalierung
        attr_value = action.actor.get_attribute(scaling_attr)
        
        # Heilung berechnen
        healing_amount = calculate_damage(base_healing, attr_value, multiplier)  # Wir verwenden die Schadensformel für Heilung
        
        # Heilung anwenden
        actual_healing = target.heal(healing_amount)
        
        # Ergebnis aktualisieren
        result.healing_done[target] = actual_healing
        logger.info(f"{action.actor.name} heilt {target.name} um {actual_healing} HP mit {action.skill.name}")


# Globales Kampfsystem
combat_system = CombatSystem()


def get_combat_system() -> CombatSystem:
    """
    Gibt die globale Instanz des Kampfsystems zurück.
    
    Returns:
        CombatSystem: Die globale Instanz
    """
    return combat_system


class CombatEncounter:
    """
    Repräsentiert einen Kampf zwischen Gruppen von Charakteren (Spieler und Gegner).
    """
    def __init__(self, players: List[CharacterInstance], opponents: List[CharacterInstance]):
        """
        Initialisiert einen Kampf.
        
        Args:
            players (List[CharacterInstance]): Die Spielercharaktere
            opponents (List[CharacterInstance]): Die Gegner
        """
        self.players = players
        self.opponents = opponents
        self.round = 0
        self.combat_system = get_combat_system()
        self.turn_order: List[CharacterInstance] = []
        self.is_active = False
        self.winner = None  # 'players' oder 'opponents' oder None
        
        # Regenerationsraten (Prozentsatz der Maximalressource pro Runde)
        self.resource_regen_rates = {
            'MANA': 0.05,     # 5% pro Runde
            'STAMINA': 0.05,  # 5% pro Runde
            'ENERGY': 0.05    # 5% pro Runde
        }
        
        # Minimale Regeneration (Absolutwert pro Runde)
        self.min_resource_regen = {
            'MANA': 2,
            'STAMINA': 2,
            'ENERGY': 2
        }
    
    def start_combat(self) -> None:
        """Startet den Kampf und initialisiert die erste Runde."""
        logger.info("Kampf beginnt!")
        
        # Status zurücksetzen
        self.round = 0
        self.is_active = True
        self.winner = None
        
        # Kampfteilnehmer loggen
        logger.info(f"Spieler: {', '.join(p.name for p in self.players)}")
        logger.info(f"Gegner: {', '.join(o.name for o in self.opponents)}")
        
        # Erste Runde starten
        self.next_round()
    
    def next_round(self) -> None:
        """Startet die nächste Kampfrunde."""
        self.round += 1
        logger.info(f"Runde {self.round} beginnt!")
        
        # Zugreihenfolge berechnen
        self.calculate_turn_order()
        
        # Status-Effekte für alle Charaktere verarbeiten
        all_characters = self.players + self.opponents
        for character in all_characters:
            if character.is_alive():
                # Status-Effekte verarbeiten
                character.process_status_effects()
                
                # Ressourcen regenerieren
                self._regenerate_resources(character)
    
    def _regenerate_resources(self, character: CharacterInstance) -> None:
        """
        Regeneriert Ressourcen für einen Charakter basierend auf der Regenerationsrate.
        
        Args:
            character (CharacterInstance): Der Charakter, dessen Ressourcen regeneriert werden sollen
        """
        # Mana regenerieren
        if character.mana < character.base_combat_values.get('base_mana', 0):
            max_mana = character.base_combat_values.get('base_mana', 0)
            if max_mana > 0:
                regen_amount = max(
                    self.min_resource_regen['MANA'],
                    int(max_mana * self.resource_regen_rates['MANA'])
                )
                character.restore_resource('MANA', regen_amount)
                logger.debug(f"{character.name} regeneriert {regen_amount} Mana")
        
        # Stamina regenerieren
        if character.stamina < character.base_combat_values.get('base_stamina', 0):
            max_stamina = character.base_combat_values.get('base_stamina', 0)
            if max_stamina > 0:
                regen_amount = max(
                    self.min_resource_regen['STAMINA'],
                    int(max_stamina * self.resource_regen_rates['STAMINA'])
                )
                character.restore_resource('STAMINA', regen_amount)
                logger.debug(f"{character.name} regeneriert {regen_amount} Stamina")
        
        # Energy regenerieren
        if character.energy < character.base_combat_values.get('base_energy', 0):
            max_energy = character.base_combat_values.get('base_energy', 0)
            if max_energy > 0:
                regen_amount = max(
                    self.min_resource_regen['ENERGY'],
                    int(max_energy * self.resource_regen_rates['ENERGY'])
                )
                character.restore_resource('ENERGY', regen_amount)
                logger.debug(f"{character.name} regeneriert {regen_amount} Energy")
    
    def calculate_turn_order(self) -> None:
        """Berechnet die Zugreihenfolge basierend auf Initiative."""
        # Alle lebenden Charaktere sammeln
        all_alive = []
        for character in self.players + self.opponents:
            if character.is_alive():
                all_alive.append((character, character.get_initiative()))
        
        # Nach Initiative sortieren (höchste zuerst)
        all_alive.sort(key=lambda x: x[1], reverse=True)
        
        # Zugreihenfolge setzen
        self.turn_order = [char for char, _ in all_alive]
        
        initiative_log = ", ".join(f"{char.name} ({init})" for char, init in all_alive)
        logger.debug(f"Zugreihenfolge: {initiative_log}")
    
    def check_combat_end(self) -> bool:
        """
        Prüft, ob der Kampf beendet ist (eine Seite ist vollständig besiegt).
        
        Returns:
            bool: True, wenn der Kampf beendet ist, sonst False
        """
        players_alive = any(player.is_alive() for player in self.players)
        opponents_alive = any(opponent.is_alive() for opponent in self.opponents)
        
        if not players_alive and not opponents_alive:
            # Unentschieden (sollte selten vorkommen)
            logger.info("Kampf endet unentschieden! Alle Teilnehmer sind gefallen.")
            self.is_active = False
            return True
        elif not players_alive:
            # Gegner haben gewonnen
            logger.info("Kampf endet! Die Gegner sind siegreich.")
            self.is_active = False
            self.winner = 'opponents'
            return True
        elif not opponents_alive:
            # Spieler haben gewonnen
            logger.info("Kampf endet! Die Spieler sind siegreich.")
            self.is_active = False
            self.winner = 'players'
            return True
        
        # Kampf geht weiter
        return False
    
    def get_valid_targets(self, for_player: bool) -> List[CharacterInstance]:
        """
        Gibt gültige Ziele für einen Angriff zurück.
        
        Args:
            for_player (bool): True für Spieler-Angriffe (gegen Gegner), False für Gegner-Angriffe (gegen Spieler)
            
        Returns:
            List[CharacterInstance]: Die gültigen Ziele
        """
        targets = self.opponents if for_player else self.players
        return [target for target in targets if target.can_be_targeted()]
    
    def award_xp_for_victory(self, leveling_service=None) -> None:
        """
        Vergibt XP an die Spieler für besiegte Gegner.
        
        Args:
            leveling_service (Optional): Der Leveling-Service (wird importiert, wenn nicht angegeben)
        """
        if self.winner != 'players':
            logger.debug("Keine XP vergeben, da die Spieler nicht gewonnen haben")
            return
        
        # Leveling-Service importieren, wenn nicht angegeben
        if leveling_service is None:
            from src.game_logic.leveling import get_leveling_service
            leveling_service = get_leveling_service()
        
        # Gesamt-XP aus allen Gegnern berechnen
        total_xp = sum(opponent.xp_reward for opponent in self.opponents)
        
        # XP an alle lebenden Spieler verteilen
        living_players = [player for player in self.players if player.is_alive()]
        if not living_players:
            logger.warning("Keine lebenden Spieler für XP-Vergabe!")
            return
        
        # XP gleichmäßig verteilen
        xp_per_player = total_xp // len(living_players)
        if xp_per_player <= 0:
            xp_per_player = 1  # Mindestens 1 XP
        
        logger.info(f"Vergebe {xp_per_player} XP an jeden überlebenden Spieler")
        
        # XP zuweisen und auf Level-Ups prüfen
        for player in living_players:
            level_up_occurred = leveling_service.award_xp(player, xp_per_player)
            if level_up_occurred:
                logger.info(f"{player.name} ist aufgestiegen!")
