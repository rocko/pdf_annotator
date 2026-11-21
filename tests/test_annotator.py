"""Run with: python -m pytest -q"""
import json
from pathlib import Path

import fitz
import pytest

from pdf_keyword_annotator.annotator import annotate_pdf, find_pdf_files, load_categories
from pdf_keyword_annotator.cli import main


def sample_pdf(path: Path) -> None:
    with fitz.open() as document:
        page = document.new_page()
        page.insert_text((50, 100), "SMOTE improves class imbalance in CNN experiments.")
        page.insert_text((50, 130), "Accuracy and precision can be compared.")
        document.save(path)


def test_annotations_preserve_source_and_generate_summary(tmp_path: Path) -> None:
    source = tmp_path / "study.pdf"
    sample_pdf(source)
    original = source.read_bytes()
    cfg = Path(__file__).resolve().parents[1] / "examples" / "categories.json"
    code = main([str(source), "--config", str(cfg), "--output", str(tmp_path / "out")])
    output = tmp_path / "out" / "marked_study.pdf"
    assert code == 0
    assert source.read_bytes() == original
    assert output.exists()
    assert (tmp_path / "out" / "marked_study.csv").exists()
    with fitz.open(output) as document:
        assert sum(1 for page in document for _ in (page.annots() or [])) >= 3


def test_recursion_and_skip_generated(tmp_path: Path) -> None:
    folder = tmp_path / "nested"
    folder.mkdir()
    sample_pdf(folder / "study.PDF")
    sample_pdf(folder / "marked_older.pdf")
    assert [p.name for p in find_pdf_files(tmp_path, recursive=True)] == ["study.PDF"]


def test_no_silent_overwrite(tmp_path: Path) -> None:
    source = tmp_path / "study.pdf"
    sample_pdf(source)
    destination = tmp_path / "marked_study.pdf"
    destination.write_text("Existing output")
    with pytest.raises(FileExistsError):
        annotate_pdf(source, destination, [])


def test_invalid_config_rejected(tmp_path: Path) -> None:
    cfg = tmp_path / "invalid.json"
    cfg.write_text(json.dumps({"categories": {"test": {"terms": ["SMOTE"], "color": [300, 2, 3]}}}))
    with pytest.raises(ValueError):
        load_categories(cfg)
