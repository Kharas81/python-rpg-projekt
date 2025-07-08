# src/definitions/item.py
"""
Definiert die Datenstruktur für Item-Templates, die aus JSON5-Dateien geladen werden.
Diese Struktur spiegelt die Definitionen in `items.json5` wider.
"""

from typing import List, Dict, Any, Optional

class ItemEffectData:
    """
    Daten für die direkten Effekte eines Items (z.B. Heilung, Manawiederherstellung).
    Entspricht dem 'direct_effects'-Objekt in der JSON5-Definition.
    """
    def __init__(self,
                 base_healing: Optional[int] = None,
                 # Wie besprochen, fügen wir hier das benutzerdefinierte Feld hinzu:
                 base_mana_restore: Optional[int] = None,
                 **kwargs: Any): # Fängt zusätzliche, unerwartete Felder ab
        self.base_healing = base_healing
        self.base_mana_restore = base_mana_restore

    def __repr__(self) -> str:
        details = []
        if self.base_healing is not None:
            details.append(f"Heal: {self.base_healing}")
        if self.base_mana_restore is not None:
            details.append(f"Mana Restore: {self.base_mana_restore}")
        return f"ItemEffectData({', '.join(details)})"


class ItemAppliedEffectData:
    """
    Daten für einen Status-Effekt, der durch ein Item angewendet wird.
    Strukturell identisch zu `AppliedEffectData` bei Skills.
    """
    def __init__(self,
                 effect_id: str,
                 potency: float,
                 duration_rounds: int,
                 application_chance: float = 1.0,
                 **kwargs: Any):
        self.effect_id = effect_id
        self.potency = potency
        self.duration_rounds = duration_rounds
        self.application_chance = application_chance

    def __repr__(self) -> str:
        return (f"ItemAppliedEffectData(id='{self.effect_id}', pot={self.potency}, "
                f"dur={self.duration_rounds}r, chance={self.application_chance:.0%})")


class ItemTemplate:
    """
    Repräsentiert die Definition eines Item-Templates,
    geladen aus der `items.json5`-Datei.
    """
    def __init__(self,
                 item_id: str,
                 name: str,
                 description: str,
                 item_type: str,
                 effects: Dict[str, Any],
                 usable_in_combat: bool,
                 rarity: str = "common",
                 max_stack: int = 99,
                 buy_price: Optional[int] = None,
                 sell_price: Optional[int] = None,
                 **kwargs: Any): # Fängt zusätzliche, unerwartete Felder ab

        self.id: str = item_id
        self.name: str = name
        self.description: str = description
        self.item_type: str = item_type
        self.usable_in_combat: bool = usable_in_combat
        self.rarity: str = rarity
        self.max_stack: int = max_stack
        self.buy_price: Optional[int] = buy_price
        self.sell_price: Optional[int] = sell_price

        # Verarbeite die verschachtelten Effekt-Daten
        direct_effects_data = effects.get("direct_effects", {})
        self.direct_effects: Optional[ItemEffectData] = ItemEffectData(**direct_effects_data) if direct_effects_data else None

        applied_effects_data = effects.get("applied_status_effects", [])
        self.applied_status_effects: List[ItemAppliedEffectData] = [ItemAppliedEffectData(**eff) for eff in applied_effects_data]

    def __repr__(self) -> str:
        return f"ItemTemplate(id='{self.id}', name='{self.name}', type='{self.item_type}')"