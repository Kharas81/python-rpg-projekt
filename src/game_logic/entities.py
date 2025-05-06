import typing
import logging

# Importiere die Basis-Definition und den Loader
try:
    from src.definitions.character import Character as CharacterDefinition
    from src.definitions import loader
    from src.game_logic.formulas import calculate_max_hp, calculate_attribute_bonus
    from src.config import config
    # Importiere StatusEffect für Type Hinting und Methoden
    if typing.TYPE_CHECKING:
        from src.game_logic.effects import StatusEffect
    # Dynamischer Import für Methoden, um Lade-Probleme zu vermeiden
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
        # Verwende jetzt eine Liste von StatusEffect-Objekten
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
        """
        Fügt einen neuen Status-Effekt hinzu oder aktualisiert die Dauer eines vorhandenen.

        Args:
            effect_data: Das Dictionary aus skill.applies_effects (muss 'id' und 'duration' enthalten).
            source_entity_id: Optionale ID der Quelle des Effekts.
        """
        try:
            # Importiere StatusEffect hier, um Abhängigkeiten beim Modul-Laden zu reduzieren
            from src.game_logic.effects import StatusEffect
        except ImportError:
            logger.error("Kann StatusEffect Klasse nicht importieren in add_status_effect.")
            return

        effect_id = effect_data.get("id")
        duration = effect_data.get("duration")
        potency = effect_data.get("potency") # Kann None sein

        if not effect_id or duration is None:
            logger.warning(f"Ungültige Status-Effekt-Daten erhalten: {effect_data}")
            return

        # Prüfe, ob ein Effekt mit derselben ID bereits existiert
        existing_effect: typing.Optional[StatusEffect] = None
        for effect in self.active_status_effects:
            if effect.effect_id == effect_id:
                existing_effect = effect
                break

        if existing_effect:
            # Effekt existiert: Dauer aktualisieren (Maximum aus alter und neuer Dauer)
            # TODO: Stacking-Regeln könnten komplexer sein (z.B. Potenz addieren?)
            old_duration = existing_effect.duration
            existing_effect.duration = max(existing_effect.duration, int(duration))
            # Optional: Potenz aktualisieren, wenn die neue höher ist? Oder überschreiben?
            if potency is not None:
                 existing_effect.potency = potency # Überschreiben für den Moment
            existing_effect.source_entity_id = source_entity_id # Quelle aktualisieren
            existing_effect.applied_effect_data = effect_data # Daten aktualisieren

            logger.info(f"Status-Effekt '{effect_id}' auf '{self.name}' aktualisiert. "
                        f"Dauer: {old_duration} -> {existing_effect.duration}, Potenz: {existing_effect.potency}")
        else:
            # Effekt existiert nicht: Neu hinzufügen
            new_effect = StatusEffect(
                effect_id=effect_id,
                duration=int(duration),
                potency=potency,
                source_entity_id=source_entity_id,
                applied_effect_data=effect_data
            )
            self.active_status_effects.append(new_effect)
            logger.info(f"Status-Effekt '{effect_id}' auf '{self.name}' angewendet. "
                        f"Dauer: {new_effect.duration}, Potenz: {new_effect.potency}")

    def remove_status_effect(self, effect_id_to_remove: str):
        """Entfernt einen Status-Effekt anhand seiner ID."""
        initial_len = len(self.active_status_effects)
        # Erstelle neue Liste ohne den zu entfernenden Effekt
        self.active_status_effects = [eff for eff in self.active_status_effects if eff.effect_id != effect_id_to_remove]
        if len(self.active_status_effects) < initial_len:
            logger.info(f"Status-Effekt '{effect_id_to_remove}' von '{self.name}' entfernt.")
        else:
            logger.debug(f"Versucht, Status-Effekt '{effect_id_to_remove}' zu entfernen, aber nicht gefunden bei '{self.name}'.")


    def tick_status_effects(self):
        """
        Verarbeitet alle aktiven Status-Effekte für eine Runde/Tick.
        - Wendet Effekte an (z.B. Schaden über Zeit).
        - Verringert die Dauer.
        - Entfernt abgelaufene Effekte.
        """
        if not self.is_alive(): # Besiegte Charaktere ticken keine Effekte mehr? Oder doch? (z.B. für Wiederbelebung)
             return # Vorerst nicht

        # Importiere StatusEffect hier, um Abhängigkeiten beim Modul-Laden zu reduzieren
        try: from src.game_logic.effects import StatusEffect
        except ImportError: logger.error("Kann StatusEffect nicht importieren in tick_status_effects."); return

        logger.debug(f"Ticke Status-Effekte für '{self.name}'...")
        expired_effect_ids = []
        effects_to_process = list(self.active_status_effects) # Kopie erstellen, falls Liste während Iteration geändert wird

        for effect in effects_to_process:
            # 1. Effekt-Wirkung anwenden (TODO: Hier Logik für verschiedene Effekte einfügen)
            if effect.effect_id == "BURNING":
                damage = int(effect.potency) if effect.potency is not None else 1
                logger.info(f"'{self.name}' erleidet {damage} Schaden durch '{effect.effect_id}'.")
                self.take_damage(damage) # Direkter Schaden, ignoriert Rüstung? Oder sollte es eine Schadensart geben?
                if not self.is_alive(): break # Bearbeitung stoppen, wenn Charakter stirbt

            # TODO: Andere Effekte wie HEALING_OVER_TIME, STAT_MODIFICATION etc. hier behandeln

            # 2. Dauer verringern und prüfen, ob abgelaufen
            if effect.tick(): # tick() gibt True zurück, wenn Dauer <= 0
                expired_effect_ids.append(effect.effect_id)
                logger.info(f"Status-Effekt '{effect.effect_id}' auf '{self.name}' ist abgelaufen.")

        # 3. Abgelaufene Effekte entfernen (nachdem alle Effekte für diesen Tick angewendet wurden)
        if expired_effect_ids:
            # Erstelle neue Liste ohne die abgelaufenen Effekte
            self.active_status_effects = [eff for eff in self.active_status_effects if eff.effect_id not in expired_effect_ids]
            logger.debug(f"Abgelaufene Effekte entfernt für '{self.name}': {expired_effect_ids}")


    def has_status_effect(self, effect_id: str) -> bool:
        """Prüft, ob ein bestimmter Status-Effekt aktiv ist."""
        return any(eff.effect_id == effect_id for eff in self.active_status_effects)


    # --- Bestehende Methoden (gekürzt zur Übersicht) ---
    def get_attribute(self, attr_name: str, base_value: bool = False) -> int:
        # TODO: Hier Status-Effekte berücksichtigen, die Attribute modifizieren
        base_val = self.attributes.get(attr_name.upper(), 0)
        if base_value: return base_val
        modified_val = base_val # Platzhalter
        # Beispiel: if self.has_status_effect("WEAKENED") and attr_name.upper() == "STR": modified_val -= potency
        return modified_val
    def get_attribute_bonus(self, attr_name: str) -> int: return calculate_attribute_bonus(self.get_attribute(attr_name))
    def get_current_resource(self, rt: str) -> int: rt=rt.upper(); return self.current_mana if rt=="MANA" else self.current_stamina if rt=="STAMINA" else self.current_energy if rt=="ENERGY" else 9999 if rt=="NONE" or rt=="" else 0
    def can_afford_cost(self, rt: str, a: int) -> bool: return True if a==0 or rt.upper()=="NONE" else self.get_current_resource(rt) >= a
    def pay_cost(self, rt: str, a: int) -> bool: # ... (Implementierung wie zuvor) ...
        if not self.can_afford_cost(rt, a): return False; rt=rt.upper(); paid=False; # ... (Rest wie gehabt)
        if a==0 or rt=="NONE": return True
        if rt=="MANA": self.current_mana-=a; paid=True
        elif rt=="STAMINA": self.current_stamina-=a; paid=True
        elif rt=="ENERGY": self.current_energy-=a; paid=True
        if paid: logger.info(f"'{self.name}' bezahlt {a} {rt}. Neuer Stand: {self.get_current_resource(rt)}")
        return paid
    def take_damage(self, a: int): # ... (Implementierung wie zuvor) ...
        if a<=0 or not self.is_alive_flag:return;self.current_hp-=a;logger.info(f"'{self.name}' erleidet {a} Schaden. HP: {self.current_hp}/{self.max_hp}");if self.current_hp<=0:self.current_hp=0;self.is_alive_flag=False;logger.info(f"'{self.name}' wurde besiegt!")
    def heal(self, a: int): # ... (Implementierung wie zuvor) ...
        if a<=0 or not self.is_alive_flag:return;ha=min(a,self.max_hp-self.current_hp);if ha>0:self.current_hp+=ha;logger.info(f"'{self.name}' wird um {ha} HP geheilt. HP: {self.current_hp}/{self.max_hp}")
    def is_alive(self) -> bool: return self.is_alive_flag
    def gain_xp(self, a: int): # ... (Implementierung wie zuvor) ...
        if a<=0 or not self.is_alive():return;self.current_xp+=a;logger.info(f"'{self.name}' erhält {a} XP. Aktuelle XP: {self.current_xp}/{self.xp_to_next_level}"); #... (Rest wie gehabt)
        try:
            from src.game_logic import leveling
            while self.is_alive() and self.current_xp >= self.xp_to_next_level:
                # ... (Level-Up Logik wie gehabt) ...
                leveling.handle_level_up(self)
        except ImportError: logger.error("Modul 'leveling' konnte nicht für gain_xp importiert werden.")
        except Exception as e: logger.error(f"Fehler im Level-Up Prozess für '{self.name}': {e}", exc_info=True)


    def __repr__(self) -> str:
        status = "Alive" if self.is_alive() else "Defeated"
        active_effects_str = ', '.join([e.effect_id for e in self.active_status_effects])
        if not active_effects_str: active_effects_str = "None"
        return (f"<CharacterInstance(name='{self.name}', Lvl={self.level}, XP={self.current_xp}/{self.xp_to_next_level}, "
                f"HP={self.current_hp}/{self.max_hp}, Mana={self.current_mana}/{self.max_mana}, "
                f"Stamina={self.current_stamina}/{self.max_stamina}, Energy={self.current_energy}/{self.max_energy}, "
                f"Effects=[{active_effects_str}], Status={status})>")

