"""
Entity Module

Dieses Modul definiert die Basisklasse für Spielcharaktere und Gegner.
"""

import uuid
import logging
import math
from enum import Enum, auto
from typing import Dict, Any, List, Optional, Set, Tuple

from src.definitions.data_loader import data_loader

# Logger für dieses Modul einrichten
logger = logging.getLogger(__name__)


class EntityType(Enum):
    """Enum für die Typen von Entitäten."""
    PLAYER = auto()
    ENEMY = auto()
    NPC = auto()


class StatusEffectInstance:
    """
    Repräsentiert eine Instanz eines Status-Effekts auf einer Entität.
    """
    
    def __init__(self, effect_id: str, duration: int, 
                 source_entity_id: Optional[str] = None,
                 params: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialisiert einen Status-Effekt.
        
        Args:
            effect_id: ID des Status-Effekts in den Daten
            duration: Dauer in Runden
            source_entity_id: ID der Entität, die den Effekt verursacht hat
            params: Zusätzliche Parameter für den Effekt
        """
        self.effect_id = effect_id
        self.duration = duration
        self.source_entity_id = source_entity_id
        self.params = params or {}
        
        # Lade Effektdaten
        try:
            self.effect_data = data_loader.get_status_effect(effect_id)
            self.name = self.effect_data["name"]
            self.description = self.effect_data["description"]
            self.icon = self.effect_data.get("icon", "?")
        except KeyError:
            logger.warning(f"Status-Effekt {effect_id} nicht gefunden, verwende Standardwerte")
            self.effect_data = {}
            self.name = effect_id
            self.description = "Unbekannter Effekt"
            self.icon = "?"
    
    def on_apply(self, entity: 'Entity') -> None:
        """
        Wird aufgerufen, wenn der Effekt auf eine Entität angewendet wird.
        
        Args:
            entity: Die Entität, auf die der Effekt angewendet wird
        """
        logger.debug(f"Status-Effekt {self.name} auf {entity.name} angewandt")
        
        # Wende Effekte auf die Entität an
        effects = self.effect_data.get("effects", [])
        
        if "prevent_actions" in effects:
            entity.can_act = False
        
        if "reduce_initiative" in effects:
            modifier = self.effect_data.get("initiative_modifier", 0)
            entity.initiative_modifier += modifier
        
        if "increase_initiative" in effects:
            modifier = self.effect_data.get("initiative_bonus", 0)
            entity.initiative_modifier += modifier
        
        if "reduce_accuracy" in effects:
            modifier = self.effect_data.get("accuracy_modifier", 0)
            entity.accuracy_modifier += modifier
        
        if "increase_defenses" in effects:
            armor_bonus = self.effect_data.get("armor_bonus", 0)
            magic_res_bonus = self.effect_data.get("magic_resistance_bonus", 0)
            entity.armor_modifier += armor_bonus
            entity.magic_resistance_modifier += magic_res_bonus
    
    def on_remove(self, entity: 'Entity') -> None:
        """
        Wird aufgerufen, wenn der Effekt von einer Entität entfernt wird.
        
        Args:
            entity: Die Entität, von der der Effekt entfernt wird
        """
        logger.debug(f"Status-Effekt {self.name} von {entity.name} entfernt")
        
        # Entferne Effekte von der Entität
        effects = self.effect_data.get("effects", [])
        
        if "prevent_actions" in effects:
            entity.can_act = True
        
        if "reduce_initiative" in effects:
            modifier = self.effect_data.get("initiative_modifier", 0)
            entity.initiative_modifier -= modifier
        
        if "increase_initiative" in effects:
            modifier = self.effect_data.get("initiative_bonus", 0)
            entity.initiative_modifier -= modifier
        
        if "reduce_accuracy" in effects:
            modifier = self.effect_data.get("accuracy_modifier", 0)
            entity.accuracy_modifier -= modifier
        
        if "increase_defenses" in effects:
            armor_bonus = self.effect_data.get("armor_bonus", 0)
            magic_res_bonus = self.effect_data.get("magic_resistance_bonus", 0)
            entity.armor_modifier -= armor_bonus
            entity.magic_resistance_modifier -= magic_res_bonus
    
    def on_turn(self, entity: 'Entity') -> None:
        """
        Wird zu Beginn eines Zuges für die Entität aufgerufen.
        
        Args:
            entity: Die Entität mit diesem Effekt
        """
        effects = self.effect_data.get("effects", [])
        
        # Führe Effekte aus, die jede Runde wirken
        if "damage_over_time" in effects:
            damage = self.effect_data.get("damage_per_turn", 0)
            damage_type = self.effect_data.get("damage_type", "untyped")
            logger.debug(f"{entity.name} erleidet {damage} {damage_type}-Schaden durch {self.name}")
            entity.take_damage(damage, damage_type)
        
        # Reduziere die verbleibende Dauer
        self.duration -= 1
        
        if self.duration <= 0:
            logger.debug(f"Status-Effekt {self.name} läuft aus für {entity.name}")
            entity.remove_status_effect(self.effect_id)


class Entity:
    """
    Basisklasse für Spieler und Gegner.
    
    Diese Klasse verwaltet die grundlegenden Attribute, Ressourcen und Status-Effekte
    für alle Entitäten im Spiel.
    """
    
    def __init__(self, entity_id: str, entity_type: EntityType, data_dict: Dict[str, Any]) -> None:
        """
        Initialisiert eine neue Spielentität.
        
        Args:
            entity_id: Eindeutige ID für diese Entität (z.B. "warrior", "goblin")
            entity_type: Typ der Entität (PLAYER, ENEMY, NPC)
            data_dict: Dictionary mit den Daten der Entität aus der JSON-Datei
        """
        self.id = entity_id
        self.entity_type = entity_type
        self.unique_id = str(uuid.uuid4())  # Eindeutige Instanz-ID
        
        # Grundlegende Informationen
        self.name = data_dict["name"]
        self.description = data_dict.get("description", "")
        self.level = data_dict.get("level", 1)
        
        # Attribute
        self.attributes = {
            "strength": data_dict["attributes"].get("strength", 10),
            "dexterity": data_dict["attributes"].get("dexterity", 10),
            "intelligence": data_dict["attributes"].get("intelligence", 10),
            "constitution": data_dict["attributes"].get("constitution", 10),
            "wisdom": data_dict["attributes"].get("wisdom", 10)
        }
        
        # Defensivwerte
        self.armor = data_dict["defenses"].get("armor", 0)
        self.magic_resistance = data_dict["defenses"].get("magic_resistance", 0)
        self.armor_modifier = 0
        self.magic_resistance_modifier = 0
        
        # HP-Berechnung (50 + Konstitution * 5)
        self.max_hp = 50 + (self.attributes["constitution"] * 5)
        self.current_hp = self.max_hp
        
        # Ressourcen
        self.max_stamina = data_dict["resources"].get("max_stamina")
        self.current_stamina = self.max_stamina if self.max_stamina is not None else None
        
        self.max_energy = data_dict["resources"].get("max_energy")
        self.current_energy = self.max_energy if self.max_energy is not None else None
        
        self.max_mana = data_dict["resources"].get("max_mana")
        self.current_mana = self.max_mana if self.max_mana is not None else None
        
        # Kampfwerte
        self.initiative = self.attributes["dexterity"]  # Basis-Initiative ist Geschicklichkeit
        self.initiative_modifier = 0
        self.accuracy_modifier = 0
        self.can_act = True  # Kann die Entität handeln? (z.B. nicht bei Betäubung)
        
        # Skills
        self.known_skills = data_dict.get("known_skills", [])
        
        # Status-Effekte
        self.status_effects: Dict[str, StatusEffectInstance] = {}
        
        # Widerstandsfähigkeiten und Schwächen
        self.resistances = data_dict.get("resistances", {})
        self.vulnerabilities = data_dict.get("vulnerabilities", {})
        
        # Kampfverhalten (für KI-gesteuerte Entitäten)
        self.combat_behavior = data_dict.get("combat_behavior", {})
        
        # Creatiure Type (für spezielle Effekte)
        self.creature_type = data_dict.get("creature_type", "humanoid")
        
        logger.info(f"Entität erstellt: {self.name} (Level {self.level}, HP: {self.current_hp})")
    
    def get_attribute_bonus(self, attribute: str) -> int:
        """
        Berechnet den Attribut-Bonus nach der Formel (Attributwert - 10) // 2.
        
        Args:
            attribute: Name des Attributs ("strength", "dexterity", etc.)
            
        Returns:
            Berechneter Bonus
        """
        if attribute not in self.attributes:
            logger.warning(f"Ungültiges Attribut: {attribute}, verwende 0 als Bonus")
            return 0
        return (self.attributes[attribute] - 10) // 2
    
    def get_effective_armor(self) -> int:
        """
        Berechnet die effektive Rüstung unter Berücksichtigung von Modifikatoren.
        
        Returns:
            Effektiver Rüstungswert
        """
        return max(0, self.armor + self.armor_modifier)
    
    def get_effective_magic_resistance(self) -> int:
        """
        Berechnet die effektive Magieresistenz unter Berücksichtigung von Modifikatoren.
        
        Returns:
            Effektiver Magieresistenzwert
        """
        return max(0, self.magic_resistance + self.magic_resistance_modifier)
    
    def get_effective_initiative(self) -> int:
        """
        Berechnet die effektive Initiative unter Berücksichtigung von Modifikatoren.
        
        Returns:
            Effektiver Initiativewert
        """
        return max(1, self.initiative + self.initiative_modifier)
    
    def get_hit_chance_modifier(self) -> int:
        """
        Berechnet den Genauigkeitsmodifikator für Trefferchancen.
        
        Returns:
            Genauigkeitsmodifikator
        """
        base_mod = self.get_attribute_bonus("dexterity")
        return base_mod + self.accuracy_modifier
    
    def get_evasion_modifier(self) -> int:
        """
        Berechnet den Ausweichmodifikator für Trefferchancen.
        
        Returns:
            Ausweichmodifikator
        """
        return self.get_attribute_bonus("dexterity")
    
    def add_status_effect(self, effect_id: str, duration: int, 
                          source_entity_id: Optional[str] = None,
                          params: Optional[Dict[str, Any]] = None) -> None:
        """
        Fügt einen Status-Effekt zur Entität hinzu.
        
        Args:
            effect_id: ID des Effekts
            duration: Dauer in Runden
            source_entity_id: ID der Entität, die den Effekt verursacht hat
            params: Zusätzliche Parameter für den Effekt
        """
        # Prüfe, ob der Effekt bereits vorhanden ist
        if effect_id in self.status_effects:
            # Entferne den alten Effekt
            self.remove_status_effect(effect_id)
        
        # Erstelle und füge den neuen Effekt hinzu
        effect = StatusEffectInstance(effect_id, duration, source_entity_id, params)
        self.status_effects[effect_id] = effect
        
        # Wende den Effekt an
        effect.on_apply(self)
    
    def remove_status_effect(self, effect_id: str) -> None:
        """
        Entfernt einen Status-Effekt von der Entität.
        
        Args:
            effect_id: ID des zu entfernenden Effekts
        """
        if effect_id in self.status_effects:
            # Führe on_remove aus, bevor der Effekt entfernt wird
            self.status_effects[effect_id].on_remove(self)
            # Entferne den Effekt
            del self.status_effects[effect_id]
    
    def handle_turn_start(self) -> None:
        """
        Verarbeitet Ereignisse zum Beginn eines Zuges.
        """
        # Verarbeite alle Status-Effekte
        expired_effects: List[str] = []
        
        for effect_id, effect in self.status_effects.items():
            effect.on_turn(self)
            if effect.duration <= 0:
                expired_effects.append(effect_id)
        
        # Ressourcen regenerieren (falls implementiert)
        self.regenerate_resources()
    
    def regenerate_resources(self) -> None:
        """
        Regeneriert Ressourcen wie Stamina, Energie und Mana zu Beginn des Zuges.
        Diese Methode kann in Unterklassen überschrieben werden.
        """
        # Grundlegende Regeneration - kann in abgeleiteten Klassen angepasst werden
        if self.current_stamina is not None and self.max_stamina is not None:
            self.current_stamina = min(self.max_stamina, self.current_stamina + 5)
        
        if self.current_energy is not None and self.max_energy is not None:
            self.current_energy = min(self.max_energy, self.current_energy + 10)
        
        if self.current_mana is not None and self.max_mana is not None:
            self.current_mana = min(self.max_mana, self.current_mana + 5)
    
    def is_alive(self) -> bool:
        """
        Prüft, ob die Entität noch lebt.
        
        Returns:
            True, wenn die Entität noch lebt, sonst False
        """
        return self.current_hp > 0
    
    def take_damage(self, amount: int, damage_type: str = "physical") -> Tuple[int, bool]:
        """
        Fügt der Entität Schaden zu.
        
        Args:
            amount: Schadensmenge
            damage_type: Art des Schadens ("physical", "magical", "fire", etc.)
            
        Returns:
            Tuple aus (tatsächlicher Schaden, ist_kritisch)
        """
        # Bestimme die entsprechende Verteidigung
        if damage_type in ["physical", "piercing"]:
            defense = self.get_effective_armor()
        elif damage_type in ["magical", "fire", "frost", "holy"]:
            defense = self.get_effective_magic_resistance()
        else:
            defense = 0
        
        # Berücksichtige Rüstungsdurchdringung bei "piercing"-Schaden
        if damage_type == "piercing":
            defense = int(defense * 0.5)  # 50% der Rüstung ignorieren
        
        # Berücksichtige Resistenzen und Schwächen
        modifier = 1.0
        if damage_type in self.resistances:
            modifier -= self.resistances[damage_type]  # Reduzierter Schaden
        if damage_type in self.vulnerabilities:
            modifier += self.vulnerabilities[damage_type]  # Erhöhter Schaden
        
        # Berechne den tatsächlichen Schaden
        modified_amount = max(1, int(amount * modifier) - defense)
        
        # Ziehe Schaden von HP ab
        self.current_hp -= modified_amount
        
        # Logge den Schaden
        if modifier != 1.0:
            if modifier > 1.0:
                logger.debug(f"{self.name} ist anfällig für {damage_type}-Schaden!")
            else:
                logger.debug(f"{self.name} widersteht {damage_type}-Schaden.")
                
        logger.debug(f"{self.name} erleidet {modified_amount} {damage_type}-Schaden. "
                    f"Verbleibende HP: {self.current_hp}")
        
        # Prüfe, ob die Entität gestorben ist
        if self.current_hp <= 0:
            self.current_hp = 0
            logger.info(f"{self.name} wurde besiegt!")
        
        return modified_amount, False  # Zweiter Wert für kritischen Treffer, aktuell nicht implementiert
    
    def heal(self, amount: int) -> int:
        """
        Heilt die Entität.
        
        Args:
            amount: Heilungsmenge
            
        Returns:
            Tatsächliche Heilung
        """
        # Berechne die tatsächliche Heilung
        old_hp = self.current_hp
        self.current_hp = min(self.max_hp, self.current_hp + amount)
        actual_healing = self.current_hp - old_hp
        
        if actual_healing > 0:
            logger.debug(f"{self.name} wird um {actual_healing} HP geheilt. "
                        f"HP: {self.current_hp}/{self.max_hp}")
        
        return actual_healing
    
    def can_use_skill(self, skill_id: str) -> bool:
        """
        Prüft, ob die Entität einen bestimmten Skill einsetzen kann.
        
        Args:
            skill_id: ID des Skills
            
        Returns:
            True, wenn der Skill eingesetzt werden kann, sonst False
        """
        if not self.can_act:
            logger.debug(f"{self.name} kann nicht handeln und daher keine Skills einsetzen")
            return False
        
        if skill_id not in self.known_skills:
            logger.debug(f"{self.name} kennt den Skill {skill_id} nicht")
            return False
        
        # Lade Skill-Daten
        try:
            skill_data = data_loader.get_skill(skill_id)
        except KeyError:
            logger.error(f"Skill {skill_id} nicht in der Datenbank gefunden")
            return False
        
        # Prüfe Ressourcenanforderungen
        cost_type = skill_data["cost"]["type"]
        cost_amount = skill_data["cost"]["amount"]
        
        if cost_type == "stamina":
            if self.current_stamina is None or self.current_stamina < cost_amount:
                logger.debug(f"{self.name} hat nicht genug Stamina für {skill_id}")
                return False
        elif cost_type == "energy":
            if self.current_energy is None or self.current_energy < cost_amount:
                logger.debug(f"{self.name} hat nicht genug Energie für {skill_id}")
                return False
        elif cost_type == "mana":
            if self.current_mana is None or self.current_mana < cost_amount:
                logger.debug(f"{self.name} hat nicht genug Mana für {skill_id}")
                return False
        
        return True
    
    def use_skill(self, skill_id: str, targets: List['Entity']) -> Dict[str, Any]:
        """
        Führt einen Skill gegen bestimmte Ziele aus.
        
        Args:
            skill_id: ID des Skills
            targets: Liste der Zielentitäten
            
        Returns:
            Dictionary mit Ergebnissen der Skill-Nutzung
        """
        if not self.can_use_skill(skill_id):
            return {"success": False, "message": f"{self.name} kann {skill_id} nicht einsetzen"}
        
        # Lade Skill-Daten
        skill_data = data_loader.get_skill(skill_id)
        
        # Ressourcen abziehen
        cost_type = skill_data["cost"]["type"]
        cost_amount = skill_data["cost"]["amount"]
        
        if cost_type == "stamina":
            self.current_stamina -= cost_amount
        elif cost_type == "energy":
            self.current_energy -= cost_amount
        elif cost_type == "mana":
            self.current_mana -= cost_amount
        
        # Skill-Effekte anwenden
        results = {"success": True, "targets": {}, "message": ""}
        
        for effect in skill_data["effects"]:
            effect_type = effect["type"]
            
            if effect_type == "damage":
                results["message"] += self._apply_damage_effect(effect, targets, results)
            elif effect_type == "healing":
                results["message"] += self._apply_healing_effect(effect, targets, results)
            elif effect_type == "shield":
                results["message"] += self._apply_shield_effect(effect, targets, results)
            elif effect_type == "status":
                results["message"] += self._apply_status_effect(effect, targets, results)
        
        return results
    
    def _apply_damage_effect(self, effect: Dict[str, Any], targets: List['Entity'],
                            results: Dict[str, Any]) -> str:
        """Wendet einen Schadenseffekt auf Ziele an."""
        damage_type = effect["damage_type"]
        scaling_attribute = effect.get("scaling_attribute", "strength")
        base_value = effect["base_value"]
        
        # Basiswert ermitteln
        if base_value == "weapon_damage":
            # Lade Basiswaffenschaden aus der Konfiguration
            character_data = data_loader.get_character_data()
            base_damage = character_data.get("base_weapon_damage", 5)
        else:
            base_damage = base_value
        
        # Attributsbonus
        attribute_bonus = self.get_attribute_bonus(scaling_attribute)
        
        # Waffen-Schadenmodifikatoren würden hier berücksichtigt
        
        # Formel auswerten
        formula = effect["scaling_formula"]
        # Ersetze Platzhalter in der Formel
        formula = formula.replace("base", str(base_damage))
        formula = formula.replace("attribute_bonus", str(attribute_bonus))
        formula = formula.replace("attribute", str(self.attributes[scaling_attribute]))
        
        try:
            damage = eval(formula)
        except Exception as e:
            logger.error(f"Fehler beim Auswerten der Schadensformel: {e}")
            damage = base_damage + attribute_bonus
        
        # Runde auf ganze Zahlen
        damage = int(damage)
        
        message = ""
        
        # Wende Schaden auf alle Ziele an
        for i, target in enumerate(targets):
            # Für sekundäre Ziele (bei Flächenangriffen)
            if i > 0 and "secondary_targets_modifier" in effect:
                damage_mod = int(damage * effect["secondary_targets_modifier"])
            else:
                damage_mod = damage
            
            # Füge Schaden zu
            actual_damage, is_critical = target.take_damage(damage_mod, damage_type)
            
            # Speichere Ergebnis
            if target.unique_id not in results["targets"]:
                results["targets"][target.unique_id] = []
            
            results["targets"][target.unique_id].append({
                "type": "damage",
                "damage_type": damage_type,
                "amount": actual_damage,
                "is_critical": is_critical
            })
            
            # Erstelle Nachricht
            crit_text = " (Kritisch!)" if is_critical else ""
            message += f"{self.name} fügt {target.name} {actual_damage} {damage_type}-Schaden zu{crit_text}. "
        
        return message
    
    def _apply_healing_effect(self, effect: Dict[str, Any], targets: List['Entity'],
                             results: Dict[str, Any]) -> str:
        """Wendet einen Heilungseffekt auf Ziele an."""
        scaling_attribute = effect.get("scaling_attribute", "wisdom")
        base_value = effect["base_value"]
        
        # Formel auswerten
        formula = effect["scaling_formula"]
        # Ersetze Platzhalter in der Formel
        formula = formula.replace("base", str(base_value))
        formula = formula.replace("attribute_bonus", str(self.get_attribute_bonus(scaling_attribute)))
        formula = formula.replace("attribute", str(self.attributes[scaling_attribute]))
        
        try:
            healing = eval(formula)
        except Exception as e:
            logger.error(f"Fehler beim Auswerten der Heilungsformel: {e}")
            healing = base_value + self.get_attribute_bonus(scaling_attribute)
        
        # Runde auf ganze Zahlen
        healing = int(healing)
        
        message = ""
        
        # Wende Heilung auf alle Ziele an
        for target in targets:
            actual_healing = target.heal(healing)
            
            # Speichere Ergebnis
            if target.unique_id not in results["targets"]:
                results["targets"][target.unique_id] = []
            
            results["targets"][target.unique_id].append({
                "type": "healing",
                "amount": actual_healing
            })
            
            # Erstelle Nachricht
            message += f"{self.name} heilt {target.name} um {actual_healing} HP. "
        
        return message
    
    def _apply_shield_effect(self, effect: Dict[str, Any], targets: List['Entity'],
                            results: Dict[str, Any]) -> str:
        """Wendet einen Schildeffekt auf Ziele an."""
        scaling_attribute = effect.get("scaling_attribute", "intelligence")
        base_value = effect["base_value"]
        duration = effect.get("duration", 1)
        
        # Formel auswerten
        formula = effect["scaling_formula"]
        formula = formula.replace("base", str(base_value))
        formula = formula.replace("attribute_bonus", str(self.get_attribute_bonus(scaling_attribute)))
        formula = formula.replace("attribute", str(self.attributes[scaling_attribute]))
        
        try:
            shield_value = eval(formula)
        except Exception as e:
            logger.error(f"Fehler beim Auswerten der Schildformel: {e}")
            shield_value = base_value + self.attributes[scaling_attribute]
        
        # Runde auf ganze Zahlen
        shield_value = int(shield_value)
        
        message = ""
        
        # Wende Schild auf alle Ziele an
        for target in targets:
            # Füge Schild als Status-Effekt hinzu
            target.add_status_effect("shield", duration, self.unique_id, {
                "shield_value": shield_value
            })
            
            # Speichere Ergebnis
            if target.unique_id not in results["targets"]:
                results["targets"][target.unique_id] = []
            
            results["targets"][target.unique_id].append({
                "type": "shield",
                "amount": shield_value,
                "duration": duration
            })
            
            # Erstelle Nachricht
            message += f"{self.name} gibt {target.name} einen Schild mit {shield_value} Absorption für {duration} Runden. "
        
        return message
    
    def _apply_status_effect(self, effect: Dict[str, Any], targets: List['Entity'],
                            results: Dict[str, Any]) -> str:
        """Wendet einen Statuseffekt auf Ziele an."""
        status_effect = effect["status_effect"]
        duration = effect.get("duration", 1)
        chance = effect.get("chance", 1.0)
        
        message = ""
        
        # Wende Status-Effekt auf alle Ziele an
        for target in targets:
            # Würfle für Chance
            import random
            if random.random() <= chance:
                # Erstelle Parameter-Dict für zusätzliche Effektdaten
                params = {}
                for key, value in effect.items():
                    if key not in ["type", "status_effect", "duration", "chance"]:
                        params[key] = value
                
                # Füge Status-Effekt hinzu
                target.add_status_effect(status_effect, duration, self.unique_id, params)
                
                # Speichere Ergebnis
                if target.unique_id not in results["targets"]:
                    results["targets"][target.unique_id] = []
                
                results["targets"][target.unique_id].append({
                    "type": "status_effect",
                    "status_effect": status_effect,
                    "duration": duration,
                    "applied": True
                })
                
                # Erstelle Nachricht
                effect_data = data_loader.get_status_effect(status_effect)
                effect_name = effect_data["name"]
                message += f"{self.name} verursacht den Status '{effect_name}' bei {target.name} für {duration} Runden. "
            else:
                # Status-Effekt wurde widerstanden
                if target.unique_id not in results["targets"]:
                    results["targets"][target.unique_id] = []
                
                results["targets"][target.unique_id].append({
                    "type": "status_effect",
                    "status_effect": status_effect,
                    "applied": False
                })
                
                message += f"{target.name} widersteht dem Status-Effekt von {self.name}. "
        
        return message
    
    def get_resource_amount(self, resource_type: str) -> Optional[int]:
        """
        Gibt den aktuellen Wert einer Ressource zurück.
        
        Args:
            resource_type: Typ der Ressource ("stamina", "energy", "mana")
            
        Returns:
            Aktueller Wert der Ressource oder None, wenn die Ressource nicht vorhanden ist
        """
        if resource_type == "stamina":
            return self.current_stamina
        elif resource_type == "energy":
            return self.current_energy
        elif resource_type == "mana":
            return self.current_mana
        else:
            return None
    
    def get_max_resource_amount(self, resource_type: str) -> Optional[int]:
        """
        Gibt den Maximalwert einer Ressource zurück.
        
        Args:
            resource_type: Typ der Ressource ("stamina", "energy", "mana")
            
        Returns:
            Maximalwert der Ressource oder None, wenn die Ressource nicht vorhanden ist
        """
        if resource_type == "stamina":
            return self.max_stamina
        elif resource_type == "energy":
            return self.max_energy
        elif resource_type == "mana":
            return self.max_mana
        else:
            return None
    
    def level_up(self) -> Dict[str, Any]:
        """
        Erhöht das Level der Entität und passt Werte entsprechend an.
        
        Returns:
            Dictionary mit Informationen zu den Änderungen durch das Level-Up
        """
        old_level = self.level
        old_max_hp = self.max_hp
        
        # Level erhöhen
        self.level += 1
        
        # HP-Bonus durch Konstitution
        hp_increase = 5 * self.attributes["constitution"]
        self.max_hp += hp_increase
        
        # HP auffüllen
        self.current_hp = self.max_hp
        
        logger.info(f"{self.name} erreicht Level {self.level}! Max HP: {old_max_hp} -> {self.max_hp}")
        
        return {
            "old_level": old_level,
            "new_level": self.level,
            "hp_increase": hp_increase
        }


# Klasse für Spielercharaktere
class Player(Entity):
    """Spielercharakter-Klasse, die von Entity erbt."""
    
    def __init__(self, class_id: str, name: Optional[str] = None) -> None:
        """
        Initialisiert einen neuen Spielercharakter.
        
        Args:
            class_id: ID der Charakterklasse ("warrior", "mage", etc.)
            name: Benutzerdefinierter Name (optional)
        """
        # Charakterdaten laden
        character_data = data_loader.get_character_class(class_id)
        
        # Name anpassen, falls angegeben
        if name:
            character_data = dict(character_data)  # Kopie erstellen
            character_data["name"] = name
        
        super().__init__(class_id, EntityType.PLAYER, character_data)
        
        # Spielerspezifische Attribute
        self.xp = 0
        self.xp_to_next_level = self._calculate_xp_for_level(self.level + 1)
        self.skill_points = 0
        self.attribute_points = 0
        
        # Wachstumsmodifikatoren (werden bei Level-Ups verwendet)
        self.growth_modifiers = character_data.get("growth_modifiers", {})
    
    def _calculate_xp_for_level(self, level: int) -> int:
        """
        Berechnet die benötigte XP für ein bestimmtes Level.
        
        Args:
            level: Das zu berechnende Level
            
        Returns:
            Benötigte XP für dieses Level
        """
        base_value = 100
        factor = 1.5
        return int(base_value * (factor ** (level - 1)))
    
    def gain_xp(self, amount: int) -> Dict[str, Any]:
        """
        Fügt XP hinzu und führt ggf. ein Level-Up durch.
        
        Args:
            amount: Menge an XP
            
        Returns:
            Dictionary mit Informationen zu Änderungen
        """
        old_xp = self.xp
        old_level = self.level
        
        self.xp += amount
        logger.info(f"{self.name} erhält {amount} XP. Gesamt: {self.xp}")
        
        result = {
            "xp_gained": amount,
            "new_xp": self.xp,
            "level_up": False,
            "level_ups": []
        }
        
        # Prüfe auf Level-Ups
        while self.xp >= self.xp_to_next_level:
            # Level-Up durchführen
            level_up_result = self.level_up()
            result["level_ups"].append(level_up_result)
            result["level_up"] = True
            
            # XP für das nächste Level berechnen
            self.xp_to_next_level = self._calculate_xp_for_level(self.level + 1)
        
        if result["level_up"]:
            result["old_level"] = old_level
            result["new_level"] = self.level
        
        return result
    
    def level_up(self) -> Dict[str, Any]:
        """
        Erweiterte Level-Up-Funktion für Spielercharaktere.
        
        Returns:
            Dictionary mit Informationen zum Level-Up
        """
        result = super().level_up()
        
        # Ressourcen anpassen
        if self.max_mana is not None:
            mana_increase = 10 * (self.get_attribute_bonus("intelligence") + self.get_attribute_bonus("wisdom"))
            old_max_mana = self.max_mana
            self.max_mana += mana_increase
            self.current_mana = self.max_mana
            result["mana_increase"] = mana_increase
            logger.info(f"{self.name} erhöht maximales Mana: {old_max_mana} -> {self.max_mana}")
        
        if self.max_stamina is not None:
            stamina_increase = 5 * self.get_attribute_bonus("constitution")
            old_max_stamina = self.max_stamina
            self.max_stamina += stamina_increase
            self.current_stamina = self.max_stamina
            result["stamina_increase"] = stamina_increase
            logger.info(f"{self.name} erhöht maximale Ausdauer: {old_max_stamina} -> {self.max_stamina}")
        
        if self.max_energy is not None:
            energy_increase = 5 * self.get_attribute_bonus("dexterity")
            old_max_energy = self.max_energy
            self.max_energy += energy_increase
            self.current_energy = self.max_energy
            result["energy_increase"] = energy_increase
            logger.info(f"{self.name} erhöht maximale Energie: {old_max_energy} -> {self.max_energy}")
        
        # Attributpunkte und Skillpunkte vergeben
        self.attribute_points += 1
        self.skill_points += 1
        result["attribute_points"] = self.attribute_points
        result["skill_points"] = self.skill_points
        
        # Automatische Attributsteigerung basierend auf Wachstumsmodifikatoren
        # (Dies könnte später durch manuelle Attributpunktverteilung ersetzt werden)
        if self.growth_modifiers:
            for attr, modifier in self.growth_modifiers.items():
                if attr in self.attributes:
                    increase = int(modifier * 0.5)  # Geringe automatische Steigerung
                    if increase > 0:
                        old_value = self.attributes[attr]
                        self.attributes[attr] += increase
                        logger.info(f"{self.name} erhöht {attr}: {old_value} -> {self.attributes[attr]}")
        
        return result


# Klasse für Gegner
class Enemy(Entity):
    """Gegner-Klasse, die von Entity erbt."""
    
    def __init__(self, enemy_id: str) -> None:
        """
        Initialisiert einen neuen Gegner.
        
        Args:
            enemy_id: ID des Gegners (z.B. "goblin", "skeleton")
        """
        # Gegnerdaten laden
        enemy_data = data_loader.get_enemy(enemy_id)
        super().__init__(enemy_id, EntityType.ENEMY, enemy_data)
        
        # Gegner-spezifische Attribute
        self.xp_reward = enemy_data["loot_table"].get("xp", 0)
        self.gold_reward = enemy_data["loot_table"].get("gold", {"min": 0, "max": 0})
        self.loot_table = enemy_data["loot_table"].get("items", [])
    
    def get_xp_reward(self) -> int:
        """
        Gibt die XP-Belohnung für das Besiegen dieses Gegners zurück.
        
        Returns:
            XP-Menge
        """
        return self.xp_reward
    
    def get_gold_reward(self) -> int:
        """
        Würfelt die Gold-Belohnung für das Besiegen dieses Gegners aus.
        
        Returns:
            Gold-Menge
        """
        import random
        min_gold = self.gold_reward.get("min", 0)
        max_gold = self.gold_reward.get("max", 0)
        return random.randint(min_gold, max_gold)
    
    def roll_loot(self) -> List[Dict[str, Any]]:
        """
        Würfelt den Loot aus der Loot-Tabelle aus.
        
        Returns:
            Liste der Gegenstände
        """
        import random
        dropped_items = []
        
        for loot_entry in self.loot_table:
            item_id = loot_entry["item_id"]
            chance = loot_entry["chance"]
            
            if random.random() <= chance:
                dropped_items.append({
                    "item_id": item_id,
                    # Hier würden später weitere Item-Details geladen
                })
        
        return dropped_items


# Beispielnutzung
if __name__ == "__main__":
    # Konfiguriere Logging
    logging.basicConfig(level=logging.DEBUG)
    
    # Erstelle einen Spielercharakter
    player = Player("warrior", "Thorin")
    print(f"Spieler erstellt: {player.name} (Level {player.level}, HP: {player.current_hp})")
    print(f"Attribute: {player.attributes}")
    
    # Erstelle einen Gegner
    enemy = Enemy("goblin")
    print(f"Gegner erstellt: {enemy.name} (Level {enemy.level}, HP: {enemy.current_hp})")
    
    # Demo eines Angriffs
    if player.can_use_skill("basic_strike_phys"):
        result = player.use_skill("basic_strike_phys", [enemy])
        print(result["message"])
        
        # Prüfe, ob der Gegner besiegt wurde
        if not enemy.is_alive():
            print(f"{enemy.name} wurde besiegt!")
            xp_reward = enemy.get_xp_reward()
            gold_reward = enemy.get_gold_reward()
            print(f"Belohnungen: {xp_reward} XP, {gold_reward} Gold")
            
            # XP zum Spieler hinzufügen
            xp_result = player.gain_xp(xp_reward)
            if xp_result["level_up"]:
                print(f"{player.name} ist aufgestiegen! Neues Level: {player.level}")
