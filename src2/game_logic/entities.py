"""
Entitäten

Enthält die Klasse CharacterInstance, die eine konkrete Instanz eines Charakters oder Gegners
im Spiel repräsentiert, mit aktuellem Zustand wie HP, Statuseffekte, etc.
"""
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
import math

from src.definitions.character import CharacterTemplate, OpponentTemplate
from src.definitions.skill import SkillDefinition
from src.game_logic.formulas import (
    calculate_attribute_bonus, calculate_max_hp, 
    calculate_accuracy_modifier, calculate_evasion_modifier
)
from src.game_logic.effects import StatusEffect, create_status_effect
from src.utils.logging_setup import get_logger


# Logger für dieses Modul
logger = get_logger(__name__)


@dataclass
class CharacterInstance:
    """
    Repräsentiert eine konkrete Instanz eines Charakters oder Gegners im Spiel.
    
    Diese Klasse enthält den aktuellen Zustand eines Charakters (Spieler oder Gegner),
    einschließlich aktueller Lebenspunkte, Ressourcen und Status-Effekte.
    """
    # Basisinformationen
    id: str
    name: str
    template_id: str
    
    # Primärattribute (aus Template + Statusmodifikatoren)
    base_attributes: Dict[str, int]
    
    # Kampfwerte (aus Template + Statusmodifikatoren)
    base_combat_values: Dict[str, int]
    
    # Verfügbare Skills
    skill_ids: List[str]
    
    # Aktueller Zustand
    hp: int
    mana: int = 0
    stamina: int = 0
    energy: int = 0
    shield_points: int = 0  # Für Schild-Effekte
    
    # Erfahrung und Level
    xp: int = 0
    level: int = 1
    
    # Status-Effekte und Modifikatoren
    active_effects: Dict[str, StatusEffect] = field(default_factory=dict)
    status_mods: Dict[str, int] = field(default_factory=dict)
    status_flags: Dict[str, bool] = field(default_factory=dict)
    
    # Tags für den Charakter (z.B. WARRIOR, UNDEAD)
    tags: Set[str] = field(default_factory=set)
    
    # Für Gegner: KI-Strategie und XP-Belohnung
    ai_strategy: Optional[str] = None
    xp_reward: int = 0
    
    def __post_init__(self):
        """Wird nach der Initialisierung aufgerufen, um Standardwerte zu setzen."""
        # Standardwerte für Status-Modifikatoren
        default_mods = [
            'STR', 'DEX', 'INT', 'CON', 'WIS',  # Primärattribute
            'armor', 'magic_resist', 'initiative',  # Kampfwerte
            'accuracy', 'evasion'  # Berechnete Werte
        ]
        for mod in default_mods:
            if mod not in self.status_mods:
                self.status_mods[mod] = 0
        
        # Standardwerte für Status-Flags
        default_flags = ['can_act', 'can_be_targeted']
        for flag in default_flags:
            if flag not in self.status_flags:
                self.status_flags[flag] = True
        
        # Sicherstellen, dass "basic_attack_free" vorhanden ist
        if "basic_attack_free" not in self.skill_ids:
            self.skill_ids.append("basic_attack_free")
    
    def __hash__(self) -> int:
        """
        Macht die CharacterInstance hashable, damit sie als Dictionary-Schlüssel verwendet werden kann.
        
        Returns:
            int: Der Hash-Wert basierend auf der id
        """
        return hash(self.id)
    
    def __eq__(self, other) -> bool:
        """
        Vergleicht zwei CharacterInstances auf Gleichheit.
        
        Args:
            other: Ein anderes Objekt zum Vergleich
            
        Returns:
            bool: True, wenn die IDs übereinstimmen, sonst False
        """
        if not isinstance(other, CharacterInstance):
            return False
        return self.id == other.id
    
    @classmethod
    def from_template(cls, template: CharacterTemplate, level: int = 1) -> 'CharacterInstance':
        """
        Erstellt eine CharacterInstance aus einem CharacterTemplate.
        
        Args:
            template (CharacterTemplate): Das zu verwendende Template
            level (int): Das Startlevel des Charakters
            
        Returns:
            CharacterInstance: Eine neue CharacterInstance
        """
        # Basis-HP und Ressourcen berechnen
        base_hp = template.get_combat_value('base_hp')
        base_mana = template.get_combat_value('base_mana')
        base_stamina = template.get_combat_value('base_stamina')
        base_energy = template.get_combat_value('base_energy')
        
        # Maximales HP mit Konstitutionsbonus berechnen
        constitution = template.get_attribute('CON')
        max_hp = calculate_max_hp(base_hp, constitution)
        
        # Skills kopieren und sicherstellen, dass basic_attack_free enthalten ist
        skills = template.skills.copy()
        if "basic_attack_free" not in skills:
            skills.append("basic_attack_free")
        
        instance = cls(
            id=f"{template.id}_{id(template)}",  # Eindeutige ID erstellen
            name=template.name,
            template_id=template.id,
            base_attributes=template.primary_attributes.copy(),
            base_combat_values=template.combat_values.copy(),
            skill_ids=skills,
            hp=max_hp,
            mana=base_mana,
            stamina=base_stamina,
            energy=base_energy,
            level=level,
            tags=set(template.tags)
        )
        
        # Wenn es ein Gegner-Template ist, zusätzliche Werte setzen
        if isinstance(template, OpponentTemplate):
            instance.ai_strategy = template.ai_strategy
            instance.xp_reward = template.xp_reward
        
        return instance
    
    def get_attribute(self, attr_name: str) -> int:
        """
        Gibt den aktuellen Wert eines Primärattributs zurück, inklusive Statusmodifikatoren.
        
        Args:
            attr_name (str): Der Name des Attributs (z.B. 'STR')
            
        Returns:
            int: Der aktuelle Attributwert
        """
        base_value = self.base_attributes.get(attr_name, 0)
        mod_value = self.status_mods.get(attr_name, 0)
        return base_value + mod_value
    
    def get_combat_value(self, value_name: str) -> int:
        """
        Gibt den aktuellen Wert eines Kampfwerts zurück, inklusive Statusmodifikatoren.
        
        Args:
            value_name (str): Der Name des Kampfwerts (z.B. 'armor')
            
        Returns:
            int: Der aktuelle Kampfwert
        """
        base_value = self.base_combat_values.get(value_name, 0)
        mod_value = self.status_mods.get(value_name, 0)
        return base_value + mod_value
    
    def get_max_hp(self) -> int:
        """
        Berechnet die maximalen Lebenspunkte basierend auf Basis-HP und Konstitution.
        
        Returns:
            int: Die maximalen Lebenspunkte
        """
        base_hp = self.base_combat_values.get('base_hp', 0)
        constitution = self.get_attribute('CON')
        return calculate_max_hp(base_hp, constitution)
    
    def get_accuracy(self) -> int:
        """
        Berechnet den Genauigkeitsmodifikator basierend auf Geschicklichkeit und Statuseffekten.
        
        Returns:
            int: Der aktuelle Genauigkeitsmodifikator
        """
        dexterity = self.get_attribute('DEX')
        effects_mod = self.status_mods.get('accuracy', 0)
        return calculate_accuracy_modifier(dexterity, effects_mod)
    
    def get_evasion(self) -> int:
        """
        Berechnet den Ausweichmodifikator basierend auf Geschicklichkeit und Statuseffekten.
        
        Returns:
            int: Der aktuelle Ausweichmodifikator
        """
        dexterity = self.get_attribute('DEX')
        effects_mod = self.status_mods.get('evasion', 0)
        return calculate_evasion_modifier(dexterity, effects_mod)
    
    def get_initiative(self) -> int:
        """
        Berechnet die Initiative basierend auf Geschicklichkeit und Statuseffekten.
        
        Returns:
            int: Der aktuelle Initiativewert
        """
        base_initiative = self.get_attribute('DEX') * 2
        initiative_mod = self.status_mods.get('initiative', 0)
        return base_initiative + initiative_mod
    
    def is_alive(self) -> bool:
        """
        Prüft, ob der Charakter noch lebt.
        
        Returns:
            bool: True, wenn HP > 0, sonst False
        """
        return self.hp > 0
    
    def can_act(self) -> bool:
        """
        Prüft, ob der Charakter handeln kann (nicht betäubt, etc.).
        
        Returns:
            bool: True, wenn der Charakter handeln kann, sonst False
        """
        return self.status_flags.get('can_act', True) and self.is_alive()
    
    def can_be_targeted(self) -> bool:
        """
        Prüft, ob der Charakter als Ziel ausgewählt werden kann.
        
        Returns:
            bool: True, wenn der Charakter ein gültiges Ziel ist, sonst False
        """
        return self.status_flags.get('can_be_targeted', True) and self.is_alive()
    
    def has_tag(self, tag: str) -> bool:
        """
        Prüft, ob der Charakter einen bestimmten Tag hat.
        
        Args:
            tag (str): Der zu prüfende Tag
            
        Returns:
            bool: True, wenn der Tag vorhanden ist, sonst False
        """
        return tag in self.tags
    
    def has_enough_resource(self, skill: SkillDefinition) -> bool:
        """
        Prüft, ob der Charakter genug Ressourcen für den Skill hat.
        
        Args:
            skill (SkillDefinition): Der zu prüfende Skill
            
        Returns:
            bool: True, wenn genug Ressourcen vorhanden sind, sonst False
        """
        cost_value = skill.get_cost_value()
        cost_type = skill.get_cost_type()
        
        if cost_type == 'NONE' or cost_value <= 0:
            return True
        
        resource_map = {
            'MANA': self.mana,
            'STAMINA': self.stamina,
            'ENERGY': self.energy,
        }
        
        current_resource = resource_map.get(cost_type, 0)
        return current_resource >= cost_value
    
    def spend_resource(self, skill: SkillDefinition) -> bool:
        """
        Verbraucht Ressourcen für einen Skill.
        
        Args:
            skill (SkillDefinition): Der Skill, für den Ressourcen verbraucht werden
            
        Returns:
            bool: True, wenn erfolgreich, False wenn nicht genug Ressourcen vorhanden waren
        """
        cost_value = skill.get_cost_value()
        cost_type = skill.get_cost_type()
        
        if cost_type == 'NONE' or cost_value <= 0:
            return True
        
        # Prüfen, ob genug Ressourcen vorhanden sind
        if not self.has_enough_resource(skill):
            return False
        
        # Ressourcen verbrauchen
        if cost_type == 'MANA':
            self.mana -= cost_value
        elif cost_type == 'STAMINA':
            self.stamina -= cost_value
        elif cost_type == 'ENERGY':
            self.energy -= cost_value
        
        return True
    
    def apply_status_effect(self, effect_id: str, duration: int, potency: int) -> None:
        """
        Wendet einen Statuseffekt auf den Charakter an.
        
        Args:
            effect_id (str): Die ID des Statuseffekts
            duration (int): Die Dauer in Runden
            potency (int): Die Stärke des Effekts
        """
        # Statuseffekt erstellen
        effect = create_status_effect(effect_id, duration, potency)
        if not effect:
            logger.warning(f"Konnte Statuseffekt {effect_id} nicht erstellen")
            return
        
        # Prüfen, ob der Effekt bereits aktiv ist
        if effect_id in self.active_effects:
            existing_effect = self.active_effects[effect_id]
            # Dauer auf das Maximum setzen (Refresh)
            existing_effect.duration = max(existing_effect.duration, duration)
            # Potenz überschreiben (kein Stacken)
            existing_effect.potency = potency
            logger.debug(f"Statuseffekt {effect_id} bei {self.name} erneuert/überschrieben")
        else:
            # Neuen Effekt anwenden
            self.active_effects[effect_id] = effect
            effect.on_apply(self)
            logger.debug(f"Statuseffekt {effect_id} auf {self.name} angewendet")
    
    def remove_status_effect(self, effect_id: str) -> None:
        """
        Entfernt einen Statuseffekt vom Charakter.
        
        Args:
            effect_id (str): Die ID des zu entfernenden Statuseffekts
        """
        if effect_id in self.active_effects:
            effect = self.active_effects[effect_id]
            effect.on_remove(self)
            del self.active_effects[effect_id]
            logger.debug(f"Statuseffekt {effect_id} von {self.name} entfernt")
    
    def process_status_effects(self) -> None:
        """
        Verarbeitet alle aktiven Statuseffekte für eine Runde.
        """
        effects_to_remove = []
        
        for effect_id, effect in self.active_effects.items():
            # Effekt-Tick verarbeiten
            is_active = effect.tick(self)
            if not is_active:
                effects_to_remove.append(effect_id)
        
        # Abgelaufene Effekte entfernen
        for effect_id in effects_to_remove:
            del self.active_effects[effect_id]
    
    def take_damage(self, damage: int, damage_type: str) -> Tuple[int, bool]:
        """
        Lässt den Charakter Schaden nehmen, unter Berücksichtigung von Rüstung/Resistenz.
        
        Args:
            damage (int): Der Rohe Schaden
            damage_type (str): Der Schadenstyp (PHYSICAL, MAGICAL, HOLY, etc.)
            
        Returns:
            Tuple[int, bool]: Der tatsächlich zugefügte Schaden und ob der Charakter dadurch stirbt
        """
        # Schutzschild-Punkte zuerst anwenden, wenn vorhanden
        if self.shield_points > 0:
            absorbed = min(self.shield_points, damage)
            self.shield_points -= absorbed
            damage -= absorbed
            logger.debug(f"{self.name}'s Schild absorbiert {absorbed} Schaden, {self.shield_points} Schildpunkte übrig")
            if damage <= 0:
                return absorbed, False
        
        # Passende Verteidigung basierend auf Schadenstyp wählen
        defense = 0
        if damage_type == 'PHYSICAL':
            defense = self.get_combat_value('armor')
        elif damage_type in ('MAGICAL', 'HOLY', 'DARK'):
            defense = self.get_combat_value('magic_resist')
        
        # Schadenreduzierung durch Verteidigung
        reduced_damage = max(1, damage - defense)  # Mindestens 1 Schaden
        self.hp -= reduced_damage
        
        # Lebendstatus prüfen
        is_dead = self.hp <= 0
        if is_dead:
            self.hp = 0
            logger.info(f"{self.name} wurde besiegt!")
        else:
            logger.debug(f"{self.name} nimmt {reduced_damage} Schaden ({damage} - {defense}), verbleibende HP: {self.hp}")
        
        return reduced_damage, is_dead
    
    def take_raw_damage(self, damage: int) -> Tuple[int, bool]:
        """
        Lässt den Charakter direkten Schaden nehmen, der Rüstung und Resistenzen ignoriert.
        
        Args:
            damage (int): Der Schaden
            
        Returns:
            Tuple[int, bool]: Der tatsächlich zugefügte Schaden und ob der Charakter dadurch stirbt
        """
        self.hp -= damage
        is_dead = self.hp <= 0
        if is_dead:
            self.hp = 0
            logger.info(f"{self.name} wurde durch direkten Schaden besiegt!")
        else:
            logger.debug(f"{self.name} nimmt {damage} direkten Schaden, verbleibende HP: {self.hp}")
        
        return damage, is_dead
    
    def heal(self, amount: int) -> int:
        """
        Heilt den Charakter um die angegebene Menge.
        
        Args:
            amount (int): Die Heilungsmenge
            
        Returns:
            int: Die tatsächlich geheilte Menge
        """
        if not self.is_alive():
            logger.debug(f"{self.name} ist tot und kann nicht geheilt werden")
            return 0
        
        max_hp = self.get_max_hp()
        old_hp = self.hp
        self.hp = min(max_hp, self.hp + amount)
        actual_healing = self.hp - old_hp
        
        if actual_healing > 0:
            logger.debug(f"{self.name} wird um {actual_healing} HP geheilt, neue HP: {self.hp}/{max_hp}")
        
        return actual_healing
    
    def restore_resource(self, resource_type: str, amount: int) -> int:
        """
        Stellt eine Ressource (Mana, Stamina, Energy) wieder her.
        
        Args:
            resource_type (str): Der Ressourcentyp ('MANA', 'STAMINA', 'ENERGY')
            amount (int): Die Menge
            
        Returns:
            int: Die tatsächlich wiederhergestellte Menge
        """
        if resource_type == 'MANA':
            max_value = self.base_combat_values.get('base_mana', 0)
            old_value = self.mana
            self.mana = min(max_value, self.mana + amount)
            return self.mana - old_value
        
        elif resource_type == 'STAMINA':
            max_value = self.base_combat_values.get('base_stamina', 0)
            old_value = self.stamina
            self.stamina = min(max_value, self.stamina + amount)
            return self.stamina - old_value
        
        elif resource_type == 'ENERGY':
            max_value = self.base_combat_values.get('base_energy', 0)
            old_value = self.energy
            self.energy = min(max_value, self.energy + amount)
            return self.energy - old_value
        
        return 0
    
    def gain_xp(self, amount: int) -> bool:
        """
        Lässt den Charakter Erfahrungspunkte erhalten und prüft auf Level-Aufstieg.
        
        Args:
            amount (int): Die Menge an XP
            
        Returns:
            bool: True, wenn ein Level-Aufstieg stattfand, sonst False
        """
        if not self.is_alive():
            return False
        
        self.xp += amount
        logger.debug(f"{self.name} erhält {amount} XP, neue Gesamtsumme: {self.xp}")
        
        # Diese Funktion macht noch keinen Level-Up - das überlassen wir dem Leveling-Service,
        # der über diese Funktion informiert wird und dann die level_up-Methode aufruft.
        
        # In einer späteren Implementierung würden wir hier ein Event auslösen,
        # das vom Leveling-System abonniert wird.
        return False
    
    def level_up(self) -> None:
        """
        Führt einen Level-Aufstieg durch.
        Diese Funktion wird vom Leveling-Service aufgerufen.
        """
        self.level += 1
        logger.info(f"{self.name} ist auf Level {self.level} aufgestiegen!")
        
        # Volle Heilung und Ressourcenwiederherstellung
        max_hp = self.get_max_hp()
        self.hp = max_hp
        
        for resource_type in ['MANA', 'STAMINA', 'ENERGY']:
            max_resource = self.base_combat_values.get(f'base_{resource_type.lower()}', 0)
            if resource_type == 'MANA':
                self.mana = max_resource
            elif resource_type == 'STAMINA':
                self.stamina = max_resource
            elif resource_type == 'ENERGY':
                self.energy = max_resource
