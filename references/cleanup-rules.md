# Cleanup Rules

1. Normalize line endings, whitespace, and repeated blank lines.
2. Remove image placeholder lines only when the image is not part of the requested human output; retain image metadata and paths in database JSON.
3. Remove page headers, footers, page numbers, and table-of-contents noise only when MinerU structure or repeated-position evidence identifies them.
4. Preserve repeated normative/legal text unless it is proven page furniture.
5. Repair numbered heading levels deterministically; keep sibling numbering at one level and close level gaps.
6. Parse tables from structured MinerU content. Keep all cells, including `rowspan` and `colspan` semantics.
7. For continuation tables, retain the original caption, repeat the header in retrieval chunks, and store `continuation_of` / `continued_from` metadata. Never join tables solely because they are adjacent pages.
8. Record every non-trivial cleanup in `cleanup_flags` or document warnings.

## Merged clauses

OCR sometimes joins consecutive clauses into one paragraph, e.g. `4.1.3 ……要求。4.1.4 ……`. Split only when a sentence-ending mark (`。；;！!？?`) is followed by a multi-level clause number (`x.y` to `x.y.z.w`), whitespace, and a CJK character other than `条/款/节/章/表/图`. Never split inside tables, headings, or pipe-table rows. Record `merged_clause_split`.

## Canonical names

When the source filename carries only a standard code (e.g. `GB15603-2022.pdf`), take the title from the first CJK level-1 heading in the cover area, skipping banners such as `中华人民共和国国家标准`, `前言`, `目次`. Remove spaces between CJK characters before matching.
