# src/utils/exceptions.py

class RPGBaseException(Exception):
    """Basisklasse für alle benutzerdefinierten Exceptions im RPG-Projekt."""
    pass

# --- Definition File Errors ---
class DefinitionFileError(RPGBaseException):
    """Basisklasse für Fehler im Zusammenhang mit Definitionsdateien."""
    def __init__(self, message: str, filepath: str = None): # type: ignore
        super().__init__(message)
        self.filepath = filepath
        self.message = message # Store message for potential custom __str__

    def __str__(self):
        if self.filepath:
            return f"{self.message} (Datei: {self.filepath})"
        return self.message

class DefinitionFileNotFoundError(DefinitionFileError):
    """Wird ausgelöst, wenn eine Definitionsdatei nicht gefunden wurde."""
    def __init__(self, filepath: str): # type: ignore
        super().__init__(message="Definitionsdatei nicht gefunden", filepath=filepath)

class DefinitionParsingError(DefinitionFileError):
    """Wird ausgelöst, wenn beim Parsen einer Definitionsdatei ein Fehler auftritt."""
    def __init__(self, filepath: str, original_exception: Exception = None): # type: ignore
        msg = "Fehler beim Parsen der JSON5-Definitionsdatei"
        super().__init__(message=msg, filepath=filepath)
        self.original_exception = original_exception

    def __str__(self):
        base_str = super().__str__()
        if self.original_exception:
            return f"{base_str}\n  Ursprünglicher Fehler: {type(self.original_exception).__name__}: {self.original_exception}"
        return base_str

class DefinitionContentError(DefinitionFileError):
    """Wird ausgelöst, wenn der Inhalt einer Definitionsdatei nicht dem erwarteten Format entspricht."""
    def __init__(self, filepath: str, message: str = "Inhalt der Definitionsdatei entspricht nicht dem erwarteten Format."): # type: ignore
        super().__init__(message=message, filepath=filepath)


# --- Configuration Errors ---
class ConfigError(RPGBaseException):
    """Basisklasse für Konfigurationsfehler."""
    pass

class CriticalConfigError(ConfigError):
    """Wird ausgelöst, wenn kritische Konfigurationen nicht geladen werden können."""
    def __init__(self, message: str, original_exception: Exception = None): # type: ignore
        super().__init__(message)
        self.original_exception = original_exception

    def __str__(self):
        base_str = super().__str__()
        if self.original_exception:
            return f"{base_str}\n  Ursache: {type(self.original_exception).__name__}: {self.original_exception}"
        return base_str

# Hier könnten später weitere spezifische Exceptions hinzugefügt werden,
# z.B. für Spiellogik-Fehler, ungültige Aktionen etc.