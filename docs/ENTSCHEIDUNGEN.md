# Entscheidungsprotokoll

Dieses Dokument protokolliert wichtige Entscheidungen, die während der Entwicklung des Projekts getroffen wurden.

* **[2025-05-04]:** Festlegung der grundlegenden Projektstruktur mit Fokus auf modulare Organisation und JSON-basierte Datenhaltung.

* **[2025-05-04]:** Implementierung eines zentralen DataLoader-Systems mit Caching-Mechanismus zur effizienten Verwaltung der JSON-Daten. Der DataLoader ermöglicht den Zugriff auf Charakter-, Skill- und Gegner-Daten mit Singletonmuster für einfache Verwendung im gesamten Projekt.

* **[2023-05-04 09:21:29]:** Entscheidung für modulare Loader-Struktur mit separaten Loader-Klassen pro Datentyp (Charaktere, Skills, Gegner, etc.) anstelle eines einzelnen großen DataLoader. Dies fördert das Single Responsibility Prinzip und erleichtert die Wartung und Erweiterung. Ergänzend wurde ein DataService als Fassade erstellt, der eine einheitliche Schnittstelle bietet und die spezialisierten Loader integriert.

* **[2025-05-04 09:28:40]:** Entscheidung für eine modulare Entity-Struktur anstelle einer monolithischen Entity-Klasse. Die Funktionalität wird aufgeteilt in spezialisierte Module: base_entity, status_effect, player, enemy sowie separate Module für verschiedene Skill-Effekte. Dies verbessert die Wartbarkeit, Testbarkeit und ermöglicht später leichtere Erweiterungen.

* **[2025-05-04 10:23:01]:** Implementierung eines CombatManager für die Kampflogik. Der Manager übernimmt die Steuerung des Kampfablaufs, die Bestimmung der Initiative, die Ausführung von Aktionen (Angriffe, Skills, Flucht) und die Überprüfung der Kampfende-Bedingungen. Die Klasse ist bewusst unabhängig vom UI-Layer gestaltet und gibt strukturierte Informationen zurück, die in verschiedenen UI-Umgebungen (CLI, Web, GUI) dargestellt werden können.

* **[2025-05-04 10:27:02]:** Modularisierung des Combat-Systems in mehrere spezialisierte Komponenten: InitiativeManager (Zuständig für Initiativreihenfolge und Rundenwechsel), ActionResolver (Führt verschiedene Aktionstypen wie Angriffe und Skills aus), RewardCalculator (Berechnet Erfahrungspunkte und Beute) und ein schlankerer CombatManager als zentrale Koordinationskomponente. Diese Aufteilung verbessert die Wartbarkeit und Erweiterbarkeit des Systems gemäß dem Single Responsibility Principle.
