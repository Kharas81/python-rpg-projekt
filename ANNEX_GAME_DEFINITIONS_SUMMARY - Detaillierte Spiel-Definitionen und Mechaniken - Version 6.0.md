Dieses Dokument enthält die detaillierten Informationen zu Charakteren, Skills, Gegnern und den grundlegenden Spielmechaniken, basierend auf den JSON5-Dateien, Konfigurationsdateien (src/config/settings.json5) und dem aktuellen Stand des Codes im Projekt. Es dient als primäre Referenz für die Spielinhalte und deren Funktionsweise.
Wichtig: JSON5 Format und Kommentare
Wir verwenden das JSON5-Format für unsere Datendateien (typischerweise mit der Dateiendung .json5). JSON5 ist eine Erweiterung von JSON, die zusätzliche Features für menschliche Lesbarkeit erlaubt. Das wichtigste für uns ist die Unterstützung für Kommentare.
Single-line Kommentare: Beginnen mit //
Multi-line Kommentare: Eingeschlossen in /* ... */
{
  // Dies ist ein einzelner Kommentar
  "name": "Beispiel-Charakter",
  "level": 1, // Level des Charakters
  /*
  Dies ist ein mehrzeiliger Kommentar
  und beschreibt die Attribute.
  */
  "attributes": {
    "STR": 10,
    "DEX": 12,
    "INT": 5,
    "CON": 8,
    "WIS": 7, // Weisheit
  }, // Nach dem letzten Element ist ein Komma erlaubt (JSON5 Feature)
  "skills": [
    "basic_attack", // Standardangriff
  ],
} // Ein Komma am Ende des Top-Level-Objekts ist erlaubt (JSON5 Feature)
Du musst sicherstellen, dass du dieses JSON5-Format für Datendateien verwendest und verstehst, dass im Python-Code die -Bibliothek (anstelle der Standard json-Bibliothek) zum Laden dieser Dateien benötigt wird.
Umfassende Zusammenfassung der Spiel-Definitionen und Mechaniken (Stand: Basierend auf bereitgestellten Dokumenten und Q&A)
1. Datenformat und Primäre Datenquellen:
Format: JSON5 (erlaubt Kommentare, flexiblere Syntax). Benötigt json5-Bibliothek in Python.
Konfigurationsdatei: src/config/settings.json5 (globale Spielparameter).
Definitionsdateien:
src/definitions/json_data/characters.json5 (Charakterklassen-Startwerte)
src/definitions/json_data/skills.json5 (Skill-Definitionen)
src/definitions/json_data/opponents.json5 (Gegner-Definitionen)
(Implizit: primary_attributes.json, combat_stats.json aus Teil 1 sind nun in diesen detaillierteren Dateien aufgegangen oder konzeptionell vorhanden).


