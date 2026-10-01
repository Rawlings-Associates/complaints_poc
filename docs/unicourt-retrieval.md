# UniCourt DEEP API: MDL data retrieval process

A plan for retrieving the same outputs as the CourtListener tool -- **member
cases, plaintiffs, counsel and complaints** for an MDL -- from the UniCourt DEEP
API. It is based on `UniCourt-DEEP-API-Spec-2026-08-03.yaml` (OpenAPI 3.1, 208
operations), together with UniCourt's developer documentation archived in
[`unicourt-deep-v3-api-docs/`](unicourt-deep-v3-api-docs/INDEX.md), and their
Python SDK in [`unicourt-sdk/`](unicourt-sdk/README.md), kept for reference and
not used. Nothing here has been run against a live key yet. Items marked
**verify** need a pilot run to confirm.

## Why UniCourt: gaps it closes

| CourtListener limit (see README) | UniCourt answer |
| --- | --- |
| Member list is scraped from the text of JPML docket entries | `relatedCases` on the lead case plus a docket-text search, both from UniCourt's repository |
| `/parties/` is empty for these dockets | `GET /case/{id}/parties` and `/counsel`, with normalized attorneys and firms |
| Member complaint PDFs are not in RECAP (0 of 6 sampled) | Download complaints already in UniCourt's store (`repository: UNICOURT`); buy from PACER only as a last resort |
| Search caps results at 20 per page, so ~295 requests for titles | `relatedCases` includes `caseNumber` and `caseName`, about 100 rows per page |
| No residence signal for direct-filed plaintiffs | `Party.contact.addressArray` exists (**verify**: federal dockets rarely list plaintiff addresses) |