# --- Testblock ---
if __name__ == '__main__':
    try:
        from src.utils.logging_setup import setup_logging
        setup_logging()
    except ImportError: print("WARNUNG: Logging für entities.py Test nicht gefunden.")
    print("\n--- CharacterInstance Test (inkl. Status Effects) ---")
    try:
        krieger_def = loader.get_character_class("krieger")
        if not krieger_def: print("FEHLER: Krieger-Def nicht geladen.")
        else:
            krieger_inst = CharacterInstance(krieger_def)
            print(f"\nInitial: {krieger_inst}")

            # Definiere Test-Effekt-Daten
            burning_data = {"id": "BURNING", "duration": 3, "potency": 5}
            stunned_data = {"id": "STUNNED", "duration": 1}
            weakened_data = {"id": "WEAKENED", "duration": 2, "potency": -3} # z.B. -3 STR

            # Füge Effekte hinzu
            print("\nFüge Effekte hinzu:")
            krieger_inst.add_status_effect(burning_data, "Magier1")
            print(f"Nach BURNING: {krieger_inst}")
            assert krieger_inst.has_status_effect("BURNING")

            krieger_inst.add_status_effect(stunned_data)
            print(f"Nach STUNNED: {krieger_inst}")
            assert krieger_inst.has_status_effect("STUNNED")

            # Teste Refresh/Überschreiben
            print("\nFüge BURNING erneut hinzu (längere Dauer):")
            burning_data_refresh = {"id": "BURNING", "duration": 4, "potency": 6} # Neue Potenz
            krieger_inst.add_status_effect(burning_data_refresh, "Magier2")
            print(f"Nach BURNING Refresh: {krieger_inst}")
            # Finde den Effekt und prüfe Dauer/Potenz
            refreshed_burn = next((e for e in krieger_inst.active_status_effects if e.effect_id == "BURNING"), None)
            assert refreshed_burn is not None
            assert refreshed_burn.duration == 4, f"Falsche Dauer nach Refresh: {refreshed_burn.duration}"
            assert refreshed_burn.potency == 6, f"Falsche Potenz nach Refresh: {refreshed_burn.potency}"


            print("\nTicke Effekte (Runde 1):")
            initial_hp_tick1 = krieger_inst.current_hp
            krieger_inst.tick_status_effects() # BURNING tickt (5 Schaden), Dauer sinkt
            print(f"Nach Tick 1: {krieger_inst}")
            assert krieger_inst.current_hp == initial_hp_tick1 - 5 # 5 Schaden durch Burning
            assert krieger_inst.has_status_effect("BURNING") # Noch aktiv
            assert krieger_inst.has_status_effect("STUNNED") # Noch aktiv
            refreshed_burn = next((e for e in krieger_inst.active_status_effects if e.effect_id == "BURNING"), None)
            stunned_eff = next((e for e in krieger_inst.active_status_effects if e.effect_id == "STUNNED"), None)
            assert refreshed_burn.duration == 3
            assert stunned_eff.duration == 0 # STUNNED läuft nach 1 Tick ab

            print("\nTicke Effekte (Runde 2):")
            initial_hp_tick2 = krieger_inst.current_hp
            krieger_inst.tick_status_effects() # BURNING tickt (5 Schaden), Dauer sinkt, STUNNED wird entfernt
            print(f"Nach Tick 2: {krieger_inst}")
            assert krieger_inst.current_hp == initial_hp_tick2 - 5 # 5 Schaden durch Burning
            assert not krieger_inst.has_status_effect("STUNNED") # STUNNED sollte weg sein
            refreshed_burn = next((e for e in krieger_inst.active_status_effects if e.effect_id == "BURNING"), None)
            assert refreshed_burn.duration == 2

            print("\nEntferne BURNING manuell:")
            krieger_inst.remove_status_effect("BURNING")
            print(f"Nach Entfernen: {krieger_inst}")
            assert not krieger_inst.has_status_effect("BURNING")


            print("\nAlle Entity-Effekt-Tests erfolgreich.")

    except Exception as e:
        logger.error(f"Fehler im CharacterInstance Effekt Testblock: {e}", exc_info=True)
        print(f"FEHLER im Test: {e}")

    # Stelle sicher, dass die Dummy leveling.py weg ist, falls erstellt
    if 'temp_leveling_created' in locals() and locals()['temp_leveling_created'] and leveling_py_path.exists():
        print(f"INFO: Entferne temporäre Dummy-Datei {leveling_py_path}.")
        leveling_py_path.unlink()


