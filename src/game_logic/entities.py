# src/game_logic/entities.py
"""
Enthält die Klasse CharacterInstance, die eine konkrete Instanz eines Charakters
oder Gegners im Spiel repräsentiert, inklusive aktuellem Zustand.
"""
import uuid # Für eindeutige Instanz-IDs
import logging
from typing import Dict, List, Optional, Any

# Importiere Template-Klassen und Formeln
from src.definitions.character import CharacterTemplate
from src.definitions.opponent import OpponentTemplate
from src.definitions.skill import SkillTemplate # Wird für Skill-Listen etc. benötigt
# from src.definitions.loader import load_skill_templates # Um Skill-Objekte zu erhalten
from src.game_logic import formulas # Um Formeln für Berechnungen zu nutzen
# from .effects import StatusEffect # Wird später für Status-Effekte benötigt

# Erhalte einen Logger für dieses Modul
logger = logging.getLogger(__name__)

# Importiere die globale Konfiguration
try:
    from src.config.config import CONFIG
except ImportError:
    logger.critical("FATAL: Konfigurationsmodul src.config.config konnte nicht importiert werden in entities.py.")
    CONFIG = None # Sollte nicht passieren in normaler Ausführung

class CharacterInstance:
    """
    Repräsentiert eine aktive Instanz eines Charakters oder Gegners im Spiel.
    Diese Klasse hält den aktuellen Zustand (HP, Mana, Position, Status-Effekte etc.).
    """
    def __init__(self,
                 base_template: CharacterTemplate | OpponentTemplate,
                 instance_id: Optional[str] = None,
                 name_override: Optional[str] = None):
        
        self.instance_id: str = instance_id if instance_id else str(uuid.uuid4())
        self.base_template: CharacterTemplate | OpponentTemplate = base_template
        
        self.name: str = name_override if name_override else self.base_template.name
        
        # Primärattribute initialisieren (als Kopie, um Template nicht zu ändern)
        self.attributes: Dict[str, int] = dict(self.base_template.primary_attributes)
        
        # Kampfwerte initialisieren
        self._initialize_combat_stats()

        # Aktuelle Ressourcen und HP
        self.current_hp: int = self.max_hp
        self.current_mana: int = self.max_mana
        self.current_stamina: int = self.max_stamina
        self.current_energy: int = self.max_energy
        
        self.shield_points: int = 0 # Aktuelle Schildpunkte

        # Status-Effekte (wird später mit StatusEffect-Objekten gefüllt)
        self.status_effects: List[Any] = [] # TODO: Typ anpassen zu List[StatusEffect]

        # Gelernte Skills (Liste von SkillTemplate-Objekten oder Skill-IDs)
        # Für den Anfang speichern wir die Skill-IDs, tatsächliche Skill-Objekte können bei Bedarf geladen werden.
        self.skills: List[str] = list(self.base_template.skills) if hasattr(self.base_template, 'skills') else \
                                  list(self.base_template.starting_skills) if hasattr(self.base_template, 'starting_skills') else []


        self.level: int = getattr(self.base_template, 'level', 1) # Gegner haben Level, Spieler starten auf Level 1
        self.xp: int = 0 # Aktuelle Erfahrungspunkte
        self.xp_for_next_level: int = formulas.calculate_xp_for_next_level(self.level)

        self.is_defeated: bool = False
        self.can_act: bool = True # Kann durch Effekte wie Stun modifiziert werden

        logger.info(f"Charakter-Instanz '{self.name}' (ID: {self.instance_id}) erstellt "
                    f"basiert auf Template '{self.base_template.id}'. "
                    f"HP: {self.current_hp}/{self.max_hp}")

    def _initialize_combat_stats(self):
        """Initialisiert abgeleitete Kampfstatistiken basierend auf Attributen und Template."""
        # Max HP
        self.max_hp: int = formulas.calculate_max_hp(
            base_hp=self.base_template.base_hp,
            constitution_value=self.attributes.get("CON", 10) # Fallback CON 10
        )
        
        # Max Ressourcen (direkt aus Template-combat_values oder berechnet)
        # Annahme: base_mana, base_stamina, base_energy sind in combat_values des Templates
        template_cv = self.base_template.combat_values
        self.max_mana: int = template_cv.get("base_mana", 0) # Default 0 wenn nicht vorhanden
        self.max_stamina: int = template_cv.get("base_stamina", 0)
        self.max_energy: int = template_cv.get("base_energy", 0)
        
        # Weitere Kampfwerte
        self.armor: int = template_cv.get("armor", 0)
        self.magic_resist: int = template_cv.get("magic_resist", 0)
        
        # Initiative (Basis, ohne Status-Effekt-Modifikatoren)
        # Initiative-Bonus kann von Gegner-Templates kommen
        initiative_bonus_template = template_cv.get("initiative_bonus", 0)
        self.base_initiative: int = formulas.calculate_initiative(
            dexterity_value=self.attributes.get("DEX", 10), # Fallback DEX 10
            initiative_bonus=initiative_bonus_template
        )
        self.current_initiative: int = self.base_initiative # Kann durch Effekte modifiziert werden

        # Genauigkeit und Ausweichen (Basiswerte, könnten durch Attribute/Skills modifiziert werden)
        # Für den Moment nehmen wir an, sie sind 0, wenn nicht explizit gesetzt.
        # In einer komplexeren Implementierung würden sie von DEX, Skills, Items etc. abhängen.
        self.accuracy: int = template_cv.get("accuracy", 0) # Basis-Genauigkeit
        self.evasion: int = template_cv.get("evasion", 0)   # Basis-Ausweichen

    def get_attribute_bonus(self, attribute_name: str) -> int:
        """Gibt den Bonus für ein gegebenes Attribut zurück."""
        attr_val = self.attributes.get(attribute_name.upper(), 10) # Default 10, falls Attribut nicht existiert
        return formulas.calculate_attribute_bonus(attr_val)

    def take_damage(self, amount: int, damage_type: str = "PHYSICAL") -> int:
        """
        Verarbeitet eingehenden Schaden. Reduziert Schildpunkte zuerst, dann HP.
        Gibt den tatsächlich an HP verursachten Schaden zurück.
        """
        if self.is_defeated:
            return 0

        # Schadensreduktion durch Rüstung/Magieresistenz
        resistance_value = self.armor if damage_type in ["PHYSICAL", "PIERCING", "BLUDGEONING"] else self.magic_resist # Vereinfachte Logik
        # TODO: Detailliertere Schadens-Typ vs. Resistenz-Typ Logik
        
        actual_damage_after_reduction = formulas.calculate_damage_reduction(amount, resistance_value)
        
        # Schildpunkte absorbieren Schaden zuerst
        absorbed_by_shield = 0
        if self.shield_points > 0:
            absorbed_by_shield = min(self.shield_points, actual_damage_after_reduction)
            self.shield_points -= absorbed_by_shield
            actual_damage_after_reduction -= absorbed_by_shield
            logger.debug(f"'{self.name}' absorbiert {absorbed_by_shield} Schaden mit Schild. Restschaden: {actual_damage_after_reduction}. Schild verbleibend: {self.shield_points}")

        if actual_damage_after_reduction <= 0: # Kein Schaden nach Reduktion und Schild
            logger.info(f"'{self.name}' erleidet keinen Schaden (abgewehrt/absorbiert).")
            return 0

        self.current_hp -= actual_damage_after_reduction
        logger.info(f"'{self.name}' erleidet {actual_damage_after_reduction} {damage_type} Schaden. HP: {self.current_hp}/{self.max_hp}")

        if self.current_hp <= 0:
            self.current_hp = 0
            self.is_defeated = True
            self.can_act = False # Besiegte Charaktere können nicht handeln
            logger.info(f"'{self.name}' wurde besiegt!")
        
        return actual_damage_after_reduction # Der Schaden, der tatsächlich die HP reduziert hat

    def heal(self, amount: int) -> int:
        """Heilt die Instanz um einen bestimmten Betrag, bis maximal HP."""
        if self.is_defeated: # Besiegte können nicht geheilt werden (optional, Regelentscheidung)
            logger.info(f"'{self.name}' ist besiegt und kann nicht geheilt werden.")
            return 0
            
        if amount <= 0:
            return 0
            
        healed_amount = min(amount, self.max_hp - self.current_hp)
        self.current_hp += healed_amount
        logger.info(f"'{self.name}' wird um {healed_amount} HP geheilt. HP: {self.current_hp}/{self.max_hp}")
        return healed_amount

    def restore_resource(self, amount: int, resource_type: str) -> int:
        """Stellt eine spezifische Ressource wieder her (Mana, Stamina, Energy)."""
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

    def consume_resource(self, amount: int, resource_type: str) -> bool:
        """Verbraucht eine Ressource. Gibt True zurück, wenn erfolgreich, sonst False."""
        if amount < 0: return True # Negativer Verbrauch ist wie Wiederherstellung, hier nicht behandelt
        if amount == 0: return True # Kein Verbrauch, immer erfolgreich

        resource_type_upper = resource_type.upper()
        
        if resource_type_upper == "MANA":
            if self.current_mana >= amount:
                self.current_mana -= amount
                logger.debug(f"'{self.name}' verbraucht {amount} Mana. Verbleibend: {self.current_mana}")
                return True
        elif resource_type_upper == "STAMINA":
            if self.current_stamina >= amount:
                self.current_stamina -= amount
                logger.debug(f"'{self.name}' verbraucht {amount} Stamina. Verbleibend: {self.current_stamina}")
                return True
        elif resource_type_upper == "ENERGY":
            if self.current_energy >= amount:
                self.current_energy -= amount
                logger.debug(f"'{self.name}' verbraucht {amount} Energy. Verbleibend: {self.current_energy}")
                return True
        elif resource_type_upper == "NONE" or resource_type is None: # "NONE" Typ für kostenlose Skills
            logger.debug(f"'{self.name}' führt eine Aktion ohne Ressourcenkosten aus.")
            return True
            
        logger.warning(f"Nicht genügend {resource_type_upper} für '{self.name}' (benötigt {amount}, hat {getattr(self, 'current_' + resource_type_upper.lower(), 0)}).")
        return False

    def add_xp(self, amount: int):
        """Fügt Erfahrungspunkte hinzu und prüft auf Level-Up."""
        if self.is_defeated or amount <= 0:
            return

        self.xp += amount
        logger.info(f"'{self.name}' erhält {amount} XP. Gesamt-XP: {self.xp}/{self.xp_for_next_level}")
        
        while self.xp >= self.xp_for_next_level:
            self._level_up()

    def _level_up(self):
        """Führt die Aktionen für einen Levelaufstieg durch."""
        self.level += 1
        self.xp -= self.xp_for_next_level # XP-Übertrag, wenn mehr als nötig gesammelt wurde
        if self.xp < 0: self.xp = 0 # Sollte nicht passieren, aber sicher ist sicher
        
        self.xp_for_next_level = formulas.calculate_xp_for_next_level(self.level)
        
        logger.info(f"LEVEL UP! '{self.name}' hat Level {self.level} erreicht!")
        
        # Level-Up Boni (gemäß ANNEX_GAME_DEFINITIONS_SUMMARY)
        # Volle Heilung und Ressourcenwiederherstellung
        self.current_hp = self.max_hp
        self.current_mana = self.max_mana
        self.current_stamina = self.max_stamina
        self.current_energy = self.max_energy
        self.shield_points = 0 # Schild zurücksetzen
        logger.info(f"'{self.name}' wurde vollständig geheilt und Ressourcen wiederhergestellt.")
        
        # TODO: Weitere Level-Up-Boni implementieren:
        # - Attributpunkte zum Verteilen?
        # - Skillpunkte?
        # - Automatische Attributerhöhungen? (Müsste in Charakter-Template oder einer Wachstums-Kurve definiert sein)
        # - Neue Skills freischalten?

    def get_info(self) -> Dict[str, Any]:
        """Gibt ein Dictionary mit den wichtigsten Informationen zur Instanz zurück."""
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
            "status_effects": [str(se) for se in self.status_effects] # Platzhalter, bis StatusEffect Klasse existiert
        }

    def __str__(self) -> str:
        return (f"{self.name} (Lvl {self.level}, HP: {self.current_hp}/{self.max_hp}, "
                f"Schild: {self.shield_points}, {'Besiegt' if self.is_defeated else 'Aktiv'})")


