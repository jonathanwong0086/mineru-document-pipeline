# Output Schema

Each database JSON document contains:

```json
{
  "doc_id": "GB50016",
  "canonical_name": "GB50016建筑设计防火规范",
  "source_file": "original.pdf",
  "source_sha256": "...",
  "page_count": 466,
  "parser": {"provider": "mineru", "model": "vlm"},
  "chunks": [
    {
      "chunk_id": "GB50016-p12-text-00001",
      "content_type": "text",
      "text": "...",
      "section": "总则",
      "page_start": 12,
      "page_end": 13,
      "part": 1,
      "cleanup_flags": []
    }
  ],
  "warnings": []
}
```

Required invariants: stable IDs, non-empty text for searchable chunks, valid page ranges, source provenance, and no missing referenced assets. The manifest records one entry per source file and points to all three output lanes.
