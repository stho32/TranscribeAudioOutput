#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///

"""
System-Audio Aufnahme für Linux.

Nimmt den System-Audio-Output über PipeWire (pw-record) auf und
speichert ihn als WAV-Datei mit Zeitstempel im Dateinamen.

Anforderungen: siehe ../Anforderungen/record.md
"""

import argparse
import logging
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Ermittle das Verzeichnis des Scripts (Repository-Root)
SCRIPT_DIR = Path(__file__).parent.parent
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "Recordings"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Globale Variable für den Prozess
recording_process = None
start_time = None


def signal_handler(signum, frame):
    """Handler für SIGINT (Ctrl+C)."""
    global recording_process
    if recording_process:
        logger.info("Beende Aufnahme...")
        recording_process.terminate()


def format_duration(seconds: float) -> str:
    """Formatiert Sekunden als lesbare Dauer."""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    if minutes > 0:
        return f"{minutes} Minute{'n' if minutes != 1 else ''} {secs} Sekunde{'n' if secs != 1 else ''}"
    return f"{secs} Sekunde{'n' if secs != 1 else ''}"


def format_size(bytes_size: int) -> str:
    """Formatiert Bytes als lesbare Größe."""
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_size < 1024:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.1f} TB"


def get_default_monitor() -> str | None:
    """Ermittelt den Standard-Monitor-Sink (System-Audio-Output)."""
    try:
        result = subprocess.run(
            ["pactl", "get-default-sink"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            default_sink = result.stdout.strip()
            return f"{default_sink}.monitor"
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def get_audio_sources() -> list[tuple[str, str]]:
    """Listet verfügbare Audio-Quellen auf."""
    sources = []

    # Standard-Monitor (System-Output) zuerst
    monitor = get_default_monitor()
    if monitor:
        sources.append((monitor, "System-Audio (Output)"))

    # Weitere Quellen über pactl
    try:
        result = subprocess.run(
            ["pactl", "list", "sources", "short"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                parts = line.split("\t")
                if len(parts) >= 2:
                    source_name = parts[1]
                    # Überspringe den bereits hinzugefügten Monitor
                    if monitor and source_name == monitor:
                        continue
                    # Beschreibung erstellen
                    if "monitor" in source_name.lower():
                        desc = f"Monitor: {source_name}"
                    elif "input" in source_name.lower() or "mic" in source_name.lower():
                        desc = f"Mikrofon: {source_name}"
                    else:
                        desc = source_name
                    sources.append((source_name, desc))
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return sources


def ask_audio_source(sources: list[tuple[str, str]]) -> str | None:
    """Fragt den Benutzer nach der Audio-Quelle."""
    print()
    print("Audio-Quelle auswählen:")
    for i, (_, desc) in enumerate(sources):
        default_marker = " (Standard)" if i == 0 else ""
        print(f"  [{i}] {desc}{default_marker}")
    print()

    while True:
        try:
            choice = input(f"Auswahl (0-{len(sources)-1}, Enter für Standard): ").strip()
            if choice == "":
                return sources[0][0] if sources else None
            idx = int(choice)
            if 0 <= idx < len(sources):
                return sources[idx][0]
            print(f"Ungültige Auswahl, bitte 0-{len(sources)-1} eingeben.")
        except ValueError:
            print("Bitte eine Zahl eingeben.")
        except KeyboardInterrupt:
            print()
            sys.exit(0)


def main():
    global recording_process, start_time

    parser = argparse.ArgumentParser(
        description="Nimmt System-Audio auf und speichert als WAV-Datei"
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help=f"Ausgabe-Verzeichnis (Standard: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--source",
        "-s",
        help="Audio-Quelle (ohne Angabe: interaktive Auswahl, Standard ist System-Output)",
    )

    args = parser.parse_args()

    # Signal-Handler registrieren
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("App gestartet")

    # Ausgabe-Verzeichnis erstellen
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Ausgabe-Verzeichnis: {output_dir}")

    # Prüfe ob pw-record verfügbar ist
    result = subprocess.run(["which", "pw-record"], capture_output=True)
    if result.returncode != 0:
        logger.error("pw-record nicht gefunden!")
        logger.error("Bitte installieren: sudo apt install pipewire-audio-client-libraries")
        sys.exit(1)

    # Audio-Quelle bestimmen
    source = args.source
    if source is None:
        sources = get_audio_sources()
        if not sources:
            logger.error("Keine Audio-Quellen gefunden!")
            sys.exit(1)
        source = ask_audio_source(sources)

    logger.info(f"Audio-Quelle: {source}")

    # Dateiname mit Zeitstempel
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"recording_{timestamp}.wav"
    filepath = output_dir / filename

    logger.info(f"Starte Aufnahme: {filename}")
    logger.info("Drücke Ctrl+C zum Beenden der Aufnahme...")
    logger.info("")

    # pw-record starten mit --target für die Quelle
    cmd = [
        "pw-record",
        "--format", "s16",      # 16-bit signed
        "--rate", "44100",      # CD-Qualität
        "--channels", "2",      # Stereo
        "--target", source,     # Audio-Quelle
        str(filepath),
    ]

    try:
        start_time = time.time()
        recording_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Warte auf Prozessende (durch Signal-Handler)
        recording_process.wait()

        end_time = time.time()
        duration = end_time - start_time

        logger.info("")
        logger.info("=" * 50)
        logger.info("Aufnahme beendet")
        logger.info(f"Dauer: {format_duration(duration)}")

        # Dateigröße anzeigen
        if filepath.exists():
            size = filepath.stat().st_size
            logger.info(f"Gespeichert: {filepath}")
            logger.info(f"Dateigröße: {format_size(size)}")
        else:
            logger.warning("Datei wurde nicht erstellt")

        logger.info("=" * 50)

    except FileNotFoundError:
        logger.error("pw-record nicht gefunden!")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fehler bei Aufnahme: {e}")
        sys.exit(1)

    logger.info("App beendet")


if __name__ == "__main__":
    main()
