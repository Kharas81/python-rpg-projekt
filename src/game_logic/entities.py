# src/game_logic/entities.py
"""
Enthält die Klasse CharacterInstance, die eine konkrete Instanz eines Charakters
oder Gegners im Spiel repräsentiert, inklusive aktuellem Zustand.
"""
import uuid # Für eindeutige Instanz-IDs
import logging
import math # Hinzugefügt, falls für Formeln benötigt, die hier direkt aufgerufen werden könnten
from typing import Dict, List, Optional, Any, TYPE_CHECKING

# Importiere Template-Klassen und Formeln
from src.definitions.character import CharacterTemplate
from src.definitions.opponent import OpponentTemplate
from src.definitions.skill import SkillTemplate # KORREKTUR: SkillTemplate für Typ-Hinweis importieren
from src.game_logic import formulas 
# from .effects import StatusEffect # Wird später für Status-Effekte benötigt (wenn StatusEffect-Objekte hier direkt gehandhabt werden)

# Um zirkuläre Importe bei Typ-Hinweisen zu vermeiden, wenn effects.py CharacterInstance importieren würde
if TYPE_CHECKING:
    from src.game_logic.effects import StatusEffect 


logger = logging.getLogger(__name__)

try:
    from src.config.config import CONFIG
except ImportError:
    logger.critical("FATAL: Konfigurationsmodul src.config.config konnte nicht importiert werden in entities.py.")
    CONFIG = None 

