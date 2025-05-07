import typing
import logging
import math # Import math für floor/ceil falls benötigt

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
        con = self.get_attribute('CON', base_value=True) # Nehme Basiswert für HP-Berechnung
        self.max_hp: int = calculate_max_hp(base_hp, con)
        self.current_hp: int = self.max_hp
        self.max_mana: int = self.definition.get_combat_value('base_mana')
        self.current_mana: int = self.max_mana
        self.max_stamina: int = self.definition.get_combat_value('base_stamina')
        self.current_stamina: int = self.max_stamina
        self.max_energy: int = self.definition.get_combat_value('base_energy')
        self.current_energy: int = self.max_energy
        self.armor: int = self.definition.get_combat_value('armor') # Basis-Rüstung
        self.magic_resist: int = self.definition.get_combat_value('magic_resist') # Basis-Magieresistenz
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
        except ImportError: logger.error("Modul 'leveling' konnte nicht importiert werden."); return 100 * level_to_calculate_for

    # --- Status Effect Management (Methoden add, remove, has bleiben gleich) ---
    def add_status_effect(self, effect_data: typing.Dict[str, typing.Any], source_entity_id: typing.Optional[str] = None):
        # ... (Code wie zuvor) ...
        try: from src.game_logic.effects import StatusEffect
        except ImportError: logger.error("Kann StatusEffect Klasse nicht importieren in add_status_effect."); return
        effect_id = effect_data.get("id"); duration = effect_data.get("duration"); potency = effect_data.get("potency")
        if not effect_id or duration is None: logger.warning(f"Ungültige Status-Effekt-Daten: {effect_data}"); return
        existing_effect: typing.Optional[StatusEffect] = next((eff for eff in self.active_status_effects if eff.effect_id == effect_id), None)
        if existing_effect:
            old_duration = existing_effect.duration; existing_effect.duration = max(existing_effect.duration, int(duration))
            if potency is not None: existing_effect.potency = potency
            existing_effect.source_entity_id = source_entity_id; existing_effect.applied_effect_data = effect_data
            logger.info(f"Status-Effekt '{effect_id}' auf '{self.name}' aktualisiert. Dauer: {old_duration} -> {existing_effect.duration}, Potenz: {existing_effect.potency}")
        else:
            new_effect = StatusEffect(effect_id=effect_id, duration=int(duration), potency=potency, source_entity_id=source_entity_id, applied_effect_data=effect_data)
            self.active_status_effects.append(new_effect)
            logger.info(f"Status-Effekt '{effect_id}' auf '{self.name}' angewendet. Dauer: {new_effect.duration}, Potenz: {new_effect.potency}")

    def remove_status_effect(self, effect_id_to_remove: str):
        # ... (Code wie zuvor) ...
        initial_len = len(self.active_status_effects); self.active_status_effects = [eff for eff in self.active_status_effects if eff.effect_id != effect_id_to_remove]
        if len(self.active_status_effects) < initial_len: logger.info(f"Status-Effekt '{effect_id_to_remove}' von '{self.name}' entfernt.")

    def tick_status_effects(self):
        """Verarbeitet Effekte für eine Runde (DoT, Dauerreduktion, Entfernung)."""
        if not self.is_alive(): return
        try: from src.game_logic.effects import StatusEffect
        except ImportError: logger.error("Kann StatusEffect nicht importieren in tick_status_effects."); return
        logger.debug(f"Ticke Status-Effekte für '{self.name}'...")
        expired_effect_ids = []
        effects_to_process = list(self.active_status_effects)
        for effect in effects_to_process:
            # 1. Effekt-Wirkung anwenden (z.B. Schaden über Zeit)
            if effect.effect_id == "BURNING":
                damage = int(effect.potency) if effect.potency is not None else 1
                logger.info(f"'{self.name}' erleidet {damage} Schaden durch '{effect.effect_id}'.")
                self.take_damage(damage) # Ruft take_damage auf
                if not self.is_alive(): break # Bearbeitung stoppen, wenn Charakter stirbt
            # TODO: Hier weitere DoT/HoT Effekte implementieren

            # 2. Dauer verringern und prüfen, ob abgelaufen
            if effect.tick(): # tick() reduziert Dauer und gibt True zurück, wenn abgelaufen
                expired_effect_ids.append(effect.effect_id)
                logger.info(f"Status-Effekt '{effect.effect_id}' auf '{self.name}' ist abgelaufen.")
        # 3. Abgelaufene Effekte entfernen
        if expired_effect_ids:
            self.active_status_effects = [eff for eff in self.active_status_effects if eff.effect_id not in expired_effect_ids]
            logger.debug(f"Abgelaufene Effekte entfernt für '{self.name}': {expired_effect_ids}")

    def has_status_effect(self, effect_id: str) -> bool:
        return any(eff.effect_id == effect_id for eff in self.active_status_effects)

    # --- Attribute & Werte unter Berücksichtigung von Effekten ---
    def get_attribute(self, attr_name: str, base_value: bool = False) -> int:
        """Gibt den aktuellen Wert eines Attributs zurück, optional modifiziert durch Effekte."""
        attr_upper = attr_name.upper()
        base_val = self.attributes.get(attr_upper, 0)
        if base_value:
            return base_val

        # Modifikatoren durch Effekte anwenden
        modified_val = base_val
        modifier = 0
        for effect in self.active_status_effects:
            # Beispielhafte Logik für Effekte, die Attribute direkt ändern
            if effect.effect_id == "WEAKENED" and attr_upper == "STR":
                # Potenz ist hier die Reduktion (z.B. 3 in skills.json5 -> -3)
                modifier -= int(effect.potency) if effect.potency is not None else 1
            # TODO: Hier weitere Attribut-Modifikatoren hinzufügen (z.B. STRENGTH_UP etc.)

        modified_val += modifier
        # Optional: Mindestwert für Attribute? (z.B. 1)
        # modified_val = max(1, modified_val)

        if modifier != 0:
             logger.debug(f"Attribut '{attr_upper}' für '{self.name}': Basis={base_val}, Mod={modifier} -> Final={modified_val}")

        return modified_val

    def get_attribute_bonus(self, attr_name: str) -> int:
        """Berechnet den Bonus für das aktuelle (ggf. modifizierte) Attribut."""
        return calculate_attribute_bonus(self.get_attribute(attr_name)) # Nutzt das potenziell modifizierte Attribut

    def get_current_armor(self) -> int:
        """Gibt den aktuellen Rüstungswert zurück, modifiziert durch Effekte."""
        base_armor = self.armor
        modifier = 0
        for effect in self.active_status_effects:
            if effect.effect_id == "DEFENSE_UP":
                 modifier += int(effect.potency) if effect.potency is not None else 1
            # TODO: DEFENSE_DOWN etc. hinzufügen
        final_armor = max(0, base_armor + modifier) # Rüstung kann nicht negativ sein
        if modifier != 0: logger.debug(f"Rüstung für '{self.name}': Basis={base_armor}, Mod={modifier} -> Final={final_armor}")
        return final_armor

    def get_current_magic_resist(self) -> int:
        """Gibt den aktuellen Magieresistenzwert zurück, modifiziert durch Effekte."""
        base_mr = self.magic_resist
        modifier = 0
        for effect in self.active_status_effects:
            if effect.effect_id == "DEFENSE_UP": # DEFENSE_UP wirkt auf beides
                 modifier += int(effect.potency) if effect.potency is not None else 1
            # TODO: MAGIC_RESIST_DOWN etc. hinzufügen
        final_mr = max(0, base_mr + modifier)
        if modifier != 0: logger.debug(f"MagRes für '{self.name}': Basis={base_mr}, Mod={modifier} -> Final={final_mr}")
        return final_mr

    def get_current_accuracy_modifier(self) -> int:
        """Gibt den Modifikator für Genauigkeit zurück (basiert auf DEX-Bonus), modifiziert durch Effekte."""
        base_dex_bonus = self.get_attribute_bonus('DEX')
        modifier = 0
        for effect in self.active_status_effects:
             if effect.effect_id == "ACCURACY_DOWN":
                  modifier -= int(effect.potency) if effect.potency is not None else 1
             # TODO: ACCURACY_UP etc.
        final_mod = base_dex_bonus + modifier
        if modifier != 0: logger.debug(f"GenauigkeitsMod für '{self.name}': Basis={base_dex_bonus}, Mod={modifier} -> Final={final_mod}")
        return final_mod

    def get_current_evasion_modifier(self) -> int:
        """Gibt den Modifikator für Ausweichen zurück (basiert auf DEX-Bonus), modifiziert durch Effekte."""
        base_dex_bonus = self.get_attribute_bonus('DEX')
        modifier = 0
        for effect in self.active_status_effects:
             if effect.effect_id == "SLOWED":
                  modifier -= int(effect.potency) if effect.potency is not None else 1
             # TODO: EVASION_UP etc.
        final_mod = base_dex_bonus + modifier
        if modifier != 0: logger.debug(f"AusweichMod für '{self.name}': Basis={base_dex_bonus}, Mod={modifier} -> Final={final_mod}")
        return final_mod

    # --- Ressourcen & Lebensstatus Methoden (korrekt formatiert) ---
    def get_current_resource(self, rt: str) -> int: rt=rt.upper(); return self.current_mana if rt=="MANA" else self.current_stamina if rt=="STAMINA" else self.current_energy if rt=="ENERGY" else 9999 if rt=="NONE" or rt=="" else 0
    def can_afford_cost(self, rt: str, a: int) -> bool: return True if a<=0 or rt.upper()=="NONE" else self.get_current_resource(rt) >= a
    def pay_cost(self, rt: str, a: int) -> bool: # ... (Code wie zuvor) ...
        if a <= 0 or rt.upper() == "NONE": return True
        if not self.can_afford_cost(rt, a): logger.warning(f"'{self.name}' kann Kosten von {a} {rt} nicht bezahlen."); return False
        res_type = rt.upper(); paid = False
        if res_type == "MANA": self.current_mana -= a; paid = True
        elif res_type == "STAMINA": self.current_stamina -= a; paid = True
        elif res_type == "ENERGY": self.current_energy -= a; paid = True
        if paid: logger.info(f"'{self.name}' bezahlt {a} {res_type}. Neuer Stand: {self.get_current_resource(res_type)}"); return True
        else: logger.error(f"Kosten konnten nicht bezahlt werden für Ressource '{res_type}'."); return False
    def take_damage(self, amount: int): # ... (Code wie zuvor) ...
        if amount <= 0 or not self.is_alive_flag: return
        self.current_hp -= amount
        logger.info(f"'{self.name}' erleidet {amount} Schaden. HP: {self.current_hp}/{self.max_hp}")
        if self.current_hp <= 0: self.current_hp = 0; self.is_alive_flag = False; logger.info(f"'{self.name}' wurde besiegt!")
    def heal(self, amount: int): # ... (Code wie zuvor) ...
        if amount <= 0 or not self.is_alive_flag: return
        heal_applied = min(amount, self.max_hp - self.current_hp)
        if heal_applied > 0: self.current_hp += heal_applied; logger.info(f"'{self.name}' wird um {heal_applied} HP geheilt. HP: {self.current_hp}/{self.max_hp}")
    def is_alive(self) -> bool: return self.is_alive_flag

    # --- Aktionsfähigkeit ---
    def can_act(self) -> bool:
        """Prüft, ob der Charakter aktuell handeln kann (z.B. nicht betäubt ist)."""
        if not self.is_alive():
            return False
        if self.has_status_effect("STUNNED"):
            logger.info(f"'{self.name}' kann nicht handeln (STUNNED).")
            return False
        # TODO: Hier andere Effekte prüfen, die Handlungen verhindern (z.B. SLEEP, FEAR)
        return True

    # --- XP & Leveling Methoden (korrekt formatiert) ---
    def gain_xp(self, amount: int): # ... (Code wie zuvor) ...
        if amount <= 0 or not self.is_alive(): return
        self.current_xp += amount; logger.info(f"'{self.name}' erhält {amount} XP. Aktuelle XP: {self.current_xp}/{self.xp_to_next_level}")
        try:
            from src.game_logic import leveling
            while self.is_alive() and self.current_xp >= self.xp_to_next_level:
                logger.info(f"LEVEL UP VORBEREITUNG für '{self.name}'! XP: {self.current_xp}/{self.xp_to_next_level}, Level: {self.level}")
                leveling.handle_level_up(self); logger.info(f"LEVEL UP für '{self.name}'! Neues Level: {self.level}. XP: {self.current_xp}/{self.xp_to_next_level}")
        except ImportError: logger.error("Modul 'leveling' konnte nicht für gain_xp importiert werden.")
        except Exception as e: logger.error(f"Fehler im Level-Up Prozess für '{self.name}': {e}", exc_info=True)

    def __repr__(self) -> str: # ... (Code wie zuvor) ...
        status = "Alive" if self.is_alive() else "Defeated"; active_effects_str = ', '.join([f"{e.effect_id}({e.duration})" for e in self.active_status_effects]);
        if not active_effects_str: active_effects_str = "None"
        return (f"<CharacterInstance(name='{self.name}', Lvl={self.level}, XP={self.current_xp}/{self.xp_to_next_level}, "
                f"HP={self.current_hp}/{self.max_hp}, Mana={self.current_mana}/{self.max_mana}, Stamina={self.current_stamina}/{self.max_stamina}, Energy={self.current_energy}/{self.max_energy}, "
                f"Effects=[{active_effects_str}], Status={status})>")

