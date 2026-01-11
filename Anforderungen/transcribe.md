# Transcribe - Audio-Output Transkription

## Zweck

Transkribiert den Audio-Output des Linux-Systems in Echtzeit zu Text. Nutzt PipeWire (`pw-record`) zur Audio-Aufnahme und OpenAI Whisper für die Transkription.

## Funktionale Anforderungen

- [x] Audio-Output des Systems über PipeWire aufnehmen
- [x] Echtzeit- oder Chunk-basierte Transkription
- [x] Ausgabe der Transkription auf STDOUT
- [x] Graceful Shutdown mit Ctrl+C
- [x] Automatische Erkennung des Monitor-Sinks

## Technische Anforderungen

- Python >= 3.11
- PipeWire mit `pw-record` (extern installiert)
- Abhängigkeiten:
  - `openai-whisper` oder `faster-whisper` für lokale Transkription
  - `numpy` für Audio-Verarbeitung

## Verwendung

```bash
# Standard-Ausführung (nimmt System-Audio auf und transkribiert)
uv run Apps/transcribe.py

# Mit spezifischem Audio-Device
uv run Apps/transcribe.py --device <device-name>

# Mit anderem Whisper-Modell
uv run Apps/transcribe.py --model medium
```

## Beispiele

```bash
$ uv run Apps/transcribe.py
2024-01-11 10:30:00 [INFO] App gestartet
2024-01-11 10:30:01 [INFO] Verwende Audio-Device: alsa_output.pci-0000_00_1f.3.analog-stereo.monitor
2024-01-11 10:30:02 [INFO] Whisper-Modell 'base' geladen
2024-01-11 10:30:05 [INFO] Aufnahme gestartet, drücke Ctrl+C zum Beenden
2024-01-11 10:30:10 [INFO] Transkription: "Hello and welcome to today's presentation..."
2024-01-11 10:30:15 [INFO] Transkription: "We will be discussing the new features..."
^C
2024-01-11 10:30:20 [INFO] Aufnahme beendet
2024-01-11 10:30:20 [INFO] App beendet
```

## Architektur

1. **Audio-Aufnahme**: `pw-record` nimmt den Monitor-Sink auf (System-Audio-Output)
2. **Chunking**: Audio wird in Segmente aufgeteilt (z.B. 5-10 Sekunden)
3. **Transkription**: Jedes Segment wird mit Whisper transkribiert
4. **Ausgabe**: Transkribierter Text wird auf STDOUT ausgegeben
