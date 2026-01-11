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
import sys
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


def format_size(bytes_size: int) -> str:
    """Formatiert Bytes als lesbare Größe."""
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_size < 1024:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.1f} TB"


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

    if file_size > MAX_FILE_SIZE:
        logger.error(f"Datei zu groß! Max. {format_size(MAX_FILE_SIZE)} für OpenAI API")
        logger.error("Tipp: Konvertiere zu MP3 für kleinere Dateigröße:")
        logger.error(f"  ffmpeg -i '{file_path}' -b:a 64k '{file_path.stem}.mp3'")
        sys.exit(1)

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

    # Transkribieren
    try:
        text = transcribe_file(client, file_path, language=language)
    except Exception as e:
        logger.error(f"Fehler bei Transkription: {e}")
        sys.exit(1)

    # Ausgabe
    print()
    print("=" * 50)
    print("TRANSKRIPTION")
    print("=" * 50)
    print()
    print(text)
    print()
    print("=" * 50)

    # Transkription als .txt neben der Audio-Datei speichern
    txt_path = file_path.with_suffix(".txt")
    txt_path.write_text(text, encoding="utf-8")
    logger.info(f"Transkription gespeichert: {txt_path}")

    logger.info("App beendet")


if __name__ == "__main__":
    main()
