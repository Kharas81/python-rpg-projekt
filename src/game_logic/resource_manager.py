class ResourceManager:
    def __init__(self, resource_type, max_resource):
        """
        Initialisiert das Ressourcenmanagement.

        :param resource_type: Typ der Ressource (z. B. 'mana', 'stamina', 'energy')
        :param max_resource: Maximale Menge der Ressource
        """
        self.resource_type = resource_type
        self.max_resource = max_resource
        self.current_resource = max_resource

    def use_resource(self, cost):
        """
        Verwendet die Ressource, wenn genügend vorhanden ist.

        :param cost: Die Menge der Ressource, die verbraucht werden soll
        :return: True, wenn die Ressource erfolgreich verwendet wurde, sonst False
        """
        if self.current_resource >= cost:
            self.current_resource -= cost
            return True
        else:
            print(f"Nicht genügend {self.resource_type}!")
            return False

    def regenerate(self, amount):
        """
        Regeneriert die Ressource bis zum Maximum.

        :param amount: Die Menge der Ressource, die regeneriert werden soll
        """
        self.current_resource = min(self.current_resource + amount, self.max_resource)

    def __str__(self):
        return f"{self.resource_type.capitalize()}: {self.current_resource}/{self.max_resource}"


# Beispielverwendung
if __name__ == "__main__":
    # Mana-Management für einen Magier
    mana_manager = ResourceManager("mana", 100)
    print(mana_manager)

    # Fähigkeit nutzen
    if mana_manager.use_resource(20):
        print("Feuerball wurde gewirkt!")
    print(mana_manager)

    # Regeneration
    mana_manager.regenerate(10)
    print(mana_manager)
