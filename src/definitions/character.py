# src/definitions/character.py
"""
Definiert die Datenstruktur für Charakter-Templates unter Verwendung von Pydantic.

FINALE VERSION: Kombiniert die saubere Architektur von Version 1 mit den
detaillierten Validatoren aus Version 4 für maximale Robustheit und Wartbarkeit.

WICHTIG: Die ausführlichen Docstrings und Kommentare sind ein wichtiger Teil
dieser Datei und unseres Entwicklungsprozesses. Sie sollen bei zukünftigen
Änderungen beibehalten und für neuen Code entsprechend ergänzt werden.
"""
from __future__ import annotations
import logging
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, ValidationError, validator

logger = logging.getLogger(__name__)


class ResourceType(str, Enum):
    """Definiert die erlaubten Ressourcentypen für Charaktere."""
    MANA = "MANA"
    STAMINA = "STAMINA"
    ENERGY = "ENERGY"
    NONE = "NONE"


class PrimaryAttributes(BaseModel):
    """Kapselt die Primärattribute eines Charakters."""
    STR: int = Field(..., gt=0, description="Stärke")
    DEX: int = Field(..., gt=0, description="Geschicklichkeit")
    INT: int = Field(..., gt=0, description="Intelligenz")
    CON: int = Field(..., gt=0, description="Konstitution")
    WIS: int = Field(..., gt=0, description="Weisheit")

    class Config:
        frozen: bool = True
        extra: str = "forbid"


class CombatValues(BaseModel):
    """Kapselt die abgeleiteten Kampfwerte eines Charakters."""
    base_stamina: int = Field(..., ge=0, description="Basis-Ausdauer")
    base_mana: int = Field(..., ge=0, description="Basis-Mana")
    base_energy: int = Field(..., ge=0, description="Basis-Energie")
    armor: int = Field(..., ge=0, description="Rüstungswert")
    magic_resist: int = Field(..., ge=0, description="Magieresistenz")

    class Config:
        frozen: bool = True
        extra: str = "forbid"


class CharacterTemplate(BaseModel):
    """
    Repräsentiert die validierte und unveränderliche Definition einer Charakterklasse.
    """
    id: str = Field(..., min_length=1, description="Eindeutiger ID-String für die Charakterklasse.")
    name: str = Field(..., min_length=1, description="Anzeigename der Klasse.")
    description: str = Field(..., description="Kurze Beschreibung der Klasse.")
    asset_key: Optional[str] = Field(None, description="Schlüssel für das visuelle Asset (Sprite).")
    
    base_hp: int = Field(..., gt=0, description="Basis-Lebenspunkte, müssen positiv sein.")
    resource_type: ResourceType = Field(..., description="Der primäre Ressourcentyp der Klasse.")
    
    primary_attributes: PrimaryAttributes
    combat_values: CombatValues
    
    starting_skills: List[str] = Field(..., min_items=1, description="Liste der Start-Skill-IDs.")

    # Eigene Validatoren (inspiriert von Version 4)
    @validator('id')
    def validate_id_format(cls, v: str) -> str:
        """Stellt sicher, dass die ID nur Kleinbuchstaben, Zahlen und Unterstriche enthält."""
        if not all(c.islower() or c.isdigit() or c == '_' for c in v):
            raise ValueError('ID darf nur Kleinbuchstaben, Zahlen und Unterstriche enthalten.')
        return v
        
    @validator('asset_key')
    def validate_asset_key_prefix(cls, v: Optional[str]) -> Optional[str]:
        """Stellt sicher, dass der Asset-Key, falls vorhanden, mit 'HERO_' beginnt."""
        if v is not None and not v.startswith('HERO_'):
            raise ValueError("Asset-Key für einen Helden muss mit 'HERO_' beginnen.")
        return v

    # Konfiguration der Pydantic-Klasse
    class Config:
        frozen: bool = True
        extra: str = "forbid"
        use_enum_values = True

    def clone(self) -> CharacterTemplate:
        """Erstellt eine tiefe Kopie des Templates."""
        return self.model_copy(deep=True)

    def to_dict(self) -> dict:
        """Serialisiert das Template-Objekt in ein Python-Dictionary."""
        return self.model_dump()