# --- Testblock (Erweitert für neue Methoden) ---
if __name__ == '__main__':
    try:
        from src.utils.logging_setup import setup_logging; setup_logging()
    except ImportError: print("WARNUNG: Logging für entities.py Test nicht gefunden.")
    print("\n--- CharacterInstance Test (inkl. Effekt-Auswirkungen) ---")
    try:
        import sys; from pathlib import Path
        project_root_for_test = Path(__file__).parent.parent.parent
        if str(project_root_for_test) not in sys.path: sys.path.insert(0, str(project_root_for_test))
        from src.definitions import loader

        krieger_def = loader.get_character_class("krieger") # Armor 5, MR 1, STR 14, DEX 10 (Bonus 0)
        kleriker_def = loader.get_character_class("kleriker") # Armor 4, MR 3
        schurke_def = loader.get_character_class("schurke") # DEX 14 (Bonus +2)

        if not all([krieger_def, kleriker_def, schurke_def]): print("FEHLER: Definitionen nicht geladen.")
        else:
            krieger_inst = CharacterInstance(krieger_def)
            kleriker_inst = CharacterInstance(kleriker_def)
            schurke_inst = CharacterInstance(schurke_def)
            print(f"\nInitial: {krieger_inst}")
            print(f"Initial: {kleriker_inst}")
            print(f"Initial: {schurke_inst}")

            # Test DEFENSE_UP (vom Kleriker Skill 'protective_ward', Potency 3)
            defense_up_data = {"id": "DEFENSE_UP", "duration": 3, "potency": 3}
            print("\nTest DEFENSE_UP:")
            krieger_inst.add_status_effect(defense_up_data)
            print(f"Krieger nach DEFENSE_UP: {krieger_inst}")
            assert krieger_inst.get_current_armor() == krieger_def.combat_values['armor'] + 3 # 5 + 3 = 8
            assert krieger_inst.get_current_magic_resist() == krieger_def.combat_values['magic_resist'] + 3 # 1 + 3 = 4
            print(f"  -> Aktuelle Rüstung: {krieger_inst.get_current_armor()} (Basis: {krieger_inst.armor})")
            print(f"  -> Aktuelle MagRes: {krieger_inst.get_current_magic_resist()} (Basis: {krieger_inst.magic_resist})")
            krieger_inst.remove_status_effect("DEFENSE_UP") # Aufräumen für nächsten Test
            assert krieger_inst.get_current_armor() == krieger_def.combat_values['armor'] # Sollte wieder Basis sein

            # Test SLOWED (vom Magier Skill 'frostbolt', Potency 2)
            slowed_data = {"id": "SLOWED", "duration": 1, "potency": 2} # Reduziert Evasion Mod um 2
            print("\nTest SLOWED (auf Schurke):")
            schurke_basis_evasion_mod = schurke_inst.get_attribute_bonus('DEX') # Schurke DEX 14 -> Bonus +2
            schurke_inst.add_status_effect(slowed_data)
            print(f"Schurke nach SLOWED: {schurke_inst}")
            assert schurke_inst.get_current_evasion_modifier() == schurke_basis_evasion_mod - 2 # 2 - 2 = 0
            print(f"  -> Aktueller Evasion Mod: {schurke_inst.get_current_evasion_modifier()} (Basis DEX Bonus: {schurke_basis_evasion_mod})")
            schurke_inst.tick_status_effects() # Dauer war nur 1 Runde
            assert not schurke_inst.has_status_effect("SLOWED")
            assert schurke_inst.get_current_evasion_modifier() == schurke_basis_evasion_mod # Sollte wieder Basis sein

            # Test STUNNED (vom Krieger Skill 'shield_bash', Dauer 1)
            stunned_data = {"id": "STUNNED", "duration": 1}
            print("\nTest STUNNED:")
            krieger_inst.add_status_effect(stunned_data)
            print(f"Krieger nach STUNNED: {krieger_inst}")
            assert not krieger_inst.can_act(), "Krieger sollte wegen STUNNED nicht handeln können."
            print(f"  -> Kann handeln? {krieger_inst.can_act()}")
            krieger_inst.tick_status_effects() # Tick entfernt STUNNED
            assert krieger_inst.can_act(), "Krieger sollte nach Ablauf von STUNNED wieder handeln können."
            print(f"  -> Kann nach Tick handeln? {krieger_inst.can_act()}")

            # Test WEAKENED (vom Goblin-Schamanen Skill 'weakening_curse', Potency 3)
            weakened_data = {"id": "WEAKENED", "duration": 3, "potency": 3} # Reduziert STR um 3
            print("\nTest WEAKENED:")
            krieger_basis_str = krieger_inst.get_attribute('STR', base_value=True) # Krieger STR 14
            krieger_basis_str_bonus = krieger_inst.get_attribute_bonus('STR') # Sollte +2 sein
            krieger_inst.add_status_effect(weakened_data)
            print(f"Krieger nach WEAKENED: {krieger_inst}")
            assert krieger_inst.get_attribute('STR') == krieger_basis_str - 3 # 14 - 3 = 11
            assert krieger_inst.get_attribute_bonus('STR') == 0 # Bonus von 11 STR ist 0
            print(f"  -> Aktuelle STR: {krieger_inst.get_attribute('STR')} (Basis: {krieger_basis_str})")
            print(f"  -> Aktueller STR Bonus: {krieger_inst.get_attribute_bonus('STR')} (Basis Bonus: {krieger_basis_str_bonus})")
            krieger_inst.remove_status_effect("WEAKENED")
            assert krieger_inst.get_attribute('STR') == krieger_basis_str

            print("\nAlle Entity-Effekt-Auswirkungs-Tests erfolgreich.")

    except Exception as e:
        logger.error(f"Fehler im CharacterInstance Effekt Testblock: {e}", exc_info=True)
        print(f"FEHLER im Test: {e}")

    # Dummy Aufräumen
    import sys, pathlib
    project_root_for_test = pathlib.Path(__file__).parent.parent.parent
    leveling_py_path = project_root_for_test / "src" / "game_logic" / "leveling.py"
    if 'temp_leveling_created' in locals() and locals()['temp_leveling_created'] and leveling_py_path.exists():
        print(f"INFO: Entferne temporäre Dummy-Datei {leveling_py_path}.")
        leveling_py_path.unlink()

