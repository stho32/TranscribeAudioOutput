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
import re
import shutil
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

# Segment-Länge in Sekunden (10 Minuten = 600 Sekunden)
# Bei 64 kbps ergibt das ca. 4.8 MB pro Segment
SEGMENT_DURATION = 600

# Überlappung in Sekunden (30 Sekunden Überlappung für saubere Übergänge)
SEGMENT_OVERLAP = 30


def format_size(bytes_size: int) -> str:
    """Formatiert Bytes als lesbare Größe."""
    for unit in ["B", "KB", "MB", "GB"]:
        if bytes_size < 1024:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.1f} TB"


def get_audio_duration(file_path: Path) -> float | None:
    """
    Ermittelt die Dauer einer Audio-Datei in Sekunden mit ffprobe.

    Returns:
        Dauer in Sekunden oder None bei Fehler
    """
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(file_path),
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return float(result.stdout.strip())
        return None
    except (FileNotFoundError, ValueError):
        return None


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


def split_audio_to_segments(input_path: Path, temp_dir: Path) -> list[Path]:
    """
    Teilt eine Audio-Datei in überlappende Segmente und konvertiert zu MP3.

    Die Segmente überlappen sich um SEGMENT_OVERLAP Sekunden, damit keine
    Wörter an den Übergangsstellen abgeschnitten werden.

    Args:
        input_path: Pfad zur Eingabedatei
        temp_dir: Verzeichnis für temporäre Segment-Dateien

    Returns:
        Liste der Segment-Dateipfade (sortiert nach Reihenfolge)
    """
    duration = get_audio_duration(input_path)
    if duration is None:
        logger.error("Konnte Audio-Dauer nicht ermitteln")
        return []

    # Berechne Segment-Startzeiten mit Überlappung
    # Effektiver Fortschritt pro Segment = SEGMENT_DURATION - SEGMENT_OVERLAP
    step = SEGMENT_DURATION - SEGMENT_OVERLAP
    segment_starts = []
    start = 0.0
    while start < duration:
        segment_starts.append(start)
        start += step

    num_segments = len(segment_starts)
    logger.info(f"Audio-Dauer: {duration/60:.1f} Minuten - teile in {num_segments} überlappende Segment(e)")

    segments = []
    for i, start_time in enumerate(segment_starts):
        segment_path = temp_dir / f"segment_{i:03d}.mp3"

        # Für das letzte Segment: bis zum Ende
        remaining = duration - start_time
        segment_len = min(SEGMENT_DURATION, remaining)

        logger.info(f"Erstelle Segment {i+1}/{num_segments} (ab {start_time/60:.1f} min)...")

        try:
            result = subprocess.run(
                [
                    "ffmpeg",
                    "-i", str(input_path),
                    "-ss", str(start_time),
                    "-t", str(segment_len),
                    "-b:a", MP3_BITRATE,
                    "-y",
                    str(segment_path),
                ],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                logger.error(f"ffmpeg Fehler bei Segment {i+1}: {result.stderr}")
                continue

            segment_size = segment_path.stat().st_size
            if segment_size > 0:
                segments.append(segment_path)
                logger.info(f"  Segment {i+1}: {format_size(segment_size)}")
            else:
                segment_path.unlink(missing_ok=True)

        except FileNotFoundError:
            logger.error("ffmpeg nicht gefunden!")
            return []

    return segments


def find_overlap_and_merge(texts: list[str]) -> str:
    """
    Fügt überlappende Transkriptions-Texte zusammen.

    Sucht am Ende jedes Segments nach überlappenden Wörtern mit dem Anfang
    des nächsten Segments und entfernt die Duplikate.

    Args:
        texts: Liste der Transkriptions-Texte (in Reihenfolge)

    Returns:
        Zusammengefügter Text ohne Duplikate
    """
    if not texts:
        return ""
    if len(texts) == 1:
        return texts[0]

    result_parts = []

    for i, text in enumerate(texts):
        if i == 0:
            # Erstes Segment: komplett übernehmen
            result_parts.append(text)
        else:
            # Finde Überlappung mit vorherigem Segment
            prev_text = texts[i - 1]
            merged_text = _merge_overlapping_texts(prev_text, text)
            result_parts.append(merged_text)

    return " ".join(result_parts)


def _merge_overlapping_texts(prev_text: str, curr_text: str) -> str:
    """
    Findet die Überlappung zwischen zwei Texten und gibt den nicht-überlappenden
    Teil des zweiten Textes zurück.

    Strategie: Suche die letzten N Wörter des vorherigen Textes im aktuellen Text.
    Wenn gefunden, nimm nur den Teil nach der Überlappung.
    """
    prev_words = prev_text.split()
    curr_words = curr_text.split()

    if not prev_words or not curr_words:
        return curr_text

    # Suche nach Überlappung: Prüfe die letzten 5-20 Wörter des vorherigen Textes
    # und schaue, ob sie am Anfang des aktuellen Textes vorkommen
    max_overlap_words = min(20, len(prev_words), len(curr_words))

    best_overlap_len = 0

    for overlap_len in range(3, max_overlap_words + 1):
        # Die letzten overlap_len Wörter des vorherigen Textes
        prev_end = prev_words[-overlap_len:]
        # Die ersten overlap_len Wörter des aktuellen Textes
        curr_start = curr_words[:overlap_len]

        # Vergleiche (case-insensitive, ignoriere Interpunktion für Vergleich)
        if _words_match(prev_end, curr_start):
            best_overlap_len = overlap_len

    if best_overlap_len > 0:
        # Überspringe die überlappenden Wörter am Anfang
        return " ".join(curr_words[best_overlap_len:])
    else:
        # Keine Überlappung gefunden - Text komplett übernehmen
        return curr_text


def _words_match(words1: list[str], words2: list[str]) -> bool:
    """
    Prüft ob zwei Wortlisten übereinstimmen (case-insensitive, Interpunktion ignoriert).
    """
    if len(words1) != len(words2):
        return False

    def normalize(word: str) -> str:
        # Entferne Interpunktion und konvertiere zu lowercase
        return re.sub(r'[^\w]', '', word.lower())

    for w1, w2 in zip(words1, words2):
        if normalize(w1) != normalize(w2):
            return False

    return True


def find_untranscribed_recordings(directory: Path) -> list[Path]:
    """Findet alle Audio-Dateien ohne entsprechende .txt-Datei."""
    audio_files = []
    for ext in SUPPORTED_FORMATS:
        audio_files.extend(directory.glob(f"*{ext}"))

    # Nur Dateien ohne .txt-Entsprechung
    untranscribed = [
        f for f in audio_files
        if not f.with_suffix(".txt").exists()
    ]

    # Sortiere nach Änderungszeit (älteste zuerst)
    untranscribed.sort(key=lambda f: f.stat().st_mtime)
    return untranscribed


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
        description="Transkribiert alle Audio-Dateien ohne .txt-Entsprechung im Recordings-Verzeichnis"
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

    # Recordings-Verzeichnis prüfen
    search_dir = Path(args.dir).expanduser()
    if not search_dir.exists():
        logger.error(f"Verzeichnis nicht gefunden: {search_dir}")
        sys.exit(1)

    # Untranscribierte WAV-Dateien finden
    files_to_process = find_untranscribed_recordings(search_dir)

    if not files_to_process:
        logger.info(f"Keine unverarbeiteten Audio-Dateien in: {search_dir}")
        sys.exit(0)

    logger.info(f"{len(files_to_process)} Datei(en) zu verarbeiten:")
    for f in files_to_process:
        logger.info(f"  - {f.name}")

    # Sprache (None = automatische Erkennung)
    language = args.language
    if language:
        logger.info(f"Sprache: {language}")
    else:
        logger.info("Sprache: Automatische Erkennung")

    # OpenAI-Client erstellen
    client = OpenAI(api_key=api_key)

    # Alle Dateien verarbeiten
    for file_path in files_to_process:
        logger.info(f"--- Verarbeite: {file_path.name} ---")

        file_size = file_path.stat().st_size
        logger.info(f"Dateigröße: {format_size(file_size)}")

        if file_size == 0:
            logger.warning("Datei ist leer, überspringe...")
            continue

        # Datei für Transkription vorbereiten (ggf. konvertieren/splitten)
        temp_dir = None
        segments_to_transcribe = []

        if file_size > MAX_FILE_SIZE:
            logger.warning(f"Datei zu groß ({format_size(file_size)}) - teile in Segmente...")

            # Temporäres Verzeichnis für Segmente
            temp_dir = Path(tempfile.mkdtemp(prefix="transcribe_"))

            # Erst versuchen, als einzelne MP3 zu konvertieren
            temp_mp3 = temp_dir / "converted.mp3"
            if convert_to_mp3(file_path, temp_mp3):
                temp_size = temp_mp3.stat().st_size
                logger.info(f"Konvertiert: {format_size(temp_size)}")

                if temp_size <= MAX_FILE_SIZE:
                    # Passt als einzelne Datei
                    segments_to_transcribe = [temp_mp3]
                else:
                    # Immer noch zu groß - in Segmente teilen
                    logger.info("Immer noch zu groß - teile in Segmente...")
                    temp_mp3.unlink()
                    segments_to_transcribe = split_audio_to_segments(file_path, temp_dir)
            else:
                # Konvertierung fehlgeschlagen
                if temp_dir:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                continue

            if not segments_to_transcribe:
                logger.error("Keine Segmente erstellt")
                if temp_dir:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                continue
        else:
            # Datei ist klein genug
            segments_to_transcribe = [file_path]

        # Transkribieren
        try:
            all_texts = []
            for idx, segment_path in enumerate(segments_to_transcribe):
                if len(segments_to_transcribe) > 1:
                    logger.info(f"Transkribiere Segment {idx+1}/{len(segments_to_transcribe)}...")
                text = transcribe_file(client, segment_path, language=language)
                all_texts.append(text)

            # Alle Texte zusammenfügen (mit Überlappungs-Erkennung bei mehreren Segmenten)
            if len(all_texts) > 1:
                logger.info("Führe Segmente zusammen (entferne Überlappungen)...")
                full_text = find_overlap_and_merge(all_texts)
            else:
                full_text = all_texts[0] if all_texts else ""

            # Transkription als .txt neben der Audio-Datei speichern
            txt_path = file_path.with_suffix(".txt")
            txt_path.write_text(full_text, encoding="utf-8")
            logger.info(f"Transkription gespeichert: {txt_path}")

            # Transkription ausgeben
            print()
            print(full_text)
            print()

        except Exception as e:
            logger.error(f"Fehler bei Transkription: {e}")
        finally:
            # Temporäres Verzeichnis aufräumen
            if temp_dir:
                shutil.rmtree(temp_dir, ignore_errors=True)

    logger.info("App beendet")


if __name__ == "__main__":
    main()
