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

Long runs should use `--out PATH`: the file is rewritten after every batch, so
a run that is killed keeps everything it has resolved. Without it the CSV is
written only at the end and an interrupted job shows nothing -- though the
response cache still means the next run does not re-fetch.

Captions are a separate, **budgeted** step. The search endpoint ignores
`page_size` and hard-caps results at 20 per page, so queries batch exactly 20
case numbers -- one filled page per request. That is ~295 requests for all of
3140, about 30 minutes at 10/min. Every response is cached, so a run capped
with `--budget N` simply continues where it left off next time.

> Membership comes from the JPML docket, never from a name search. Searching
> `flnd` for nearby case numbers returns unrelated matters (BP Exploration,
> USCIS), so only the docket text is authoritative.

### Plaintiffs and counsel come free with the titles

The `/parties/` endpoint returns **nothing** for these dockets -- they carry
`source: 1` (a court scrape, not a purchased PACER docket report), so no party
rows were ever created. The *search* index is populated regardless, and its
results carry `party`, `attorney`, `firm` and `docket_id` alongside `caseName`.

So `--resolve-names` fills in the plaintiff, counsel and firms at **no cost
beyond the title lookup itself**. Corporate defendants (Pfizer, Viatris,
Pharmacia, Upjohn, Greenstone, Prasco, and anything with a corporate suffix)
are filtered out; on a 20-case sample the remaining party matched the case-name
plaintiff **20 times out of 20**.

### Origin state

`origin_state` is derived from the district a case transferred *from*:
`cacd` &rarr; California, `mnd` &rarr; Minnesota.

It is deliberately **blank for direct-filed cases**, which is most of them:

| | Cases | Origin state |
| --- | ---: | --- |
| Transferred in (order, motion, tag-along) | 165 | derived from the originating district |
| Filed directly in the transferee district | 5,731 | *blank* |

A transferee court takes direct filings from plaintiffs nationwide, so `flnd`
would be a statement about where the MDL sits, not where the plaintiff lives --
counsel on those cases includes firms from Michigan, New Jersey and New York.
Calling all 5,731 "Florida" would be wrong, so the field stays empty and
`--transferred-only` selects the subset where the signal is real.

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
| `--transferred-only` | off | only cases with a real originating court |
| `--out PATH` | stdout | write to PATH, refreshed after every batch |
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

## State-court plaintiffs via UniCourt (`unicourt`)

A separate tool that uses the UniCourt DEEP API. It finds cases that name one
or more parties, scoped by **jurisdiction** (state, optionally county), **court
type** (state or federal) or a **single court**, and saves them as a case list
you can edit or pipe. For the cases on that list it inventories and prices every
filing, downloads the **free** cover sheets (paid ones are priced and
planned, but downloading them is not supported) and writes the **text** of
each one to a JSONL file. The tool does not parse names: forms differ by state
and by court, so an agent reads the text and picks out the plaintiffs.

### Setup

```console
$ pip install -e .                                   # installs the `unicourt` command and pypdf
$ export UNICOURT_CLIENT_ID=... UNICOURT_CLIENT_SECRET=...
$ unicourt token                                     # optional: create the token now
```

You never handle the access token yourself.

1. **First run:** the first command that needs the API exchanges your client
   ID and secret for a **workspace token** (`POST /generateNewWorkspaceToken`).
   If you didn't name a workspace, it looks one up first:
   1. It creates a temporary account token.
   2. It takes the account's **DEEP** workspace, from the token response or
      else from `GET /workspaces`. If there is only one workspace in total,
      it uses that one. If the choice is ambiguous, it stops and lists them.
   3. It revokes the temporary account token straight away, even if a step
      failed, so it doesn't use up one of the account's 10 token slots.
2. **Storage:** it saves the token to `~/.config/unicourt/credentials.json`.
   The file is readable only by you (permissions 600, in a 700 directory) and
   is written atomically. It holds the token, its ID, the workspace ID, the
   creation time and a hash of the client ID. **The client secret is never
   written anywhere.**
3. **Later runs** reuse the stored token, so they need no environment
   variables at all. Tokens never expire, and a workspace may hold at most 10,
   so one is created once rather than on every run.
