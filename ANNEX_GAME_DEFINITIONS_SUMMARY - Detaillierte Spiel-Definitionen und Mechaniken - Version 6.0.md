ANNEX_GAME_DEFINITIONS_SUMMARY - Detaillierte Spiel-Definitionen und Mechaniken - Version 7.0
Aktualisiert am: 2025-05-08
Dieses Dokument enthält die detaillierten Informationen zu Charakteren, Skills, Gegnern und den grundlegenden Spielmechaniken, basierend auf den JSON5-Dateien, Konfigurationsdateien und der aktuellen Implementierung.
JSON5 Format und Kommentare
Wir verwenden das JSON5-Format für unsere Datendateien (typischerweise mit der Dateiendung .json5). JSON5 ist eine Erweiterung von JSON, die zusätzliche Features für menschliche Lesbarkeit erlaubt:
Single-line Kommentare: Beginnen mit //
Multi-line Kommentare: Eingeschlossen in /* ... */
JSON5
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

Du musst sicherstellen, dass du dieses JSON5-Format für Datendateien verwendest und verstehst, dass im Python-Code die json5-Bibliothek (anstelle der Standard json-Bibliothek) zum Laden dieser Dateien benötigt wird.
Umfassende Zusammenfassung der Spiel-Definitionen und Mechaniken
1. Datenformat und Primäre Datenquellen:
Format: JSON5 (erlaubt Kommentare, flexiblere Syntax). Benötigt json5-Bibliothek in Python.
Konfigurationsdatei: src/config/settings.json5 (globale Spielparameter).
Definitionsdateien:
src/definitions/json_data/characters.json5 (Charakterklassen-Startwerte)
src/definitions/json_data/skills.json5 (Skill-Definitionen)
src/definitions/json_data/opponents.json5 (Gegner-Definitionen)
2. Globale Konfigurationen (aus settings.json5):
game_settings.min_damage: 1
game_settings.base_weapon_damage: 5 (genutzt für Skills mit base_damage: null)
game_settings.hit_chance_base: 90
game_settings.hit_chance_accuracy_factor: 3
game_settings.hit_chance_evasion_factor: 2
game_settings.hit_chance_min: 5
game_settings.hit_chance_max: 95
game_settings.xp_level_base: 100
game_settings.xp_level_factor: 1.5
(Logging- und RL-spezifische Settings sind ebenfalls vorhanden)
3. Primärattribute:
STR (Stärke): Physischer Schaden, Tragkraft (Tragkraft-Mechanik TBD).
DEX (Geschicklichkeit): Angriffsgeschwindigkeit, Ausweichen, Fernkampfschaden, Genauigkeit, Initiative.
INT (Intelligenz): Magischer Schaden, Beeinflusst Mana.
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
INITIATIVE: Bestimmt Zugreihenfolge (basierend auf DEX*2 + Status-Modifikatoren).
SHIELD_POINTS: Absorbiert Schaden, bevor HP reduziert werden.
5. Charakterklassen (aus characters.json5):
Alle Klassen haben base_hp: 50 (vor CON-Bonus).
Krieger ("krieger"):
Primärattribute: STR:14, DEX:10, INT:8, CON:12, WIS:8
Kampfwerte: base_stamina:100, armor:5, magic_resist:1. (Mana/Energy: 0)
Primärressource: STAMINA
Skills: basic_strike_phys, power_strike, shield_bash, cleave.
Magier ("magier"):
Primärattribute: STR:8, DEX:10, INT:14, CON:9, WIS:11
Kampfwerte: base_mana:120, armor:1, magic_resist:4. (Stamina/Energy: 0)
Primärressource: MANA
Skills: basic_magic_bolt, fireball, frostbolt, arcane_barrier.
Schurke ("schurke"):
Primärattribute: STR:10, DEX:14, INT:8, CON:10, WIS:8
Kampfwerte: base_energy:100, armor:3, magic_resist:2. (Mana/Stamina: 0)
Primärressource: ENERGY
Skills: basic_strike_finesse, precise_stab, distraction, sprint.
Kleriker ("kleriker"):
Primärattribute: STR:10, DEX:8, INT:10, CON:11, WIS:13
Kampfwerte: base_mana:110, armor:4, magic_resist:3. (Stamina/Energy: 0)
Primärressource: MANA
Skills: basic_holy_spark, heal, holy_light, protective_ward.
6. Skills (aus skills.json5):
Jeder Skill hat ID, Kosten (Wert & Typ), Effekte (Basis-Schaden, Attributskalierung, Multiplikator) und ggf. applies_effects (Status-Effekte).
Schadens-Skills:
base_damage: null nutzt game_settings.base_weapon_damage (5).
Beispiele: power_strike (STR, x1.5), shield_bash (STR, Basis 2 + STUNNED 1 Rd.), fireball (INT, Basis 10 x2 + BURNING 3DMG/2Rd.), frostbolt (INT, Basis 8 x2 + SLOWED 1Rd.), precise_stab (DEX, 25% Krit-Chance).
Support-Skills:
heal (Heilt 15 + WIS*0.5), distraction (ACCURACY_DOWN -3 für 2Rd.), sprint (INITIATIVE_UP +20 für 1Rd.), protective_ward (DEFENSE_UP +3 für 3Rd.).
Gegner-Skills:
basic_shot_phys (DEX), weakening_curse (WEAKENED STR -3 für 3Rd.), heal_lesser (Heilt 10 + WIS*3).
Flächeneffekt-Typen:
CLEAVE: Trifft das Hauptziel und ein sekundäres Ziel
SPLASH: Trifft alle Ziele im Bereich (Hauptziel + alle anderen verfügbaren Ziele)
7. Gegner (aus opponents.json5):
Jeder Gegner hat Primärattribute, combat_values, eine Liste von Skill-IDs, einen xp_reward und eine ai_strategy.
Beispiele:
goblin_lv1: STR:8, DEX:12, CON:9, base_hp:50, armor:2, xp_reward:50. Skills: basic_strike_phys. Tags: ["GOBLINOID", "HUMANOID"]. AI-Strategy: basic_melee.
goblin_archer_lv2: DEX:14, base_hp:50, armor:1, xp_reward:75. Skills: basic_shot_phys. Tags: ["GOBLINOID", "HUMANOID", "RANGED"]. AI-Strategy: basic_ranged.
goblin_schamane_lv3: INT:14, WIS:12, base_hp:50, base_mana:100, magic_resist:3, xp_reward:100. Skills: basic_magic_bolt, weakening_curse, heal_lesser. AI-Strategy: support_caster.
skeleton_lv2: STR:10, CON:10, base_hp:60, armor:3, xp_reward:75. Tags: ["UNDEAD", "SKELETON"]. Weaknesses: ["HOLY"].
wolf_lv1: DEX:14, base_hp:40, initiative_bonus:10, xp_reward:40. Tags: ["BEAST", "ANIMAL"].
8. KI-Strategien (implementiert in src/ai/strategies/):
Regelbasierte Strategien, die das Kampfverhalten der Gegner steuern:
BasicMeleeStrategy (basic_melee):
Priorität: Schwächere Ziele, starke Angriffe
Zielauswahl: 80% schwächstes Ziel, 20% zufällig
Skill-Auswahl: Bevorzugt offensive Skills, wählt mit 70% Chance den stärksten Angriff
BasicRangedStrategy (basic_ranged):
Priorität: Taktische Ziele (Magier/Heiler), Status-Effekte
Zielauswahl: 70% Zauberkundige, 60% schwächstes Ziel, Rest zufällig
Skill-Auswahl: Bevorzugt Skills mit Status-Effekten (60% Chance)
SupportCasterStrategy (support_caster):
Priorität: 1. Heilung, 2. Verbündeten-Buffs, 3. Gegner-Debuffs, 4. Angriffe
Zielauswahl für Heilung: Am stärksten verletzter Verbündeter
Zielauswahl für Debuff: Starke Gegner oder Zauberkundige
9. Status-Effekte (implementiert in src/game_logic/effects.py):
Status-Effekte haben eine Dauer (in Runden) und eine Stärke (potency). Wenn ein bereits aktiver Effekt erneut angewendet wird, wird die Dauer auf MAX(alte_dauer, neue_dauer) gesetzt und die Stärke überschrieben (kein Stapeln).
Implementierte Effekte:
Effekt-ID
Beschreibung
Implementierung
BURNING
Verursacht Schaden über Zeit
Direkter Schaden (ignoriert Rüstung): potency Punkte pro Runde
STUNNED
Verhindert Aktionen
Setzt 'can_act' auf False
SLOWED
Reduziert Initiative und Ausweichen
Initiative -5*potency, Ausweichen -potency
WEAKENED
Reduziert Stärke
STR -potency
ACCURACY_DOWN
Reduziert Treffergenauigkeit
Genauigkeit -potency
INITIATIVE_UP
Erhöht Initiative
Initiative +potency
SHIELDED
Absorbiert Schaden
Erzeugt shield_points in Höhe von potency
DEFENSE_UP
Erhöht Rüstung und Magieresistenz
Rüstung +potency, Magieresistenz +potency

