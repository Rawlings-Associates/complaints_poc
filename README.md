# MDL Complaints POC

Given an MDL **master docket number**, list (and optionally download) the
member-case **complaints** attached to that MDL's **motion(s) to transfer**,
using the [CourtListener REST API v4](https://www.courtlistener.com/help/api/rest/).

```console
$ python3 -m mdl_complaints 3140
MDL No. 3140 - IN RE: Depo-Provera (Depot Medroxyprogesterone Acetate) Products Liability Litigation
Docket 69433786 | filed 2024-11-26 | https://www.courtlistener.com/docket/69433786/...
Entries matching 'MOTION TO TRANSFER': 5 | complaints found: 28

#   Att  Court                Case No.       Pages  PDF
--  ---  -------------------  -------------  -----  ---
1   5    California Northern  3:24-6875      65     yes
2   6    Indiana Southern     1:24-1831      22     yes
...
28  9    California Northern  4:24-cv-08679  52     yes

[api] 2 request(s), 0 cache hit(s), 8/10 left in this minute
```

## Why this only costs two requests

An MDL is created by a motion to transfer filed with the JPML, and that motion
carries the member-case complaints as **numbered attachments**. The attachments
are embedded in the `docket-entries` payload, so the complaints are reachable
without ever touching the member dockets:

1. `GET /dockets/?court=jpml&docket_number=MDL No. 3140` &rarr; the docket id.
2. `GET /docket-entries/?docket=<id>&order_by=date_filed` &rarr; page 1 of entries,
   with `recap_documents` inlined.

Everything after that is local filtering.

Three things keep the request count down, which matters on a 10 requests/minute key:

- **Ascending order.** The motion that creates an MDL is entry 1. The API
  defaults to newest-first, so on a docket with ~290 entries the motion is ~15
  cursor-paginated pages deep. `order_by=date_filed` puts it on page 1.
- **Inlined attachments.** `recap_documents` already contains every attachment
  with its description, page count and PDF path. No per-document lookups.
- **On-disk cache.** Responses are cached by URL, so re-runs cost **0 requests**.
  Use `--no-cache` to refresh.

A persistent token bucket (in the cache dir) enforces the per-minute limit
*across* invocations, so two back-to-back runs can't blow the budget.

## Usage

```console
python3 -m mdl_complaints 3140                      # table
python3 -m mdl_complaints 3140 --format json
python3 -m mdl_complaints 3140 --format csv > complaints.csv
python3 -m mdl_complaints 3140 --available-only     # only complaints with a PDF
python3 -m mdl_complaints 3140 --download ./pdfs    # fetch the PDFs
python3 -m mdl_complaints 3140 -v                   # log requests / cache hits
```

| Flag | Default | Notes |
| --- | --- | --- |
| `--format` | `table` | `table`, `json`, `csv` |
| `--entry-prefix` | `MOTION TO TRANSFER` | entry description prefix to match |
| `--max-pages` | `1` | pages of docket entries to scan, 20 per page |
| `--available-only` | off | skip complaints with no PDF in RECAP |
| `--download DIR` | off | download PDFs (storage host, not rate limited) |
| `--rate` | `10` | max API requests per minute |
| `--no-cache` / `--cache-dir` | cache on | `~/.cache/mdl_complaints` |

Requires `COURTLISTENER_API_KEY` in the environment (or `--token`).
Python 3.9+, standard library only.

## Input normalization

`docket_number` is an **exact-match** field on the API, and there is no
`icontains` lookup — so `?docket_number=md 3140` returns zero results rather
than an error. All input is normalized to the canonical stored form:

| Input | Sent to the API |
| --- | --- |
| `3140`, `md 3140`, `MDL 3140`, `MDL-3140` | `MDL No. 3140` |

## Two court-code conventions

The same docket mixes two abbreviation schemes, so both are decoded rather than
kept in a hand-maintained table of ~94 districts:

| Style | Example | Expands to |
| --- | --- | --- |
| JPML (state + division) | `CAN`, `MOW`, `INS` | California Northern, Missouri Western, Indiana Southern |
| Reporter (division + `D` + state) | `NDCA`, `SDIN` | California Northern, Indiana Southern |

Case numbers are likewise written both ways (`3:24-6875` and `3:24-cv-08746`),
so each row also carries `case_number_normalized` (`3:24-cv-06875`) for joining
across motions. Unrecognised codes pass through unchanged rather than being
guessed at, so bad input stays visible.

## What counts as a match

- Docket entries whose description starts with `MOTION TO TRANSFER`. For MDL
  3140 that is 5 entries: the initial motion, three `(CORRECTED)` entries that
  carry no attachments, and a later `(SUBSEQUENT)` motion.
- Within those, attachments (`document_type == 2`) whose description starts with
  `Complaint`. This excludes the motion itself, the Brief, Schedule of Actions,
  Oral Argument Statement and Proof of Service.

Complaints are de-duplicated by document id across entries.

## Tests

Run entirely from saved fixtures — **no API requests**:

```console
python3 -m unittest discover -s tests -v
```

## Known limits

- `--max-pages 1` scans the first 20 entries. Motions to transfer cluster at the
  start of a docket, but a very late subsequent motion would be missed; the tool
  prints a note whenever it stopped early, so this is visible rather than silent.
- Only complaints that a party actually attached to the motion are found. Cases
  that join an MDL later by conditional transfer order (CTO) are not attached
  there and are out of scope.
- `is_available: false` means the PDF is not in RECAP; the row is still listed.
