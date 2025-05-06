import typing
import logging

logger = logging.getLogger(__name__)

class StatusEffect:
    """
    Repräsentiert einen aktiven Status-Effekt auf einer CharacterInstance.
    """
    def __init__(self,
                 effect_id: str,
                 duration: int,
                 potency: typing.Optional[typing.Any] = None,
                 source_entity_id: typing.Optional[str] = None,
                 applied_effect_data: typing.Optional[typing.Dict[str, typing.Any]] = None):
        self.effect_id: str = effect_id
        self.duration: int = duration
        self.potency: typing.Optional[typing.Any] = potency
        self.source_entity_id: typing.Optional[str] = source_entity_id
        self.applied_effect_data = applied_effect_data if applied_effect_data else {}
        logger.debug(f"StatusEffect '{self.effect_id}' erstellt (Dauer: {self.duration}, Potenz: {self.potency})")

    def tick(self) -> bool:
        self.duration -= 1
        logger.debug(f"StatusEffect '{self.effect_id}' getickt. Verbleibende Dauer: {self.duration}")
        return self.duration <= 0

    def __repr__(self) -> str:
        details = [f"id='{self.effect_id}'", f"duration={self.duration}"]
        if self.potency is not None: details.append(f"potency={self.potency}")
        if self.source_entity_id: details.append(f"source='{self.source_entity_id}'")
        return f"<StatusEffect({', '.join(details)})>"

# --- Testblock ---
if __name__ == '__main__':
    try:
        from src.utils.logging_setup import setup_logging
        setup_logging()
    except ImportError:
        print("WARNUNG: Logging-Setup für effects.py Test nicht gefunden.")

    print("--- StatusEffect Test ---")

    burning_effect = StatusEffect(effect_id="BURNING", duration=3, potency=5, source_entity_id="Magier1")
    stunned_effect = StatusEffect(effect_id="STUNNED", duration=1)

    # KORRIGIERTE ERSTELLUNG für defense_up_effect:
    defense_up_effect_data = {"id": "DEFENSE_UP", "duration": 2, "potency": 3}
    defense_up_effect = StatusEffect(
        effect_id=defense_up_effect_data["id"], # Explizite Zuweisung
        duration=defense_up_effect_data["duration"],
        potency=defense_up_effect_data["potency"],
        source_entity_id="Kleriker1",
        applied_effect_data=defense_up_effect_data
    )

    print(f"Erstellt: {burning_effect}")
    print(f"Erstellt: {stunned_effect}")
    print(f"Erstellt: {defense_up_effect}") # Sollte jetzt funktionieren

    print("\nTicke 'BURNING':")
    expired1 = burning_effect.tick() # Dauer 2
    print(f"  Abgelaufen? {expired1} -> {burning_effect}")
    expired2 = burning_effect.tick() # Dauer 1
    print(f"  Abgelaufen? {expired2} -> {burning_effect}")
    expired3 = burning_effect.tick() # Dauer 0
    print(f"  Abgelaufen? {expired3} -> {burning_effect}")
    assert expired3 == True

    print("\nTicke 'STUNNED':")
    expired_stun = stunned_effect.tick() # Dauer 0
    print(f"  Abgelaufen? {expired_stun} -> {stunned_effect}")
    assert expired_stun == True

    print("\nAlle Effekt-Tests erfolgreich.")
