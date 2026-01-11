# Record - System-Audio Aufnahme

## Zweck

Nimmt den System-Audio-Output unter Linux auf und speichert ihn als WAV-Datei mit automatischem Zeitstempel im Dateinamen.

## Funktionale Anforderungen

- [x] Audio-Output des Systems über PipeWire (pw-record) aufnehmen
- [x] WAV-Datei mit Zeitstempel im Namen speichern (z.B. `recording_20240111_143052.wav`)
- [x] Graceful Shutdown mit Ctrl+C
- [x] Ausgabe-Verzeichnis konfigurierbar (Standard: `~/transcripts`)
- [x] Anzeige der Aufnahmedauer

## Technische Anforderungen

- Python >= 3.11
- PipeWire mit `pw-record` (extern installiert)
- Keine Python-Abhängigkeiten nötig (nur Standardbibliothek)

## Verwendung

```bash
# Standard-Ausführung (speichert in ~/transcripts/)
uv run Apps/record.py

# Mit anderem Ausgabe-Verzeichnis
uv run Apps/record.py --output-dir /pfad/zum/ordner

# Aufnahme beenden: Ctrl+C drücken
```

## Beispiele

```bash
$ uv run Apps/record.py
2024-01-11 14:30:00 [INFO] App gestartet
2024-01-11 14:30:00 [INFO] Ausgabe-Verzeichnis: /home/user/transcripts
2024-01-11 14:30:00 [INFO] Starte Aufnahme: recording_20240111_143000.wav
2024-01-11 14:30:00 [INFO] Drücke Ctrl+C zum Beenden der Aufnahme...
^C
2024-01-11 14:35:30 [INFO] Aufnahme beendet
2024-01-11 14:35:30 [INFO] Dauer: 5 Minuten 30 Sekunden
2024-01-11 14:35:30 [INFO] Gespeichert: /home/user/transcripts/recording_20240111_143000.wav
2024-01-11 14:35:30 [INFO] Dateigröße: 52.3 MB
```

## Ausgabeformat

- Format: WAV (unkomprimiert)
- Sample-Rate: 44100 Hz (CD-Qualität)
- Kanäle: Stereo (2)
- Bit-Tiefe: 16-bit