2. Globale Konfigurationen (aus 
game_settings.min_damage: 1
game_settings.base_weapon_damage: 5 (genutzt für Skills mit base_damage: null)
game_settings.hit_chance_base: 90
game_settings.hit_chance_accuracy_factor: 3
game_settings.hit_chance_evasion_factor: 2
game_settings.hit_chance_min: 5
game_settings.hit_chance_max: 95
game_settings.xp_level_base: 100
game_settings.xp_level_factor: 1.5
(Logging- und RL-spezifische Settings sind ebenfalls vorhanden).
3. Primärattribute:
STR (Stärke): Physischer Schaden, Tragkraft (Tragkraft-Mechanik TBD).
DEX (Geschicklichkeit): Angriffsgeschwindigkeit (nicht explizit implementiert), Ausweichen, Fernkampfschaden, Genauigkeit.
INT (Intelligenz): Magischer Schaden, Beeinflusst Mana (aktuell nur base_mana als Max-Wert, keine weitere Skalierung der Max-Menge durch INT).
CON (Konstitution): Maximale Lebenspunkte (HP).
WIS (Weisheit): Willenskraft, Magieresistenz, Effektivität von Heilzaubern.
4. Kampfwerte:
HP (Lebenspunkte): Gesundheit.
MANA: Ressource für Magier, Kleriker.
STAMINA: Ressource für Krieger.
ENERGY: Ressource für Schurken.
ARMOR (Rüstung): Reduziert physischen Schaden.
MAGIC_RESIST (Magieresistenz): Reduziert magischen Schaden.
HIT_CHANCE (Trefferchance): Basis-Wahrscheinlichkeit zu treffen.
EVASION (Ausweichen): Reduziert Trefferchance des Angreifers.
ACCURACY (Genauigkeit): Erhöht eigene Trefferchance.
INITIATIVE: Bestimmt Zugreihenfolge (Kernmechanik TBD).
5. Charakterklassen (aus 
Alle Klassen haben base_hp: 50 (vor CON-Bonus).
* Krieger ("krieger"):
* Primärattribute: STR:14, DEX:10, INT:8, CON:12, WIS:8
* Kampfwerte: base_stamina:100, armor:5, magic_resist:1. (Mana/Energy: 0)
* Primärressource: STAMINA
* Skills: basic_strike_phys, power_strike, shield_bash, cleave.
* Magier ("magier"):
* Primärattribute: STR:8, DEX:10, INT:14, CON:9, WIS:11
* Kampfwerte: base_mana:120, armor:1, magic_resist:4. (Stamina/Energy: 0)
* Primärressource: MANA
* Skills: basic_magic_bolt, fireball, frostbolt, arcane_barrier.
* Schurke ("schurke"):
* Primärattribute: STR:10, DEX:14, INT:8, CON:10, WIS:8
* Kampfwerte: base_energy:100, armor:3, magic_resist:2. (Mana/Stamina: 0)
* Primärressource: ENERGY
* Skills: basic_strike_finesse, precise_stab, distraction, sprint.
* Kleriker ("kleriker"):
* Primärattribute: STR:10, DEX:8, INT:10, CON:11, WIS:13
* Kampfwerte: base_mana:110, armor:4, magic_resist:3. (Stamina/Energy: 0)
* Primärressource: MANA
* Skills: basic_holy_spark, heal, holy_light, protective_ward.
6. Skills (aus 
Jeder Skill hat ID, Kosten (Wert & Typ), Effekte (Basis-Schaden, Attributskalierung, Multiplikator) und ggf. applies_effects (Status-Effekte).
* Schadens-Skills:
* base_damage: null nutzt game_settings.base_weapon_damage (5).
* Beispiele: power_strike (STR, x1.5), shield_bash (STR, Basis 2 + STUNNED 1 Rd.), fireball (INT, Basis 10 x2 + BURNING 3DMG/2Rd.), frostbolt (INT, Basis 8 x2 + SLOWED 1Rd.), precise_stab (DEX, 25% Rüstungs-Ignoranz).
* Heil-Skills: heal (Heilt 15 + WIS5).5 für 3Rd.), distraction (ACCURACY_DOWN -3 für 2Rd.), sprint (INITIATIVE_UP +20 für 1Rd.), protective_ward (DEFENSE_UP +3 für 3Rd.).
* Gegner-Skills: basic_shot_phys (DEX), weakening_curse (WEAKENED STR -3 für 3Rd.), heal_lesser (Heilt 10 + WIS*3).
* Status-Effekt-Anwendung: Aktuell 100% Chance bei Treffer. Geplant: variables Feld application_chance.
7. Gegner (aus src/definitions/json_data/opponents.json5):
Jeder Gegner hat Primärattribute, combat_values (base_hp, base_mana etc., armor, magic_resist), eine Liste von Skill-IDs und einen xp_reward.
* Beispiele:
* goblin_lv1: STR:8, DEX:12, CON:9, base_hp:50, armor:2, xp_reward:50. Skills: basic_strike_phys. Tags: ["GOBLINOID", "HUMANOID"].
* goblin_schamane_lv3: INT:14, WIS:12, base_hp:50, base_mana:100, magic_resist:3, xp_reward:100. Skills: basic_magic_bolt, weakening_curse, heal_lesser.
* Gegner-Tags: Definiert im tags-Feld (z.B. ["UNDEAD"]). Logik für Boni wie holy_lights bonus_vs_type: "UNDEAD" muss in Schadensberechnung implementiert werden.
8. Kern-Spielmechaniken & Berechnungen:
HP-Berechnung (Start): MaxHP = base_hp (aus JSON) + (CON * 5).
Maximal-Ressourcen (Mana, Stamina, Energy): Aktuell die base_... Werte aus den JSON-Dateien. Keine weitere Skalierung durch Attribute für die Max-Werte.
Attribut-Bonus: (Attributwert - 10) // 2 (Ganzzahlige Division).
Schadensberechnung (Basis-Skill): floor((Basis-Schaden + Attribut-Bonus) * Multiplikator).
Basis-Schaden: Aus Skill-Definition oder game_settings.base_weapon_damage (5).


Schadensreduktion: max(game_settings.min_damage (1), Eingehender_Schaden - (Rüstung oder Magieresistenz)).
Trefferchance: max(hit_chance_min (5), min(hit_chance_max (95), hit_chance_base (90) + (Angreifer_GenauigkeitsMod * hit_chance_accuracy_factor (3)) - (Ziel_AusweichMod * hit_chance_evasion_factor (2)))).
Genauigkeits-/Ausweich-Modifikator: Basis (DEX - 10) // 2 + Effekte.


Status-Effekte (Interaktion):
Bei Neuanwendung desselben Effekts: Dauer wird auf max(alte_Dauer, neue_Dauer) gesetzt (Refresh/Verlängerung).
Potency wird von der neuen Anwendung überschrieben (kein Stacken der Stärke).


XP-Vergabe: Fester Wert pro Gegner (xp_reward).
XP für Levelaufstieg: ceil(xp_level_base (100) * (xp_level_factor (1.5) ^ (Aktuelles_Level - 1))).
Level-Up-Boni: Aktuell: Volle Heilung/Ressourcenwiederherstellung. Weitere Boni (Attributpunkte etc.) sind TODO. Es gibt kein festes Maximallevel im Spieldesign.
9. Wichtige Offene Punkte / Zukünftige Features (Design & Implementierung):
Initiative & Zugreihenfolge: Die Kernmechanik zur Bestimmung der Basis-Initiative und der Kampfreihenfolge fehlt. Der INITIATIVE_UP-Effekt existiert, aber seine Einbindung ist offen. (Aktuell feste Reihenfolge in cli_main_loop.py).
Items & Waffen: Geplant, insbesondere Waffen, die den base_weapon_damage ersetzen/modifizieren. Struktur für Item-Definitionen (z.B. items.json5) fehlt.
Tragkraft: Konzeptionell durch STR beeinflusst, aber Mechanik und Formel (z.B. Basis + STR * Faktor) sowie Konsequenzen bei Überschreitung sind TBD.
Multi-Target Skill Logik: Auswahl von Sekundärzielen für AREA-Skills (z.B. cleaves zweites Ziel) muss implementiert werden.
Implementierung von bonus_vs_type: Die Logik, um den Schadensbonus gegen bestimmte Gegner-Tags (z.B. UNDEAD) anzuwenden, muss in die Schadensberechnung integriert werden.
Detaillierte Level-Up-Boni: Konkrete numerische Boni (Attributpunkte, Skillpunkte, etc.) sind noch zu definieren.
Chance für Status-Effekte: Implementierung eines application_chance-Feldes für Skills, um Effekte mit <100% Wahrscheinlichkeit zu ermöglichen.