10. Kern-Spielmechaniken & Berechnungen:
HP-Berechnung (Start): MaxHP = base_hp (aus JSON) + (CON * 5).
Maximal-Ressourcen (Mana, Stamina, Energy): Aktuell die base_... Werte aus den JSON-Dateien.
Attribut-Bonus: (Attributwert - 10) // 2 (Ganzzahlige Division).
Schadensberechnung (Basis-Skill): floor((Basis-Schaden + Attribut-Bonus) * Multiplikator).
Basis-Schaden: Aus Skill-Definition oder game_settings.base_weapon_damage (5).
Schadensreduktion: max(game_settings.min_damage (1), Eingehender_Schaden - (Rüstung oder Magieresistenz)).
Trefferchance:
Code
hit_chance = base_chance + (accuracy * accuracy_factor) - (evasion * evasion_factor)
hit_chance = max(min_chance, min(max_chance, hit_chance))

Initiative & Zugreihenfolge:
Basis-Initiative-Formel: base_initiative = DEX * 2
Gesamtinitiative: gesamt_initiative = base_initiative + status_mods['initiative']
In jeder Kampfrunde wird die Zugreihenfolge basierend auf Initiative neu berechnet (höchste zuerst)
XP-Vergabe und Level-System:
XP-Vergabe: Fester Wert pro Gegner (xp_reward), gleichmäßig auf überlebende Spieler verteilt.
XP für Levelaufstieg: ceil(xp_level_base (100) * (xp_level_factor (1.5) ^ (Aktuelles_Level - 1))).
Level-Up-Boni: Volle Heilung und Ressourcenwiederherstellung.
Schild-Mechanismus:
Charaktere haben ein shield_points-Attribut (standardmäßig 0)
Bei Schadensanwendung wird zuerst der Schild reduziert, bevor HP verloren gehen
Der SHIELDED-Status-Effekt setzt die Schildpunkte auf den Stärkewert des Effekts
11. Wichtige Offene Punkte / Zukünftige Features:
Items & Waffen: Geplant, insbesondere Waffen, die den base_weapon_damage ersetzen/modifizieren. Struktur für Item-Definitionen (items.json5) ist als Platzhalter vorhanden.
Tragkraft: Konzeptionell durch STR beeinflusst, aber Mechanik und Formel (z.B. Basis + STR * Faktor) sowie Konsequenzen bei Überschreitung sind TBD.
Detaillierte Level-Up-Boni: Konkrete numerische Boni (Attributpunkte, Skillpunkte, etc.) sind noch zu definieren.
Chance für Status-Effekte: Implementierung eines application_chance-Feldes für Skills, um Effekte mit <100% Wahrscheinlichkeit zu ermöglichen.
Erweitertes RL-Training: Integration von Curriculum Learning und parallelen Trainingsläufen.
Grafische Benutzeroberfläche: Aktuell nur CLI-Simulation implementiert.
Hinweis: Dieses Dokument ist eine vollständige Zusammenfassung der aktuellen Spiel-Definitionen und Implementierungen. Für weitere technische Details zur Implementierung siehe auch das separate Dokument IMPLEMENTIERUNGSDETAILS.md.