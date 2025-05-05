Dieses Dokument enthält die detaillierten Informationen zu Charakteren, Skills, Gegnern und den grundlegenden Spielmechaniken, basierend auf den JSON-Dateien und dem aktuellen Stand des Codes im Projekt. Es dient als primäre Referenz für die Spielinhalte und deren Funktionsweise.
1. Charaktere (Spieler/Helden-Templates)
Krieger
Name: Krieger
Level: 1
Attribute: Stärke: 15, Geschicklichkeit: 10, Intelligenz: 5, Konstitution: 14, Weisheit: 6
Kampfwerte (Basis): Rüstung: 5, Magieresistenz: 1
Ressourcen: Maximale Ausdauer: 100, Maximale Energie: null, Maximales Mana: null
Bekannte Skills: basic_strike_phys, power_strike, shield_bash, cleave
Berechnungen (Beispiele): Start-HP: 50+(14∗5)=120, Attribut-Bonus (STR): (15−10)//2=2
Magier
Name: Magier
Level: 1
Attribute: Stärke: 5, Geschicklichkeit: 10, Intelligenz: 15, Konstitution: 8, Weisheit: 12
Kampfwerte (Basis): Rüstung: 1, Magieresistenz: 4
Ressourcen: Maximale Ausdauer: null, Maximale Energie: null, Maximales Mana: 100
Bekannte Skills: basic_magic_bolt, fireball, frostbolt, arcane_barrier
Berechnungen (Beispiele): Start-HP: 50+(8∗5)=90, Attribut-Bonus (INT): (15−10)//2=2
Schurke
Name: Schurke
Level: 1
Attribute: Stärke: 10, Geschicklichkeit: 15, Intelligenz: 8, Konstitution: 10, Weisheit: 7
Kampfwerte (Basis): Rüstung: 2, Magieresistenz: 2
Ressourcen: Maximale Ausdauer: null, Maximale Energie: 100, Maximales Mana: null
Bekannte Skills: basic_strike_finesse, precise_stab, distraction, sprint
Berechnungen (Beispiele): Start-HP: 50+(10∗5)=100, Attribut-Bonus (DEX): (15−10)//2=2
Kleriker
Name: Kleriker
Level: 1
Attribute: Stärke: 8, Geschicklichkeit: 7, Intelligenz: 12, Konstitution: 10, Weisheit: 13
Kampfwerte (Basis): Rüstung: 3, Magieresistenz: 3
Ressourcen: Maximale Ausdauer: null, Maximale Energie: null, Maximales Mana: 100
Bekannte Skills: basic_holy_spark, heal, holy_light, protective_ward
Berechnungen (Beispiele): Start-HP: 50+(10∗5)=100, Attribut-Bonus (WIS): (13−10)//2=1
2. Skills
Eine detaillierte Liste der definierten Skills mit ihren Eigenschaften:
Krieger Skills
Basic Strike Phys (ID: basic_strike_phys): Waffenschlag. Physischer Schaden (Waffe + STR-Bonus). Kosten: Keine. Ziel: Gegner.
Power Strike (ID: power_strike): Mächtiger Schlag. Physischer Schaden ((Waffe + STR-Bonus) * 1.5). Kosten: 20 Stamina. Ziel: Gegner.
Shield Bash (ID: shield_bash): Schildschlag. Physischer Schaden (2 + STR-Bonus) + STUNNED (1 Runde). Kosten: 15 Stamina. Ziel: Gegner.
Cleave (ID: cleave): Spalten. Physischer Schaden (Waffe + STR-Bonus) auf Hauptziel & Sekundärziel (50%). Kosten: 25 Stamina. Ziel: Bereich (2 Gegner).
Magier Skills
Basic Magic Bolt (ID: basic_magic_bolt): Magisches Geschoss. Magischer Schaden (2 + INT-Bonus). Kosten: 1 Mana. Ziel: Gegner.
Fireball (ID: fireball): Feuerball. Feuerschaden ((10 + INT-Bonus) * 2) + BURNING (3 Feuerschaden/Runde für 2 Runden). Kosten: 20 Mana. Ziel: Gegner.
Frostbolt (ID: frostbolt): Frostblitz. Frostschaden ((8 + INT-Bonus) * 2) + SLOWED (reduziert Evasion Mod um 2 für 1 Runde). Kosten: 15 Mana. Ziel: Gegner.
Arcane Barrier (ID: arcane_barrier): Arkane Barriere. Absorbiert Schaden (20 + INT * 5) für 3 Runden. Kosten: 25 Mana. Ziel: Selbst.
Schurke Skills
Basic Strike Finesse (ID: basic_strike_finesse): Schneller Stich. Physischer Schaden (Waffe + DEX-Bonus). Kosten: Keine. Ziel: Gegner.
Precise Stab (ID: precise_stab): Präziser Stich. Physischer Schaden (Waffe + DEX-Bonus) mit 25% Rüstungs-Ignoranz. Kosten: 20 Energie. Ziel: Gegner.
Distraction (ID: distraction): Ablenkung. ACCURACY_DOWN (reduziert Accuracy Mod um 3 für 2 Runden). Kosten: 15 Energie. Ziel: Gegner.
Sprint (ID: sprint): Sprint. INITIATIVE_UP (erhöht Initiative um 20 für 1 Runde). Kosten: 25 Energie. Ziel: Selbst.
Kleriker Skills
Basic Holy Spark (ID: basic_holy_spark): Heiliger Funke. Heiliger Schaden (2 + WIS-Bonus). Kosten: 1 Mana. Ziel: Gegner.
Heal (ID: heal): Heilung. Heilt HP (15 + WIS * 5). Kosten: 25 Mana. Ziel: Verbündeter.
Holy Light (ID: holy_light): Heiliges Licht. Heiliger Schaden ((8 + WIS-Bonus) * 2). Bonus vs UNDEAD (+50% Schaden). Kosten: 20 Mana. Ziel: Gegner.
Protective Ward (ID: protective_ward): Schutzsegen. DEFENSE_UP (erhöht Rüstung und Magieresistenz um 3 für 3 Runden). Kosten: 20 Mana. Ziel: Verbündeter.
(Weitere Skills wie basic_shot_phys, weakening_curse, heal_lesser existieren ebenfalls und sind in skills.json und/oder opponents.json definiert.)
3. Gegner
Liste der verfügbaren Gegner-Templates:
Goblin (Level 1): Nahkämpfer (STR 8, DEX 12, CON 9), HP 95, Rüstung 2. Skills: basic_strike_phys. XP: 50.
Skelett (Level 1): Nahkämpfer (STR 10, DEX 8, CON 10), HP 100, Rüstung 3. Skills: basic_strike_phys. XP: 60.
Riesenratte (Level 1): Nahkämpfer (STR 6, DEX 14, CON 7), HP 85, Rüstung 1. Skills: basic_strike_finesse. XP: 35.
Goblin-Krieger (Level 2): Nahkämpfer (STR 12, DEX 10, CON 11), HP 105, Rüstung 4. Skills: basic_strike_phys, power_strike. XP: 75.
Skelett-Bogenschütze (Level 2): Fernkämpfer (DEX 14, CON 9), HP 95, Rüstung 2. Skills: basic_shot_phys. XP: 80.
Goblin-Schamane (Level 3): Magier/Unterstützer (INT 14, WIS 12, CON 8), HP 90, Rüstung 1, MagRes 3. Skills: basic_magic_bolt, weakening_curse, heal_lesser. XP: 100.
4. Spielmechaniken (Basis-Logik & Berechnungen)
HP-Berechnung (Start): 50 + (Konstitution * 5)
Attribut-Bonus: (Attributwert - 10) // 2 (Ganzzahlige Division)
Schadensberechnung (Basis): (Basis-Schaden + Attribut-Bonus) * Multiplikator
Basis-Schaden: Fester Wert oder Waffenschaden (Standardwert aus Konfiguration/Code: 5).
Attribut-Bonus: Abhängig vom Skill (STR, DEX, INT, WIS).
Multiplikator: Abhängig vom Skill (Standard: 1.0).
Schadensreduktion: Eingehender Schaden - (Rüstung oder Magieresistenz) (Minimum 1 Schaden). Physisch -> Rüstung, Magisch/Elementar -> Magieresistenz.
Trefferchance: max(5, min(95, 90 + (Angreifer_GenauigkeitsMod * 3) - (Ziel_AusweichMod * 2)))
Genauigkeits-/Ausweich-Modifikator: (Geschicklichkeit - 10) // 2, beeinflusst durch Effekte (ACCURACY_DOWN, SLOWED etc.).
Faktoren aus Konfiguration/Code: HIT_CHANCE_ACCURACY_FACTOR = 3, HIT_CHANCE_EVASION_FACTOR = 2.
Min/Max Trefferchance: 5%/95%.
Status-Effekte (Beispiele): STUNNED (1 Runde Aktion aussetzen), BURNING (3 Feuer/Runde, 2 Runden), SLOWED (reduziert Evasion Mod um 2, 1 Runde), ACCURACY_DOWN (reduziert Accuracy Mod um 3, 2 Runden), DEFENSE_UP (erhöht Rüstung/MagRes um 3, 3 Runden), WEAKENED (reduziert STR um 3, 3 Runden), INITIATIVE_UP (erhöht Initiative um 20, 1 Runde). (Details sind im Code/JSON definiert.)
XP-Vergabe: Fester Wert pro besiegt (siehe Gegnerliste).
XP für Levelaufstieg: Basiswert * (Level Faktor), Basiswert = 100, Faktor = 1.5. (Level-Up-Boni und Mechanik noch zu implementieren).
(Dieses Dokument ist eine detaillierte Zusammenfassung und dient als Referenz. Die tatsächliche "Source of Truth" sind die entsprechenden JSON-Dateien (src/definitions/json_data/) und der Python-Code in src/definitions/ und src/game_logic/.)