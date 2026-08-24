# MinerU Document Pipeline

A Codex skill and deterministic Python pipeline for turning local documents into clean Word, RAG Markdown, and structured database JSON outputs.

## Supported Inputs

- PDF, DOC/DOCX, PPT/PPTX, XLS/XLSX
- PNG, JPG, JPEG, TIFF
- HTML when supported by the selected MinerU route
- Standards, technical books, papers, contracts, reports, and scanned documents

## Features

- MinerU Precision API with `vlm` defaults
- 180-page / 180MB safe PDF splitting
- Up to six concurrent parts with checkpointed retries
- Structured `content_list_v2.json` processing
- Heading, page-furniture, and table-continuation cleanup
- `.doc`, `.docx`, RAG Markdown, and database JSON output lanes
- Atomic publication and validation

## Install

Install the skill from this repository with Codex's skill installer:

```powershell
python C:\Users\jonathan\.codex\skills\.system\skill-installer\scripts\install-skill-from-github.py `
  --repo jonathanwong0086/mineru-document-pipeline `
  --path . `
  --name mineru-document-pipeline
```

Set the Standard API key in the environment before processing large files or requesting Word output:

```powershell
$env:MINERU_API_KEY = '...'
```

## CLI

```powershell
python scripts/pipeline.py D:\docs\document.pdf --output .\output --workers 6
```

The output contains `human_doc`, `rag_markdown`, `database_json`, and `manifest.json`.

## Tests

```powershell
python -m unittest discover -s tests -q
```

The test suite is offline and does not contain credentials or user documents.

## License

MIT. See [LICENSE](LICENSE).
