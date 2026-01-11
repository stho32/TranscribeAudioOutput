# TranscribeAudioOutput

Dieses Repository enthält UV-basierte Python-Anwendungen als Single-File-Scripts.

## Struktur

- **Anforderungen/** - Anforderungsdokumente für neue Apps (Markdown-Dateien)
- **Apps/** - Fertige UV-Single-File-Scripts

## Verwendung

### App ausführen

```bash
uv run Apps/<app-name>.py
```

### Neue App erstellen

1. Anforderungsdokument in `Anforderungen/` anlegen
2. App in `Apps/` implementieren

## Apps

| App | Beschreibung |
|-----|--------------|
| [transcribe.py](Apps/transcribe.py) | Transkribiert Audio-Output des Systems in Echtzeit |

## UV Single-File Script Format

Jede App ist ein einzelnes Python-Script mit eingebetteten Abhängigkeiten:

```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "package1",
#     "package2>=1.0",
# ]
# ///

"""
App-Beschreibung hier.
"""

# Code hier...
```
