import os

def save_project_as_txt(project_dir: str, output_file: str) -> None:
    """
    Speichert den gesamten Inhalt eines Projekts in einer einzigen .txt-Datei.

    Args:
        project_dir (str): Der Pfad zum Projektverzeichnis.
        output_file (str): Der Pfad zur Ausgabedatei (.txt).
    """
    try:
        with open(output_file, 'w') as outfile:
            for root, _, files in os.walk(project_dir):
                for file in files:
                    # Ignoriere bestimmte Dateitypen (z.B. __pycache__)
                    if file.endswith('.pyc') or file == '__pycache__':
                        continue
                    
                    file_path = os.path.join(root, file)
                    outfile.write(f"===== {file_path} =====\n")
                    
                    try:
                        with open(file_path, 'r') as infile:
                            outfile.write(infile.read())
                    except Exception as e:
                        outfile.write(f"Fehler beim Lesen der Datei: {e}\n")
                    
                    outfile.write("\n\n")
        
        print(f"Projekt erfolgreich in {output_file} gespeichert.")
    except Exception as e:
        print(f"Fehler beim Speichern des Projekts: {e}")

# Pfade definieren
project_directory = "/workspaces/python-rpg-projekt"  # Dein Projektverzeichnis
output_txt_file = "/workspaces/python-rpg-projekt/project_backup.txt"  # Ziel .txt-Datei

# Funktion aufrufen
save_project_as_txt(project_directory, output_txt_file)