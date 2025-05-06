import typing
import logging

# Importiere die Basis-Definition und den Loader
try:
    from src.definitions.character import Character as CharacterDefinition
    from src.definitions import loader
    from src.game_logic.formulas import calculate_max_hp, calculate_attribute_bonus
    from src.config import config
    if typing.TYPE_CHECKING:
        from src.game_logic.effects import StatusEffect
except ModuleNotFoundError:
    print("WARNUNG: entities.py - Module nicht direkt geladen, versuche relativen Import (nur für Test)")
    from ..definitions.character import Character as CharacterDefinition
    from ..definitions import loader
    from .formulas import calculate_max_hp, calculate_attribute_bonus
    from ..config import config
    if typing.TYPE_CHECKING:
        from .effects import StatusEffect


logger = logging.getLogger(__name__)

class CharacterInstance:
    def __init__(self, definition: CharacterDefinition):
        self.definition: CharacterDefinition = definition
        self.name: str = definition.name
        self.level: int = definition.level
        self.attributes: typing.Dict[str, int] = definition.attributes.copy()
        base_hp = self.definition.get_combat_value('base_hp')
        con = self.get_attribute('CON')
        self.max_hp: int = calculate_max_hp(base_hp, con)
        self.current_hp: int = self.max_hp
        self.max_mana: int = self.definition.get_combat_value('base_mana')
        self.current_mana: int = self.max_mana
        self.max_stamina: int = self.definition.get_combat_value('base_stamina')
        self.current_stamina: int = self.max_stamina
        self.max_energy: int = self.definition.get_combat_value('base_energy')
        self.current_energy: int = self.max_energy
        self.armor: int = self.definition.get_combat_value('armor')
        self.magic_resist: int = self.definition.get_combat_value('magic_resist')
        self.active_status_effects: typing.List['StatusEffect'] = []
        self.is_alive_flag: bool = True
        self.current_xp: int = 0
        self.xp_to_next_level: int = self._calculate_xp_for_level(self.level)
        logger.debug(f"Charakter-Instanz '{self.name}' (Lvl {self.level}) erstellt: "
                     f"HP={self.current_hp}/{self.max_hp}, XP={self.current_xp}/{self.xp_to_next_level}, "
                     f"[Resourcen...] Effekte: {len(self.active_status_effects)}")

    def _calculate_xp_for_level(self, level_to_calculate_for: int) -> int:
        try:
            from src.game_logic import leveling
            return leveling.calculate_xp_for_level(level_to_calculate_for)
        except ImportError:
            logger.error("Modul 'leveling' konnte nicht importiert werden.")
            return 100 * level_to_calculate_for

    # --- Status Effect Management ---
    def add_status_effect(self, effect_data: typing.Dict[str, typing.Any], source_entity_id: typing.Optional[str] = None):
        try: from src.game_logic.effects import StatusEffect
        except ImportError: logger.error("Kann StatusEffect Klasse nicht importieren in add_status_effect."); return
        effect_id = effect_data.get("id")
        duration = effect_data.get("duration")
        potency = effect_data.get("potency")
        if not effect_id or duration is None: logger.warning(f"Ungültige Status-Effekt-Daten erhalten: {effect_data}"); return
        existing_effect: typing.Optional[StatusEffect] = None
        for effect in self.active_status_effects:
            if effect.effect_id == effect_id: existing_effect = effect; break
        if existing_effect:
            old_duration = existing_effect.duration
            existing_effect.duration = max(existing_effect.duration, int(duration))
            if potency is not None: existing_effect.potency = potency
            existing_effect.source_entity_id = source_entity_id
            existing_effect.applied_effect_data = effect_data
            logger.info(f"Status-Effekt '{effect_id}' auf '{self.name}' aktualisiert. Dauer: {old_duration} -> {existing_effect.duration}, Potenz: {existing_effect.potency}")
        else:
            new_effect = StatusEffect(effect_id=effect_id, duration=int(duration), potency=potency,
                                      source_entity_id=source_entity_id, applied_effect_data=effect_data)
            self.active_status_effects.append(new_effect)
            logger.info(f"Status-Effekt '{effect_id}' auf '{self.name}' angewendet. Dauer: {new_effect.duration}, Potenz: {new_effect.potency}")

    def remove_status_effect(self, effect_id_to_remove: str):
        initial_len = len(self.active_status_effects)
        self.active_status_effects = [eff for eff in self.active_status_effects if eff.effect_id != effect_id_to_remove]
        if len(self.active_status_effects) < initial_len: logger.info(f"Status-Effekt '{effect_id_to_remove}' von '{self.name}' entfernt.")

    def tick_status_effects(self):
        if not self.is_alive(): return
        try: from src.game_logic.effects import StatusEffect
        except ImportError: logger.error("Kann StatusEffect nicht importieren in tick_status_effects."); return
        logger.debug(f"Ticke Status-Effekte für '{self.name}'...")
        expired_effect_ids = []
        effects_to_process = list(self.active_status_effects)
        for effect in effects_to_process:
            # Effekt-Wirkung anwenden (Beispiel BURNING)
            if effect.effect_id == "BURNING":
                damage = int(effect.potency) if effect.potency is not None else 1
                logger.info(f"'{self.name}' erleidet {damage} Schaden durch '{effect.effect_id}'.")
                self.take_damage(damage)
                if not self.is_alive(): break # Stopp, wenn Charakter stirbt
            # Dauer verringern und prüfen, ob abgelaufen
            if effect.tick():
                expired_effect_ids.append(effect.effect_id)
                logger.info(f"Status-Effekt '{effect.effect_id}' auf '{self.name}' ist abgelaufen.")
        # Abgelaufene Effekte entfernen
        if expired_effect_ids:
            self.active_status_effects = [eff for eff in self.active_status_effects if eff.effect_id not in expired_effect_ids]
            logger.debug(f"Abgelaufene Effekte entfernt für '{self.name}': {expired_effect_ids}")

    def has_status_effect(self, effect_id: str) -> bool:
        return any(eff.effect_id == effect_id for eff in self.active_status_effects)

    # --- Attribute & Ressourcen Methoden (korrekt formatiert) ---
    def get_attribute(self, attr_name: str, base_value: bool = False) -> int:
        base_val = self.attributes.get(attr_name.upper(), 0)
        # TODO: Hier Status-Effekte berücksichtigen
        if base_value: return base_val
        else: modified_val = base_val; return modified_val
    def get_attribute_bonus(self, attr_name: str) -> int: return calculate_attribute_bonus(self.get_attribute(attr_name))
    def get_current_resource(self, rt: str) -> int: rt=rt.upper(); return self.current_mana if rt=="MANA" else self.current_stamina if rt=="STAMINA" else self.current_energy if rt=="ENERGY" else 9999 if rt=="NONE" or rt=="" else 0
    def can_afford_cost(self, rt: str, a: int) -> bool: return True if a<=0 or rt.upper()=="NONE" else self.get_current_resource(rt) >= a
    def pay_cost(self, rt: str, a: int) -> bool:
        if a <= 0 or rt.upper() == "NONE": return True
        if not self.can_afford_cost(rt, a): logger.warning(f"'{self.name}' kann Kosten von {a} {rt} nicht bezahlen."); return False
        res_type = rt.upper(); paid = False
        if res_type == "MANA": self.current_mana -= a; paid = True
        elif res_type == "STAMINA": self.current_stamina -= a; paid = True
        elif res_type == "ENERGY": self.current_energy -= a; paid = True
        if paid: logger.info(f"'{self.name}' bezahlt {a} {res_type}. Neuer Stand: {self.get_current_resource(res_type)}"); return True
        else: logger.error(f"Kosten konnten nicht bezahlt werden für Ressource '{res_type}'."); return False

    # --- HP & Lebensstatus Methoden (korrekt formatiert) ---
    def take_damage(self, amount: int):
        if amount <= 0 or not self.is_alive_flag: return
        self.current_hp -= amount
        logger.info(f"'{self.name}' erleidet {amount} Schaden. HP: {self.current_hp}/{self.max_hp}")
        if self.current_hp <= 0:
            self.current_hp = 0
            self.is_alive_flag = False
            logger.info(f"'{self.name}' wurde besiegt!")
    def heal(self, amount: int):
        if amount <= 0 or not self.is_alive_flag: return
        heal_applied = min(amount, self.max_hp - self.current_hp)
        if heal_applied > 0:
            self.current_hp += heal_applied
            logger.info(f"'{self.name}' wird um {heal_applied} HP geheilt. HP: {self.current_hp}/{self.max_hp}")
    def is_alive(self) -> bool: return self.is_alive_flag

    # --- XP & Leveling Methoden (korrekt formatiert) ---
    def gain_xp(self, amount: int):
        if amount <= 0 or not self.is_alive(): return
        self.current_xp += amount
        logger.info(f"'{self.name}' erhält {amount} XP. Aktuelle XP: {self.current_xp}/{self.xp_to_next_level}")
        try:
            from src.game_logic import leveling
            while self.is_alive() and self.current_xp >= self.xp_to_next_level:
                logger.info(f"LEVEL UP VORBEREITUNG für '{self.name}'! XP: {self.current_xp}/{self.xp_to_next_level}, Level: {self.level}")
                leveling.handle_level_up(self)
                logger.info(f"LEVEL UP für '{self.name}'! Neues Level: {self.level}. XP: {self.current_xp}/{self.xp_to_next_level}")
        except ImportError: logger.error("Modul 'leveling' konnte nicht für gain_xp importiert werden.")
        except Exception as e: logger.error(f"Fehler im Level-Up Prozess für '{self.name}': {e}", exc_info=True)

    def __repr__(self) -> str:
        status = "Alive" if self.is_alive() else "Defeated"
        active_effects_str = ', '.join([f"{e.effect_id}({e.duration})" for e in self.active_status_effects]) # Zeige auch Dauer an
        if not active_effects_str: active_effects_str = "None"
        return (f"<CharacterInstance(name='{self.name}', Lvl={self.level}, XP={self.current_xp}/{self.xp_to_next_level}, "
                f"HP={self.current_hp}/{self.max_hp}, Mana={self.current_mana}/{self.max_mana}, "
                f"Stamina={self.current_stamina}/{self.max_stamina}, Energy={self.current_energy}/{self.max_energy}, "
                f"Effects=[{active_effects_str}], Status={status})>")

