# 4. Sample a few cases before a bulk run

## Problem

A batch is only checked after it has finished. When the chosen document type
turns out not to hold what is needed, the whole batch's time is lost.

## Evidence

- The 26 Hennepin cover sheets took 18 minutes and none listed the plaintiffs
  (each is the 5-page form with "<lead plaintiff>, et al.").
- The "try one case first" step that found the Hennepin complaints took two
  minutes and settled the question.

## Design

Add `--sample N` to `get-complaints` and `get-documents`:

1. Pick N cases spread across the input: different courts first, then
   different counsel or filing dates when those columns are present.
2. Fetch only their planned documents, as a normal run would.
3. Print, for each sampled document: case, document name, pages, pages with
   text, and the first ~40 lines of text, plus the lines around the words
   "plaintiff", "exhibit" and "et al.".
4. Stop, and print the command that runs the rest
   (`--skip-sampled` reuses the sampled PDFs, as `get-documents` already reuses
   PDFs on disk).

`--sample` writes its text records to the normal `--text-out`, so nothing is
fetched twice.

## Tests

- `--sample 2` over 6 cases in 3 courts picks 2 different courts.
- The printed excerpt includes the lines around "Exhibit A".
- The follow-up run with the same `--text-out` does not fetch the sampled
  documents again.

## Done when

On the Hennepin cases, `get-complaints --sample 2` shows within a few minutes
that the cover sheets have no plaintiff list.
