# 3. List documents once, with selection hints

## Problem

The only way to see a case's documents today is `get-complaints --dry-run`,
which also matches names against `--doc-types` and plans downloads. Every
`get-complaints` run lists every case's documents again. And when names do not
identify the wanted document, nothing in `documents.csv` helps to spot it.

## Evidence

- Three `get-complaints` runs over the Hennepin cases each listed ~586
  documents (~30 API calls per run).
- 23 of 26 Hennepin complaints are named "Other Document". They were found by
  noticing that they were filed on the case's opening day and were the largest
  same-day filing (84–134 pages, against 10 pages for the other one).
- The most common names among documents filed on the 26 cases' opening days
  were "Other Document" (43), "Civil Cover Sheet" (26), "Affidavit of Service"
  (25) and "Certificate of Representation" (23).

## Design

### `unicourt documents`

```console
$ unicourt documents -i cases.csv --out documents.csv
```

Lists every document of every case (parallel, as today) and writes
`documents.csv` with no matching or planning. New columns, as hints for a
person or an agent; the CLI does not act on them:

| Column | Meaning |
| --- | --- |
| `opening_day` | `yes` when the document was filed on the case's filing date |
| `rank_in_day` | 1 = most pages among that day's filings in the case |
| `in_store` | `yes` when `repository` is `UNICOURT` (downloads at once) |
| `listed_at` | When the listing was taken, so a stale file is visible |

### Reuse the listing

- `get-complaints --documents documents.csv` plans from an existing listing
  instead of listing again (cases missing from it are listed as today).
- `get-documents` already reads `documents.csv` rows.
- A short recipe in the README for the agent: filter `documents.csv` (for
  example `opening_day == yes and rank_in_day == 1`), save as `picks.csv`, then
  `get-documents -i picks.csv`.

### Not planned

A built-in rule that picks documents automatically was considered and set
aside: selection by id, made by a person or an agent, was the chosen design.

## Tests

- `documents` writes one row per document plus a placeholder row for a case with
  none; `opening_day` and `rank_in_day` are right for ties and missing pages.
- `get-complaints --documents` makes no listing calls for cases in the file.
- A `documents.csv` with extra or reordered columns still loads.

## Done when

The Hennepin complaints can be chosen from one `documents.csv` with a single
filter, and a second `get-complaints` run makes no listing calls.
