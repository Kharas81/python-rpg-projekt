# Implementierungsdetails des RPG-Systems

**Datum: 2025-05-08**

Dieses Dokument beschreibt die konkreten technischen Implementierungsdetails, die im Rahmen des Python-RPG-Projekts umgesetzt wurden. Es ergänzt die Spiel-Definitionen aus dem ANNEX_GAME_DEFINITIONS_SUMMARY und erklärt, wie die konzeptionellen Mechaniken im Code realisiert wurden.

## 1. Initiative & Zugreihenfolge

Die zuvor offene Frage der Initiative wurde wie folgt implementiert:

- **Basis-Initiative-Formel**: `base_initiative = DEX * 2`
- **Gesamtinitiative**: `gesamt_initiative = base_initiative + status_mods['initiative']`

Bei der Berechnung der Zugreihenfolge in einem Kampf:
1. Für jeden lebenden Charakter wird die Initiative berechnet
2. Charaktere werden absteigend nach Initiative sortiert (höchste Initiative zuerst)
3. In jeder Runde wird diese Reihenfolge neu berechnet, um Status-Effekt-Änderungen zu berücksichtigen

Implementiert in: `src/game_logic/entities.py` (get_initiative-Methode) und `src/game_logic/combat.py` (calculate_turn_order-Methode)

## 2. Status-Effekte

Status-Effekte wurden als polymorphe Klassen implementiert, die alle von einer gemeinsamen abstrakten Basisklasse `StatusEffect` erben:

### Kern-Effekt-Mechanik
- Jeder Effekt hat eine **Dauer** (Rundenzahl) und eine **Stärke** (potency)
- Effekte implementieren drei Hauptmethoden:
  - `on_apply(target)`: Wird beim ersten Anwenden des Effekts aufgerufen
  - `on_tick(target)`: Wird in jeder Runde aufgerufen
  - `on_remove(target)`: Wird beim Ablaufen des Effekts aufgerufen

### Implementierte Effekte

| Effekt-ID | Beschreibung | Implementierung |
|-----------|--------------|----------------|
| BURNING | Verursacht Schaden über Zeit | Direkter Schaden (ignoriert Rüstung): potency Punkte pro Runde |
| STUNNED | Verhindert Aktionen | Setzt 'can_act' auf False |
| SLOWED | Reduziert Initiative und Ausweichen | Initiative -5*potency, Ausweichen -potency |
| WEAKENED | Reduziert Stärke | STR -potency |
| ACCURACY_DOWN | Reduziert Treffergenauigkeit | Genauigkeit -potency |
| INITIATIVE_UP | Erhöht Initiative | Initiative +potency |
| SHIELDED | Absorbiert Schaden | Erzeugt shield_points in Höhe von potency |
| DEFENSE_UP | Erhöht Rüstung und Magieresistenz | Rüstung +potency, Magieresistenz +potency |

### Stapel-Mechanik
Wenn ein bereits aktiver Effekt erneut angewendet wird:
- Die Dauer wird auf MAX(alte_dauer, neue_dauer) gesetzt (Refresh)
- Die Stärke wird auf den neuen Wert überschrieben (kein Stapeln)

Implementiert in: `src/game_logic/effects.py`

## 3. Schild-Mechanismus

Ein Schutzschildmechanismus wurde implementiert, der nicht explizit im ursprünglichen Dokument definiert war:

- Charaktere haben ein `shield_points`-Attribut (standardmäßig 0)
- Bei Schadensanwendung wird zuerst der Schild reduziert, bevor HP verloren gehen
- Der SHIELDED-Status-Effekt setzt die Schildpunkte auf den Stärkewert des Effekts
- Nach Ablauf des Effekts werden Schildpunkte auf 0 zurückgesetzt

Implementiert in: `src/game_logic/entities.py` (take_damage-Methode)

## 4. KI-Strategien

Drei verschiedene KI-Strategien wurden implementiert, die unterschiedliche Kampfverhalten für Gegner ermöglichen:

### BasicMeleeStrategy
- **Priorität**: Schwächere Ziele, starke Angriffe
- **Zielauswahl**: 80% schwächstes Ziel, 20% zufällig
- **Skill-Auswahl**: Bevorzugt offensive Skills, wählt mit 70% Chance den stärksten Angriff

### BasicRangedStrategy
- **Priorität**: Taktische Ziele (Magier/Heiler), Status-Effekte
- **Zielauswahl**: 70% Zauberkundige, 60% schwächstes Ziel, Rest zufällig
- **Skill-Auswahl**: Bevorzugt Skills mit Status-Effekten (60% Chance)

### SupportCasterStrategy
- **Priorität**: 1. Heilung, 2. Verbündeten-Buffs, 3. Gegner-Debuffs, 4. Angriffe
- **Zielauswahl für Heilung**: Am stärksten verletzter Verbündeter
- **Zielauswahl für Debuff**: Starke Gegner oder Zauberkundige

Implementiert in: `src/ai/strategies/`

## 5. Flächeneffekt-Logik

Die Multi-Target-Logik für Skills wurde implementiert:

### Flächeneffekt-Typen:
- **CLEAVE**: Trifft das Hauptziel und ein sekundäres Ziel
- **SPLASH**: Trifft alle Ziele im Bereich (implementiert als Hauptziel + alle anderen Ziele)

Die Auswahl der sekundären Ziele erfolgt in den KI-Strategien und wird vom Kampfsystem bei der Schadensberechnung berücksichtigt.

Implementiert in: `src/ai/strategies/*.py` und `src/game_logic/combat.py`

## 6. XP- und Level-System

Das XP- und Level-System wurde als separater Service implementiert:

- **Benötigte XP für Level**: `math.ceil(xp_level_base * (xp_level_factor ^ (level - 1)))`
- **Level-Up-Effekte**: Vollständige Wiederherstellung von HP und allen Ressourcen
- **XP-Vergabe**: Auf alle überlebenden Spieler gleichmäßig verteilt

Implementiert in: `src/game_logic/leveling.py`

## 7. Trefferchance und Schadensberechnung

Die Trefferchance- und Schadensformeln wurden wie folgt implementiert:

### Trefferchance

hit_chance = base_chance + (accuracy * accuracy_factor) - (evasion * evasion_factor) hit_chance = max(min_chance, min(max_chance, hit_chance))


### Schadensberechnung

raw_damage = floor((base_damage + attribute_bonus) * multiplier) final_damage = max(min_damage, raw_damage - defense)


Für Gegner mit spezifischen Schwächen:

if has_weakness: multiplier *= bonus_multiplier


Implementiert in: `src/game_logic/formulas.py` und `src/game_logic/combat.py`

## 8. CLI-Simulation

Die Spielsimulation wurde als CLI-basierte automatische Kampfsimulation implementiert:

- Zufällige Auswahl von Spielercharakteren aus verfügbaren Templates
- Zufällige Generierung von Gegnern mit Level-Anpassung basierend auf Spieler-Durchschnittslevel
- Automatische Kampfabwicklung mit visueller Ausgabe (Lebensbalken, formatierte Nachrichten)
- XP-Vergabe und Level-Ups nach erfolgreichen Kämpfen

Implementiert in: `src/ui/cli_main_loop.py` und `src/ui/cli_output.py`

