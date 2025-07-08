# src/definitions/quest.py
"""
Definiert die Datenstrukturen für Quests und ihre Ziele.
"""
from typing import List, Dict, Any

class QuestObjective:
    """
    Definiert ein einzelnes Ziel innerhalb einer Quest.
    """
    # HINZUGEFÜGT: description_template im Konstruktor
    def __init__(self, type: str, target_id: str, required_amount: int, description_template: str):
        self.type = type
        self.target_id = target_id
        self.required_amount = required_amount
        self.current_amount = 0
        # HINZUGEFÜGT: Das neue Attribut
        self.description_template = description_template

    def is_complete(self) -> bool:
        return self.current_amount >= self.required_amount

    def __repr__(self) -> str:
        return f"Objective({self.type} {self.target_id}: {self.current_amount}/{self.required_amount})"


class Quest:
    """
    Repräsentiert eine vollständige Quest mit all ihren Zielen.
    """
    def __init__(self, quest_id: str, name: str, description: str, objectives: List[Dict[str, Any]]):
        self.quest_id = quest_id
        self.name = name
        self.description = description
        self.objectives = [QuestObjective(**obj_data) for obj_data in objectives]
        self.is_complete = False

    def update_completion_status(self):
        """Prüft alle Ziele und setzt den Quest-Status auf 'is_complete', wenn alle erledigt sind."""
        if all(obj.is_complete() for obj in self.objectives):
            self.is_complete = True
            return True
        return False

    def __repr__(self) -> str:
        return f"Quest(id='{self.quest_id}', name='{self.name}', complete={self.is_complete})"