class CharacterInstance:
    def __init__(self,
                 base_template: CharacterTemplate | OpponentTemplate,
                 instance_id: Optional[str] = None,
                 name_override: Optional[str] = None):
        
        self.instance_id: str = instance_id if instance_id else str(uuid.uuid4())
        self.base_template: CharacterTemplate | OpponentTemplate = base_template
        
        self.name: str = name_override if name_override else self.base_template.name
        
        self.attributes: Dict[str, int] = dict(self.base_template.primary_attributes)
        
        self._initialize_combat_stats()

        self.current_hp: int = self.max_hp
        self.current_mana: int = self.max_mana
        self.current_stamina: int = self.max_stamina
        self.current_energy: int = self.max_energy
        
        self.shield_points: int = 0 

        self.status_effects: List['StatusEffect'] = [] # Typ-Hinweis angepasst

        self.skills: List[str] = list(getattr(self.base_template, 'skills', [])) or \
                                  list(getattr(self.base_template, 'starting_skills', []))


        self.level: int = getattr(self.base_template, 'level', 1) 
        self.xp: int = 0 
        self.xp_for_next_level: int = formulas.calculate_xp_for_next_level(self.level)

        self.is_defeated: bool = False
        self.can_act: bool = True 

        # Zusätzliche Attribute für die KI-Nutzung (Basiswerte, können durch Effekte modifiziert werden)
        template_cv = self.base_template.combat_values
        self.accuracy: int = template_cv.get("accuracy", 0) 
        self.evasion: int = template_cv.get("evasion", 0)   

        logger.info(f"Charakter-Instanz '{self.name}' (ID: {self.instance_id}) erstellt "
                    f"basiert auf Template '{self.base_template.id}'. "
                    f"HP: {self.current_hp}/{self.max_hp}")

    def _initialize_combat_stats(self):
        self.max_hp: int = formulas.calculate_max_hp(
            base_hp=self.base_template.base_hp,
            constitution_value=self.attributes.get("CON", 10) 
        )
        
        template_cv = self.base_template.combat_values
        self.max_mana: int = template_cv.get("base_mana", 0) 
        self.max_stamina: int = template_cv.get("base_stamina", 0)
        self.max_energy: int = template_cv.get("base_energy", 0)
        
        self.armor: int = template_cv.get("armor", 0)
        self.magic_resist: int = template_cv.get("magic_resist", 0)
        
        initiative_bonus_template = template_cv.get("initiative_bonus", 0)
        self.base_initiative: int = formulas.calculate_initiative(
            dexterity_value=self.attributes.get("DEX", 10), 
            initiative_bonus=initiative_bonus_template
        )
        self.current_initiative: int = self.base_initiative 

    def get_attribute_bonus(self, attribute_name: str) -> int:
        attr_val = self.attributes.get(attribute_name.upper(), 10) 
        return formulas.calculate_attribute_bonus(attr_val)

    def take_damage(self, amount: int, damage_type: str = "PHYSICAL") -> int:
        if self.is_defeated:
            return 0

        # Bestimme relevante Resistenz
        resistance_value = 0
        # Vereinfachte Logik für Schadenswiderstand - könnte komplexer sein
        if damage_type.upper() in ["PHYSICAL", "PIERCING", "BLUDGEONING", "SLASHING"]:
            resistance_value = self.armor
        elif damage_type.upper() in ["MAGIC", "FIRE", "ICE", "HOLY", "DARK"]: # Beispielhafte magische Typen
            resistance_value = self.magic_resist
        else: # Unbekannter Schadenstyp oder direkter Schaden
            resistance_value = 0
        
        actual_damage_after_reduction = formulas.calculate_damage_reduction(amount, resistance_value)
        
        absorbed_by_shield = 0
        if self.shield_points > 0:
            absorbed_by_shield = min(self.shield_points, actual_damage_after_reduction)
            self.shield_points -= absorbed_by_shield
            actual_damage_after_reduction -= absorbed_by_shield
            logger.debug(f"'{self.name}' absorbiert {absorbed_by_shield} Schaden mit Schild. Restschaden: {actual_damage_after_reduction}. Schild verbleibend: {self.shield_points}")

        if actual_damage_after_reduction <= 0: 
            logger.info(f"'{self.name}' erleidet keinen HP-Schaden (abgewehrt/absorbiert).")
            return 0 # Nur der Schildschaden wurde verursacht, kein HP-Schaden

        hp_damage_taken = actual_damage_after_reduction
        self.current_hp -= hp_damage_taken
        # logger.info(f"'{self.name}' erleidet {hp_damage_taken} {damage_type} HP-Schaden. HP: {self.current_hp}/{self.max_hp}") # Wird jetzt vom CombatHandler geloggt

        if self.current_hp <= 0:
            self.current_hp = 0
            self.is_defeated = True
            self.can_act = False 
            logger.info(f"'{self.name}' wurde besiegt!")
        
        return hp_damage_taken # Gibt den tatsächlich an HP verursachten Schaden zurück

    def heal(self, amount: int) -> int:
        if self.is_defeated: 
            logger.info(f"'{self.name}' ist besiegt und kann nicht geheilt werden.")
            return 0
        if amount <= 0: return 0
            
        healed_amount = min(amount, self.max_hp - self.current_hp)
        self.current_hp += healed_amount
        # logger.info(f"'{self.name}' wird um {healed_amount} HP geheilt. HP: {self.current_hp}/{self.max_hp}") # Wird vom CombatHandler geloggt
        return healed_amount

    def restore_resource(self, amount: int, resource_type: str) -> int:
        if amount <= 0: return 0
        restored_amount = 0
        resource_type_upper = resource_type.upper()

        if resource_type_upper == "MANA":
            restored_amount = min(amount, self.max_mana - self.current_mana)
            self.current_mana += restored_amount
            logger.debug(f"'{self.name}' stellt {restored_amount} Mana wieder her. Mana: {self.current_mana}/{self.max_mana}")
        elif resource_type_upper == "STAMINA":
            restored_amount = min(amount, self.max_stamina - self.current_stamina)
            self.current_stamina += restored_amount
            logger.debug(f"'{self.name}' stellt {restored_amount} Stamina wieder her. Stamina: {self.current_stamina}/{self.max_stamina}")
        elif resource_type_upper == "ENERGY":
            restored_amount = min(amount, self.max_energy - self.current_energy)
            self.current_energy += restored_amount
            logger.debug(f"'{self.name}' stellt {restored_amount} Energy wieder her. Energy: {self.current_energy}/{self.max_energy}")
        else:
            logger.warning(f"Unbekannter Ressourcentyp '{resource_type}' für Wiederherstellung bei '{self.name}'.")
        return restored_amount

    def consume_resource(self, amount: int, resource_type: Optional[str]) -> bool: # resource_type kann None sein
        if amount < 0: return True 
        if amount == 0: return True 

        if resource_type is None: # Manche Skills haben type: null in JSON, als NONE interpretieren
            resource_type_upper = "NONE"
        else:
            resource_type_upper = resource_type.upper()
        
        current_value = 0
        if resource_type_upper == "MANA": current_value = self.current_mana
        elif resource_type_upper == "STAMINA": current_value = self.current_stamina
        elif resource_type_upper == "ENERGY": current_value = self.current_energy
        elif resource_type_upper == "NONE":
            logger.debug(f"'{self.name}' führt eine Aktion ohne Ressourcenkosten aus.")
            return True
        else: # Unbekannter Ressourcentyp
            logger.warning(f"'{self.name}' versucht, unbekannte Ressource '{resource_type}' zu verbrauchen.")
            return False # Kann nicht verbraucht werden

        if current_value >= amount:
            if resource_type_upper == "MANA": self.current_mana -= amount
            elif resource_type_upper == "STAMINA": self.current_stamina -= amount
            elif resource_type_upper == "ENERGY": self.current_energy -= amount
            logger.debug(f"'{self.name}' verbraucht {amount} {resource_type_upper}. Verbleibend: {getattr(self, 'current_' + resource_type_upper.lower())}")
            return True
        
        logger.warning(f"Nicht genügend {resource_type_upper} für '{self.name}' (benötigt {amount}, hat {current_value}).")
        return False

    # KORREKTUR: Hinzufügen der can_afford_skill Methode
    def can_afford_skill(self, skill_template: SkillTemplate) -> bool:
        """Prüft, ob die Instanz genügend Ressourcen für einen Skill hat."""
        if not skill_template:
            return False
        
        cost_type = skill_template.cost.type
        cost_value = skill_template.cost.value

        if cost_value == 0: # Kostenlose Skills sind immer leistbar
            return True

        cost_type_upper = ""
        if cost_type: # Sicherstellen, dass cost_type nicht None ist
            cost_type_upper = cost_type.upper()
        else: # Wenn type null ist, aber Kosten > 0, ist das ein Definitionsfehler
            logger.error(f"Skill '{skill_template.name}' hat Kosten ({cost_value}) aber keinen Ressourcentyp (type: null).")
            return False


        if cost_type_upper == "NONE": # Sollte durch cost_value == 0 abgedeckt sein, aber zur Sicherheit
            return True
        elif cost_type_upper == "MANA":
            return self.current_mana >= cost_value
        elif cost_type_upper == "STAMINA":
            return self.current_stamina >= cost_value
        elif cost_type_upper == "ENERGY":
            return self.current_energy >= cost_value
        
        logger.warning(f"Unbekannter Ressourcentyp '{skill_template.cost.type}' bei der Kostenprüfung für Skill '{skill_template.name}'.")
        return False


    def add_xp(self, amount: int):
        if self.is_defeated or amount <= 0:
            return

        self.xp += amount
        logger.info(f"'{self.name}' erhält {amount} XP. Gesamt-XP: {self.xp}/{self.xp_for_next_level}")
        
        while self.xp >= self.xp_for_next_level:
            self._level_up()

    def _level_up(self):
        self.level += 1
        # XP-Übertrag richtig berechnen
        xp_overflow = self.xp - self.xp_for_next_level
        self.xp = xp_overflow if xp_overflow > 0 else 0
        
        self.xp_for_next_level = formulas.calculate_xp_for_next_level(self.level)
        
        # Ausgabe des Level-Ups über cli_output im Hauptloop, hier nur Log
        logger.info(f"LEVEL UP! '{self.name}' hat Level {self.level} erreicht! Nächstes Level bei {self.xp_for_next_level} XP.")
        
        self.current_hp = self.max_hp
        self.current_mana = self.max_mana
        self.current_stamina = self.max_stamina
        self.current_energy = self.max_energy
        self.shield_points = 0 
        logger.info(f"'{self.name}' wurde vollständig geheilt und Ressourcen wiederhergestellt.")
        
    def get_info(self) -> Dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "name": self.name,
            "level": self.level,
            "hp": f"{self.current_hp}/{self.max_hp}",
            "mana": f"{self.current_mana}/{self.max_mana}",
            "stamina": f"{self.current_stamina}/{self.max_stamina}",
            "energy": f"{self.current_energy}/{self.max_energy}",
            "shield": self.shield_points,
            "attributes": self.attributes,
            "is_defeated": self.is_defeated,
            "can_act": self.can_act,
            "status_effects": [str(se) for se in self.status_effects] 
        }

    def __str__(self) -> str:
        return (f"{self.name} (Lvl {self.level}, HP: {self.current_hp}/{self.max_hp}, "
                f"Schild: {self.shield_points}, {'Besiegt' if self.is_defeated else 'Aktiv'})")


