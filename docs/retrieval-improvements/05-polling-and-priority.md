# 5. Faster status checks and a priority option

## Problem

`documents.obtain_file_url()` checks a retrieval every 10 seconds at first and
multiplies the wait by 1.5 each time, up to 60 seconds. A retrieval that
finishes just after a check is noticed up to a minute late. The wait before
giving up is fixed at 30 minutes regardless of `--priority`.

## Evidence

- Checks happened at about 10, 25, 47, 81, 132 and 192 seconds after submit,
  then every minute.
- Most retrievals took 20 seconds to 4 minutes, which falls in the range where
  the gaps are 30–60 seconds.
- The `get-documents` run made 44 status checks for 3 retrievals.

## Design

- **Interval:** check every 5 seconds for the first minute, then every 15
  seconds, with no growth beyond that (`--poll` to override). With item 1 one
  list call covers every pending retrieval, so the shorter interval does not
  multiply API calls by the number of documents.
- **Waiting time follows the priority:** stop waiting (and report pending, per
  item 2) after the priority's own timeout: 5 minutes for `level1`, 30 for
  `level2`, and a configurable cap for `level5` (24 hours is too long for an
  interactive run; default 30 minutes, `--wait`).
- **Priority:** keep `--priority` (default `level2`). Document that `level1`
  ("critical") is processed first by UniCourt and moves to `DELAYED` after 5
  minutes. **verify:** whether `level1` costs more or uses more allowance;
  the docs do not say.
- Respect `statusDetails.nextRetry` on `DELAYED`: no checks before that time.

## Tests

- Fake clock: checks at 5-second steps for a minute, then 15-second steps.
- `--priority level1` stops waiting after 5 minutes and reports pending.
- A `DELAYED` callback with `nextRetry` in 10 minutes is not checked before then.

## Done when

A retrieval's completion is noticed within 15 seconds, and API calls per run
are not higher than today's.