4. **A rejected token:** if UniCourt rejects the stored token (it was
   revoked), a new one is created automatically, provided the client ID and
   secret are in the environment.

| Variable | Needed | Purpose |
| --- | --- | --- |
| `UNICOURT_CLIENT_ID`, `UNICOURT_CLIENT_SECRET` | To create the token, then only to replace or revoke it | If unset in a terminal, you are asked (the secret is hidden) |
| `UNICOURT_WORKSPACE` | Never: the DEEP workspace is looked up | Only to choose a different workspace (or `--workspace`); stored with the token |
| `UNICOURT_TOKEN` | Never | Uses this token instead of the stored one (needs a workspace) |
| `UNICOURT_CREDENTIALS_FILE` | Never | Stores the token somewhere else |
| `UNICOURT_API_ROOT` | Never | Base URL (default `https://deep-api.unicourt.com`) |

Managing the stored token. These commands never print the token itself:

```console
$ unicourt token              # status: workspace, token ID, created, file path
$ unicourt token --refresh    # new token, then the old one is revoked with UniCourt
$ unicourt token --revoke     # revoke with UniCourt and delete the local copy
```

In a cloud session the home directory is temporary, so a new session creates
a new token. Run `unicourt token --revoke` at the end of a session, or set
`UNICOURT_CREDENTIALS_FILE` to a persistent location, to stay under the
10-token limit. Put the client ID and secret in the environment's secrets
rather than in chat.

`python -m unicourt_state ...` works the same without installing.

### Workflow

```console
$ unicourt search --state "New York" --court-type state \
      --party "Pfizer" --party "Pharmacia" --limit 0 --out cases.csv  # 1-2. save the cases
                                                                  # 3. edit cases.csv
$ unicourt get-complaints -i cases.csv --dry-run                  # 4. plan and price, fetch nothing
$ unicourt get-complaints -i cases.csv --limit 1                  # 5. free cover sheets, one case first
$ unicourt get-complaints -i cases.csv                            #    then the rest -> texts.jsonl
$ unicourt get-complaints -i cases.csv --dry-run \
      --include-paid --budget 25                                  # 6. plan paid ones within $25
```

Only cover sheets are looked for by default. Add complaints with
`--doc-types civil-cover-sheet,complaint` (a complaint is then fetched only if
the cover sheet gives no text), or ask for them alone with
`--doc-types complaint`.

Or skip the file and pipe a search straight in:

```console
$ unicourt search --state "New York" --court-type state --party "Pfizer" | unicourt get-complaints --dry-run
```

To search one court instead, find its ID with `unicourt courts "Los Angeles"`
and pass `--court-id`.

**2. `search`** shows a table in a terminal and writes CSV when its output is
piped (`--format table|csv` forces either). `--out` also saves the CSV, which
includes each case's `court_type` and `state`, to a file.

**Where to search.** Give at least one scope; the scopes combine with AND, so
a search is never nationwide by accident:

| Option | Searches | Sent to UniCourt as |
| --- | --- | --- |
| `--state "New York"` | One jurisdiction (the full state name) | `(JurisdictionGeo:(state:"New York"))` |
| `--county "Kings"` (with `--state`) | One county in that state | `(JurisdictionGeo:(state:"New York" AND county:"Kings"))` |
| `--court-type state` / `federal` | Only state courts, or only federal courts | `(Court:(type:"State"))` |
| `--court-id` / `--court-name` | One court | `(Court:(courtId:"..."))` |

```console
$ unicourt search --state "New York" --court-type state --party "Pfizer" --party "Pharmacia"
```

**Parties.** With several `--party` names, **every** party must appear in the
case (`--match all`, also written `and`; this is the default). Use
`--match any` (or `or`) to find cases naming at least one of them.

Other options:

- `--role defendant`: match the parties only in that role.
- `--filed-from` / `--filed-to`: limit by filing date.
- `--limit`: defaults to 100 cases; `0` returns all of them.

**Pagination.** Every list call starts at `pageNumber=1` and follows
`nextPageAPI` until it is null. Page sizes are fixed by UniCourt: 10 per page
for case search, 100 for documents.

