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

# Globale Variablen für Prozesse
recording_process = None
start_time = None


def signal_handler(signum, frame):
    """Handler für SIGINT (Ctrl+C)."""
    global recording_process
    logger.info("Beende Aufnahme...")
    if recording_process:
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


def get_audio_sources() -> list[tuple[str, str, bool]]:
    """
    Listet verfügbare Audio-Quellen über wpctl auf.
    Gibt Liste von (target_name, beschreibung, is_monitor) zurück.

    Für System-Audio (Sinks) wird der ALSA-Name mit .monitor verwendet,
    für Mikrofone (Sources) der direkte ALSA-Name.
    """
    sources = []
    default_sink_alsa = None
    default_source_alsa = None

    # wpctl status parsen um Default-Geräte zu finden
    try:
        result = subprocess.run(
            ["wpctl", "status"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            for line in result.stdout.split("\n"):
                # Settings-Sektion: Hole die ALSA-Namen für Defaults
                if "Audio/Sink" in line:
                    parts = line.split("Audio/Sink")
                    if len(parts) >= 2:
                        default_sink_alsa = parts[1].strip()
                elif "Audio/Source" in line:
                    parts = line.split("Audio/Source")
                    if len(parts) >= 2:
                        default_source_alsa = parts[1].strip()

    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # ALSA-Namen und Beschreibungen aus pw-cli holen
    try:
        result = subprocess.run(
            ["pw-cli", "list-objects"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            current_node_name = None
            current_media_class = None
            current_description = None

            for line in result.stdout.split("\n"):
                line = line.strip()
                if "node.name" in line and "=" in line:
                    parts = line.split("=", 1)
                    if len(parts) >= 2:
                        current_node_name = parts[1].strip().strip('"')
                elif "node.description" in line and "=" in line:
                    parts = line.split("=", 1)
                    if len(parts) >= 2:
                        current_description = parts[1].strip().strip('"')
                elif "media.class" in line and "=" in line:
                    parts = line.split("=", 1)
                    if len(parts) >= 2:
                        current_media_class = parts[1].strip().strip('"')

                        # Wenn wir node.name und media.class haben, verarbeiten
                        if current_node_name and current_media_class:
                            if current_media_class == "Audio/Sink" and current_node_name.startswith("alsa_output"):
                                # System-Audio: Monitor des Sinks
                                monitor_name = f"{current_node_name}.monitor"
                                display_name = current_description or current_node_name
                                is_default = (current_node_name == default_sink_alsa)

                                desc = f"System-Audio: {display_name}"
                                if is_default:
                                    desc += " (Standard)"
                                    sources.insert(0, (monitor_name, desc, True))
                                else:
                                    sources.append((monitor_name, desc, True))

                            elif current_media_class == "Audio/Source" and current_node_name.startswith("alsa_input"):
                                # Mikrofon: Direkte Quelle
                                display_name = current_description or current_node_name
                                is_default = (current_node_name == default_source_alsa)

                                desc = f"Mikrofon: {display_name}"
                                if is_default:
                                    desc += " (Standard)"
                                sources.append((current_node_name, desc, False))

                        # Reset nach Verarbeitung
                        current_node_name = None
                        current_media_class = None
                        current_description = None

    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return sources


def ask_audio_source(sources: list[tuple[str, str, bool]]) -> str | None:
    """Fragt den Benutzer nach der Audio-Quelle."""
    print()
    print("Audio-Quelle auswählen:")
    for i, (_, desc, _) in enumerate(sources):
        print(f"  [{i}] {desc}")
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


def ask_recording_mode() -> int | None:
    """
    Fragt den Benutzer nach dem Aufnahme-Modus.
    Gibt None zurück für unbegrenzte Aufnahme, oder Anzahl Minuten für zeitlimitiert.
    """
    print()
    print("Aufnahme-Modus:")
    print("  [0] Unbegrenzt (Ctrl+C zum Stoppen)")
    print("  [1] Zeitlimitiert (Minuten angeben)")
    print()

    while True:
        try:
            choice = input("Auswahl (0-1, Enter für unbegrenzt): ").strip()
            if choice == "" or choice == "0":
                return None
            if choice == "1":
                return ask_duration_minutes()
            print("Ungültige Auswahl, bitte 0 oder 1 eingeben.")
        except KeyboardInterrupt:
            print()
            sys.exit(0)


def ask_duration_minutes() -> int:
    """Fragt den Benutzer nach der Aufnahme-Dauer in Minuten."""
    while True:
        try:
            minutes_str = input("Aufnahme-Dauer in Minuten: ").strip()
            minutes = int(minutes_str)
            if minutes > 0:
                return minutes
            print("Bitte eine positive Zahl eingeben.")
        except ValueError:
            print("Bitte eine ganze Zahl eingeben.")
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

    # Prüfe ob parecord verfügbar ist
    result = subprocess.run(["which", "parecord"], capture_output=True)
    if result.returncode != 0:
        logger.error("parecord nicht gefunden!")
        logger.error("Bitte installieren: sudo apt install pulseaudio-utils")
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

    # Aufnahme-Modus bestimmen
    duration_minutes = ask_recording_mode()
    if duration_minutes:
        logger.info(f"Zeitlimitierte Aufnahme: {duration_minutes} Minute{'n' if duration_minutes != 1 else ''}")
    else:
        logger.info("Unbegrenzte Aufnahme (Ctrl+C zum Stoppen)")

    # Dateiname mit Zeitstempel
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"recording_{timestamp}.wav"
    filepath = output_dir / filename

    logger.info(f"Starte Aufnahme: {filename}")
    if duration_minutes:
        logger.info(f"Aufnahme stoppt automatisch nach {duration_minutes} Minute{'n' if duration_minutes != 1 else ''}...")
    else:
        logger.info("Drücke Ctrl+C zum Beenden der Aufnahme...")
    logger.info("")

    try:
        start_time = time.time()

        # Nutze parecord (PulseAudio/PipeWire-Pulse Recorder)
        # Dies ist der zuverlässigste Weg für Monitor-Aufnahmen
        record_cmd = [
            "parecord",
            "-d", source,               # Audio-Quelle (inkl. .monitor für System-Audio)
            "--file-format=wav",        # WAV-Format
            str(filepath),
        ]
        logger.debug(f"Starte Aufnahme: {' '.join(record_cmd)}")
        recording_process = subprocess.Popen(
            record_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Warte auf Prozessende (durch Signal-Handler oder Timeout)
        if duration_minutes:
            timeout_seconds = duration_minutes * 60
            try:
                recording_process.wait(timeout=timeout_seconds)
            except subprocess.TimeoutExpired:
                logger.info(f"Zeitlimit von {duration_minutes} Minute{'n' if duration_minutes != 1 else ''} erreicht")
                recording_process.terminate()
                recording_process.wait()
        else:
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
        logger.error("parecord nicht gefunden!")
        logger.error("Bitte installieren: sudo apt install pulseaudio-utils")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fehler bei Aufnahme: {e}")
        sys.exit(1)

    logger.info("App beendet")


if __name__ == "__main__":
    main()
