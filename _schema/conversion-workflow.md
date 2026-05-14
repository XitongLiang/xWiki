# Conversion Workflow

Use this workflow when source material is not already available as readable
markdown.

## Purpose

The wiki should cite immutable files in `_raw/`, but markdown is often easier
for agents to inspect. `.tools/file_to_md.py` creates markdown companions for
source files before ingest.

Run:

```bash
python3 .tools/file_to_md.py path/to/source.pdf
```

By default, converted files are written to `_inbox/converted/`. Move or ingest
them deliberately after reviewing the output.

## Supported Behavior

- Markdown and plain-text-like files are copied into markdown form directly.
- Rich formats such as PDF, DOCX, PPTX, XLSX, and HTML use the optional
  `markitdown` package when installed.
- The tool fails clearly when `markitdown` is needed but unavailable.

Install the optional converter with:

```bash
python3 -m pip install markitdown
```

## Ingest Policy

- Do not delete the original source file after conversion unless the human asks.
- Preserve source provenance in the source page.
- If conversion quality is poor, cite the original file and record the
  extraction limitation in `Open Questions` or `Limitations`.
