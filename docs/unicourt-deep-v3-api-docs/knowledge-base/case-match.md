---
title: "Case Match"
source: https://dart.unicourt.com/res-deep/assets/deep-v3-api-doc/knowledge-base/case-match/
retrieved: 2026-10-01
---

# Case Match

The Case Match API fuzzy-matches imperfect case identifiers—incomplete case numbers, inconsistent court names, partial captions—to UniCourt cases. Unlike [Case Search](../knowledge-base/case-search.md), which filters with exact keyword expressions, Case Match normalizes inputs, scores candidates, and returns ranked results with **similarity** and **confidence** scores so you can decide which match to accept.

Not PACER Case Locator

**Case Match** (v2 name: **Case Locator**, `POST /caseLocator`) matches *your* case attributes to UniCourt holdings. It is distinct from **PACER Case Locator (PCL)**, which searches PACER itself—see [PACER API](../knowledge-base/pacer-api.md#pacer-case-locator-pcl).

See [Match a case](../common-use-cases/find-and-read-cases/match-a-case.md) for a walkthrough with thresholds and decision logic. Matched results include `caseId` values prefixed `CASE`—see [Object ID Prefixes](../knowledge-base/object-id-prefixes.md).

## Endpoints

| Method | Path | Description |
| --- | --- | --- |
| POST | `/workspace/{workspaceId}/caseMatch` | Locate UniCourt cases from partial or noisy input (`matchCase`) |

## Submitting a case match

Submit a **POST** to [**/workspace/{workspaceId}/caseMatch**](#). The flow:

1. Send whatever case attributes you have under `caseMatchInput` (and optional `matchingCriteria` for filing-date tolerance).
2. Receive a `CaseMatchResponse` with up to **10** ranked `LocatedCase` results.
3. Inspect `confidenceScore`, `similarityScore`, and `matchedObjectArray` to accept, review, or reject each candidate.

Provide at least one input field. Requests with no usable parameters return `400` / `INVALID_INPUT`.

### Request fields

The body has two top-level objects:

| Field | Required | Description |
| --- | --- | --- |
| `caseMatchInput` | Yes (with at least one attribute) | Case attributes to match against UniCourt data. |
| `matchingCriteria` | No | Filing-date comparison rules (see [Matching criteria](#matching-criteria)). |

#### `caseMatchInput`

| Field | Description |
| --- | --- |
| `caseNumber` | Docket / case number (fuzzy matching tolerates missing prefixes and formatting variants). |
| `caseName` | Case caption or style. |
| `filedDate` | Filing date (`YYYY-MM-DD`). Pair with `matchingCriteria.filedDate` for range tolerance. |
| `caseType` | Master-data IDs (`caseClassIdArray`, `areaOfLawIdArray`, `caseTypeGroupIdArray`, `caseTypeArray`) and/or natural-language `caseTypeNL`. |
| `caseStatus` | Master-data IDs (`caseStatusIdArray`, `caseStatusGroupIdArray`) and/or `caseStatusNL`. |
| `court` | Master-data IDs (`courtTypeIdArray`, `courtSystemIdArray`, `courtIdArray`) and/or natural-language `courtNL` (for example, `"California Superior Court Contra Costa County"`). |
| `county` | County name. |
| `state` | State name (helps disambiguate court text and abbreviations). |
| `parties` | Array of party objects: `name`, optional `partyRole` (IDs or `partyRoleNL`), and optional contact arrays (`emailIdArray`, `phoneNumberArray`, `addressArray`). |
| `attorneys` | Array of attorney objects: `name`, optional `barNumber`, and optional contact arrays. |
| `judges` | Array of judge objects: `name` and optional `addressArray`. |
| `lawFirms` | Array of law firm objects: `name` and optional contact arrays. |

Master-data IDs are more precise than natural-language (`*NL`) fields. Resolve IDs with [Resolve master data](../common-use-cases/find-and-read-cases/resolve-master-data.md) when you can.

Case match request

```Shell
curl -X 'POST' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/caseMatch' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>' \  -H 'Content-Type: application/json' \  -d '{  "caseMatchInput": {    "caseNumber": "MSC13-01945",    "caseName": "GEMENES VS WEM PACIFIC INVESTMENT",    "filedDate": "2013-09-06",    "state": "California",    "court": {      "courtNL": "Contra Costa County Superior Court"    },    "parties": [      { "name": "GEMENES" }    ],    "attorneys": [      { "name": "CARLSON, MARK C" }    ]  },  "matchingCriteria": {    "filedDate": {      "comparison": "greaterOrLessThan",      "numberOfDays": 30    }  }}'
```

### Matching criteria

Optional `matchingCriteria.filedDate` controls how `caseMatchInput.filedDate` is compared:

| Field | Description |
| --- | --- |
| `comparison` | `exact`, `lessThan`, `greaterThan`, or `greaterOrLessThan` (within ± `numberOfDays`). |
| `numberOfDays` | Day window for non-exact comparisons. |

When `matchingCriteria` is present, both `comparison` and `numberOfDays` are required. Invalid values return `400` / `INVALID_INPUT`.

### Response: CaseMatchResponse

Case match response (excerpt)

```json
{  "object": "CaseMatchResponse",  "caseMatchResultArray": [    {      "object": "LocatedCase",      "case": {        "object": "CaseMatchResult",        "caseId": "CASEag154a302cb8c4",        "caseNumber": "MSC13-01945",        "caseName": "GEMENES VS WEM PACIFIC INVESTMENT, INC.",        "filedDate": "2013-09-06T00:00:00+00:00",        "caseAPI": "/case/CASEag154a302cb8c4/",        "matchedObjectArray": [          {            "object": "CaseMatchedObject",            "inputValue": "MSC13-01945",            "matchedObjectAttribute": "caseNumber",            "highlightSnippet": "<b>MSC13-01945</b>",            "similarityScore": 1,            "matchedObjectAPI": "/case/CASEag154a302cb8c4/",            "additionalData": null          }        ]      },      "similarityScore": 1,      "confidenceScore": 1    }  ],  "totalLocatedCases": 1}
```

| Field | Description |
| --- | --- |
| `caseMatchResultArray` | Ranked located cases (0–10). Each item is a `LocatedCase`. |
| `totalLocatedCases` | Number of located cases returned. |

#### `LocatedCase`

| Field | Description |
| --- | --- |
| `case` | `CaseMatchResult` preview: identifiers, court, type/status, fetch dates, `caseAPI`, and `matchedObjectArray`. |
| `similarityScore` | Unweighted average of field-level match scores (0.0–1.0). |
| `confidenceScore` | Weighted average emphasizing stronger identifiers (0.0–1.0). |

#### `matchedObjectArray`

Each `CaseMatchedObject` explains one field-level match:

| Field | Description |
| --- | --- |
| `inputValue` | Value you provided for that attribute. |
| `matchedObjectAttribute` | Attribute that matched (for example `caseNumber`, `caseName`, `name`). |
| `matchedObjectId` / `matchedObjectName` | Matched entity (case, party, attorney, judge, and so on). |
| `highlightSnippet` | HTML snippet showing the matched text. |
| `similarityScore` | Field-level similarity for this attribute (0.0–1.0). |
| `matchedObjectAPI` | Relative API path for the matched object when available. |
| `additionalData` | Extra context (for example party role) when present. |

Use `matchedObjectArray` to debug unexpected scores—see which fields matched, partially matched, or did not contribute.

## Similarity and confidence scores

Case Match exposes two scores on every `LocatedCase`. They answer different questions:

| Score | Question it answers | How it is calculated |
| --- | --- | --- |
| **Similarity** | How much of my input overlapped with this case? | Simple average of field-level scores: `(sum of field scores) / (number of input fields provided)`. Unmatched provided fields contribute `0`. |
| **Confidence** | How strong is this match, given which fields hit? | Weighted average: more important identifiers contribute more than weaker ones. |

**Critical insight:** Low similarity with high confidence is common and often correct—for example, only the case number matched among several inputs. High similarity with lower confidence can occur when weaker fields matched but a strong identifier (such as case number) did not.

### Field importance (highest to lowest)

Exact numeric weights are not published. Relative importance for confidence scoring:

1. **Case number** — strongest identifier
2. **Party name** — highly distinctive when combined with court context
3. **Case name, filed date, court system, court ID, state, party role group, attorney name, judge name, and contact details** (email, phone, address) — moderate identifiers
4. **Court type** — weakest of the weighted court fields

Include every reliable field you have. Extra context improves disambiguation even when some fields score low.

### Field-level scoring (conceptual)

Individual attributes in `matchedObjectArray` use type-specific rules:

- **Case number** — Exact matches score highest; known aliases, punctuation-stripped forms, and segment-style matches (seed / year / residual) score progressively lower.
- **Name fields** (case name, party, attorney, judge) — Exact text scores highest; partial word overlap and subset matches score lower.
- **Filing date** — Exact match, or within the configured `matchingCriteria` window, scores as a full match; outside the window scores as no match.
- **Master-data and contact fields** (court IDs, case type/status IDs, state, email, phone, address) — Exact match or no match (no partial credit).

## Case Match vs Case Search

| Use… | When… |
| --- | --- |
| **Case Match** | You are trying to find a case from imperfect data—fuzzy-match your inputs against UniCourt’s holdings to resolve to the standardized, cleaned version of the case. |
| **Case Search** | You need a list of cases that meet certain criteria, or you already confidently know key identifying information about a single case and want exact keyword filters with sorting and pagination. |

## Errors

| Condition | Typical response |
| --- | --- |
| No input parameters | `400` — `INVALID_INPUT` (“provide at least one parameter”) |
| Invalid `filedDate` format | `400` — `INVALID_INPUT` (expect `YYYY-MM-DD`) |
| Invalid `matchingCriteria` | `400` — `INVALID_INPUT` (valid `comparison` and `numberOfDays` required) |

See [General Error Codes](../knowledge-base/general-error-codes.md), [Error Management](../knowledge-base/error-codes.md), and [HTTP response codes](../knowledge-base/glossary-of-HTTP-response-codes.md).

## Migration Notes for v2 Integrators

In v2 this feature was named **Case Locator** (`POST /caseLocator`). Behavior is the same idea—fuzzy-match your records to UniCourt cases—but paths, payload wrappers, and response type names changed in v3.

| v2 | v3 | Notes |
| --- | --- | --- |
| `POST /caseLocator` | `POST /workspace/{workspaceId}/caseMatch` | Workspace-scoped on `deep-api.unicourt.com` |
| Request body fields at root | Wrapped in `caseMatchInput` | Court / type / status also support `*NL` natural-language fields |
| Filing-date range config (v2-specific) | `matchingCriteria.filedDate` (`comparison` + `numberOfDays`) | See [Matching criteria](#matching-criteria) |
| `CaseLocatorResponse` / `caseLocatorResultArray` | `CaseMatchResponse` / `caseMatchResultArray` | Items are `LocatedCase` with nested `CaseMatchResult` |
| Up to 30 results (v2 product docs) | Up to **10** results (`caseMatchResultArray` maximum in the v3 schema) | Apply client-side confidence filtering as needed |
| `https://enterpriseapi.unicourt.com/…` | `https://deep-api.unicourt.com/workspace/{workspaceId}/…` | Base URL and workspace prefix |

Do not confuse this migration with PACER Case Locator paths (`/pacerCaseLocator/…`), which remain a separate PACER search surface.
