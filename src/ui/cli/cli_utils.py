"""
CLI Utilities Module

Hilfsfunktionen für die Kommandozeilen-Benutzeroberfläche.
"""

import os
import platform
from typing import Tuple, Optional, Any, Union

# ANSI-Farbcodes für die Textformatierung
COLORS = {
    "black": "\033[30m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    "white": "\033[37m",
    "reset": "\033[0m",
    "bold": "\033[1m",
    "underline": "\033[4m"
}


def clear_screen() -> None:
    """
    Löscht den Bildschirminhalt basierend auf dem Betriebssystem.
    """
    if platform.system() == "Windows":
        os.system("cls")
    else:
        os.system("clear")


def colorize(text: str, color: str) -> str:
    """
    Färbt einen Text mit dem angegebenen ANSI-Farbcode.
    
    Args:
        text: Der zu färbende Text
        color: Der Name der Farbe
        
    Returns:
        Der gefärbte Text
    """
    color_code = COLORS.get(color.lower(), COLORS["reset"])
    return f"{color_code}{text}{COLORS['reset']}"


def print_title(title: str, color: str = "white") -> None:
    """
    Gibt einen formatierten Titel aus.
    
    Args:
        title: Der Titeltext
        color: Die Farbe des Titels
    """
    width = 60
    print(colorize("=" * width, color))
    print(colorize(title.center(width), color + COLORS["bold"]))
    print(colorize("=" * width, color))


def print_boxed(text: str, color: str = "white") -> None:
    """
    Gibt einen Text in einem Box-Rahmen aus.
    
    Args:
        text: Der Text
        color: Die Farbe der Box
    """
    width = 40
    print(colorize("┌" + "─" * (width - 2) + "┐", color))
    print(colorize("│" + text.center(width - 2) + "│", color))
    print(colorize("└" + "─" * (width - 2) + "┘", color))


def get_input(prompt: str, valid_range: Optional[Tuple[int, int]] = None) -> int:
    """
    Fordert eine Benutzereingabe an und validiert sie.
    
    Args:
        prompt: Der Eingabeaufforderungstext
        valid_range: Optionaler gültiger Bereich für Ganzzahlen (min, max)
        
    Returns:
        Die validierte Ganzzahl-Eingabe
    """
    while True:
        try:
            user_input = input(prompt)
            value = int(user_input)
            
            if valid_range and (value < valid_range[0] or value > valid_range[1]):
                print(f"Bitte gib eine Zahl zwischen {valid_range[0]} und {valid_range[1]} ein.")
                continue
            
            return value
        except ValueError:
            print("Bitte gib eine gültige Zahl ein.")
