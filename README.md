# TranscribeAudioOutput

Dieses Repository enthält UV-basierte Python-Anwendungen als Single-File-Scripts zur Aufnahme und Transkription von System-Audio unter Linux.

## Struktur

- **Anforderungen/** - Anforderungsdokumente für neue Apps (Markdown-Dateien)
- **Apps/** - Fertige UV-Single-File-Scripts
- **Recordings/** - Aufnahmen und Transkriptionen (in .gitignore)

## Voraussetzungen

- Python >= 3.11
- [UV](https://github.com/astral-sh/uv) installiert
- PipeWire mit `pw-record` (für Aufnahme)
- OpenAI API-Key (für Transkription)

```bash
# PipeWire Tools installieren (falls nicht vorhanden)
sudo apt install pipewire-audio-client-libraries

# OpenAI API-Key setzen
export OPENAI_API_KEY='sk-...'
```

## Apps

| App | Beschreibung |
|-----|--------------|
| [record.py](Apps/record.py) | Nimmt System-Audio auf und speichert als WAV |
| [transcribe.py](Apps/transcribe.py) | Transkribiert Audio-Dateien mit OpenAI Whisper API |

## Verwendung

### 1. Audio aufnehmen

```bash
# Startet Aufnahme (beenden mit Ctrl+C)
uv run Apps/record.py
```

Aufnahmen werden in `Recordings/` gespeichert mit Zeitstempel im Namen:
`recording_20240111_143052.wav`

### 2. Audio transkribieren

```bash
# Neueste Aufnahme transkribieren
uv run Apps/transcribe.py

# Mit Sprache (schneller und genauer)
uv run Apps/transcribe.py --language de

# Spezifische Datei transkribieren
uv run Apps/transcribe.py Recordings/recording_20240111_143052.wav
```

Die Transkription wird automatisch als `.txt` neben der Audio-Datei gespeichert.

## Workflow-Beispiel

```bash
# 1. Audio aufnehmen (z.B. von YouTube, Meeting, etc.)
uv run Apps/record.py
# ... Audio abspielen, dann Ctrl+C zum Stoppen

# 2. Transkribieren
uv run Apps/transcribe.py --language de

# Ergebnis in Recordings/:
# recording_20240111_143052.wav  (Audio)
# recording_20240111_143052.txt  (Transkription)
```

## Hinweise

- **Dateigröße**: OpenAI Whisper API unterstützt max. 25 MB. Bei größeren Dateien:
  ```bash
  ffmpeg -i recording.wav -b:a 64k recording.mp3
  ```
- **Kosten**: OpenAI Whisper API kostet ca. $0.006 pro Minute Audio

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

# Code hier...
```
