"""Small, side-effect-free PDF annotation core.

The source PDF is never modified: all annotations are written to a new file.
"""

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
import json

import fitz


RGB = Tuple[int, int, int]
SUPPORTED_STYLES = {"highlight", "underline", "squiggly"}


@dataclass(frozen=True)
class Category:
    """One keyword category with its own annotation appearance."""

    name: str
    terms: Tuple[str, ...]
    style: str
    color: Optional[RGB]


def load_categories(path: Path) -> List[Category]:
    """Validate the JSON configuration before reading or changing any PDF."""
    data: Dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    
    if not isinstance(data, dict) or not isinstance(data.get("categories"), dict):
        raise ValueError("Config must contain a 'categories' object.")

    categories: List[Category] = []
    
    for name, definition in data["categories"].items():
        if not isinstance(definition, dict):
            raise ValueError(f"Category '{name}' must be an object.")
        
        style = definition.get("style", "highlight")
        
        if style not in SUPPORTED_STYLES:
            raise ValueError(f"Unknown annotation style '{style}' in category '{name}'.")
        
        raw_terms = definition.get("terms", [])
        
        if not isinstance(raw_terms, list) or not all(isinstance(t, str) for t in raw_terms):
            raise ValueError(f"Category '{name}' must contain a list of term strings.")
        
        # Deduplicate case-insensitively to avoid repeated annotations for the same word.
        terms = tuple(dict((t.strip().casefold(), t.strip()) for t in raw_terms if t.strip()).values())
        
        raw_color = definition.get("color")
        color: Optional[RGB] = None
        
        if raw_color is not None:
            if (not isinstance(raw_color, list) or len(raw_color) != 3 or
                    any(type(v) is not int or not 0 <= v <= 255 for v in raw_color)):
                raise ValueError(f"Category '{name}' color must be three integers from 0 to 255.")
            color = (raw_color[0], raw_color[1], raw_color[2])
        
        categories.append(Category(name=name, terms=terms, style=style, color=color))
    
    return categories


def _create_annotation(page: fitz.Page, quads: List[fitz.Quad], category: Category) -> None:
    """Use text quads rather than rectangles, including for rotated PDF text."""
    if category.style == "underline":
        annotation = page.add_underline_annot(quads)
    elif category.style == "squiggly":
        annotation = page.add_squiggly_annot(quads)
    else:
        annotation = page.add_highlight_annot(quads)
    if category.color is not None:
        # PyMuPDF stores PDF annotation stroke colors on a 0..1 scale.
        annotation.set_colors(stroke=tuple(component / 255 for component in category.color))
    annotation.update()


def annotate_pdf(source: Path, output: Path, categories: Iterable[Category],
                 overwrite: bool = False) -> Counter:
    """Create an annotated copy of a text-searchable PDF and count occurrences.

    Returns counts indexed by (category name, keyword). Identical matches within
    one category are deduplicated even when terms overlap; overlaps between
    different categories are kept intentionally, so users can see both marks.
    """
    source = source.resolve()
    output = output.resolve()
    if source == output:
        raise ValueError("Input and output paths must be different.")
    if output.exists() and not overwrite:
        raise FileExistsError(f"Output already exists: {output} (use --overwrite)")
    output.parent.mkdir(parents=True, exist_ok=True)
    counts: Counter = Counter()
    with fitz.open(source) as document:
        if not document.is_pdf:
            raise ValueError(f"Not a PDF: {source}")
        
        # Reject encryption without silently generating incomplete output.
        if document.needs_pass:
            raise ValueError(f"Password-protected PDF: {source}")
        
        for page in document:
            for category in categories:
                seen: set = set()
                for term in category.terms:
                    # The legacy project used page.search_for(). Use the same
                    # PDF-aware search so line wraps can still be matched.
                    quads = page.search_for(term, quads=True)
                    fresh = []
                    
                    for quad in quads:
                        key = tuple(round(v, 3) for p in quad for v in (p.x, p.y))
                        if key in seen:
                            continue
                        seen.add(key)
                        fresh.append(quad)
                    
                    if fresh:
                        _create_annotation(page, fresh, category)
                        counts[(category.name, term)] += len(fresh)
        
        # Save a new file rather than applying incremental changes to the original.
        document.save(output, garbage=4, deflate=True)
    
    return counts


def find_pdf_files(source: Path, recursive: bool = False) -> List[Path]:
    """Accept one PDF or a folder; exclude generated 'marked_' files."""
    if source.is_file():
        if source.suffix.lower() != ".pdf":
            raise ValueError(f"Expected a PDF input: {source}")
        return [source]
    
    if not source.is_dir():
        raise FileNotFoundError(f"Input path does not exist: {source}")
    
    iterator = source.rglob("*") if recursive else source.iterdir()
    
    return sorted(p for p in iterator if p.is_file() and p.suffix.lower() == ".pdf" and not p.name.lower().startswith("marked_"))
