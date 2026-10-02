# 6. Check usage and limits before large runs

## Problem

UniCourt applies several limits that a large run can reach part-way through:

| Limit | How it shows up |
| --- | --- |
| Account allowance per billable activity; **document orders count toward "Case Document View", free documents included** | Usage APIs; over-allowance use is overage |
| Daily caps on orders and downloads | HTTP `403` / `UN203` |
| Per-court-source daily order cap | The order is accepted, then its callback ends `FAILURE` with `UN203 LIMIT_REACHED` |
| Rate limit: 30 requests per 5 seconds | `429` / `UN429` (already handled) |

The CLI checks none of these before starting, and reports a per-court cap only
as a generic failure.

## Evidence

- The Minnesota run placed ~35 retrievals in a day without reaching a cap, but
  a multi-state run would place hundreds or thousands.
- The rate limiter handled 4 `429` responses in the cover-sheet run without
  losing a request.

## Design

- **`unicourt usage`** prints today's and this month's allocated, consumed and
  overage figures for the workspace
  (`GET /workspace/{workspaceId}/dailyUsage/{date}` and `.../monthlyUsage/{month}`,
  which a workspace token can read).
- **Pre-flight in `get-complaints` and `get-documents`** (not in `--dry-run`
  unless asked): estimate the retrievals the run would place (documents not
  already on disk, in the ledger or in UniCourt's store) and compare with the
  remaining "Case Document View" allowance. Warn when the run would use more
  than 80% of what is left, and stop unless `--yes` when it would exceed it.
- **Per-court cap:** recognise `UN203 LIMIT_REACHED` on a callback, record it in
  the ledger with the court source id, stop submitting to that court for the
  rest of the run, and say so in the summary ("court source CTSS… reached its
  daily limit; N documents left pending, retry tomorrow with
  `unicourt orders --refresh`").
- **`--max-pending N`** (item 1) keeps the number of retrievals in flight
  bounded.

## Tests

- Fake usage response with 10 units left and a run needing 25: the run stops
  before any `PUT` and prints the numbers.
- A `UN203` callback for one court: later documents from that court are not
  submitted; documents from other courts continue.

## Open questions

- **verify:** the exact activity label for document orders in the usage
  response, and whether `UNICOURT`-store downloads count toward it.
- **verify:** whether the account has an allowance at all on this plan, or
  overage only.

## Done when

A run that would exceed the remaining allowance stops before placing any
retrieval, and a per-court cap leaves the affected documents pending rather
than failed.
