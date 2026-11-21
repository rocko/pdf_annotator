"""Command-line interface for the cleaned PDF annotator."""

import argparse
import csv
from collections import Counter
from pathlib import Path
from typing import List, Optional

from .annotator import annotate_pdf, find_pdf_files, load_categories


def _write_counts(destination: Path, counts: Counter) -> None:
    """Keep the summary machine-readable without requiring pandas."""
    with destination.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["category", "term", "count"])
        for (category, term), count in sorted(counts.items()):
            writer.writerow([category, term, count])


def _make_wordcloud(destination: Path, counts: Counter) -> None:
    """Render a word cloud only when the optional dependency is installed."""
    try:
        from wordcloud import WordCloud
    except ImportError as exc:
        raise RuntimeError("Install the optional dependency: uv pip install -e '.[cloud]'") from exc
    totals: Counter = Counter()
    for (_, term), count in counts.items():
        totals[term] += count
    if totals:
        WordCloud(width=1000, height=600, background_color="white").generate_from_frequencies(
            dict(totals)).to_file(str(destination))


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Highlight PDF keywords and keep input PDFs unchanged.")
    parser.add_argument("input", type=Path, help="PDF file or directory containing PDFs")
    parser.add_argument("--config", type=Path, default=Path(__file__).resolve().parents[2] / "examples" / "categories.json",
                        help="JSON keyword category configuration")
    parser.add_argument("--output", type=Path, default=Path("annotated"),
                        help="Output directory (default: ./annotated)")
    parser.add_argument("--recursive", action="store_true", help="Find PDFs in subdirectories")
    parser.add_argument("--overwrite", action="store_true", help="Replace existing generated output")
    parser.add_argument("--wordcloud", action="store_true", help="Generate PNG word clouds")
    args = parser.parse_args(argv)

    try:
        categories = load_categories(args.config)
        inputs = find_pdf_files(args.input, recursive=args.recursive)
        if not inputs:
            parser.error("No PDF files found.")
        for source in inputs:
            # Preserve the directory structure for a recursive directory input.
            relative = source.relative_to(args.input) if args.input.is_dir() else Path(source.name)
            destination = args.output / relative.parent / f"marked_{relative.name}"
            counts = annotate_pdf(source, destination, categories, overwrite=args.overwrite)
            _write_counts(destination.with_suffix(".csv"), counts)
            if args.wordcloud:
                _make_wordcloud(destination.with_suffix(".png"), counts)
            print(f"{source} -> {destination} ({sum(counts.values())} keyword matches)")
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(1, f"Error: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