if __name__ == '__main__':
    # Testen der CharacterInstance Klasse
    # Benötigt geladene Templates und Konfiguration
    
    # Simuliere das Laden von Definitionen
    try:
        from src.definitions.loader import load_character_templates, load_opponent_templates, load_skill_templates
        from src.config.config import CONFIG # Stellt sicher, dass CONFIG geladen ist
        
        print("\nLade Test-Definitionen...")
        load_skill_templates() # Laden, damit Skill-Listen in Templates existieren
        char_templates = load_character_templates()
        opp_templates = load_opponent_templates()
        
        if not char_templates or not opp_templates:
            raise Exception("Konnte keine Charakter- oder Gegner-Templates für den Test laden.")

        # Hole ein Krieger-Template
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
        # Direkter Schadensaufruf (vereinfacht, ohne Skill-Logik)
        schaden_an_spieler = 15 # Angenommener Rohschaden des Goblins
        spieler.take_damage(schaden_an_spieler, damage_type="PHYSICAL") 
        print(spieler)

        print(f"\n{spieler.name} ({spieler.current_hp} HP) heilt sich.")
        spieler.heal(20)
        print(spieler)

        print(f"\n{spieler.name} verbraucht 10 Stamina. Erfolg: {spieler.consume_resource(10, 'STAMINA')}")
        print(f"Verbleibende Stamina: {spieler.current_stamina}/{spieler.max_stamina}")
        print(f"{spieler.name} versucht 200 Mana zu verbrauchen. Erfolg: {spieler.consume_resource(200, 'MANA')}") # Sollte fehlschlagen

        print("\n--- Teste XP und Level Up ---")
        print(f"{spieler.name} (Level {spieler.level}, XP: {spieler.xp}/{spieler.xp_for_next_level})")
        spieler.add_xp(70) # Nicht genug für Level Up
        print(f"{spieler.name} (Level {spieler.level}, XP: {spieler.xp}/{spieler.xp_for_next_level})")
        spieler.add_xp(50) # Sollte für Level Up reichen (70+50=120 > 100 für Lvl 2)
        print(f"{spieler.name} (Level {spieler.level}, XP: {spieler.xp}/{spieler.xp_for_next_level})")
        print(f"HP nach Level Up: {spieler.current_hp}/{spieler.max_hp}") # Sollte voll sein

        print("\n--- Teste Schildmechanik ---")
        spieler.shield_points = 20
        print(f"{spieler.name} hat {spieler.shield_points} Schildpunkte.")
        spieler.take_damage(25, "PHYSICAL") # 20 vom Schild, 5 von HP (nach Rüstung)
        print(spieler)
        
        print("\n--- Info-Dictionary ---")
        print(spieler.get_info())


    except ImportError as e:
        print(f"FEHLER bei Imports für den Test in entities.py: {e}. Stelle sicher, dass alle Definitionen und Config geladen werden können.")
    except Exception as e:
        print(f"Ein Fehler ist während des Testlaufs in entities.py aufgetreten: {e}")
        import traceback
        traceback.print_exc()