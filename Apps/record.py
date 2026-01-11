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

    # Dateiname mit Zeitstempel
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"recording_{timestamp}.wav"
    filepath = output_dir / filename

    logger.info(f"Starte Aufnahme: {filename}")
    logger.info("Drücke Ctrl+C zum Beenden der Aufnahme...")
    logger.info("")

    # pw-record starten
    cmd = [
        "pw-record",
        "--format", "s16",      # 16-bit signed
        "--rate", "44100",      # CD-Qualität
        "--channels", "2",      # Stereo
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