- **The 10,000-case cap:** a query is capped at 1,000 pages, so a case search
  reaches at most 10,000 cases.
- **Automatic splitting:** when a search matches more than that, `search`
  splits it into filing-date ranges (halving until every range fits),
  searches the ranges newest first, and removes duplicates. Each split prints
  a note.
- **When it can't split:** if a single day still matches more than 10,000
  cases, it warns and returns the first 10,000. Narrow the search.
- **Cases with no filing date** can't be reached once a search is split by
  date.

**3. Edit the list.** Only `case_id` is required, so any CSV with that column
works, from `-i/--input-file` or from stdin.

**4. `get-complaints --dry-run`** lists every document of every case and
matches them **by name similarity** against the `--doc-types`, in order:

- A **civil cover sheet** ("Civil Case Cover Sheet", "Case Information Sheet"
  and similar): the default.
- A **complaint** ("Complaint for Damages", "Original Petition" and
  similar), when asked for.
- Look-alikes such as "Answer to Complaint", "Cross-Complaint" and "Proof of
  Service" are excluded.

Nothing is ordered or downloaded. It writes **`--out` (default
`documents.csv`)**, which has one row per document, including the ones that
matched nothing. Each row carries the case, the document name and
description, filing date, pages, **price**, repository, availability, preview
availability, the type it matched and its score, and the planned **action**:

| Action | Meaning |
| --- | --- |
| `download` | Free: downloaded |
| `fallback` | Free: downloaded only if the documents before it give no text (failed, or a scan) |
| `buy` | Priced, within `--budget` (dry-run plan only) |
| `buy-fallback` | Priced: needed only if the documents before it give no text (plan only) |
| `over-budget` | Priced: would exceed `--budget` |
| `paid-skip` | Priced: not downloaded |
| `unknown-price` | No price given: never fetched |
| `sealed` | Sealed: never fetched |
| `alternative` | A weaker match of a type already covered: not fetched |
| *(blank)* | Not one of the `--doc-types` |
| `no-documents` | The case lists no documents |

A real run fills in `result` (`downloaded`, `declined`, `failed` or
`paid-not-supported`), `pdf_path` and `text_pages` (pages with a text layer)
on the same rows.

The summary (illustrative, with `--doc-types civil-cover-sheet,complaint`):

```console
Summary for 6 case(s), 8 document(s) listed (dry run: nothing was ordered or downloaded):
  civil-cover-sheet  found    1 | free    1 | paid    0 ($0.00) | price unknown 0 | sealed 0 | none 5
  complaint          found    4 | free    1 | paid    2 ($3.70) | price unknown 1 | sealed 0 | none 2
  Cases with a free document: 2
  Cases with only paid documents: 1 (cheapest document per case: $2.50 in total)
  Cases with nothing usable: 3
  Paid documents are not downloaded (downloading them is not supported).
```

How to read it:

- The `paid` figure on each line is the cost of every priced document of that
  type, so the complaint line answers "what would all the complaints cost".
- Add `--include-paid --budget N` to a dry run to see which paid documents
  would be needed and which would go over the budget. This is a plan only.
- Use `--doc-types complaint` to look at complaints only.
- Prices are what UniCourt reports for each document at the court/source.
  UniCourt's own charges, if any, are not included.

**5. Without `--dry-run`**, only **free** documents are downloaded:

1. **Free means a price of exactly `0`.** A missing or unreadable price counts
   as not free.
2. **The price is re-checked.** Right before any order or download the
   document is fetched again (`GET caseDocument/{id}`) and the price checked a
   second time. If it is no longer within the cap, nothing is ordered.
3. **Each case is confirmed before anything downloads.** One prompt per case
   lists the free documents it would fetch: `y`, `n`, `a` (yes to all), or
   `q` (quit). The prompts come before the downloads start, so they never mix
   with download output. They read from the terminal even when the case list
   is piped in. `--yes` skips them. With no terminal and no `--yes`, nothing
   is downloaded.
4. **The PDF is fetched.** A free document already stored by UniCourt
   downloads directly. One still at the court is ordered (`reOrder: false`),
   polled until complete, then downloaded. PDFs are saved as
   `pdfs/{caseNumber}_{type}_{documentId}.pdf`.
