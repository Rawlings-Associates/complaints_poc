# 1. Submit all retrievals, then check them together

## Problem

`get-complaints` and `get-documents` run `--workers` threads (default 4). Each
thread calls `documents.obtain_file_url()`, which places one retrieval
(`PUT /caseDocumentOrder`) and then polls that one retrieval until it ends.
While it waits, the thread does nothing else, so at most 4 retrievals are ever
in flight. The retrievals themselves run on UniCourt's side and do not need
our threads.

## Evidence

- 26 Hennepin cover sheets, all `COURT_SOURCE`: **18 min** with 4 workers, about
  2.7 min per document on average.
- 8 complaints with `get-documents`: 15 min, of which 5 downloaded immediately;
  the rest was waiting on 3 retrievals.
- Single retrievals took from ~20 s to ~4 min. If all 26 had been submitted at
  once, the run would have taken roughly as long as the slowest one, an
  estimated 4–6 minutes (**verify**).

## Design

Split acquisition into four phases, run by one scheduler in the main thread:

1. **Check price** for every chosen document (`GET /caseDocument/{id}`), with
   the existing worker pool. Refuse anything not free (unchanged).
2. **Download at once** every document whose live `repository` is `UNICOURT`
   (`GET /caseDocumentDownload/{id}`), in parallel.
3. **Submit** a retrieval for every `COURT_SOURCE` document, back to back
   (`PUT /caseDocumentOrder`, `reOrder: false`), recording each callback id
   (see item 2). The shared rate limiter (30 requests per 5 s) paces this.
4. **Check and collect** in rounds: one call to
   `GET /caseDocumentOrder/callbacks?status=COMPLETE&...` (paginated) returns
   every completed retrieval; download each new one as it appears. Retrievals
   that are `FAILURE` end; `DELAYED` and `MANUAL` stay pending (item 2).
   Fall back to per-id `GET /callbacks/{id}` when the list endpoint is not
   usable (**verify** its filter parameter names and whether it can filter by
   `startDate` precisely enough to cover this run).

Downloads of finished files keep using the worker pool, so slow storage links
do not hold up the check loop.

### Code changes

- `documents.py`: split `obtain_file_url()` into `place_order()` (price check +
  `PUT`, returns the callback) and `order_status()` / `completed_orders()` (list
  endpoint), keeping `verify_free()` as the only gate before a `PUT`.
  `obtain_file_url()` stays as a thin wrapper for one-off use and tests.
- `cli.py`: a `RetrievalScheduler` used by both `get-complaints` (for each
  case's first planned document) and `get-documents`. `get-complaints`
  fallbacks (try the next document type when the first gives no text) run as a
  second round once the first round's documents are read.
- `status.py`: show "submitted / waiting / complete / failed" counts.
- New option `--max-pending N` (default 50) caps how many retrievals are in
  flight at once, to stay inside per-court limits (item 6).

## Tests

- Fake client with 20 `COURT_SOURCE` documents that complete after varying
  numbers of checks: all 20 `PUT`s happen before the first download, total
  checks are far fewer than 20 × rounds when the list endpoint is used, and the
  output order still follows the input.
- A document that becomes priced between listing and submit is never ordered.
- `FAILURE` ends that document only; `MANUAL` stays pending and is reported.
- Ctrl-C after submit leaves the ledger with every pending callback id (item 2).

## Risks and open questions

- **Per-court daily order caps** surface as `FAILURE` with `UN203` after a
  retrieval is accepted. Submitting many at once reaches a cap sooner;
  `--max-pending` and item 6 address it.
- **verify:** list-endpoint filters (`status`, `startDate`/`callbackGeneratedDate`
  names and formats) and its page size.
- WebSocket delivery (`type=workspaceCaseDocumentOrder`) would push results
  instantly but adds a dependency and a 2-hour connection limit; the list
  endpoint gets most of the benefit with plain HTTP. Not planned.

## Done when

The 26 Hennepin cover sheets (or a comparable batch) finish in under 8 minutes
with the default settings, with no more API calls than today.