if __name__ == '__main__':
    try:
        from src.definitions.loader import load_character_templates, load_opponent_templates, load_skill_templates
        from src.config.config import CONFIG 
        
        print("\nLade Test-Definitionen für entities.py...")
        all_skills = load_skill_templates() 
        char_templates = load_character_templates()
        opp_templates = load_opponent_templates()
        
        if not char_templates or not opp_templates or not all_skills:
            raise Exception("Konnte Templates oder Skills für den Test nicht laden.")

        krieger_template = char_templates.get("krieger")
        goblin_template = opp_templates.get("goblin_lv1")

        if not krieger_template or not goblin_template:
            raise Exception("Krieger- oder Goblin-Template nicht in geladenen Daten gefunden.")

        print("\n--- Erstelle Charakter-Instanzen ---")
        spieler = CharacterInstance(base_template=krieger_template, name_override="Held Karras")
        gegner_goblin = CharacterInstance(base_template=goblin_template)

        print(spieler)
        print(gegner_goblin)
        
        print(f"\n{spieler.name} Attribute: {spieler.attributes}")
        print(f"{spieler.name} STR Bonus: {spieler.get_attribute_bonus('STR')}")
        print(f"{gegner_goblin.name} CON Bonus: {gegner_goblin.get_attribute_bonus('CON')}")
        print(f"{spieler.name} Initiative: {spieler.current_initiative}")
        print(f"{gegner_goblin.name} Initiative: {gegner_goblin.current_initiative}")

        print("\n--- Teste Kampfaktionen ---")
        print(f"Goblin ({gegner_goblin.current_hp} HP) greift {spieler.name} ({spieler.current_hp} HP) an.")
        schaden_an_spieler = 15 
        spieler.take_damage(schaden_an_spieler, damage_type="PHYSICAL") 
        print(spieler)

        print(f"\n{spieler.name} ({spieler.current_hp} HP) heilt sich.")
        spieler.heal(20)
        print(spieler)

        # Teste can_afford_skill
        power_strike_skill = all_skills.get("power_strike") # Kostet 15 Stamina
        basic_strike_skill = all_skills.get("basic_strike_phys") # Kostet 0 

        if power_strike_skill:
            spieler.current_stamina = 100
            print(f"\n{spieler.name} hat {spieler.current_stamina} Stamina. Kann Power Strike (15) einsetzen? {spieler.can_afford_skill(power_strike_skill)}")
            assert spieler.can_afford_skill(power_strike_skill)
            
            print(f"{spieler.name} verbraucht 15 Stamina. Erfolg: {spieler.consume_resource(15, 'STAMINA')}")
            print(f"Verbleibende Stamina: {spieler.current_stamina}/{spieler.max_stamina}")
            
            spieler.current_stamina = 10
            print(f"{spieler.name} hat {spieler.current_stamina} Stamina. Kann Power Strike (15) einsetzen? {spieler.can_afford_skill(power_strike_skill)}")
            assert not spieler.can_afford_skill(power_strike_skill)

        if basic_strike_skill:
             print(f"{spieler.name} hat {spieler.current_stamina} Stamina. Kann Basic Strike (0) einsetzen? {spieler.can_afford_skill(basic_strike_skill)}")
             assert spieler.can_afford_skill(basic_strike_skill)


        print(f"{spieler.name} versucht 200 Mana zu verbrauchen. Erfolg: {spieler.consume_resource(200, 'MANA')}") 

        print("\n--- Teste XP und Level Up ---")
        spieler.current_hp = spieler.max_hp # Zurücksetzen für sauberen Level-Up-Test
        print(f"{spieler.name} (Level {spieler.level}, XP: {spieler.xp}/{spieler.xp_for_next_level})")
        spieler.add_xp(70) 
        print(f"{spieler.name} (Level {spieler.level}, XP: {spieler.xp}/{spieler.xp_for_next_level})")
        spieler.add_xp(50) 
        print(f"{spieler.name} (Level {spieler.level}, XP: {spieler.xp}/{spieler.xp_for_next_level})")
        print(f"HP nach Level Up: {spieler.current_hp}/{spieler.max_hp}") 

        print("\n--- Teste Schildmechanik ---")
        spieler.shield_points = 20
        print(f"{spieler.name} hat {spieler.shield_points} Schildpunkte.")
        spieler.take_damage(25, "PHYSICAL") 
        print(spieler)
        
        print("\n--- Info-Dictionary ---")
        print(spieler.get_info())

    except ImportError as e:
        print(f"FEHLER bei Imports für den Test in entities.py: {e}. Stelle sicher, dass alle Definitionen und Config geladen werden können.")
    except Exception as e:
        print(f"Ein Fehler ist während des Testlaufs in entities.py aufgetreten: {e}")
        import traceback
        traceback.print_exc()