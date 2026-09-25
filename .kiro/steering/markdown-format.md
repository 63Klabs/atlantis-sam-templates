---
inclusion: fileMatch
fileMatchPattern: '*.md'
---

# Markdown Formatting

These rules apply whenever you (AI or human) author or edit Markdown (`.md`) files in this repository, including specs under `.kiro/specs/`, steering docs, and end-user documentation under `docs/`.

## No hard-wrapping of prose

Do NOT insert manual line breaks into prose to keep lines under some column width. Write each paragraph as a single continuous line and let the editor soft-wrap it. Hard-wrapped prose reads poorly on narrow viewports, makes editing awkward, and produces noisy, ragged diffs when a sentence in the middle of a paragraph changes.

- One paragraph is one line. A blank line separates paragraphs.
- Do not target a print width (no 80, 100, 120, or ~124-column wrapping). There is no line-length limit for prose.
- This is a soft-wrap repository: rely on the editor's word wrap for display, not on embedded newlines.

## What this does NOT change

Keep the normal Markdown block structure. The no-hard-wrap rule is about prose only.

- Code fences (```): leave contents exactly as written; never reflow code, YAML, or JSON.
- Tables: keep each row on its own line.
- Lists: keep each list item starting on its own line. A single list item's text is one line (do not break it across multiple lines), but different items stay on separate lines and nested items keep their indentation.
- Headings, blockquotes (`>`), and horizontal rules: one per line as usual.
- Front matter and link reference definitions: unchanged.

## Editing existing documents

When you edit a Markdown file that still contains hard-wrapped prose, unwrap the paragraphs you touch (join the broken lines back into one line per paragraph) rather than matching the old wrapped style. Preserve blockquotes, tables, code blocks, and list structure per the documentation steering rules.

## Rationale

Soft-wrapped Markdown is easier to read on phones and split editor panes, easier to edit, and yields cleaner diffs (a changed sentence touches one line, not a re-flowed block). Line breaks in prose carry no semantic meaning in Markdown, so removing them loses nothing.
