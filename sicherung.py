import os

def save_project_to_single_txt(source_dir, output_file):
    """
    Speichert den gesamten Inhalt eines Projekts in einer einzigen .txt-Datei.
    Der .git-Ordner wird ignoriert.

    :param source_dir: Quellverzeichnis, das durchsucht werden soll
    :param output_file: Pfad zur Ausgabedatei (.txt)
    """
    try:
        with open(output_file, 'w', encoding='utf-8') as outfile:
            for root, dirs, files in os.walk(source_dir):
                # .git-Ordner ignorieren
                if '.git' in dirs:
                    dirs.remove('.git')

                for file in files:
                    source_file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(source_file_path, source_dir)

                    try:
                        # Dateiinhalt lesen
                        with open(source_file_path, 'r', encoding='utf-8') as infile:
                            content = infile.read()

                        # Dateiinhalt in die Ausgabedatei schreiben
                        outfile.write(f"===== {relative_path} =====\n")
                        outfile.write(content)
                        outfile.write("\n\n")

                        print(f"Gespeichert: {relative_path}")

                    except Exception as e:
                        print(f"Fehler beim Verarbeiten von {source_file_path}: {e}")
                        outfile.write(f"===== {relative_path} (Fehler beim Lesen) =====\n\n")

        print(f"Projekt erfolgreich in {output_file} gespeichert.")
    except Exception as e:
        print(f"Fehler beim Speichern des Projekts: {e}")

if __name__ == "__main__":
    # Quell- und Zielverzeichnis festlegen
    source_directory = "/workspaces/python-rpg-projekt"  # Dein Projektverzeichnis
    output_file_path = "/workspaces/python-rpg-projekt/sicherung.txt"  # Ziel-Datei

    save_project_to_single_txt(source_directory, output_file_path)