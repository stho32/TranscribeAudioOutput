"""Tests für find_untranscribed_recordings() aus transcribe.py."""

import sys
from pathlib import Path

# transcribe.py liegt im selben Verzeichnis
sys.path.insert(0, str(Path(__file__).parent))

from transcribe import SUPPORTED_FORMATS, find_untranscribed_recordings


def test_findet_wav_dateien(tmp_path):
    (tmp_path / "recording.wav").touch()
    result = find_untranscribed_recordings(tmp_path)
    assert len(result) == 1
    assert result[0].name == "recording.wav"


def test_findet_mp3_dateien(tmp_path):
    (tmp_path / "podcast.mp3").touch()
    result = find_untranscribed_recordings(tmp_path)
    assert len(result) == 1
    assert result[0].name == "podcast.mp3"


def test_findet_alle_unterstuetzten_formate(tmp_path):
    for ext in SUPPORTED_FORMATS:
        (tmp_path / f"audio{ext}").touch()
    result = find_untranscribed_recordings(tmp_path)
    gefundene_endungen = {f.suffix for f in result}
    assert gefundene_endungen == SUPPORTED_FORMATS


def test_ueberspringt_bereits_transkribierte(tmp_path):
    (tmp_path / "done.mp3").touch()
    (tmp_path / "done.txt").write_text("transkribiert")
    (tmp_path / "neu.mp3").touch()
    result = find_untranscribed_recordings(tmp_path)
    assert len(result) == 1
    assert result[0].name == "neu.mp3"


def test_ignoriert_nicht_unterstuetzte_formate(tmp_path):
    (tmp_path / "video.avi").touch()
    (tmp_path / "bild.png").touch()
    (tmp_path / "text.txt").touch()
    result = find_untranscribed_recordings(tmp_path)
    assert result == []


def test_leeres_verzeichnis(tmp_path):
    result = find_untranscribed_recordings(tmp_path)
    assert result == []


def test_sortiert_nach_aenderungszeit(tmp_path):
    import time

    erste = tmp_path / "erste.wav"
    erste.touch()
    time.sleep(0.05)
    zweite = tmp_path / "zweite.mp3"
    zweite.touch()

    result = find_untranscribed_recordings(tmp_path)
    assert result[0].name == "erste.wav"
    assert result[1].name == "zweite.mp3"