5. **The text is saved**, not parsed: every page is extracted in layout mode,
   so table rows (such as an attached list of plaintiffs) stay on one line.
   The next planned document is tried only if the earlier ones give no text.

**Workers and progress.** Cases run in parallel on `--workers N` threads
(default 4, maximum 16). The threads list documents first, then download, so
one slow court order no longer holds up the others. Each event prints as it
happens, and a status line keeps count:

```console
  25STCV03  fetching civil-cover-sheet 'Civil Case Cover Sheet'
  25STCV03  civil-cover-sheet order IN_PROGRESS
  25STCV03  civil-cover-sheet order COMPLETE
  25STCV03  saved pdfs/25STCV03_civil-cover-sheet_S1.pdf: text on 4 of 4 page(s)
[Downloading: 4/6 cases | 2 active | 2 waiting on retrievals | 4 PDFs, 4 with text | 0m48s]
```

- **In a terminal**, the status line stays at the bottom and updates every
  second.
- **When output goes to a file or a pipe**, it is printed as a plain line
  every 30 seconds instead.
- **Ctrl-C** stops cleanly: queued cases are cancelled, workers waiting on a
  court order stop waiting, and the output files keep everything finished so
  far.
- **Output order:** `documents.csv` and `texts.jsonl` are written in
  case-list order, however the workers finish.

**Rate limit.** UniCourt allows **30 requests per 5 seconds** per account, so
every API call goes through one shared limiter. However many workers run, no
5-second window ever holds more than 30 requests.

- **If UniCourt answers 429 anyway** (HTTP 429, or a body of
  `{"code": "UN429"}` / `{"message": "Too Many Requests"}`), the client pauses
  all workers for the `Retry-After` time, or a full 5-second window, and
  retries up to 6 times. Rate-limited calls are not billable.
- **PDF downloads don't count:** they come from signed storage links, not the
  API.
- **The run's last line** reports any time spent waiting on the limit and any
  429s.
- **The limit is per account**, so two runs at the same time share it. Each
  stays under 30 per 5 seconds on its own, so together they can trigger 429s,
  which are then retried.

**6. Paid documents are not downloaded.** `--include-paid --budget AMOUNT`
works only with `--dry-run`, where it plans and prices the paid cover sheets
or complaints a case would need, within the budget. Without `--dry-run`,
`--include-paid` stops at once with:

```console
Error: Downloading paid documents is not supported. Only free documents (price 0) can be downloaded; use --dry-run with --include-paid --budget to plan and price paid ones.
```

The same error guards the download code itself. A document whose price is
not 0, when listed or when re-checked just before fetching, is never ordered.
In a real run it is recorded as `paid-not-supported`.

### The text file, for an agent

`--text-out` (default `texts.jsonl`) has one JSON object per line: one per
downloaded document, or one per case that has none. Every line carries the
case (`case_id`, `case_number`, `case_name`, `court`, `filed_date`), the
document (`document_type`, `document_name`, `case_document_id`, `price`,
`pdf_path`), a `status`, `page_count`, `pages_with_text` and `text`.

`status` is one of:

| Status | Meaning |
| --- | --- |
| `ok` | Text extracted |
| `no-text-layer` | Downloaded, but a scan: OCR is not done |
| `text-extraction-failed` | Downloaded, but the PDF could not be read |
| `download-failed`, `paid-not-supported` | Nothing downloaded for that reason |
| `declined`, `not-attempted` | Not confirmed, or never reached |
| `no-matching-document`, `no-free-document` | Nothing to download |

`text` holds every page under a `=== Page N of M ===` line. Long runs of
spaces are shortened to a three-space gap, so columns stay apart. A page
without text reads `[no text layer on this page: scanned?]`. For example, a
Minnesota cover sheet with an attached plaintiff list:

