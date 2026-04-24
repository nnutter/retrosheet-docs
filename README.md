# retrosheet-docs

This repository tracks changes to Retrosheet's event file documentation by keeping a normalized Markdown snapshot of `https://www.retrosheet.org/eventfile.htm` in version control.

This is not meant to be used as a distribution of the documentation. The generated Markdown exists so Git can detect if and when the source page changes.

## How it works

- `src/retrosheet_docs/update_eventfile.py` downloads the source page.
- It removes known page chrome before conversion by deleting `ul.nav` and `font[size="2"]` elements.
- It converts the remaining HTML to Markdown.
- It rewrites plain paragraph blocks to insert newlines after sentence-ending periods while trying to avoid common abbreviations, decimals, and URLs.
- It writes the normalized result to `docs/eventfile.md`.

## Local usage

```bash
uv sync
uv run python -m retrosheet_docs.update_eventfile
uv run pytest
```

## Automation

`.github/workflows/update-eventfile.yml` runs daily and commits the refreshed snapshot only when Git detects a diff in `docs/eventfile.md`.