UniCourt's own repository is the primary source. PACER is used only for
gaps, only when the run is explicitly allowed to use it, and only within a
spending cap (see [Source priority](#source-priority-unicourt-first-pacer-last)).

## Access prerequisites

| Item | Endpoint | Notes |
| --- | --- | --- |
| Workspace token | `POST /generateNewWorkspaceToken` with `clientId`, `clientSecret` and `workspaceId` (data calls use workspace tokens; account tokens from `POST /generateNewToken` are for account administration) | Tokens **never expire**, and a workspace may hold at most **10**. Do not mint a token per run: the 11th fails with `403 UN203 LIMIT_REACHED`. `unicourt_state` looks up the account's DEEP workspace when none is given (temporary account token via `POST /generateNewToken`, its `deepWorkspace` or `GET /workspaces`, then `PUT /invalidateToken`), creates the workspace token on first use, keeps it in a private file (`~/.config/unicourt/credentials.json`, mode 600, no client secret) and replaces it automatically if it is revoked. Revoke with `PUT /invalidateWorkspaceToken`. |
| Workspace | `GET /workspaces` | Every data path is `/workspace/{workspaceId}/...` (3-10 chars). Use one workspace per project so usage can be read with `GET /workspace/{id}/monthlyUsage/{month}`. |
| PACER credentials (tier 3 only) | `PUT /pacerCredential` (`pacerUserId`, `password`, optional `pacerMFASecretKey`, `defaultPacerClientCode`) | Not needed for tiers 1 and 2. Required for every PACER import, update and document order. Set `pacerClientCode` to the matter number so PACER invoices can be reconciled. |

Base URL: `https://deep-api.unicourt.com/` (paths start `/workspace/...`). Some
UniCourt guides show `https://deep-api.unicourt.com/v3/...`. A check without
credentials on 2026-10-01 found `/v3/workspace/.../caseSearch` answering 404
while `/workspace/.../caseSearch` answered 401, so the spec's root is the live
one. Auth header: `Authorization: Bearer <token>`.

Pagination: `pageNumber` (starting at 1) is required on every list call.
Follow `nextPageAPI` until it is null. Page sizes are fixed: 10 for case
search, 100 for docket entries and documents. Queries are capped at 1,000
pages, so 10,000 cases per search; larger searches are split by `filedDate`.

## Source priority: UniCourt first, PACER last

UniCourt serves federal cases from **its own repository**, with no PACER
credentials and no PACER fees. The spec only involves PACER when data has to
be refreshed from the court or bought. The process therefore works in tiers
and stops at the first tier that answers:

| Tier | Source | PACER? | Endpoints |
| --- | --- | --- | --- |
| 1 | UniCourt repository | No | `caseSearch`, `case/{id}`, `relatedCases`, `parties`, `counsel`, `docketEntries`, `documents?repository=UNICOURT`, `caseDocumentDownload`, `caseHistory`, norm attorney/law firm analytics |
| 2 | Free public sources already in this repo | No | The CourtListener member list and the 28 JPML-attached complaints (RECAP) |
| 3 | PACER through UniCourt, **opt-in only** (`--allow-pacer`, `--max-spend`) | Yes | `pacerCaseLocator/*`, `pacer/importCaseByCourtUsingCaseNumber`, `caseUpdate` / `caseTrack` with `pacerOptions`, `caseDocumentOrder` on federal `COURT_SOURCE` documents |

What the spec does **not** offer is a non-PACER way to *refresh* a federal
case. For federal cases, `pacerUserId` is mandatory on `caseUpdate`,
`caseTrack` and `caseDocumentOrder`. When UniCourt's copy is stale or
incomplete, the choice is to accept it or to go to tier 3. Every tier-1 read
therefore records `lastFetchDate`, `participantsLastFetchDate` and
`hasOnlyMetaInfo`, so the output shows how current each row is.

A UniCourt document with `repository: UNICOURT` is already in UniCourt's
store. Downloading it never touches PACER. Documents with
`repository: COURT_SOURCE` exist only at the court, and on a federal case the
only way to get one is a PACER purchase.

**Verify:** how UniCourt bills tier-1 reads and `UNICOURT` document downloads.
The spec shows billing activity limits per API group but no prices.

## Pipeline

The full call sequence, including state courts, is in
[`unicourt-sequence.md`](unicourt-sequence.md) (rendered as
[`unicourt-sequence.svg`](unicourt-sequence.svg)).

```
MDL no. ──1──▶ lead case + JPML docket from UniCourt's repository
        ──2──▶ member list: relatedCases ∪ docket-text search ∪ CourtListener
        ──3──▶ member caseIds (bulk search)
        ──4──▶ parties + counsel from the repository
        ──5──▶ complaints with repository = UNICOURT ▶ download
        ──6──▶ [--allow-pacer only] fill the remaining gaps from PACER
```

### 1. Find the MDL in UniCourt's repository (tier 1)

- JPML docket: `GET /caseSearch?q=caseNumber:"MDL No. 3140" AND (Court:(name:(Judicial Panel on Multidistrict Litigation)))`.
  The spec's own examples store JPML cases under that court with case numbers
  in the `MDL No. 875` form.
- Transferee lead case: search by the MDL caption and the transferee court,
  e.g. `caseName:"Depo-Provera" AND (Court:(name:(Florida Northern)))`, then
  keep the result whose case number has the `md` type. **Verify** the court
  name format with `GET /masterData/court`.
- If neither is found, take the transferee court and lead number from the
  CourtListener JPML docket (tier 2, already implemented). Use PACER's MDL
  search (`pacerCaseLocator/caseSearch/multiDistrictCourts?jpmlNumber=...`,
  a $0.10 search fee per page) only as tier 3.

### 2. Build the member list without PACER (tiers 1 and 2)

Merge three sources and keep a `source` column showing where each case came
from:

1. **`GET /case/{leadCaseId}/relatedCases`** (tier 1). If anyone has ever
   pulled the lead case's Associated Cases page, the links are already in
   UniCourt, about 100 per page. Check `caseStats.relatedCaseCount` and the
   lead's `lastFetchDate` first. A count of zero means the page was never
   pulled, not that there are no members.
2. **Docket-text search** (tier 1). Member dockets record the MDL, for example
   in transfer orders and "member case" entries:
   `caseSearch?q=(DocketEntry:(text:("MDL No. 3140" OR "3:25-md-03140"))) AND (Court:(type:Federal))`,
   paged with `pageNumber` (up to 1,000 pages). **Verify** recall against the
   known list.
3. **CourtListener member list** (tier 2). This is the existing free
   `--members` path: 5,896 cases for 3140, parsed from the JPML docket.

Classify each member with `members.py` as today (`cases-entered`, `tag-along`,
and so on), and report cases found by only one source.

**Tier 3 (opt-in):** `caseUpdate` on the lead case with
`pacerOptions.additionalPageArray: [{page: associatedCases, fetchIfOlderThanDays: 30}]`,
followed by the same `relatedCases` read. This is one docket report plus one
page purchase for the whole MDL. It is the cheapest PACER call in the plan and
the first one worth allowing.

### 3. Resolve member `caseId`s (tier 1)

OR together about 40-50 `caseNumber:"..."` terms per `caseSearch` request, with
the court filter (`q` allows 2,000 characters). The spec states no operator
cap for `caseSearch`; the 15-operator cap applies only to master-data
endpoints. **Verify**.

Cases still missing after the search are not in UniCourt. Report them as
`not-in-unicourt`. **Tier 3:** `pacer/importCaseByCourtUsingCaseNumber` (Find
Case is free for district courts, but the result is meta-only) followed by a
paid `caseUpdate`.

### 4. Plaintiffs and counsel (tier 1)

For each member case that UniCourt holds:

- `GET /case/{id}/parties?partyClassification=INDIVIDUAL`: plaintiffs are
  individuals, so this server-side filter replaces the corporate-suffix
  heuristic in `members.py`. `partyRole.partyRoleGroup` gives
  plaintiff/defendant directly.
- `GET /case/{id}/counsel`: `normAttorney` and `normLawFirm` are **normalized
  across cases**, which allows counting cases per firm without fuzzy matching.
  For firm-level totals across the MDL, use
  `GET /caseCountAnalyticsByNormLawFirm`.

If `participantsLastFetchDate` is null or `hasOnlyMetaInfo` is true, UniCourt
has no participants for the case. Fall back to the CourtListener search-index
plaintiff and counsel (tier 2, already implemented). **Tier 3:** `caseUpdate`
with `fetchParticipantsIfOlderThanDays`.

### 5. Complaints from UniCourt's store (tier 1)

1. `GET /case/{id}/documents?repository=UNICOURT&sortBy=oldest to latest`.
   This lists only documents UniCourt already holds. Match the complaint on
   `name` / `description` (the same rule as `core.is_complaint`), or on the
   document of docket entry 1
   (`docketEntries?docketEntryNumber=1` → `docketEntries/primaryDocuments`).
2. `GET /caseDocumentDownload/{caseDocumentId}` returns a signed `fileUrl` with
   an `expiryDate`. Download the file immediately and do not cache the URL.
3. To find complaints held in UniCourt's store without walking every case,
   use a full-text search:
   `caseSearch?q=(CaseDocument:(name:"complaint" AND text:("Depo-Provera")))`.

For the 28 complaints attached to the JPML motions, the CourtListener path
already gets PDFs for free (tier 2). Keep it.

### 6. PACER gap-fill (tier 3, opt-in)

This step runs only with `--allow-pacer`, and in this order, cheapest first:

1. The lead case's Associated Cases page (member list; see step 2).
2. Find Case imports for members missing from UniCourt (free for district
   courts).
3. `caseDocumentOrder` for complaints with `repository: COURT_SOURCE`:
   `{caseDocumentId, isPreviewOnly: false, priorityLevel: "level5", reOrder: false, pacerOptions}`.
   Poll `GET /caseDocumentOrder/callbacks/{id}` until it is `COMPLETE`, then
   download. Check `price` against `--max-spend` first, and order in ascending
   price. Always send `reOrder: false`; `true` buys the document again.
4. `caseUpdate` for member dockets only when parties or the complaint entry
   are missing. This is the most expensive call per case.

Async jobs are polled until `COMPLETE` or `FAILURE`. Timeouts are 5 min for
`level1`, 30 min for `level2` and 24 h for `level5`. The spec also documents a
websocket channel; for a CLI, polling with backoff is simpler.

Documents bought in tier 3 become `repository: UNICOURT` for later runs, so
they are paid for once.

## Cost controls

| Control | Where |
| --- | --- |
| PACER off by default | Tier 3 runs only with `--allow-pacer`, and never beyond `--max-spend` |
| Search before import, and import before update | Steps 3 and 6: `caseSearch` has no PACER fee, and Find Case is free for district courts |
| `fetchIfOlderThanDays` on `associatedCases` | Step 6: avoids re-buying the page on reruns |
| `fetchParticipantsIfOlderThanDays` | Step 6 updates: stops paying for the parties/attorneys page on every update |
| `fetchType: INCREMENTAL` | Only new entries, where the court supports it |
| Check `price` before ordering | Step 6: order in ascending `price` order and stop at the cap |
| `repository == UNICOURT` first | Step 5: documents already in UniCourt's store need no PACER purchase |
| `pacerClientCode` = matter | Reconcile against the PACER invoice |
| `GET /workspace/{ws}/dailyUsage/{date}` | Record usage at the end of every run |

UniCourt also enforces **billing activity limits** per API group (Case View,
Case Document View and others). When a limit is reached, async jobs still
finish, but the response omits the object (`billingActivityLimitReached`). The
client must treat a `COMPLETE` status with a missing object as "fetch later",
not as empty.

**Pilot first.** Run tiers 1 and 2 on about 20 members of MDL 3140 using
`--court flnd --limit 20`, which is the sample already used to validate
plaintiff names, and measure how much UniCourt already holds. Only then price
tier 3 for the remaining gaps. Up to 5,900 docket reports plus 5,900 complaint
orders at PACER rates is a four- to five-figure spend at full scale.

## Client behaviour

Reuse the design of `client.py` (on-disk cache and persistent limiter), with a
UniCourt-specific error map:

Errors arrive two ways. Synchronous calls return them as an HTTP status.
Async jobs (`caseUpdate`, `caseImport`, `caseDocumentOrder`) return **HTTP 200**
with the error in `exception` and `statusDetails`. Every poll must check both.

| Code | Where | Meaning | Action |
| --- | --- | --- | --- |
| `UN400` | HTTP 400 | Invalid input | Fail fast and print `details` |
| `UN203 LIMIT_REACHED` | HTTP 403 or job | Token cap or billing activity limit | Stop the run, and resume after the limit resets |
| `UN402 PAYMENT_REQUIRED` | HTTP 402 | Account blocked (invoice) | Stop the run |
| `UN404` | HTTP 404 or job | Not found | Record the row as missing and continue |
| `UN100 SEALED` | HTTP 451 or job | Sealed case | Record it as sealed and continue |
| `UN103 CURRENTLY_UNAVAILABLE_IN_COURT` | job | Case missing at the court source | Record it and retry on a later run |
| `UN502 ISSUE_AT_THE_COURT_SOURCE`, `UN506 DELAYED_AT_THE_COURT_SOURCE` | job | Court down or slow | Mark the row as pending and retry later |
| `UN503 NOT_ACCEPTING_REQUESTS`, `UN505 BROKEN_INTEGRATION`, `UN504 TIMEOUT` | job | UniCourt integration down or timeout | Back off and retry, then mark the row as pending |
| `UN501 FEATURE_NOT_SUPPORTED` | job | Option not supported for this court | Drop the option and continue |
| `UN500` | job | Internal error | Retry with backoff |

`statusDetails.issueSource` (`INTERNAL`, `COURT` or `CLIENT`) tells whether a
retry can help: `CLIENT` never recovers without a change to the request.

UniCourt's rate limit is **30 requests per 5 seconds** per account (counted
per endpoint as well). Beyond it the API answers HTTP 429, or a body of
`{"code": "UN429"}` / `{"message": "Too Many Requests"}`. Rate-limited calls are
not billable. `unicourt_state` keeps every call under the limit with one shared
limiter and pauses all workers on a 429.

Caching rules:
- Cache GET responses by URL, as today.
- **Never cache** `caseUpdate`, `caseDocumentOrder` or callback polls, or
  signed `fileUrl`s.
- Persist async job ids (`caseDocumentOrderCallbackId`, `caseId` for updates)
  to a state file. A killed run can then resume polling without paying for a
  second order. This follows the existing `--out` checkpoint pattern.

## Output mapping

| Current field (`MemberCase` / `Complaint`) | UniCourt source |
| --- | --- |
| `case_number` | `RelatedCase.caseNumber` |
| `title` | `RelatedCase.caseName` or `Case.caseName` |
| `source` (cases-entered, CTO, ...) | Keep the JPML-text classification; add `unicourt_relationship` |
| `plaintiffs` | `parties`, where `partyRoleGroup` is plaintiff and `partyClassification` is `INDIVIDUAL` |
| `counsel`, `firms` | `counsel[].normAttorney.normAttorneyName` and `normLawFirm` |
| `origin_state` | Unchanged; optionally `party.contact.addressArray[].stateCode` when present |
| `pdf_url` | Downloaded file path (never the expiring `fileUrl`) |
| *new* `unicourt_case_id`, `document_price`, `document_status` | For auditing and resuming runs |

## Suggested implementation shape

- `mdl_complaints/unicourt.py`: a `UniCourtClient` that handles the bearer
  token, workspace prefix, error map, pagination via `nextPageAPI`, and an async
  `wait_for(job)` poller.
- CLI: a `--source {courtlistener,unicourt}` flag. PACER is off unless
  `--allow-pacer` is given, together with `--pacer-user`, `--client-code` and
  `--max-spend`. Credentials come from `UNICOURT_CLIENT_ID` /
  `UNICOURT_CLIENT_SECRET` (the token is created and stored automatically),
  `UNICOURT_WORKSPACE`, and `PACER_USER_ID` for tier 3.
- Tests: fixtures cut from the spec's own response examples
  (`CaseApiRelatedCasesResponse`, `CaseApiPartiesResponse`, and others), so the
  suite stays offline.

## To verify in the pilot

1. **Coverage:** for the 20-case sample, how many members UniCourt already
   holds, how many have participants, and how many complaints are in its store
   (`repository: UNICOURT`). This decides how much tier 3 is needed at all.
2. Whether the lead case already has `relatedCases` without a PACER pull, and
   whether `Court:(type:Federal)` is accepted in `caseSearch`.
3. How UniCourt bills tier-1 reads and downloads of `UNICOURT` documents.
4. Which `caseRelationshipType` name MDL member rows carry, and whether the
   lead case's Associated Cases page lists all ~5,900 members or only
   transferred ones.
5. The court name format for `caseSearch` `Court:(...)` filters, and whether an
   OR of 40+ case numbers is accepted.
6. How often `relatedCases.caseId` is null for MDL 3140 members, since this
   drives import and update cost.
7. Whether member dockets carry plaintiff addresses (possible residence data).
8. Actual per-case PACER cost for a docket update and a complaint order.
9. ~~The API rate limit~~: 30 requests per 5 seconds per account (now handled).
