# 7. Run long jobs so they are observable and stoppable

## Problem

Runs that take longer than a few minutes were hard to follow and to stop
cleanly, especially when an agent drives the CLI from a shell with a command
time limit.

## Evidence (from the Minnesota run)

- The side script fetched one document at a time (~45 minutes for 14).
- Stopping it killed its shell but not the Python process; it kept downloading
  for about 10 more minutes alongside the replacement.
- Piping output through `grep` buffered it, so progress was invisible until
  the run ended.
- Commands longer than 10 minutes moved to the background, and progress could
  only be read from a raw log full of `[api]` lines.

## Process rules (apply now)

1. **No side scripts for retrieval.** If the CLI cannot do it, change the CLI
   (as was done with `get-documents`).
2. **Long runs go straight to the background**, writing to a log file. Read the
   log; never pipe a running CLI through `grep` or `head`.
3. **Stop by process id and confirm it is gone** (`kill <pid>`, then check
   `kill -0 <pid>` fails) before starting a replacement. Never use a broad
   `pkill -f` pattern that can match the controlling shell.
4. **Sample first** (item 4) before any batch over ~10 documents.
5. **Report from the summary,** not from counting log lines.

## Code support

- **`--log FILE`:** write the `[api]` request log and event lines to a file,
  and keep stderr to event lines and the status line only.
- **`--progress-file FILE`:** rewrite a small JSON file every few seconds with
  phase, counts (submitted, waiting, complete, failed, pending), elapsed time
  and the process id, so progress can be read without parsing logs.
- **Lock file:** `get-complaints`/`get-documents` refuse to start while another
  run holds the same `--orders-file` (item 2), naming its process id. This
  prevents two runs fetching the same documents.
- **Clean stop:** `SIGTERM` behaves like Ctrl-C today (finish in-flight
  requests, record pending callbacks in the ledger, write outputs).

## Tests

- `--progress-file` contains the process id and current counts during a fake run.
- A second run with the same `--orders-file` exits with a clear message while
  the first holds the lock; a stale lock (dead process id) is taken over.
- `SIGTERM` during waiting leaves every pending callback in the ledger.

## Done when

An agent can start a run in the background, read its progress from one small
file, stop it with one command, and be sure nothing else is still running.
