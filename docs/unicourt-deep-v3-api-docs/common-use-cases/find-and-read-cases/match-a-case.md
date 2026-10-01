---
title: "Match a Case"
source: https://dart.unicourt.com/res-deep/assets/deep-v3-api-doc/common-use-cases/find-and-read-cases/match-a-case/
retrieved: 2026-10-01
---

# Match a Case

Map an external matter—CMS record, spreadsheet row, or partner feed—to the correct UniCourt **`caseId`** when your identifiers are incomplete, inconsistently formatted, or partially wrong.

Use **Case Match** when you are trying to find a case from imperfect data and resolve to UniCourt’s standardized version. Use [Case Search](../../knowledge-base/case-search.md) when you need a list of cases that meet certain criteria, or already confidently know key identifying information about a single case.

**Reference docs:** [Case Match](../../knowledge-base/case-match.md) (request/response, scoring), [Case Search](../../knowledge-base/case-search.md), [Resolve master data](../../common-use-cases/find-and-read-cases/resolve-master-data.md) (court and type IDs).

Not PACER Case Locator

Case Match finds cases in **UniCourt** from attributes you supply. To search **PACER**, use [PACER Case Locator](../../knowledge-base/pacer-api.md#pacer-case-locator-pcl).

## Before you start

You need:

- A **workspace ID** (`workspaceId`)
- A **workspace-scoped JWT** from `POST /generateNewWorkspaceToken` (see [Authentication](../../getting-started/authentication.md))
- Whatever case attributes you have (case number, caption, court, filing date, parties, counsel, and so on)

Send the token on every request:

```http
Authorization: Bearer <Your JWT accessToken>
```

Base URL: **`https://deep-api.unicourt.com`**.

## Step 1 — Gather the best input you can

More reliable fields produce clearer winners. Prefer:

1. **Case number** (strongest signal)
2. **Party names**
3. **Case name, filing date, court** (IDs when possible), **state**, attorney/judge names, and contact details

Tips:

- Include **state** even when court text looks unambiguous (abbreviations like “CA” are easy to misread).
- Prefer **`courtId` / `courtSystemId`** over free-text `courtNL` when you can resolve them—see [Resolve master data](../../common-use-cases/find-and-read-cases/resolve-master-data.md).
- Tighten filing-date tolerance when you trust the date (`matchingCriteria.filedDate` with a smaller `numberOfDays`).

## Step 2 — Call Case Match

**POST** [**/workspace/{workspaceId}/caseMatch**](#):

Match from partial matter data

```Shell
curl -X 'POST' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/caseMatch' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>' \  -H 'Content-Type: application/json' \  -d '{  "caseMatchInput": {    "caseNumber": "C14-01841",    "caseName": "GEMENES VS WEM PACIFIC INVESTMENT",    "filedDate": "2013-09-06",    "state": "California",    "court": {      "courtNL": "Contra Costa County Superior Court"    },    "parties": [      { "name": "GEMENES" }    ]  },  "matchingCriteria": {    "filedDate": {      "comparison": "greaterOrLessThan",      "numberOfDays": 90    }  }}'
```

A successful call returns **`200 OK`** with a **`CaseMatchResponse`**. Results are ranked; the array holds at most **10** candidates.

## Step 3 — Read scores and matched fields

Each `LocatedCase` includes:

| Field | Use it to… |
| --- | --- |
| `case.caseId` / `case.caseAPI` | Open or store the UniCourt case |
| `confidenceScore` | Decide auto-accept vs review (weighted importance of matching fields) |
| `similarityScore` | See how much of your input overlapped |
| `case.matchedObjectArray` | Debug which attributes matched and at what field-level score |

Low similarity with high confidence often means a strong identifier (usually case number) matched while weaker fields did not—frequently still the correct case. See [Similarity and confidence scores](../../knowledge-base/case-match.md#similarity-and-confidence-scores).

## Step 4 — Apply tiered decision logic

Do not use a single accept/reject cutoff. A practical pattern:

| Condition | Action |
| --- | --- |
| `confidenceScore` ≥ **0.85** (optionally also `similarityScore` ≥ **0.75**) | **Auto-accept** the top result |
| `confidenceScore` **0.60–0.84** | **Manual review** of the top few results |
| `confidenceScore` < **0.60** | **Verify inputs** or treat as unresolved |
| Top result ≥ **0.75** confidence **and** gap to #2 ≥ **0.15** | Strong single winner—safe to auto-accept even if similarity is only moderate |
| `totalLocatedCases` = **0** | Case may be outside UniCourt coverage, not yet ingested, or inputs too far off—fix case number and court before manual research |

Tune thresholds on your own data. Target a low false-positive rate (for example under ~5%) on a labeled sample before enabling auto-accept in production.

Example decision sketch

```text
if totalLocatedCases == 0 → escalate / verify inputselse if top.confidence >= 0.85 (and optionally top.similarity >= 0.75) → accept top.caseIdelse if top.confidence >= 0.75 and (top.confidence - second.confidence) >= 0.15 → accept top.caseIdelse if top.confidence >= 0.60 → queue manual review (show top 5)else → reject / research
```

Filter very low-confidence long-tail hits client-side if you only care about actionable candidates (for example ignore below 0.60 when presenting a review queue).

## Step 5 — Debug weak or surprising results

When scores look wrong:

1. Inspect **`matchedObjectArray`** — which fields hit, and which did not?
2. Check court and state — wrong court system is a common cause of many mid-confidence hits.
3. Try a cleaner case number or known court ID and re-run.
4. Narrow **`matchingCriteria.filedDate.numberOfDays`** if dates are reliable; widen only when dates are noisy.

Abbreviated numbers (for example `C14-01841` vs `MSC14-01841`) are expected to fuzzy-match; confirm via the case-number entry in `matchedObjectArray`.

## Next step

Once you have a **`caseId`**, continue to [Read a full case](../../common-use-cases/find-and-read-cases/read-a-full-case.md), or keep it current with [Update a case once](../../common-use-cases/keep-cases-current/update-a-case-once.md) / [Track a case on a schedule](../../common-use-cases/keep-cases-current/track-a-case-on-a-schedule.md).
