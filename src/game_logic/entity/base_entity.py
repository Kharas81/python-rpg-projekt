"""
Base Entity Module

Dieses Modul definiert die Basisklasse für Spielcharaktere und Gegner.
"""

import uuid
import logging
from typing import Dict, Any, List, Optional, Tuple

from src.game_logic.entity.entity_types import EntityType
from src.game_logic.entity.status_effect import StatusEffectInstance
from src.game_logic.entity.skills.skill_user import SkillUser

# Logger für dieses Modul einrichten
logger = logging.getLogger(__name__)


class Entity(SkillUser):
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
        
        # Creature Type (für spezielle Effekte)
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