```text
=== Page 5 of 6 ===
62-CV-26-5925   Filed in District Court
State of Minnesota
8/19/2026 12:53 PM
STATE OF   DEPO PROVERA   DEPO PROVERA   MENINGIOMA
PLAINTIFF FIRST  PLAINTIFF LAST   INJURED PARTY   CITIZENSHIP   START DATE   END DATE   DIAGNOSIS DATE
Adriane   Williams   Minnesota   3/25/1997   9/30/2024   9/29/2022
Melissa   Sunsdahl   Minnesota   1/1/1999   1/1/2004   11/7/2019
```

Read the file with any JSONL tool, e.g. one case's text:
`jq -r 'select(.case_number == "62-CV-26-5925") | .text' texts.jsonl`.
Both output files are rewritten after every case, so an interrupted run keeps
its progress.

To print the text of a PDF you already have: `unicourt extract file.pdf`.

### Chosen documents (`get-documents`)

`get-complaints` finds documents by name, and some courts name them
generically. Hennepin County, Minnesota, files most complaints as "Other
Document", for example, and a consolidation docket holds motions and orders
rather than complaints. For these, choose the documents yourself (or let an
agent choose) and fetch them by id:

```console
$ unicourt get-complaints -i cases.csv --dry-run          # documents.csv lists every document
                                                          # copy the rows you want to picks.csv
$ unicourt get-documents -i picks.csv --dry-run           # what would be fetched; no API calls
$ unicourt get-documents -i picks.csv                     # free documents only -> texts_documents.jsonl
```

- **Input:** any CSV with a `case_document_id` column. Rows of
  `documents.csv` work unchanged, so their case details, document name, pages
  and price come along.
- **Free only:** a row whose listed price is not 0 is refused without an API
  call. Every other document is re-read from UniCourt just before it is
  requested, and refused unless it is free at that moment.
- **Confirmation:** one prompt per case, as with `get-complaints`; `--yes`
  skips them.
- **Parallel:** `--workers` documents at a time (default 4). Documents held at
  the court need a retrieval request, which can take minutes; the status line
  counts them as "waiting on retrievals".
- **Resumable:** PDFs are saved as `{caseNumber}_{document-name}_{documentId}.pdf`
  in `--pdf-dir`, and a PDF already there is reused without an API call, so a
  stopped run can simply be repeated.
- **Output:** `--text-out` (default `texts_documents.jsonl`) has one line per
  chosen document, in input order, with the same fields and statuses as the
  `get-complaints` text file, plus `declined` and `interrupted`.

### Reference material

| Path | What it is |
| --- | --- |
| [`docs/unicourt-retrieval.md`](docs/unicourt-retrieval.md) | The retrieval plan: endpoints, costs, error codes |
| [`docs/unicourt-sequence.md`](docs/unicourt-sequence.md) | The sequence diagram |
| [`docs/unicourt-deep-v3-api-docs/`](docs/unicourt-deep-v3-api-docs/INDEX.md) | UniCourt's DEEP v3 developer docs, archived 2026-10-01 |
| [`docs/unicourt-sdk/`](docs/unicourt-sdk/README.md) | UniCourt's official Python SDK wheel (`unicourt` 1.0), for reference only. This tool does not use it. |

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
- `origin_state` is a *venue* signal, not residence, and exists only for the 165
  transferred-in cases. Nothing in the JPML docket records where a direct-filing
  plaintiff lives.
- Some search results give only a surname ("SANCHEZ"), others a full name
  ("DONNA TONEY"); the tool reports whichever the index holds.
- `--resolve-names` leaves a caption blank when CourtListener has no docket for
  that case; two of 3140's 28 complaint cases are absent from the index.
- **Member-case complaint PDFs are not downloadable.** The member dockets list a
  "Complaint" entry, but it is `is_available: false` with no stored file --
  nobody bought it from PACER, so RECAP has no copy. Across a six-docket sample,
  zero were fetchable. Only the complaints *attached to the motions to transfer*
  have PDFs (28 of 28 for MDL 3140), because the moving party filed them as
  exhibits on the JPML docket itself.
- A complaint attached to a motion is found only if a party actually attached
  it. For 3140, all 438 entries yielded 28 complaint attachments, every one on a
  motion to transfer -- so `--motions-only` returns the same 28 for two requests
  instead of twenty-two.
- `is_available: false` means the PDF is not in RECAP; the row is still listed.
