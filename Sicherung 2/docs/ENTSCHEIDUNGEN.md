# Wichtige Projekt-Entscheidungen

Dieses Dokument protokolliert wichtige Designentscheidungen, die während der Entwicklung getroffen wurden.

## 2025-05-08: Projektstart und grundlegende Strukturentscheidungen

- **Entscheidung**: Verwendung von json5 für Konfigurationsdateien und Spieldefinitionen
  - **Begründung**: Ermöglicht Kommentare und eine flexiblere Syntax für bessere Lesbarkeit und Wartbarkeit
  - **Alternativen**: Standard JSON (weniger lesbar), YAML (zusätzliche Abhängigkeit)

- **Entscheidung**: Modulare Projektstruktur mit klarer Trennung von Daten und Logik
  - **Begründung**: Verbessert Wartbarkeit und Erweiterbarkeit, folgt dem Single Responsibility Prinzip
  - **Implikation**: Mehr Initial-Setup, aber bessere Langzeitentwicklung

## 2025-05-08: Logging-System und Konfigurationsverwaltung

- **Entscheidung**: Implementierung eines zentralen Logging-Systems mit konfigurierbaren Levels
  - **Begründung**: Ermöglicht feinere Kontrolle über die Ausgaben, unterstützt sowohl Konsolen- als auch Datei-Logs
  - **Implikation**: Logger werden über eine zentrale Funktion (get_logger) bezogen, vereinheitlicht den Logging-Ansatz

- **Entscheidung**: Konfigurationsdaten werden zentral über ein Singleton-Objekt verwaltet
  - **Begründung**: Vermeidet Duplizierung von Konfigurationslesevorgängen, stellt konsistente Konfiguration im gesamten Projekt sicher
  - **Alternativen**: Direktes Laden in einzelnen Modulen (würde zu Duplizierung führen)
  - **Implikation**: Änderungen an der Konfiguration sind sofort im gesamten Projekt verfügbar

- **Entscheidung**: Mehrere Betriebsmodi für das Spiel (manual, auto, train, evaluate)
  - **Begründung**: Unterstützt verschiedene Anwendungsfälle (interaktives Spielen, automatische Simulation, RL-Training und -Evaluierung)
  - **Implikation**: Erfordert eine klare Trennung der Logik für die verschiedenen Modi

## 2025-05-08: Regelbasierte KI-Architektur

- **Entscheidung**: Implementierung einer flexiblen, regelbasierten KI-Architektur mit Strategie-Pattern
  - **Begründung**: Ermöglicht verschiedene Verhaltensweisen für unterschiedliche Gegnertypen
  - **Alternativen**: Feste Logik pro Gegner (nicht erweiterbar), komplexe RL-basierte KI (zu früh im Projekt)
  - **Implikation**: Einfache Erweiterbarkeit um neue Strategien, klare Trennung von Entscheidungslogik und Charakterzustand

- **Entscheidung**: Drei Basis-KI-Strategien: Nahkampf, Fernkampf, Unterstützung
  - **Begründung**: Deckt die Grundbedürfnisse des Spiels ab und passt zu den definierten Gegnertypen
  - **Implikation**: Verschiedene Gegner verhalten sich taktisch unterschiedlich, was zu abwechslungsreichen Kampferfahrungen führt

- **Entscheidung**: Einsatz eines AI-Dispatchers zur dynamischen Strategieauswahl
  - **Begründung**: Zentralisierte Zuordnung von Charakteren zu Strategien, vereinfacht die Nutzung im Code
  - **Implikation**: Strategien können zur Laufzeit gewechselt werden, erleichtert Testing und Erweiterung

## 2025-05-08: CLI-Simulation und Game Loop

- **Entscheidung**: Implementierung einer CLI-basierten Simulation für automatische Kampfabläufe
  - **Begründung**: Ermöglicht frühes Testen des Spielsystems ohne komplexe UI-Implementierung
  - **Alternativen**: Sofortige Implementierung einer GUI (zu zeitaufwendig), reines Backend ohne Ausgabe (schlecht für Testing)
  - **Implikation**: Schnelle Iteration und Validierung der Spielmechaniken, einfaches Testen von Balance-Änderungen

- **Entscheidung**: Formatierte Konsolenausgabe mit visuellen Elementen (Balken, Farbcodes)
  - **Begründung**: Verbessert die Lesbarkeit und Benutzerfreundlichkeit der Textausgabe
  - **Implikation**: Bessere Benutzererfahrung in der CLI-Phase, kann später durch grafische UI ersetzt werden

- **Entscheidung**: Zufällige Generierung von Gegnern basierend auf Spieler-Level
  - **Begründung**: Schafft Abwechslung und passt die Herausforderung dynamisch an
  - **Implikation**: Ermöglicht Spieltests mit verschiedenen Gegnertypen und Schwierigkeitsgraden
