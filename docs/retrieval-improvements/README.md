# Document retrieval improvements

A plan to make `unicourt` document retrieval faster, resumable and easier to
steer. It comes from the first full Minnesota run (30 state-court cases naming
Pfizer Inc. and Pharmacia LLC, run 2026-10-01/02), where retrieval was the slow
and fragile part of the work. Each item has its own file with the problem, the
evidence, the design, tests and open questions. Items marked **verify** need a
live check against UniCourt before they are relied on.

## What happened in the Minnesota run

| Run | Documents | Wall time | Notes |
| --- | --- | --- | --- |
| Hennepin cover sheets (`get-complaints`) | 26 | 18 min | All 26 needed a court retrieval; none listed the plaintiffs |
| Complaints by name (`get-complaints --doc-types complaint`) | 3 of 26 | 1.5 min | 23 complaints are filed as "Other Document" and were not matched |
| One-off side scripts | 14 | ~45 min | One document at a time; one copy kept running after it was stopped |
| `get-documents` | 8 | 15 min | 5 already in UniCourt's store; 1 came back `MANUAL` |

All 586 Hennepin documents were held at the court (`repository: COURT_SOURCE`),
so every download needed a retrieval request taking between ~20 seconds and ~4
minutes. Two complaints came back `MANUAL`; one of them was in UniCourt's store
about an hour later.

## Root causes

1. **Retrievals ran 4 at a time.** Each worker submits one retrieval and waits
   for it to finish, although UniCourt processes retrievals on its side.
2. **The wrong documents were fetched first,** and every run re-listed every
   document.
3. **`MANUAL` and `DELAYED` were treated as failures,** and retrieval ids were
   not saved, so the only way to check again was to request again.
4. **Status checks back off to once a minute.**
5. **The orchestration** (one-at-a-time scripts, an orphaned process, hidden
   progress) added time and confusion.

## The seven improvements

| # | Item | Effect | Effort | File |
| --- | --- | --- | --- | --- |
| 1 | Submit all retrievals, then check them together | Run time ≈ the slowest document, not the total ÷ 4 | Medium | [01-submit-all-then-poll.md](01-submit-all-then-poll.md) |
| 2 | Save every retrieval; resume instead of re-requesting | `MANUAL`/`DELAYED` documents are collected later with one command | Medium | [02-orders-ledger-and-resume.md](02-orders-ledger-and-resume.md) |
| 3 | List documents once, with selection hints | Fewer API calls; picking documents takes one step | Small | [03-list-documents-once.md](03-list-documents-once.md) |
| 4 | Sample a few cases before a bulk run | Catches the wrong document type before the whole batch | Small | [04-sample-first.md](04-sample-first.md) |
| 5 | Faster status checks and a priority option | Up to a minute less per document; urgent runs can use `level1` | Small | [05-polling-and-priority.md](05-polling-and-priority.md) |
| 6 | Check usage and limits before large runs | No surprise stop at a daily or monthly cap | Small | [06-usage-and-limits.md](06-usage-and-limits.md) |
| 7 | Run long jobs so they are observable and stoppable | No hidden progress, no orphaned processes | Process + small code | [07-running-long-jobs.md](07-running-long-jobs.md) |

## Order of work

1. **Items 1, 2 and 3 together.** 1 and 2 both change how a retrieval is
   tracked (submit → record → check → collect), so one change to
   `documents.py` and `cli.py` covers both. 3 removes re-listing and feeds the
   same commands.
2. **Items 4 and 5** as small follow-ups on the same commands.
3. **Item 6** before the next run larger than a few hundred documents.
4. **Item 7** applies now to how runs are operated; its code parts (a log file
   and a run summary) can go with item 2.

First live test: the Towle complaint (27-CV-26-11888), whose retrieval came
back `MANUAL`, collected with the new `unicourt orders --collect` from item 2.

## Unchanged rules

- Only free documents are fetched. Every retrieval is preceded by a live price
  check, and `reOrder` stays `false`.
- Names are not parsed by the CLI; it saves text for an agent to read.
- Output files with case data stay out of git.
