# R00001: MP3-Unterstützung für Batch-Transkription

## Beschreibung

Die Funktion `find_untranscribed_recordings()` in `transcribe.py` sucht aktuell nur nach `*.wav`-Dateien. Obwohl die Anwendung bereits alle von der OpenAI Whisper API unterstützten Formate verarbeiten kann (MP3, MP4, M4A, WAV, WEBM etc.), werden Nicht-WAV-Dateien im Batch-Modus ignoriert. Die Funktion soll alle unterstützten Audio-Formate finden und zur Transkription anbieten.

## Akzeptanzkriterien

### Datei-Erkennung
- [ ] `find_untranscribed_recordings()` findet alle Dateien mit Endungen aus `SUPPORTED_FORMATS`
- [ ] MP3-Dateien im Recordings-Verzeichnis werden erkannt und verarbeitet
- [ ] Für jedes unterstützte Format wird geprüft, ob bereits eine `.txt`-Datei existiert

### Konsistenz
- [ ] Beschreibungstexte in argparse und Log-Meldungen spiegeln wider, dass nicht nur WAV-Dateien verarbeitet werden
- [ ] Funktionsname und Docstring werden angepasst

## Status

- [ ] Offen

## Technische Details

### Zu ändernde Dateien

| Datei | Änderung |
|-------|----------|
| `Apps/transcribe.py` | `find_untranscribed_recordings()`: Glob über alle `SUPPORTED_FORMATS` statt nur `*.wav` |
| `Apps/transcribe.py` | argparse-Beschreibung und Log-Meldungen anpassen (nicht nur "WAV") |

### Betroffene Code-Stellen

| Stelle | Zeile | Änderung |
|--------|-------|----------|
| `find_untranscribed_recordings()` | 291-303 | `*.wav` durch Iteration über `SUPPORTED_FORMATS` ersetzen |
| `argparse.ArgumentParser(description=...)` | 343-345 | "WAV-Dateien" durch "Audio-Dateien" ersetzen |
| Log-Meldung "Keine unverarbeiteten WAV-Dateien" | 379 | "WAV-Dateien" durch "Audio-Dateien" ersetzen |

### Vermutete Implementierung

```python
def find_untranscribed_recordings(directory: Path) -> list[Path]:
    """Findet alle Audio-Dateien ohne entsprechende .txt-Datei."""
    audio_files = []
    for ext in SUPPORTED_FORMATS:
        audio_files.extend(directory.glob(f"*{ext}"))

    untranscribed = [
        f for f in audio_files
        if not f.with_suffix(".txt").exists()
    ]

    untranscribed.sort(key=lambda f: f.stat().st_mtime)
    return untranscribed
```

## Abhängigkeiten

- Abhängig von: keine
- Blockiert: keine

## Notizen

- Die Konstante `SUPPORTED_FORMATS` existiert bereits und enthält: `.mp3`, `.mp4`, `.mpeg`, `.mpga`, `.m4a`, `.wav`, `.webm`
- Die eigentliche Transkriptions-Logik (Konvertierung, Segmentierung, API-Aufruf) unterstützt bereits alle Formate — nur die Dateisuche ist auf WAV beschränkt
- Im Recordings-Verzeichnis liegt aktuell: `768-ChaseHughes-v2_nn50_5a4618c8.mp3`
