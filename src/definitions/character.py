from game_logic.resource_manager import ResourceManager

class Character:
    def __init__(self, name, char_class, attributes, skills, resource_type):
        self.name = name
        self.char_class = char_class
        self.attributes = attributes
        self.skills = skills
        self.resource_manager = ResourceManager(resource_type, attributes.get(resource_type, 100))

    def use_skill(self, skill):
        """
        Nutzt eine Fähigkeit, wenn genügend Ressourcen vorhanden sind.

        :param skill: Ein Skill-Dictionary mit Ressourcenkosten und Cooldown
        """
        cost = skill["cost"]
        if self.resource_manager.use_resource(cost):
            print(f"{self.name} nutzt {skill['name']}!")
        else:
            print(f"{self.name} hat nicht genügend {self.resource_manager.resource_type}.")

    def regenerate_resources(self):
        """
        Regeneriert Ressourcen automatisch basierend auf dem Ressourcentyp.
        """
        if self.resource_manager.resource_type == "mana":
            self.resource_manager.regenerate(5)
        elif self.resource_manager.resource_type == "stamina":
            self.resource_manager.regenerate(10)
        elif self.resource_manager.resource_type == "energy":
            # Energie regeneriert sich bei Aktionen, daher keine automatische Regeneration
            pass
        print(self.resource_manager)


# Beispielverwendung
if __name__ == "__main__":
    # Charakter erstellen
    krieger = Character(
        name="Thor",
        char_class="Krieger",
        attributes={"health": 100, "stamina": 50, "strength": 30},
        skills=[{"name": "Schwertstoß", "cost": 10, "resource": "stamina", "cooldown": 1}],
        resource_type="stamina"
    )
    print(krieger.resource_manager)

    # Fähigkeit nutzen
    krieger.use_skill(krieger.skills[0])

    # Ressourcen regenerieren
    krieger.regenerate_resources()
