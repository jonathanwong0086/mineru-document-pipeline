# MinerU API Error Handling

Classify errors before retrying:

- Retryable: service unavailable, model unavailable, queue full (`-60009`), temporary parse failure (`-60010`), upload URL failure, and transient download errors.
- Authentication: invalid or expired token. Stop and request a new `MINERU_API_KEY`; do not automate account login.
- Quota: daily task/page quota. Stop the batch and report the remaining files.
- Permanent: unsupported format, corrupt/empty file, over-size/page limit after splitting, invalid task, or export-format failure.

Use exponential backoff with a bounded retry count. Preserve the original response code and message in the part checkpoint, but never log the authorization header or key.
