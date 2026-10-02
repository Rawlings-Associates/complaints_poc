# 2. Save every retrieval; resume instead of re-requesting

## Problem

A retrieval's callback id lives only in memory. When a run stops, times out or
a retrieval ends `MANUAL`, the id is lost. The only way to find out later
whether the document arrived is to run the download again, which repeats the
price checks and submits a new `PUT`.

`documents.obtain_file_url()` also raises `DocumentUnavailable` for `MANUAL`,
so the CLI reports it as `download-failed`. UniCourt's documentation says
`MANUAL` means it is retrieving the document by hand; `DELAYED` orders can
still complete up to 72 hours later.

## Evidence

- 27-CV-26-11863 came back `MANUAL`, then timed out on a retry, then downloaded
  directly about an hour later because it had reached UniCourt's store.
- 27-CV-26-11888 (Towle) came back `MANUAL` and is still outstanding.
- Each re-run of `get-complaints` listed all ~586 documents again.

## Design

### The ledger

An append-only JSON Lines file, default `orders.jsonl` in the working
directory (`--orders-file`), one line per event:

```json
{"time": "2026-10-02T02:31:05Z", "case_document_id": "CDOCfg19d59fe219d9",
 "case_number": "27-CV-26-11888", "callback_id": "CBDOTc6abf18729DF2",
 "event": "submitted", "status": "IN_PROGRESS", "pdf_path": null, "detail": null}
```

Events: `submitted`, `status` (on change only), `downloaded`, `failed`. The
current state of a document is its last line. The file holds ids and statuses
only, no names or text, but it is git-ignored like the other run files.

### Behaviour

- Before submitting, look up the document in the ledger:
  - PDF already on disk → reuse (as `get-documents` does today).
  - Pending callback id → check that callback instead of submitting again.
  - `COMPLETE` with an expired link → `GET /caseDocumentDownload/{id}` for a
    fresh link (UniCourt's documented path; no new order).
- Treat `IN_PROGRESS`, `DELAYED` and `MANUAL` as **pending**. A run stops
  waiting after `--wait` (default: the priority's timeout, see item 5) and
  reports pending documents instead of failing them. Only `FAILURE` is a
  failure, with `statusDetails` and `exception` recorded.
- Text records (`texts*.jsonl`) gain status `pending`, with the callback status
  and `nextRetry` when UniCourt gives one.

### New command

```console
$ unicourt orders                       # pending and recent retrievals from orders.jsonl
$ unicourt orders --refresh             # check their status with UniCourt
$ unicourt orders --collect --text-out texts_late.jsonl
                                        # download every completed one and save its text
```

`--refresh` uses the callbacks list endpoint (item 1), falling back to one
`GET /callbacks/{id}` per pending retrieval. `--collect` reuses the download
and text-extraction code of `get-documents`.

## Tests

- A run interrupted after submit leaves `submitted` lines; the next run checks
  those callbacks and places no new `PUT`.
- `MANUAL` → record `pending`, exit 0, summary lists it; a later
  `orders --collect` with the fake callback now `COMPLETE` downloads it.
- `DELAYED` with `nextRetry` → shown in `unicourt orders`.
- An expired `fileUrl` → fresh link through `caseDocumentDownload`, no `PUT`.
- A corrupt last line in the ledger is ignored with a warning.

## Risks and open questions

- **verify:** whether `PUT /caseDocumentOrder` with `reOrder: false` for a
  document already being retrieved returns the existing callback or creates a
  second one. The ledger avoids relying on either.
- Callback history is listable for 30 days; the ledger keeps ids longer, but
  UniCourt may not answer for older ones.

## Done when

The Towle complaint (27-CV-26-11888) can be collected with
`unicourt orders --collect` without re-running `get-documents`, and a stopped
run resumes without any duplicate `PUT`.
