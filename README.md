# PDF Keyword Annotator

A small, local PDF keyword annotator extracted from a 2022 research-literature analysis project. Searches text-based PDFs for configured keyword categories, writes color-coded highlights, underlines, or squiggly marks, and exports document-level keyword counts as CSV. Optional word clouds are supported. **The original PDF remains unchanged.**

## Requirements

- Python 3.10 or newer
- Windows, Linux or macOS
- Text-searchable PDFs (scanned image-only PDFs require OCR; OCR is not included)

## Installation (Windows PowerShell with uv)

From the project root:

```powershell
uv venv --python 3.12
uv pip install -e ".[dev]"
```

## Usage

Annotate one PDF:

```powershell
.\.venv\Scripts\python.exe -m pdf_keyword_annotator.cli "C:\path\to\paper.pdf"
```

Annotate all PDFs in a folder:

```powershell
.\.venv\Scripts\python.exe -m pdf_keyword_annotator.cli ".\papers" --output ".\results"
```

Include subfolders and generate word clouds:

```powershell
.\.venv\Scripts\python.exe -m pdf_keyword_annotator.cli ".\papers" --recursive --output ".\results" --wordcloud
```

Use a custom keyword configuration:

```powershell
.\.venv\Scripts\python.exe -m pdf_keyword_annotator.cli ".\papers" --config ".\examples\categories.json"
```

To replace existing generated files, add `--overwrite`.

Outputs per paper:

- `results/marked_paper.pdf` - annotated PDF
- `results/marked_paper.csv` - keyword counts by category
- `results/marked_paper.png` - optional Word Cloud

When using `--recursive`, the input directory tree is preserved in the output folder. Generated files prefixed `marked_` are excluded from directory scans.

## Configure keyword categories

Edit `examples/categories.json`. Every category contains a list of keywords, a style (`highlight`, `underline`, `squiggly`) and an optional RGB color such as `[255, 0, 0]`. The configuration is based on the terms from the original research script.

Search uses PyMuPDF text matching, which is case-insensitive in common ASCII cases. It is not a full linguistic tokenizer; matches can be substrings, and different keyword categories may overlap. Overlapping annotations are possible by design.

## Limitations

- OCR for image-only PDFs is not included.
- A term split in the middle of a word across a PDF line may not match.
- Encrypted PDFs are not supported.
- PDF text extraction quality depends on the PDF's embedded text layer.
- No external network access, databases or remote services are required.

## Run tests

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## Scope

This cleaned package preserves the useful PDF annotation and optional Word Cloud components. The original Excel-driven research graph, SQL database, old experiments, generated outputs and absolute machine-specific paths are intentionally excluded. The original archive is not modified.
