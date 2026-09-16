# MDL Complaints POC

Given an MDL **master docket number**, list its **member cases** (the potential
plaintiffs) and the **complaints** attached to its motion(s) to transfer, using
the [CourtListener REST API v4](https://www.courtlistener.com/help/api/rest/).

Two modes:

| Mode | What you get | For MDL 3140 |
| --- | --- | --- |
| `--members` | every case associated with the MDL | 5,896 cases / 53 courts |
| *(default)* | complaints attached to the motions to transfer | 28 complaints |

## Member cases (the plaintiff list)

```console
$ python3 -m mdl_complaints 3140 --members --court flnd --limit 6 --resolve-names
Member cases: 6 across 1 court(s) | titles resolved: 6/6

#  Court  Case No.       Title                         Source
-  -----  -------------  ----------------------------  -------------
1  flnd   3:24-cv-00624  TONEY v. PFIZER INC           tag-along
2  flnd   3:25-cv-00108  SUTTON v. PFIZER INC          cases-entered
3  flnd   3:25-cv-00144  SANCHEZ v. PFIZER INC         cases-entered
4  flnd   3:25-cv-00168  CARRIGAN-BRODA v. PFIZER INC  cases-entered
5  flnd   3:25-cv-00200  FOSTER v. PFIZER INC          cases-entered
6  flnd   3:25-cv-00206  WASHBURN v. PFIZER INC        cases-entered
```

A master docket accumulates member cases three ways, and each names the cases
in the **text** of a docket entry, so the whole list is parsed from pages
already fetched -- **no extra requests**:

| Source | Meaning | Count in 3140 |
| --- | --- | --- |
| `cases-entered` | filed directly in the transferee district | 5,731 |
| `conditional-transfer-order` | tag-along actually transferred in | 128 |
| `motion-to-transfer` | named on a motion that created/expanded the MDL | 28 |
| `tag-along` | proposed for the MDL | 5 |

Cases are de-duplicated across entries, keeping the most authoritative mention
(a case usually appears as a tag-along notice before the order that moved it).

Captions are a separate, **budgeted** step. The search endpoint ignores
`page_size` and hard-caps results at 20 per page, so queries batch exactly 20
case numbers -- one filled page per request. That is ~295 requests for all of
3140, about 30 minutes at 10/min. Every response is cached, so a run capped
with `--budget N` simply continues where it left off next time.

> Membership comes from the JPML docket, never from a name search. Searching
> `flnd` for nearby case numbers returns unrelated matters (BP Exploration,
> USCIS), so only the docket text is authoritative.

## Complaints attached to the motions

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

### Why the complaint scan only costs two requests

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
python3 -m mdl_complaints 3140 --members                  # member cases
python3 -m mdl_complaints 3140 --members --resolve-names --budget 20
python3 -m mdl_complaints 3140 --members --court flnd --format csv > members.csv

python3 -m mdl_complaints 3140                            # complaints
python3 -m mdl_complaints 3140 --motions-only             # 2-request fast path
python3 -m mdl_complaints 3140 --download ./pdfs          # fetch the PDFs
python3 -m mdl_complaints 3140 -v                         # log requests
```

| Flag | Default | Notes |
| --- | --- | --- |
| `--format` | `table` | `table`, `json`, `csv` |
| `--members` | off | list member cases instead of complaints |
| `--resolve-names` | off | look up member captions (~1 request per 20) |
| `--budget N` | none | cap requests spent on names; resumable via cache |
| `--court ID` | all | filter to one court, e.g. `flnd` |
| `--limit N` | all | first N results only |
| `--motions-only` | off | complaints: only motion-to-transfer entries |
| `--entry-prefix` | none | complaints: entry description prefix to match |
| `--max-pages` | `0` | pages of docket entries to scan, 20 per page (0 = all) |
| `--no-titles` / `--no-pdf-titles` | titles on | skip caption lookup / PDF fallback |
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

## Where titles come from

Member-case captions are looked up on the member docket, which is
authoritative. For complaints the docket had no entry for, the tool falls back
to the complaint PDF's `Attorneys for Plaintiff <name>` signature block -- the
OCR text is already in the payload, so the fallback costs nothing. Checked
against 26 known-good titles it agreed 16 times and **contradicted none**.

A derived title yields the plaintiff only, not a full caption, so it is always
labelled: `title_source` is `docket` or `complaint-pdf`, marked `*` in the
table. Nothing is ever guessed -- unresolvable titles stay blank.

## Known limits

- Member extraction depends on the JPML writing case numbers into entry text.
  Entries naming a court the tool cannot map are skipped rather than guessed at.
- `--resolve-names` leaves a caption blank when CourtListener has no docket for
  that case; two of 3140's 28 complaint cases are absent from the index.
- A complaint attached to a motion is found only if a party actually attached
  it. For 3140, all 438 entries yielded 28 complaint attachments, every one on a
  motion to transfer -- so `--motions-only` returns the same 28 for two requests
  instead of twenty-two.
- `is_available: false` means the PDF is not in RECAP; the row is still listed.
