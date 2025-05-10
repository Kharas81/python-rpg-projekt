# src/ui/cli_menu.py
"""
Funktionen zur Anzeige von textbasierten Menüs und zur Abfrage von Benutzereingaben.
"""
from typing import List, Tuple, Callable, Any, Optional
from src.ui import cli_output # Für farbige Ausgaben

def display_menu(title: str, options: List[Tuple[str, Optional[Callable[[], Any]]]]) -> Any:
    """
    Zeigt ein nummeriertes Menü an und gibt das Ergebnis der ausgewählten Funktion zurück.
    options: Eine Liste von Tupeln, wobei jedes Tupel (Beschreibung, Funktion_oder_Wert) ist.
             Wenn Funktion None ist, wird der Index+1 als Wert zurückgegeben (für Untermenüs).
             Wenn Funktion eine Callable ist, wird sie aufgerufen und ihr Ergebnis zurückgegeben.
    """
    cli_output.print_message(f"\n--- {title} ---", cli_output.Colors.BOLD + cli_output.Colors.CYAN)
    for i, (description, _) in enumerate(options):
        cli_output.print_message(f"{i+1}. {description}")
    cli_output.print_message("0. Zurück / Beenden", cli_output.Colors.YELLOW) # Option 0 ist immer Zurück/Beenden

    while True:
        try:
            choice_str = input(cli_output._c("Wähle eine Option: ", cli_output.Colors.LIGHT_GREEN))
            choice = int(choice_str)
            
            if choice == 0:
                return "exit_menu" # Spezieller Rückgabewert für "Zurück/Beenden"
                
            if 1 <= choice <= len(options):
                _, func_or_value = options[choice - 1]
                if func_or_value is None: # Nur Auswahl, Index+1 zurückgeben
                    return choice 
                elif callable(func_or_value): # Funktion aufrufen
                    return func_or_value() 
                else: # Direkter Wert (seltener Fall, aber möglich)
                    return func_or_value
            else:
                cli_output.print_message("Ungültige Auswahl. Bitte erneut versuchen.", cli_output.Colors.RED)
        except ValueError:
            cli_output.print_message("Ungültige Eingabe. Bitte eine Zahl eingeben.", cli_output.Colors.RED)
        except Exception as e:
             cli_output.print_message(f"Ein Fehler ist aufgetreten: {e}", cli_output.Colors.RED)
             return "error"

def get_user_input_int(prompt: str, min_val: Optional[int] = None, max_val: Optional[int] = None) -> Optional[int]:
    """Fragt den Benutzer nach einer Ganzzahleingabe mit optionalen Grenzen."""
    while True:
        try:
            val_str = input(cli_output._c(f"{prompt} ", cli_output.Colors.LIGHT_GREEN))
            val = int(val_str)
            if min_val is not None and val < min_val:
                cli_output.print_message(f"Eingabe muss mindestens {min_val} sein.", cli_output.Colors.RED)
                continue
            if max_val is not None and val > max_val:
                cli_output.print_message(f"Eingabe darf höchstens {max_val} sein.", cli_output.Colors.RED)
                continue
            return val
        except ValueError:
            cli_output.print_message("Ungültige Eingabe. Bitte eine Zahl eingeben.", cli_output.Colors.RED)
        except KeyboardInterrupt: 
            cli_output.print_message("\nEingabe abgebrochen.", cli_output.Colors.YELLOW)
            return None

if __name__ == '__main__':
    def test_func_1():
        print("Funktion 1 wurde ausgeführt!")
        return "result_func1"

    def test_func_2():
        val = get_user_input_int("Gib eine Zahl zwischen 1 und 10 ein:", 1, 10)
        print(f"Funktion 2 wurde ausgeführt! Eingegebener Wert: {val}")
        return f"result_func2_val_{val}"

    test_options = [
        ("Option 1 (führt Funktion aus)", test_func_1),
        ("Option 2 (fragt nach Input)", test_func_2),
        ("Option 3 (gibt nur Auswahl zurück)", None)
    ]
    
    result = display_menu("Test Hauptmenü", test_options)
    print(f"\nMenüergebnis: {result}")

    if result == 3: 
        sub_options = [("Sub Option A", None), ("Sub Option B", None)]
        sub_result = display_menu("Test Untermenü", sub_options)
        print(f"Untermenü Ergebnis: {sub_result}")