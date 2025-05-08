Dieses Dokument beschreibt, wie wir Fehler beheben und welche Themen du erklären sollst.
1. Debugging-Ansatz
Ansatz: Frage nach relevanten Code-Ausschnitten (möglichst die relevanten kleinen Funktionen/Module betreffend), relevanten JSON5-Inhalten und vollständigen Fehlermeldungen/Tracebacks aus dem Terminal (in Codespaces/VS Code).
Tools: print(), logging-Modul (src/utils/logging_setup.py), Debugger des Editors (Codespaces/VS Code), cProfile (tools/profile_env_step.py), Tracebacks.
Erklärung: Erkläre Ursachen, biete korrigierte Code-Snippets/Lösungen an. Fokus auf robuste Fehlerbehandlung (try...except...finally, with...as...).