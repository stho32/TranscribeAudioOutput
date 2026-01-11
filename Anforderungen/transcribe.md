# Transcribe - Audio-Transkription mit OpenAI

## Zweck

Transkribiert Audio-Dateien (WAV, MP3, etc.) mit der OpenAI Whisper API zu Text.

## Funktionale Anforderungen

- [x] Audio-Dateien mit OpenAI Whisper API transkribieren
- [x] Unterstützung für WAV, MP3, M4A, WEBM, MP4
- [x] Sprache konfigurierbar (Standard: automatische Erkennung)
- [x] Ausgabe als Text auf STDOUT
- [x] Optional: Speichern als .txt Datei neben der Audio-Datei
- [x] Verarbeitung der neuesten Datei im Verzeichnis (wenn kein Pfad angegeben)

## Technische Anforderungen

- Python >= 3.11
- Abhängigkeiten:
  - `openai` - OpenAI Python SDK

## Umgebungsvariablen

- `OPENAI_API_KEY` - OpenAI API-Schlüssel (erforderlich)

## Verwendung

```bash
# Spezifische Datei transkribieren
uv run Apps/transcribe.py /pfad/zur/datei.wav

# Neueste Datei im Standard-Verzeichnis transkribieren
uv run Apps/transcribe.py

# Mit spezifischer Sprache
uv run Apps/transcribe.py recording.wav --language de

# Ausgabe in Datei speichern
uv run Apps/transcribe.py recording.wav --save
```

## Beispiele

```bash
$ uv run Apps/transcribe.py ~/transcripts/recording_20240111_143000.wav
2024-01-11 14:40:00 [INFO] App gestartet
2024-01-11 14:40:00 [INFO] Transkribiere: recording_20240111_143000.wav
2024-01-11 14:40:00 [INFO] Dateigröße: 52.3 MB
2024-01-11 14:40:05 [INFO] Sende an OpenAI Whisper API...
2024-01-11 14:40:30 [INFO] Transkription erfolgreich (25.3 Sekunden)

=== TRANSKRIPTION ===

Hallo und willkommen zu diesem Tutorial. Heute werden wir uns ansehen,
wie man Python-Anwendungen mit UV erstellt...

=====================

2024-01-11 14:40:30 [INFO] App beendet

$ uv run Apps/transcribe.py ~/transcripts/recording_20240111_143000.wav --save
2024-01-11 14:41:00 [INFO] Transkription gespeichert: recording_20240111_143000.txt
```

## OpenAI Whisper API

- Modell: `whisper-1`
- Max. Dateigröße: 25 MB
- Unterstützte Formate: mp3, mp4, mpeg, mpga, m4a, wav, webm
- Große Dateien werden automatisch aufgeteilt
