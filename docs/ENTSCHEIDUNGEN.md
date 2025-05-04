# Entscheidungsprotokoll

Dieses Dokument protokolliert wichtige Entscheidungen, die während der Entwicklung des Projekts getroffen wurden.

* **[2025-05-04]:** Festlegung der grundlegenden Projektstruktur mit Fokus auf modulare Organisation und JSON-basierte Datenhaltung.

* **[2025-05-04]:** Implementierung eines zentralen DataLoader-Systems mit Caching-Mechanismus zur effizienten Verwaltung der JSON-Daten. Der DataLoader ermöglicht den Zugriff auf Charakter-, Skill- und Gegner-Daten mit Singletonmuster für einfache Verwendung im gesamten Projekt.

* **[2023-05-04 09:21:29]:** Entscheidung für modulare Loader-Struktur mit separaten Loader-Klassen pro Datentyp (Charaktere, Skills, Gegner, etc.) anstelle eines einzelnen großen DataLoader. Dies fördert das Single Responsibility Prinzip und erleichtert die Wartung und Erweiterung. Ergänzend wurde ein DataService als Fassade erstellt, der eine einheitliche Schnittstelle bietet und die spezialisierten Loader integriert.