# --- Testblock (Assertions korrigiert) ---
if __name__ == '__main__':
    try:
        from src.utils.logging_setup import setup_logging
        setup_logging()
    except ImportError: print("WARNUNG: Logging für entities.py Test nicht gefunden.")
    print("\n--- CharacterInstance Test (inkl. Status Effects) ---")
    try:
        import sys
        from pathlib import Path
        project_root_for_test = Path(__file__).parent.parent.parent
        if str(project_root_for_test) not in sys.path: sys.path.insert(0, str(project_root_for_test))
        from src.definitions import loader

        krieger_def = loader.get_character_class("krieger")
        if not krieger_def: print("FEHLER: Krieger-Def nicht geladen.")
        else:
            krieger_inst = CharacterInstance(krieger_def)
            print(f"\nInitial: {krieger_inst}")
            burning_data = {"id": "BURNING", "duration": 3, "potency": 5}
            stunned_data = {"id": "STUNNED", "duration": 1}
            print("\nFüge Effekte hinzu:")
            krieger_inst.add_status_effect(burning_data, "Magier1")
            print(f"Nach BURNING: {krieger_inst}")
            assert krieger_inst.has_status_effect("BURNING")
            krieger_inst.add_status_effect(stunned_data)
            print(f"Nach STUNNED: {krieger_inst}")
            assert krieger_inst.has_status_effect("STUNNED")
            print("\nFüge BURNING erneut hinzu (längere Dauer, Potenz 6):")
            burning_data_refresh = {"id": "BURNING", "duration": 4, "potency": 6}
            krieger_inst.add_status_effect(burning_data_refresh, "Magier2")
            print(f"Nach BURNING Refresh: {krieger_inst}")
            refreshed_burn = next((e for e in krieger_inst.active_status_effects if e.effect_id == "BURNING"), None)
            assert refreshed_burn is not None and refreshed_burn.duration == 4 and refreshed_burn.potency == 6

            print("\nTicke Effekte (Runde 1):")
            initial_hp_tick1 = krieger_inst.current_hp
            krieger_inst.tick_status_effects() # BURNING (6 dmg) tickt, Dauer -> 3; STUNNED tickt, Dauer -> 0 -> wird entfernt
            print(f"Nach Tick 1: {krieger_inst}")
            assert krieger_inst.current_hp == initial_hp_tick1 - 6, f"Assertion failed: HP after tick 1 should be {initial_hp_tick1 - 6}, but was {krieger_inst.current_hp}"
            assert krieger_inst.has_status_effect("BURNING") # BURNING noch aktiv
            # KORRIGIERTE ASSERTION: STUNNED sollte weg sein
            assert not krieger_inst.has_status_effect("STUNNED"), "STUNNED effect should be removed after tick 1"
            # Prüfe Dauer von Burning
            burning_eff_after_tick1 = next((e for e in krieger_inst.active_status_effects if e.effect_id == "BURNING"), None)
            assert burning_eff_after_tick1 is not None and burning_eff_after_tick1.duration == 3, f"BURNING duration should be 3 after tick 1, was {burning_eff_after_tick1.duration if burning_eff_after_tick1 else 'None'}"


            print("\nTicke Effekte (Runde 2):")
            initial_hp_tick2 = krieger_inst.current_hp
            krieger_inst.tick_status_effects() # BURNING (6 dmg) tickt, Dauer -> 2
            print(f"Nach Tick 2: {krieger_inst}")
            assert krieger_inst.current_hp == initial_hp_tick2 - 6, f"Assertion failed: HP after tick 2 should be {initial_hp_tick2 - 6}, but was {krieger_inst.current_hp}"
            assert krieger_inst.has_status_effect("BURNING") # BURNING noch aktiv
            burning_eff_after_tick2 = next((e for e in krieger_inst.active_status_effects if e.effect_id == "BURNING"), None)
            assert burning_eff_after_tick2 is not None and burning_eff_after_tick2.duration == 2, f"BURNING duration should be 2 after tick 2, was {burning_eff_after_tick2.duration if burning_eff_after_tick2 else 'None'}"


            print("\nEntferne BURNING manuell:")
            krieger_inst.remove_status_effect("BURNING")
            print(f"Nach Entfernen: {krieger_inst}")
            assert not krieger_inst.has_status_effect("BURNING")
            print("\nAlle Entity-Effekt-Tests erfolgreich.")

    except Exception as e:
        logger.error(f"Fehler im CharacterInstance Effekt Testblock: {e}", exc_info=True)
        print(f"FEHLER im Test: {e}")

    # Dummy Aufräumen (keine Änderung hier)
    import sys, pathlib
    project_root_for_test = pathlib.Path(__file__).parent.parent.parent
    leveling_py_path = project_root_for_test / "src" / "game_logic" / "leveling.py"
    if 'temp_leveling_created' in locals() and locals()['temp_leveling_created'] and leveling_py_path.exists():
        print(f"INFO: Entferne temporäre Dummy-Datei {leveling_py_path}.")
        leveling_py_path.unlink()

