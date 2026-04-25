# CLAUDE.md

## Projektbeschreibung

TranscribeAudioOutput ist eine Sammlung von UV-basierten Python-Single-File-Scripts zur Aufnahme und Transkription von Computer-Audio-Output unter Linux. Das System nimmt System-Audio ueber PipeWire auf und transkribiert die Aufnahmen mit der OpenAI Whisper API.

## TechStack

- **Sprache**: Python >= 3.11
- **Paketmanager / Runner**: [UV](https://github.com/astral-sh/uv) (Single-File-Scripts mit eingebetteten Abhaengigkeiten)
- **Audio-Aufnahme**: PipeWire (`pw-record`)
- **Transkription**: OpenAI Whisper API (`openai` SDK)
- **Architektur-Vorlage**: python-uv-app

## Projektstruktur

```
Apps/               - UV-Single-File-Scripts (record.py, transcribe.py)
Anforderungen/      - Anforderungsdokumente im R-Nummernformat (RXXXXX-name.md)
Recordings/         - Aufnahmen und Transkriptionen (gitignored)
```

## Run-Befehle

```bash
# Audio aufnehmen (beenden mit Ctrl+C)
uv run Apps/record.py

# Neueste Aufnahme transkribieren
uv run Apps/transcribe.py

# Spezifische Datei transkribieren
uv run Apps/transcribe.py /pfad/zur/datei.wav
```

## Test-Befehle

```bash
# Aktuell keine automatisierten Tests vorhanden
# Tests koennen mit pytest ergaenzt werden:
# uv run pytest tests/
```

## Konventionen

- Apps sind UV-Single-File-Scripts mit eingebetteten Abhaengigkeiten (`# /// script` Header)
- Anforderungen folgen dem Nummernformat `RXXXXX-kurzname.md` mit YAML-Frontmatter
- Aufnahmen werden im `Recordings/`-Verzeichnis gespeichert (nicht im Git)
- Umgebungsvariable `OPENAI_API_KEY` muss fuer Transkription gesetzt sein
- Logging erfolgt ueber das Python `logging`-Modul
