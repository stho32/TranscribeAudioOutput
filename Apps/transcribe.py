#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "openai>=1.0.0",
# ]
# ///

"""
Audio-Transkription mit OpenAI Whisper API.

Transkribiert Audio-Dateien (WAV, MP3, etc.) zu Text.

Anforderungen: siehe ../Anforderungen/transcribe.md
"""

import argparse
import logging
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from openai import OpenAI

# Ermittle das Verzeichnis des Scripts (Repository-Root)
SCRIPT_DIR = Path(__file__).parent.parent
DEFAULT_RECORDINGS_DIR = SCRIPT_DIR / "Recordings"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Unterstützte Audio-Formate
SUPPORTED_FORMATS = {".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".wav", ".webm"}

# Max. Dateigröße für OpenAI API (25 MB)
MAX_FILE_SIZE = 25 * 1024 * 1024

# Bitrate für MP3-Konvertierung (64 kbps ist ausreichend für Sprache)
MP3_BITRATE = "64k"


def format_size(bytes_size: int) -> str:
    """Formatiert Bytes als lesbare Größe."""
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_size < 1024:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.1f} TB"


def convert_to_mp3(input_path: Path, output_path: Path) -> bool:
    """
    Konvertiert eine Audio-Datei zu MP3 mit ffmpeg.

    Args:
        input_path: Pfad zur Eingabedatei
        output_path: Pfad zur Ausgabedatei

    Returns:
        True wenn erfolgreich, False sonst
    """
    logger.info(f"Konvertiere zu MP3 ({MP3_BITRATE})...")

    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-i", str(input_path),
                "-b:a", MP3_BITRATE,
                "-y",  # Überschreibe ohne Nachfrage
                str(output_path),
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            logger.error(f"ffmpeg Fehler: {result.stderr}")
            return False
        return True
    except FileNotFoundError:
        logger.error("ffmpeg nicht gefunden!")
        logger.error("Bitte installieren: sudo apt install ffmpeg")
        return False


def find_latest_recording(directory: Path) -> Path | None:
    """Findet die neueste Audio-Datei im Verzeichnis."""
    audio_files = []
    for ext in SUPPORTED_FORMATS:
        audio_files.extend(directory.glob(f"*{ext}"))

    if not audio_files:
        return None

    # Sortiere nach Änderungszeit (neueste zuerst)
    audio_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    return audio_files[0]


def transcribe_file(
    client: OpenAI,
    file_path: Path,
    language: str | None = None,
) -> str:
    """
    Transkribiert eine Audio-Datei mit der OpenAI Whisper API.

    Args:
        client: OpenAI-Client
        file_path: Pfad zur Audio-Datei
        language: Optional: Sprache (z.B. "de", "en")

    Returns:
        Transkribierter Text
    """
    logger.info(f"Sende an OpenAI Whisper API...")

    start_time = time.time()

    with open(file_path, "rb") as audio_file:
        kwargs = {
            "model": "whisper-1",
            "file": audio_file,
        }
        if language:
            kwargs["language"] = language

        response = client.audio.transcriptions.create(**kwargs)

    duration = time.time() - start_time
    logger.info(f"Transkription erfolgreich ({duration:.1f} Sekunden)")

    return response.text


def main():
    parser = argparse.ArgumentParser(
        description="Transkribiert Audio-Dateien mit OpenAI Whisper API"
    )
    parser.add_argument(
        "file",
        nargs="?",
        help="Pfad zur Audio-Datei (ohne Angabe: neueste Datei in Recordings/)",
    )
    parser.add_argument(
        "--language",
        "-l",
        help="Sprache für Transkription (z.B. 'de', 'en'). Standard: automatische Erkennung",
    )
    parser.add_argument(
        "--dir",
        "-d",
        default=str(DEFAULT_RECORDINGS_DIR),
        help=f"Verzeichnis für Suche nach neuester Datei (Standard: {DEFAULT_RECORDINGS_DIR})",
    )

    args = parser.parse_args()

    logger.info("App gestartet")

    # API-Key prüfen
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY Umgebungsvariable nicht gesetzt!")
        logger.error("Bitte setzen: export OPENAI_API_KEY='sk-...'")
        sys.exit(1)

    # Audio-Datei finden
    if args.file:
        file_path = Path(args.file).expanduser().resolve()
    else:
        search_dir = Path(args.dir).expanduser()
        if not search_dir.exists():
            logger.error(f"Verzeichnis nicht gefunden: {search_dir}")
            sys.exit(1)

        file_path = find_latest_recording(search_dir)
        if not file_path:
            logger.error(f"Keine Audio-Dateien gefunden in: {search_dir}")
            sys.exit(1)

        logger.info(f"Neueste Datei gefunden: {file_path.name}")

    # Datei validieren
    if not file_path.exists():
        logger.error(f"Datei nicht gefunden: {file_path}")
        sys.exit(1)

    if file_path.suffix.lower() not in SUPPORTED_FORMATS:
        logger.error(f"Nicht unterstütztes Format: {file_path.suffix}")
        logger.error(f"Unterstützt: {', '.join(SUPPORTED_FORMATS)}")
        sys.exit(1)

    file_size = file_path.stat().st_size
    logger.info(f"Transkribiere: {file_path.name}")
    logger.info(f"Dateigröße: {format_size(file_size)}")

    if file_size == 0:
        logger.error("Datei ist leer!")
        sys.exit(1)

    # Sprache (None = automatische Erkennung)
    language = args.language
    if language:
        logger.info(f"Sprache: {language}")
    else:
        logger.info("Sprache: Automatische Erkennung")

    # OpenAI-Client erstellen
    client = OpenAI(api_key=api_key)

    # Datei für Transkription vorbereiten (ggf. konvertieren)
    transcribe_path = file_path
    temp_file = None

    if file_size > MAX_FILE_SIZE:
        logger.warning(f"Datei zu groß ({format_size(file_size)}) - konvertiere automatisch zu MP3...")

        # Temporäre MP3-Datei erstellen
        temp_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        temp_file.close()
        temp_path = Path(temp_file.name)

        if not convert_to_mp3(file_path, temp_path):
            temp_path.unlink(missing_ok=True)
            sys.exit(1)

        temp_size = temp_path.stat().st_size
        logger.info(f"Konvertiert: {format_size(temp_size)}")

        if temp_size > MAX_FILE_SIZE:
            logger.error(f"Konvertierte Datei immer noch zu groß ({format_size(temp_size)})")
            temp_path.unlink(missing_ok=True)
            sys.exit(1)

        transcribe_path = temp_path

    # Transkribieren
    try:
        text = transcribe_file(client, transcribe_path, language=language)
    except Exception as e:
        logger.error(f"Fehler bei Transkription: {e}")
        if temp_file:
            Path(temp_file.name).unlink(missing_ok=True)
        sys.exit(1)
    finally:
        # Temporäre Datei aufräumen
        if temp_file:
            Path(temp_file.name).unlink(missing_ok=True)

    # Transkription als .txt neben der ORIGINAL Audio-Datei speichern
    txt_path = file_path.with_suffix(".txt")
    txt_path.write_text(text, encoding="utf-8")
    logger.info(f"Transkription gespeichert: {txt_path}")

    # Transkription ausgeben
    print()
    print(text)

    logger.info("App beendet")


if __name__ == "__main__":
    main()
